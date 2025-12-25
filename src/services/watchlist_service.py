"""
Watchlist Service
애플리케이션 계층: 관심 종목 비즈니스 로직
Phase 20 투자 성향 + Phase 21 Market Buzz 통합
"""
import logging
import concurrent.futures
from datetime import datetime
from typing import List, Optional, Dict, Any

from src.domain.watchlist import (
    WatchlistItem, 
    WatchlistSummary, 
    IWatchlistRepository,
    HeatLevel
)
from src.collectors.stock_collector import StockDataCollector
from src.analyzers.technical_analyzer import TechnicalAnalyzer

logger = logging.getLogger(__name__)


class WatchlistService:
    """
    관심 종목 서비스
    
    핵심 기능:
    1. 관심 종목 CRUD
    2. 현재가 및 기술지표 조회
    3. Phase 20 투자 성향 적합도 분석
    4. Phase 21 Market Buzz 연동
    """
    
    def __init__(
        self,
        watchlist_repo: IWatchlistRepository,
        stock_collector: Optional[StockDataCollector] = None,
        profile_repo: Optional[Any] = None,  # Phase 20 ProfileRepository
        buzz_service: Optional[Any] = None   # Phase 21 MarketBuzzService
    ):
        """
        Args:
            watchlist_repo: 관심 종목 저장소
            stock_collector: 주가 데이터 수집기
            profile_repo: Phase 20 투자 성향 저장소 (선택)
            buzz_service: Phase 21 Market Buzz 서비스 (선택)
        """
        self.watchlist_repo = watchlist_repo
        self.stock_collector = stock_collector or StockDataCollector()
        self.profile_repo = profile_repo
        self.buzz_service = buzz_service
        
        # 가격 캐시
        self._price_cache: Dict[str, tuple] = {}  # {ticker: (data, timestamp)}
        self._cache_ttl = 300  # 5분
    
    # ==================== CRUD Operations ====================
    
    def add_to_watchlist(
        self,
        user_id: str,
        ticker: str,
        stock_name: str,
        market: Optional[str] = None
    ) -> WatchlistItem:
        """
        관심 종목 추가
        
        Args:
            user_id: 사용자 ID
            ticker: 종목 코드
            stock_name: 종목명
            market: 시장 구분 (자동 판별 가능)
            
        Returns:
            생성된 WatchlistItem
        """
        # 시장 자동 판별
        if market is None:
            market = self._detect_market(ticker)
        
        return self.watchlist_repo.add_item(
            user_id=user_id,
            ticker=ticker,
            stock_name=stock_name,
            market=market
        )
    
    def remove_from_watchlist(self, user_id: str, ticker: str) -> bool:
        """관심 종목 삭제"""
        return self.watchlist_repo.remove_item(user_id, ticker)
    
    def get_watchlist(self, user_id: str) -> List[WatchlistItem]:
        """관심 종목 목록 조회"""
        return self.watchlist_repo.get_all(user_id)
    
    def is_in_watchlist(self, user_id: str, ticker: str) -> bool:
        """관심 종목 여부 확인"""
        return self.watchlist_repo.exists(user_id, ticker)
    
    # ==================== Price & Analysis ====================
    
    def get_watchlist_with_prices(
        self,
        user_id: str,
        include_profile: bool = True,
        include_buzz: bool = True
    ) -> List[WatchlistSummary]:
        """
        관심 종목 + 현재가 + 분석 정보 조회
        
        병렬 처리로 성능 최적화
        
        Args:
            user_id: 사용자 ID
            include_profile: Phase 20 성향 분석 포함 여부
            include_buzz: Phase 21 Buzz 분석 포함 여부
            
        Returns:
            WatchlistSummary 리스트
        """
        items = self.watchlist_repo.get_all(user_id)
        
        if not items:
            return []
        
        # 사용자 프로필 로드 (Phase 20)
        profile = None
        if include_profile and self.profile_repo:
            try:
                profile = self.profile_repo.load(user_id)
            except Exception as e:
                logger.warning(f"Failed to load profile for {user_id}: {e}")
        
        # 병렬로 가격 데이터 조회
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            future_to_item = {
                executor.submit(
                    self._create_summary,
                    item,
                    profile,
                    include_buzz
                ): item
                for item in items
            }
            
            summaries = []
            for future in concurrent.futures.as_completed(future_to_item):
                try:
                    summary = future.result(timeout=15)
                    if summary:
                        summaries.append(summary)
                except Exception as e:
                    item = future_to_item[future]
                    logger.error(f"Failed to get summary for {item.ticker}: {e}")
                    # 에러 시 기본값
                    summaries.append(self._create_fallback_summary(item))
        
        # 추가일 기준 정렬
        summaries.sort(key=lambda x: x.item.added_at, reverse=True)
        
        return summaries
    
    def _create_summary(
        self,
        item: WatchlistItem,
        profile: Optional[Any],
        include_buzz: bool
    ) -> Optional[WatchlistSummary]:
        """개별 종목 요약 생성"""
        try:
            # 가격 데이터 조회
            price_data = self._get_price_data(item.ticker)
            
            if not price_data:
                return self._create_fallback_summary(item)
            
            # 기술지표
            rsi = price_data.get('rsi')
            macd_signal = self._get_macd_signal(price_data)
            
            # Phase 20: 성향 적합도
            profile_fit_score = None
            profile_warning = None
            if profile:
                profile_fit_score = self._calculate_profile_fit(item.ticker, profile)
                profile_warning = self._generate_profile_warning(
                    item.ticker, profile, profile_fit_score
                )
            
            # Phase 21: Buzz 분석
            buzz_score = None
            heat_level = None
            volume_anomaly = False
            if include_buzz and self.buzz_service:
                try:
                    buzz = self.buzz_service.calculate_buzz_score(item.ticker)
                    if buzz:
                        buzz_score = buzz.base_score
                        heat_level = HeatLevel(buzz.heat_level) if hasattr(buzz, 'heat_level') else None
                except Exception as e:
                    logger.debug(f"Buzz calculation failed for {item.ticker}: {e}")
            
            # 거래량 급등 확인
            volume_anomaly = self._check_volume_anomaly(item.ticker, price_data)
            
            return WatchlistSummary(
                item=item,
                current_price=price_data.get('price', 0),
                prev_close=price_data.get('prev_close', 0),
                change_pct=price_data.get('change_pct', 0),
                volume=price_data.get('volume', 0),
                rsi=rsi,
                macd_signal=macd_signal,
                profile_fit_score=profile_fit_score,
                profile_warning=profile_warning,
                buzz_score=buzz_score,
                heat_level=heat_level,
                volume_anomaly=volume_anomaly
            )
            
        except Exception as e:
            logger.error(f"Error creating summary for {item.ticker}: {e}")
            return self._create_fallback_summary(item)
    
    def _create_fallback_summary(self, item: WatchlistItem) -> WatchlistSummary:
        """에러 시 기본 요약 생성"""
        return WatchlistSummary(
            item=item,
            current_price=0,
            prev_close=0,
            change_pct=0,
            volume=0
        )
    
    # ==================== Price Data ====================
    
    def _get_price_data(self, ticker: str) -> Optional[Dict]:
        """
        가격 데이터 조회 (캐싱 적용)
        """
        # 캐시 확인
        if ticker in self._price_cache:
            data, cached_time = self._price_cache[ticker]
            if (datetime.now() - cached_time).seconds < self._cache_ttl:
                return data
        
        try:
            import yfinance as yf
            stock = yf.Ticker(ticker)
            hist = stock.history(period="1mo")  # 1개월로 확대 (RSI 14일 계산용)
            
            if hist.empty:
                return None
            
            current = hist['Close'].iloc[-1]
            prev_close = hist['Close'].iloc[-2] if len(hist) > 1 else current
            change_pct = ((current - prev_close) / prev_close * 100) if prev_close else 0
            
            # RSI 계산 (14일)
            rsi = self._calculate_rsi(hist['Close'])
            
            # 실제 변동성 계산 (표준편차 기반)
            returns = hist['Close'].pct_change().dropna()
            volatility = returns.std() * 100 if len(returns) > 0 else 0  # % 단위
            
            # 평균 거래량
            avg_volume = hist['Volume'].mean()
            current_volume = hist['Volume'].iloc[-1]
            
            data = {
                'price': current,
                'prev_close': prev_close,
                'change_pct': change_pct,
                'volume': int(current_volume),
                'avg_volume': avg_volume,
                'rsi': rsi,
                'volatility': volatility  # 실제 변동성 추가
            }
            
            # 캐시 저장
            self._price_cache[ticker] = (data, datetime.now())
            
            return data
            
        except Exception as e:
            logger.warning(f"Failed to get price for {ticker}: {e}")
            return None
    
    def _calculate_rsi(self, prices, period: int = 14) -> Optional[float]:
        """RSI 계산"""
        if len(prices) < period + 1:
            return None
        
        deltas = prices.diff()
        gain = (deltas.where(deltas > 0, 0)).rolling(window=period).mean()
        loss = (-deltas.where(deltas < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi.iloc[-1] if not rsi.empty else None
    
    def _get_macd_signal(self, price_data: Dict) -> Optional[str]:
        """MACD 기반 신호 (간략 버전)"""
        # 실제 구현에서는 TechnicalAnalyzer 사용
        return "중립"
    
    # ==================== Volume Analysis ====================
    
    def _check_volume_anomaly(self, ticker: str, price_data: Dict) -> bool:
        """거래량 급등 확인"""
        if not price_data:
            return False
        
        avg_volume = price_data.get('avg_volume', 0)
        current_volume = price_data.get('volume', 0)
        
        if avg_volume == 0:
            return False
        
        volume_ratio = current_volume / avg_volume
        return volume_ratio >= 2.0  # 평균의 2배 이상
    
    # ==================== Market Detection ====================
    
    def _detect_market(self, ticker: str) -> str:
        """티커에서 시장 자동 판별"""
        if ticker.endswith('.KS') or ticker.endswith('.KQ'):
            return 'KR'
        elif '.' not in ticker:
            # 숫자로만 구성되면 한국 종목
            code = ticker.split('.')[0]
            if code.isdigit() and len(code) == 6:
                return 'KR'
            return 'US'
        else:
            return 'US'
    
    # ==================== Phase 20: Profile Fit ====================
    
    def _calculate_profile_fit(
        self,
        ticker: str,
        profile: Any
    ) -> float:
        """
        Phase 20 프로필 기반 적합도 점수 계산
        
        요소:
        1. 변동성 적합도 (40점)
        2. 섹터 선호도 (40점)
        3. 위험 감수 레벨 매칭 (20점)
        """
        try:
            price_data = self._get_price_data(ticker)
            if not price_data:
                return 70.0  # 데이터 없으면 중립적 점수
            
            score = 0.0
            
            # 프로필에서 위험 감수 레벨 가져오기 (올바른 속성 접근)
            try:
                risk_value = profile.risk_tolerance.value  # RiskTolerance 객체의 value 속성
            except AttributeError:
                risk_value = 50  # 기본값
            
            # 실제 변동성 사용 (% 단위)
            volatility_pct = price_data.get('volatility', 2.0)  # 일일 변동성 %
            
            # 변동성 정규화 (0~1 스케일, 일반적으로 1~5% 범위)
            volatility = min(1.0, volatility_pct / 5.0)
            
            logger.debug(f"[ProfileFit] {ticker}: risk_value={risk_value}, volatility={volatility_pct:.2f}%")
            
            # 1. 변동성 적합도 (40점)
            # 프로필에서 이상적인 변동성 범위 가져오기
            try:
                ideal_min, ideal_max = profile.get_ideal_volatility_range()
                if ideal_min <= volatility <= ideal_max:
                    score += 40  # 범위 내면 만점
                else:
                    # 범위 밖이면 거리에 따라 감점
                    distance = min(abs(volatility - ideal_min), abs(volatility - ideal_max))
                    score += max(20, 40 - distance * 80)
            except:
                # 변동성 기반 기본 계산
                if risk_value <= 40:  # 안정형
                    score += max(20, 40 - volatility * 30)
                elif risk_value >= 60:  # 공격형
                    score += min(40, 20 + volatility * 30)
                else:  # 균형형
                    score += 35
            
            # 2. 섹터 선호도 (40점)
            try:
                preferred_sectors = getattr(profile, 'preferred_sectors', [])
                if preferred_sectors:
                    score += 30  # 프로필에 섹터 선호가 있으면 기본 점수
                else:
                    score += 35
            except:
                score += 30
            
            # 3. 위험 감수 레벨 매칭 (20점)
            # 안정형(<=40)은 저변동성, 공격형(>=60)은 고변동성 선호
            if risk_value <= 40:  # 안정형
                if volatility < 0.4:
                    score += 20
                elif volatility < 0.6:
                    score += 15
                else:
                    score += 5
            elif risk_value >= 60:  # 공격형
                if volatility > 0.5:
                    score += 20
                elif volatility > 0.3:
                    score += 15
                else:
                    score += 10
            else:  # 균형형
                score += 18  # 균형형은 대부분 적합
            
            return min(100, max(0, score))
            
        except Exception as e:
            logger.warning(f"Profile fit calculation failed for {ticker}: {e}")
            return 70.0  # 에러 시 중립적 점수
    
    def _generate_profile_warning(
        self,
        ticker: str,
        profile: Any,
        fit_score: float
    ) -> Optional[str]:
        """성향 불일치 경고 메시지 생성"""
        if fit_score >= 60:
            return None  # 60점 이상이면 경고 없음
        
        try:
            profile_type = getattr(profile, 'profile_type', '투자자')
            
            if fit_score < 40:
                return f"⚠️ 이 종목은 {profile_type} 투자자에게 적합하지 않을 수 있습니다."
            elif fit_score < 60:
                return f"💡 {profile_type} 투자자는 신중한 검토가 필요합니다."
            
        except Exception:
            pass
        
        return None
    
    # ==================== Statistics ====================
    
    def get_watchlist_statistics(self, user_id: str) -> Dict[str, Any]:
        """관심 종목 통계"""
        summaries = self.get_watchlist_with_prices(user_id)
        
        if not summaries:
            return {
                'total_count': 0,
                'rising_count': 0,
                'falling_count': 0,
                'avg_change_pct': 0,
                'kr_count': 0,
                'us_count': 0
            }
        
        rising = len([s for s in summaries if s.change_pct > 0])
        falling = len([s for s in summaries if s.change_pct < 0])
        avg_change = sum(s.change_pct for s in summaries) / len(summaries)
        
        kr_count = len([s for s in summaries if s.item.market == 'KR'])
        us_count = len([s for s in summaries if s.item.market == 'US'])
        
        return {
            'total_count': len(summaries),
            'rising_count': rising,
            'falling_count': falling,
            'avg_change_pct': avg_change,
            'kr_count': kr_count,
            'us_count': us_count
        }
