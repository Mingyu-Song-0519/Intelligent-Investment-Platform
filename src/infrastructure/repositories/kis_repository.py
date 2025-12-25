"""
KIS Repository - Infrastructure Layer
IKISRepository 인터페이스의 한국투자증권 구현체
"""
import requests
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict

from src.domain.repositories.interfaces import IKISRepository


class KISRepository(IKISRepository):
    """
    한국투자증권 OpenAPI를 이용한 Repository 구현체
    
    기존 KisApi 클래스의 로직 이관
    """
    
    URL_REAL = "https://openapi.koreainvestment.com:9443"
    URL_VIRTUAL = "https://openapivts.koreainvestment.com:29443"
    
    def __init__(self, app_key: str, app_secret: str, account_no: str = "", is_virtual: bool = True):
        """
        Args:
            app_key: 앱 키
            app_secret: 앱 시크릿
            account_no: 계좌번호 (옵션) "12345678-01" 형식
            is_virtual: 모의투자 여부
        """
        self.app_key = app_key
        self.app_secret = app_secret
        self.account_no = account_no
        self.is_virtual = is_virtual
        self.base_url = self.URL_VIRTUAL if is_virtual else self.URL_REAL
        
        self.access_token = None
        self.token_expired = None
        
        # 계좌번호 분리
        if '-' in account_no:
            self.cano, self.acnt_prdt_cd = account_no.split('-')
        elif len(account_no) >= 8:
            self.cano = account_no[:8]
            self.acnt_prdt_cd = account_no[8:]
        else:
            self.cano = ""
            self.acnt_prdt_cd = ""
        
        # 토큰 파일 경로
        PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
        self.token_file = PROJECT_ROOT / "kis_token.json"
        self._load_token()
    
    def _load_token(self):
        """토큰 파일에서 로드"""
        try:
            if self.token_file.exists():
                with open(self.token_file, 'r') as f:
                    data = json.load(f)
                    expired = datetime.fromisoformat(data['expired'])
                    if datetime.now() < expired:
                        self.access_token = data['token']
                        self.token_expired = expired
        except Exception as e:
            print(f"[WARNING] 토큰 로드 실패: {e}")
    
    def _save_token(self):
        """토큰 파일 저장"""
        try:
            data = {
                'token': self.access_token,
                'expired': self.token_expired.isoformat()
            }
            with open(self.token_file, 'w') as f:
                json.dump(data, f)
        except Exception as e:
            print(f"[WARNING] 토큰 저장 실패: {e}")
    
    def authenticate(self, app_key: str, app_secret: str) -> Optional[str]:
        """OAuth 토큰 발급"""
        # 기존 토큰이 있고 유효하면 반환
        if self.access_token and self.token_expired and datetime.now() < self.token_expired:
            return self.access_token
        
        path = "/oauth2/tokenP"
        url = f"{self.base_url}{path}"
        
        headers = {"content-type": "application/json"}
        body = {
            "grant_type": "client_credentials",
            "appkey": app_key or self.app_key,
            "appsecret": app_secret or self.app_secret
        }
        
        try:
            res = requests.post(url, headers=headers, data=json.dumps(body))
            res.raise_for_status()
            data = res.json()
            
            self.access_token = data['access_token']
            self.token_expired = datetime.now() + timedelta(hours=12)
            
            print(f"[INFO] KIS Access Token 발급 성공")
            self._save_token()
            
            return self.access_token
            
        except Exception as e:
            print(f"[ERROR] KIS Access Token 발급 실패: {e}")
            return None
    
    def get_realtime_price(self, ticker: str) -> Optional[Dict]:
        """실시간 시세 조회"""
        if not self.is_authenticated():
            self.authenticate(self.app_key, self.app_secret)
        
        path = "/uapi/domestic-stock/v1/quotations/inquire-price"
        url = f"{self.base_url}{path}"
        
        headers = {
            "content-type": "application/json",
            "authorization": f"Bearer {self.access_token}",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
            "tr_id": "FHKST01010100"
        }
        
        params = {
            "fid_cond_mrkt_div_code": "J",
            "fid_input_iscd": ticker
        }
        
        try:
            res = requests.get(url, headers=headers, params=params)
            res.raise_for_status()
            data = res.json()
            
            if data['rt_cd'] != '0':
                print(f"[ERROR] API 호출 오류: {data.get('msg1', '')}")
                return None
            
            output = data['output']
            return {
                'price': int(output['stck_prpr']),
                'change': int(output['prdy_vrss']),
                'change_rate': float(output['prdy_ctrt']),
                'volume': int(output['acml_vol']),
                'high': int(output['stck_hgpr']),
                'low': int(output['stck_lwpr']),
                'open': int(output['stck_oprc']),
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"[ERROR] 실시간 시세 조회 실패 ({ticker}): {e}")
            return None
    
    def get_orderbook(self, ticker: str) -> Optional[Dict]:
        """호가 정보 조회"""
        if not self.is_authenticated():
            self.authenticate(self.app_key, self.app_secret)
        
        path = "/uapi/domestic-stock/v1/quotations/inquire-asking-price-exp-ccn"
        url = f"{self.base_url}{path}"
        
        headers = {
            "content-type": "application/json",
            "authorization": f"Bearer {self.access_token}",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
            "tr_id": "FHKST01010200"
        }
        
        params = {
            "fid_cond_mrkt_div_code": "J",
            "fid_input_iscd": ticker
        }
        
        try:
            res = requests.get(url, headers=headers, params=params)
            res.raise_for_status()
            data = res.json()
            output1 = data['output1']
            
            ask = []
            bid = []
            
            for i in range(1, 11):
                ask.append((
                    int(output1[f'askp{i}']),
                    int(output1[f'askp_rsqn{i}'])
                ))
                bid.append((
                    int(output1[f'bidp{i}']),
                    int(output1[f'bidp_rsqn{i}'])
                ))
            
            return {
                'ask': ask,  # [(가격, 잔량), ...]
                'bid': bid,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"[ERROR] 호가 조회 실패 ({ticker}): {e}")
            return None
    
    def create_order(
        self, 
        ticker: str, 
        side: str,
        quantity: int, 
        price: Optional[float] = None,
        order_type: str = "LIMIT"
    ) -> Optional[Dict]:
        """주문 생성"""
        # TODO: KIS 주문 API 구현
        print(f"[WARNING] KIS 주문 기능은 아직 구현되지 않았습니다.")
        return None
    
    def get_balance(self) -> Optional[Dict]:
        """계좌 잔고 조회"""
        # TODO: KIS 잔고 조회 API 구현
        print(f"[WARNING] KIS 잔고 조회 기능은 아직 구현되지 않았습니다.")
        return None
    
    def is_authenticated(self) -> bool:
        """인증 상태 확인"""
        if not self.access_token:
            return False
        if not self.token_expired:
            return False
        return datetime.now() < self.token_expired
