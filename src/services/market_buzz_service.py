"""
Market Buzz Service - Application Layer
시장 관심도 분석 핵심 비즈니스 로직

Features:
- Buzz Score 계산 (거래량 + 변동성 기반)
- Volume Anomaly 감지 (동적 threshold 지원)
- Sector Heatmap 생성
- Graceful Degradation (API 실패 시 대응)
- Hybrid 캐싱 전략 (실시간/배치)
"""
import logging
import numpy as np
import pandas as pd
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from src.domain.market_buzz.entities.buzz_score import BuzzScore
from src.domain.market_buzz.entities.volume_anomaly import VolumeAnomaly
from src.domain.market_buzz.entities.sector_heat import SectorHeat
from src.domain.market_buzz.value_objects.heat_level import HeatLevel
from src.infrastructure.repositories.sector_repository import SectorRepository
from src.collectors.stock_collector import StockDataCollector

logger = logging.getLogger(__name__)


class MarketBuzzService:
    """
    시장 관심도 분석 서비스
    
    캐싱 전략 (Hybrid):
    - force_refresh=False: 1시간 캐시 사용
    - force_refresh=True: 실시간 재계산
    """
    
    def __init__(self, sector_repo: SectorRepository):
        """
        Args:
            sector_repo: 섹터 저장소 (DI)
        """
        self.sector_repo = sector_repo
        self.collector = StockDataCollector()
        
        # 캐싱
        self._cache: Dict[str, tuple] = {}  # {key: (data, timestamp)}
        self._cache_ttl = 3600  # 1시간
        
        # 종목명 캐시 (API 호출 최소화)
        self._name_cache: Dict[str, str] = {}
        
        # 조회 실패 종목 추적
        self._failed_tickers: List[str] = []
    
    def get_failed_tickers(self) -> List[str]:
        """조회 실패한 종목 리스트 반환"""
        return self._failed_tickers.copy()
    
    def clear_failed_tickers(self):
        """실패 종목 리스트 초기화"""
        self._failed_tickers.clear()
    
    def _get_stock_name(self, ticker: str) -> str:
        """
        종목명 조회 (캐싱 + 다중 폴백)
        
        순서:
        1. 캐시 확인
        2. yfinance shortName/longName
        3. 티커에서 추출 (예: "005930.KS" -> "삼성전자")
        4. 그냥 티커 반환
        """
        # 1. 캐시 확인
        if ticker in self._name_cache:
            return self._name_cache[ticker]
        
        name = ticker  # 기본값
        
        try:
            # 2. yfinance 시도
            import yfinance as yf
            stock = yf.Ticker(ticker)
            info = stock.info
            
            # shortName 우선 (더 짧고 읽기 쉬움)
            name = info.get('shortName') or info.get('longName') or ticker
            
            # 이상한 이름 처리 (예: "N/A", "None" 등)
            if name in ['N/A', 'None', '', None] or name == ticker:
                # 한국 주식의 경우 KRX에서 이름 조회 시도
                if '.KS' in ticker or '.KQ' in ticker:
                    name = self._get_kr_stock_name(ticker)
                    
        except Exception as e:
            logger.debug(f"[StockName] yfinance failed for {ticker}: {e}")
            # 한국 주식 폴백
            if '.KS' in ticker or '.KQ' in ticker:
                name = self._get_kr_stock_name(ticker)
        
        # 캐싱
        self._name_cache[ticker] = name
        return name
    
    def _get_kr_stock_name(self, ticker: str) -> str:
        """한국 주식 종목명 조회 (KOSPI/KOSDAQ 주요 종목)"""
        # KOSPI/KOSDAQ 주요 종목 이름 매핑 (시가총액 상위 100개+)
        KR_STOCK_NAMES = {
            # KOSPI 대형주
            '005930': '삼성전자', '000660': 'SK하이닉스', '373220': 'LG에너지솔루션',
            '207940': '삼성바이오로직스', '005380': '현대차', '006400': '삼성SDI',
            '051910': 'LG화학', '068270': '셀트리온', '035420': 'NAVER',
            '000270': '기아', '035720': '카카오', '012330': '현대모비스',
            '028260': '삼성물산', '105560': 'KB금융', '055550': '신한지주',
            '066570': 'LG전자', '003550': 'LG', '017670': 'SK텔레콤',
            '096770': 'SK이노베이션', '034730': 'SK', '015760': '한국전력',
            '086790': '하나금융지주', '032830': '삼성생명', '018260': '삼성에스디에스',
            '003490': '대한항공', '009150': '삼성전기', '033780': 'KT&G',
            '034020': '두산에너빌리티', '010130': '고려아연', '011170': '롯데케미칼',
            '088980': '맥쿼리인프라', '047050': '포스코인터내셔널', '010950': 'S-Oil',
            '030200': 'KT', '000810': '삼성화재', '047810': '한국항공우주',
            '003670': '포스코퓨처엠', '009540': '한국조선해양', '011200': 'HMM',
            '010140': '삼성중공업', '011070': 'LG이노텍', '016360': '삼성증권',
            '042660': '한화오션', '161390': '한국타이어앤테크놀로지', '090430': '아모레퍼시픽',
            '024110': '기업은행', '326030': 'SK바이오팜', '036570': 'NCsoft',
            '008770': '호텔신라', '120110': '코오롱인더', '004020': '현대제철',
            '000720': '현대건설', '001450': '현대해상', '282330': 'BGF리테일',
            '097950': 'CJ제일제당', '005490': 'POSCO홀딩스', '051900': 'LG생활건강',
            '009830': '한화솔루션', '267250': '현대중공업', '271560': '오리온',
            '000100': '유한양행', '010120': 'LS ELECTRIC', '081660': '휠라홀딩스',
            '021240': '코웨이', '032640': 'LG유플러스', '138040': '메리츠금융지주',
            '402340': 'SK스퀘어', '004990': '롯데지주', '004170': '신세계',
            '003410': '쌍용C&E', '006360': 'GS건설', '011780': '금호석유',
            '034220': 'LG디스플레이', '000880': '한화', '018880': '한온시스템',
            '009420': '한올바이오파마', '035250': '강원랜드', '069960': '현대백화점',
            '139480': '이마트', '036460': '한국가스공사', '071050': '한국금융지주',
            '005940': 'NH투자증권', '316140': '우리금융지주', '002790': '아모레G',
            '000210': '대림산업', '006800': '미래에셋증권', '001040': 'CJ',
            '006280': '녹십자', '000150': '두산', '064350': '현대로템',
            '128940': '한미약품', '002380': 'KCC', '083420': '그린케미칼',
            
            # KOSDAQ 대형주
            '247540': '에코프로비엠', '086520': '에코프로', '091990': '셀트리온헬스케어',
            '068760': '셀트리온제약', '041510': 'SM엔터테인먼트', '293490': '카카오게임즈',
            '035760': 'CJ ENM', '112040': '위메이드', '263750': '펄어비스',
            '196170': '알테오젠', '067160': '아프리카TV', '145020': '휴젤',
            '383220': 'F&F', '263720': '디앤씨미디어', '028300': 'HLB',
            '039030': '이오테크닉스', '052690': '한전기술', '330860': '네이처셀',
            '357780': '솔브레인', '084990': '헬릭스미스', '095660': '네오위즈',
            '293480': '하림지주', '251270': '넷마블', '053800': '안랩',
            '095700': '제넥신', '214150': '클래시스', '240810': '원익IPS',
            '036540': 'SFA반도체', '078340': '컴투스', '222080': '씨아이에스',
        }
        
        # 티커에서 코드 추출 (예: "005930.KS" -> "005930")
        code = ticker.split('.')[0]
        return KR_STOCK_NAMES.get(code, ticker)
    
    # ===== Buzz Score Calculation =====
    
    def calculate_buzz_score(
        self,
        ticker: str,
        lookback_days: int = 20
    ) -> Optional[BuzzScore]:
        """
        개별 종목 관심도 점수 계산
        
        계산 로직:
        1. 20일 평균 거래량 대비 현재 거래량 비율 → volume_score (0~50)
        2. 20일 평균 변동성 대비 현재 변동성 비율 → volatility_score (0~50)
        3. base_score = volume_score + volatility_score
        
        Args:
            ticker: 종목 코드
            lookback_days: 평균 계산 기간 (기본 20일)
        
        Returns:
            BuzzScore 객체 또는 None (실패 시)
        """
        try:
            # 데이터 수집 (lookback_days + 1일)
            df = self.collector.fetch_stock_data(
                ticker,
                period=f"{lookback_days + 1}d"
            )
            
            if df is None or len(df) < lookback_days:
                logger.warning(f"[BuzzScore] Insufficient data for {ticker}")
                return None
            
            # 1. 거래량 비율 계산
            current_volume = df['volume'].iloc[-1]
            avg_volume = df['volume'].iloc[:-1].mean()
            volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1.0
            
            # 2. 변동성 비율 계산
            returns = df['close'].pct_change().dropna()
            current_volatility = abs(returns.iloc[-1])
            avg_volatility = returns.iloc[:-1].std()
            volatility_ratio = current_volatility / avg_volatility if avg_volatility > 0 else 1.0
            
            # 3. 점수 계산 (개선된 로직)
            # volume_score: ratio 기반 (0.5x = 10점, 1.0x = 25점, 2.0x = 50점)
            if volume_ratio >= 1.0:
                volume_score = min(25 + (volume_ratio - 1.0) * 25, 50)
            else:
                volume_score = max(volume_ratio * 25, 10)  # 최소 10점 보장
            
            # volatility_score: ratio 기반 (유사 로직)
            if volatility_ratio >= 1.0:
                volatility_score = min(25 + (volatility_ratio - 1.0) * 25, 50)
            else:
                volatility_score = max(volatility_ratio * 25, 10)
            
            base_score = max(0, min(100, volume_score + volatility_score))
            
            # 4. Heat Level 판정
            heat_level = HeatLevel.from_score(base_score).value
            
            # 5. 종목명 조회 (개선된 메서드 사용)
            name = self._get_stock_name(ticker)
            
            return BuzzScore(
                ticker=ticker,
                name=name,
                base_score=base_score,
                volume_ratio=volume_ratio,
                volatility_ratio=volatility_ratio,
                heat_level=heat_level,
                last_updated=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"[BuzzScore] Failed to calculate for {ticker}: {e}")
            return None
    
    # ===== Volume Anomaly Detection =====
    
    def detect_volume_anomalies(
        self,
        tickers: List[str],
        threshold: float = 2.0,
        lookback_days: int = 20
    ) -> List[VolumeAnomaly]:
        """
        거래량 급증 종목 감지
        
        Args:
            tickers: 검사할 종목 리스트
            threshold: Spike 판정 임계값 (기본 2.0 = 200%)
            lookback_days: 평균 계산 기간
        
        Returns:
            VolumeAnomaly 리스트 (ratio 높은 순 정렬)
        """
        anomalies = []
        
        for ticker in tickers:
            try:
                df = self.collector.fetch_stock_data(ticker, period=f"{lookback_days + 1}d")
                if df is None or len(df) < lookback_days:
                    continue
                
                # 거래량 비율
                current_volume = int(df['volume'].iloc[-1])
                avg_volume = int(df['volume'].iloc[:-1].mean())
                volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1.0
                
                # Spike 여부
                is_spike = volume_ratio > threshold
                
                # 등락률
                price_change_pct = ((df['close'].iloc[-1] / df['close'].iloc[-2]) - 1) * 100
                
                # 종목명 (개선된 메서드 사용)
                name = self._get_stock_name(ticker)
                
                anomaly = VolumeAnomaly(
                    ticker=ticker,
                    name=name,
                    current_volume=current_volume,
                    avg_volume=avg_volume,
                    volume_ratio=volume_ratio,
                    is_spike=is_spike,
                    detected_at=datetime.now(),
                    price_change_pct=price_change_pct
                )
                
                # Spike만 또는 ratio > 1.2인 것만 포함
                if volume_ratio > 1.2:
                    anomalies.append(anomaly)
                    
            except Exception as e:
                logger.warning(f"[VolumeAnomaly] Failed for {ticker}: {e}")
                continue
        
        # Ratio 높은 순 정렬
        anomalies.sort(reverse=True)
        return anomalies
    
    # ===== Sector Heatmap =====
    
    def get_sector_heatmap(
        self,
        market: str = "KR",
        force_refresh: bool = False
    ) -> List[SectorHeat]:
        """
        섹터별 온도 히트맵 데이터 (캐싱 지원)
        
        Args:
            market: "US" 또는 "KR"
            force_refresh: 캐시 무시하고 강제 새로고침
        
        Returns:
            SectorHeat 리스트 (avg_change_pct 높은 순 정렬)
        """
        cache_key = f"heatmap_{market}"
        
        # 1. 캐시 확인
        if not force_refresh:
            cached = self._get_from_cache(cache_key)
            if cached:
                logger.info(f"[Heatmap] Using cache for {market}")
                return cached
        
        # 2. 실시간 계산
        try:
            logger.info(f"[Heatmap] Calculating for {market}...")
            heatmap = self._calculate_sector_heatmap(market)
            
            # 3. 캐싱
            self._save_to_cache(cache_key, heatmap)
            
            return heatmap
            
        except Exception as e:
            logger.error(f"[Heatmap] Failed for {market}: {e}")
            # Graceful Degradation: stale cache 반환
            stale = self._get_stale_cache(cache_key)
            return stale if stale else []
    
    def _calculate_sector_heatmap(self, market: str) -> List[SectorHeat]:
        """섹터 히트맵 실제 계산 로직"""
        sectors_map = self.sector_repo.get_sectors(market)
        heatmap = []
        
        for sector_name, tickers in sectors_map.items():
            try:
                sector_heat = self._calculate_sector_heat(sector_name, tickers)
                if sector_heat:
                    heatmap.append(sector_heat)
            except Exception as e:
                logger.warning(f"[Heatmap] Failed to calculate {sector_name}: {e}")
                continue
        
        # 정렬 (avg_change_pct 높은 순)
        heatmap.sort(reverse=True)
        return heatmap
    
    def _calculate_sector_heat(
        self,
        sector_name: str,
        tickers: List[str]
    ) -> Optional[SectorHeat]:
        """개별 섹터 온도 계산"""
        try:
            change_pcts = []
            stock_data = []
            
            # 각 종목의 등락률 수집
            for ticker in tickers[:30]:  # 최대 30개만 (성능 고려)
                try:
                    df = self.collector.fetch_stock_data(ticker, period="2d")
                    if df is None or len(df) < 2:
                        # 실패 종목 추적
                        if ticker not in self._failed_tickers:
                            self._failed_tickers.append(ticker)
                        continue
                    
                    change_pct = ((df['close'].iloc[-1] / df['close'].iloc[-2]) - 1) * 100
                    change_pcts.append(change_pct)
                    
                    # 종목명 (개선된 메서드 사용)
                    name = self._get_stock_name(ticker)
                    
                    stock_data.append({
                        "ticker": ticker,
                        "name": name,
                        "change_pct": change_pct
                    })
                except Exception as e:
                    # 실패 종목 추적
                    if ticker not in self._failed_tickers:
                        self._failed_tickers.append(ticker)
                    continue
            
            if not change_pcts:
                return None
            
            # 평균 등락률
            avg_change_pct = np.mean(change_pcts)
            
            # 상위/하위 종목
            stock_data.sort(key=lambda x: x['change_pct'], reverse=True)
            top_gainers = stock_data[:3]
            top_losers = stock_data[-3:][::-1]  # 역순
            
            # Heat Level
            heat_level = HeatLevel.from_change_pct(avg_change_pct).value
            
            return SectorHeat(
                sector_name=sector_name,
                avg_change_pct=avg_change_pct,
                top_gainers=top_gainers,
                top_losers=top_losers,
                heat_level=heat_level,
                stock_count=len(tickers)
            )
            
        except Exception as e:
            logger.error(f"[SectorHeat] Failed for {sector_name}: {e}")
            return None
    
    # ===== Top Buzz Stocks =====
    
    def get_top_buzz_stocks(
        self,
        market: str,
        top_n: int = 10,
        force_refresh: bool = False
    ) -> List[BuzzScore]:
        """
        관심도 상위 종목 리스트
        
        Args:
            market: "US" 또는 "KR"
            top_n: 상위 N개
            force_refresh: 캐시 무시
        
        Returns:
            BuzzScore 리스트 (final_score 높은 순)
        """
        cache_key = f"top_buzz_{market}_{top_n}"
        
        # 1. 캐시 확인
        if not force_refresh:
            cached = self._get_from_cache(cache_key)
            if cached:
                return cached
        
        # 2. 실시간 계산
        try:
            all_tickers = self.sector_repo.get_all_tickers(market)
            buzz_scores = []
            
            # 모든 종목 계산 (시간 오래 걸림!)
            for ticker in all_tickers[:100]:  # 성능 고려: 상위 100개만
                buzz = self.calculate_buzz_score(ticker)
                if buzz:
                    buzz_scores.append(buzz)
            
            # 정렬
            buzz_scores.sort(reverse=True)
            top_buzz = buzz_scores[:top_n]
            
            # 캐싱
            self._save_to_cache(cache_key, top_buzz)
            
            return top_buzz
            
        except Exception as e:
            logger.error(f"[TopBuzz] Failed for {market}: {e}")
            return self._get_stale_cache(cache_key) or []
    
    # ===== Caching Helpers =====
    
    def _get_from_cache(self, key: str) -> Optional[Any]:
        """캐시에서 데이터 조회 (TTL 검사)"""
        if key not in self._cache:
            return None
        
        data, timestamp = self._cache[key]
        if (datetime.now() - timestamp).total_seconds() > self._cache_ttl:
            return None
        
        return data
    
    def _save_to_cache(self, key: str, data: Any):
        """캐시에 데이터 저장"""
        self._cache[key] = (data, datetime.now())
    
    def _get_stale_cache(self, key: str) -> Optional[Any]:
        """Stale cache 반환 (TTL 무시)"""
        if key in self._cache:
            logger.warning(f"[Cache] Using stale cache for {key}")
            return self._cache[key][0]
        return None
    
    def clear_cache(self):
        """모든 캐시 삭제"""
        self._cache.clear()
        logger.info("[Cache] All caches cleared")
