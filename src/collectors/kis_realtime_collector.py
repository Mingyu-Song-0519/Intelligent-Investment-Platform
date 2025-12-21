"""
한국투자증권 실시간 데이터 수집 모듈 (WebSocket 직접 구현)
websockets 라이브러리 사용
"""
import asyncio
import json
import logging
import time
from typing import Dict, Optional, Callable, List
from pathlib import Path
import sys
from datetime import datetime
import os
import requests

try:
    import websockets
except ImportError:
    print("[ERROR] websockets 라이브러리가 필요합니다: pip install websockets")
    sys.exit(1)

# 프로젝트 루트 경로 설정
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# KIS REST API 모듈 사용
try:
    from src.collectors.kis_api import KisApi
except ImportError:
    sys.path.insert(0, str(Path(__file__).parent))
    from kis_api import KisApi

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class KISRealtimeCollector:
    """한국투자증권 실시간 데이터 수집기 (WebSocket 직접 구현)"""
    
    # 실전/모의 WebSocket URL
    WS_URL_REAL = "ws://ops.koreainvestment.com:21000"
    WS_URL_VIRTUAL = "ws://ops.koreainvestment.com:31000"
    
    def __init__(
        self,
        app_key: str,
        app_secret: str,
        account_no: str,
        is_virtual: bool = True
    ):
        self.app_key = app_key
        self.app_secret = app_secret
        self.account_no = account_no
        self.is_virtual = is_virtual
        self.base_url = self.WS_URL_VIRTUAL if is_virtual else self.WS_URL_REAL
        
        # REST API 클라이언트 (토큰 및 접속키 발급용)
        self.api = KisApi(app_key, app_secret, account_no, is_virtual)
        self.approval_key = None
        
        # 관리 변수
        self.ws = None
        self.running = False
        self.subscribed_tickers = set()
        
        # 콜백 함수
        self.price_callback: Optional[Callable] = None
        self.quote_callback: Optional[Callable] = None
        
        # 최근 데이터
        self.latest_prices = {}
        self.latest_prices = {}
        self.latest_quotes = {}

    def get_current_price(self, ticker: str) -> Dict:
        """현재가 조회 (REST API)"""
        return self.api.get_current_price(ticker)
    
    def get_orderbook(self, ticker: str) -> Dict:
        """호가 조회 (REST API)"""
        return self.api.get_orderbook(ticker)

    def _get_approval_key(self):
        """실시간 접속키 발급 (REST API)"""
        if self.approval_key is None:
            self.approval_key = self.api.get_approval_key()
            logger.info(f"Approval Key 발급 완료: {self.approval_key[:10]}...")
        return self.approval_key

    async def connect(self):
        """WebSocket 연결 (비동기)"""
        url = f"{self.base_url}/tryitout/H0STCNT0"
        logger.info(f"WebSocket 연결 시도: {url}")
        
        self.running = True
        try:
            async with websockets.connect(url) as websocket:
                self.ws = websocket
                logger.info("WebSocket 연결 성공")
                
                # 구독된 종목 다시 구독 (재연결 시)
                for ticker in self.subscribed_tickers:
                    await self._send_subscription(websocket, ticker, 'H0STCNT0') # 체결가
                
                # 메시지 수신 루프
                while self.running:
                    try:
                        message = await websocket.recv()
                        self._handle_message(message)
                    except websockets.exceptions.ConnectionClosed:
                        logger.warning("WebSocket 연결 끊김 -> 재연결 시도")
                        break
                    except Exception as e:
                        logger.error(f"메시지 수신 오류: {e}")
                        
        except Exception as e:
            logger.error(f"WebSocket 연결 실패: {e}")
            self.running = False

    async def _send_subscription(self, ws, ticker, tr_id, tr_type='1'):
        """구독 요청 전송"""
        approval_key = self._get_approval_key()
        
        data = {
            "header": {
                "approval_key": approval_key,
                "custtype": "P",
                "tr_type": tr_type, # 1: 등록, 2: 해제
                "content-type": "utf-8"
            },
            "body": {
                "input": {
                    "tr_id": tr_id, 
                    "tr_key": ticker
                }
            }
        }
        
        await ws.send(json.dumps(data))
        logger.info(f"구독 요청 전송: {ticker} (TR: {tr_id})")

    def _handle_message(self, message):
        """수신된 데이터 처리"""
        try:
            # 첫 글자가 0 또는 1이면 실시간 데이터
            if message[0] in ('0', '1'):
                parts = message.split('|')
                if len(parts) < 4:
                    return
                
                tr_id = parts[1]
                data_cnt = int(parts[2])
                data_body = parts[3]
                
                # 데이터 파싱
                rows = data_body.split('^')  # 여러 건일 경우 ^로 구분
                
                if tr_id == 'H0STCNT0': # 모의/실전 주식 체결가
                    self._parse_price(rows[0])
                elif tr_id == 'H0STASP0': # 주식 호가
                    self._parse_quote(rows[0])
                    
            else:
                # 일반 메시지 (JSON)
                data = json.loads(message)
                if 'header' in data and data['header']['tr_id'] == 'PINGPONG':
                    pass  # PINGPONG은 무시
                else:
                    logger.info(f"수신 메시지: {data}")

        except Exception as e:
            logger.error(f"데이터 처리 오류: {e}")
            # logger.error(f"원본 메시지: {message}")

    def _parse_price(self, row):
        """체결가 데이터 파싱"""
        cols = row.split('^')
        if len(cols) < 13:
            return
            
        ticker = cols[0]
        price = int(cols[2])
        change_rate = float(cols[4])
        volume = int(cols[13])
        
        parsed = {
            'ticker': ticker,
            'price': price,
            'change': int(cols[3]),
            'change_rate': change_rate,
            'volume': volume,
            'timestamp': datetime.now()
        }
        
        self.latest_prices[ticker] = parsed
        if self.price_callback:
            self.price_callback(parsed)
            
        # logger.info(f"[체결] {ticker}: {price:,}원 ({change_rate}%)")

    def _parse_quote(self, row):
        """호가 데이터 파싱"""
        # 호가 파싱 로직 구현 필요
        # 데이터 포맷이 매우 길어서 필요한 부분만 추출해야 함
        pass

    async def start(self):
        """수집 시작 (비동기)"""
        await self.connect()

    def subscribe(self, ticker):
        """종목 구독 추가"""
        self.subscribed_tickers.add(ticker)


# 사용 예시 (비동기 실행 필요)
if __name__ == "__main__":
    from dotenv import load_dotenv
    
    # 로깅 레벨 설정
    logging.basicConfig(level=logging.INFO)
    
    print("=== 한국투자증권 실시간 데이터 (WebSocket) 테스트 ===\n")
    
    # 환경변수 로드
    env_path = PROJECT_ROOT / ".env"
    if env_path.exists():
        load_dotenv(env_path)
    
    APP_KEY = os.getenv("KIS_APP_KEY")
    APP_SECRET = os.getenv("KIS_APP_SECRET")
    ACCOUNT_NO = os.getenv("KIS_ACCOUNT_NO")
    IS_VIRTUAL = os.getenv("KIS_IS_VIRTUAL", "True").lower() == "true"
    
    if not all([APP_KEY, APP_SECRET, ACCOUNT_NO]):
        print("[ERROR] .env 파일 설정 필요")
        exit(1)
        
    collector = KISRealtimeCollector(APP_KEY, APP_SECRET, ACCOUNT_NO, IS_VIRTUAL)
    
    # 콜백 정의
    def on_price(data):
        print(f"[실시간] {data['ticker']}: {data['price']:,}원 ({data['change_rate']}%)")
    
    collector.price_callback = on_price
    collector.subscribe("005930") # 삼성전자
    
    # 비동기 실행
    try:
        asyncio.run(collector.start())
    except KeyboardInterrupt:
        print("종료")
