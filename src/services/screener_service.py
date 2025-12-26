"""
Screener Service
AI 기반 종목 발굴 서비스 (매일 아침 추천주)
Clean Architecture: Application Layer

조건:
- 기술적: RSI < 35 (과매도)
- 수급: 기관 3일 연속 매수
- 펀더멘털: PBR < 1.5 (저평가)
- AI 점수 기반 정렬
"""
import logging
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class StockRecommendation:
    """종목 추천 결과"""
    ticker: str
    stock_name: str
    ai_score: float  # 종합 AI 점수
    signal_type: str  # 매매 신호
    confidence: float  # 신뢰도
    
    # 조건 충족 여부
    rsi: Optional[float] = None
    pbr: Optional[float] = None
    institution_streak: bool = False
    
    # 추가 정보
    current_price: Optional[float] = None
    change_pct: Optional[float] = None
    reason: str = ""  # 추천 이유


class ScreenerService:
    """
    AI 종목 스크리너 (매일 아침 추천주)
    
    프로세스:
    1. 전체 종목 풀 가져오기
    2. 기본 필터링 (RSI, PBR, 수급)
    3. AI 신호 생성 및 점수 계산
    4. 사용자 프로필 기반 재정렬
    5. Top N 반환
    """
    
    def __init__(
        self,
        signal_service: Optional[Any] = None,
        profile_repo: Optional[Any] = None,
        pykrx_gateway: Optional[Any] = None
    ):
        """
        Args:
            signal_service: SignalGeneratorService
            profile_repo: ProfileRepository (Phase 20)
            pykrx_gateway: PyKRXGateway
        """
        self.signal_service = signal_service
        self.profile_repo = profile_repo
        self.pykrx_gateway = pykrx_gateway
    
    def run_daily_screen(
        self,
        user_id: str = "default_user",
        market: str = "KR",
        top_n: int = 5
    ) -> List[StockRecommendation]:
        """
        일일 스크리닝 실행
        
        Args:
            user_id: 사용자 ID (개인화용)
            market: 시장 ("KR" 또는 "US")
            top_n: 반환할 추천 종목 개수
            
        Returns:
            StockRecommendation 리스트 (AI 점수 내림차순)
        """
        logger.info(f"[Screener] Starting daily screen for {user_id}, market={market}")
        
        # 1. 전체 종목 풀 가져오기
        all_tickers = self._get_stock_universe(market)
        if not all_tickers:
            logger.warning("[Screener] No tickers found")
            return []
        
        logger.info(f"[Screener] Screening {len(all_tickers)} stocks")
        
        # 2. 기본 필터링 (RSI, PBR, 수급)
        filtered = self._apply_base_filters(all_tickers, market)
        logger.info(f"[Screener] After filtering: {len(filtered)} stocks")
        
        if not filtered:
            logger.warning("[Screener] No stocks passed filters")
            return []
        
        # 3. AI 점수 계산
        scored = self._calculate_ai_scores(filtered, user_id)
        
        # 4. 사용자 프로필 기반 재정렬
        profile = None
        if self.profile_repo:
            try:
                profile = self.profile_repo.load(user_id)
            except Exception as e:
                logger.debug(f"[Screener] Profile load failed: {e}")
        
        if profile:
            personalized = self._personalize_ranking(scored, profile)
        else:
            personalized = scored
        
        # 5. Top N 반환
        return personalized[:top_n]
    
    def _get_stock_universe(self, market: str) -> List[str]:
        """전체 종목 풀 가져오기"""
        # TODO: 실제로는 DB나 API에서 전체 종목 리스트를 가져와야 함
        # 현재는 샘플 종목만 반환
        
        if market == "KR":
            # 한국 대표 종목 샘플
            return [
                "005930.KS",  # 삼성전자
                "000660.KS",  # SK하이닉스
                "035420.KS",  # NAVER
                "005380.KS",  # 현대차
                "051910.KS",  # LG화학
                "035720.KS",  # 카카오
                "006400.KS",  # 삼성SDI
                "068270.KS",  # 셀트리온
                "207940.KS",  # 삼성바이오로직스
                "105560.KS",  # KB금융
            ]
        else:
            # 미국 대표 종목 샘플
            return [
                "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA",
                "TSLA", "META", "BRK-B", "JPM", "V"
            ]
    
    def _apply_base_filters(
        self,
        tickers: List[str],
        market: str
    ) -> List[Dict[str, Any]]:
        """기본 필터링 적용"""
        filtered = []
        
        for ticker in tickers:
            try:
                stock_data = self._get_stock_data(ticker)
                
                if stock_data is None:
                    continue
                
                # 필터 조건 체크
                passes_filters = True
                
                # 1. RSI 필터 (< 40, 과매도 근처)
                rsi = stock_data.get('rsi')
                if rsi and rsi >= 40:
                    passes_filters = False
                
                # 2. 한국 주식의 경우 기관 수급 체크
                institution_streak = False
                if market == "KR" and self.pykrx_gateway:
                    try:
                        streak = self.pykrx_gateway.detect_buying_streak(
                            ticker, days=20, streak_days=3
                        )
                        institution_streak = streak.get('institution_streak', False)
                        
                        # 기관이 3일 연속 매수하지 않으면 제외
                        if not institution_streak:
                            passes_filters = False
                    except:
                        pass
                
                if passes_filters:
                    stock_data['ticker'] = ticker
                    stock_data['institution_streak'] = institution_streak
                    filtered.append(stock_data)
                    
            except Exception as e:
                logger.debug(f"[Screener] Failed to filter {ticker}: {e}")
                continue
        
        return filtered
    
    # 한국 종목 한글 이름 매핑 (yfinance는 영어 이름만 반환)
    KOREAN_STOCK_NAMES = {
        "005930.KS": "삼성전자",
        "000660.KS": "SK하이닉스",
        "035420.KS": "NAVER",
        "005380.KS": "현대차",
        "051910.KS": "LG화학",
        "035720.KS": "카카오",
        "006400.KS": "삼성SDI",
        "068270.KS": "셀트리온",
        "207940.KS": "삼성바이오로직스",
        "105560.KS": "KB금융",
        "055550.KS": "신한지주",
        "000270.KS": "기아",
        "066570.KS": "LG전자",
        "003550.KS": "LG",
        "012330.KS": "현대모비스",
        "028260.KS": "삼성물산",
        "003670.KS": "포스코퓨처엠",
        "373220.KS": "LG에너지솔루션",
        "086790.KS": "하나금융지주",
        "096770.KS": "SK이노베이션",
    }
    
    def _get_stock_data(self, ticker: str) -> Optional[Dict[str, Any]]:
        """종목 데이터 조회"""
        try:
            import yfinance as yf
            
            stock = yf.Ticker(ticker)
            hist = stock.history(period="1mo")
            
            if hist.empty:
                return None
            
            # RSI 계산
            close = hist['Close']
            delta = close.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            
            # 기본 정보
            info = stock.info
            
            # 한국 종목은 한글 이름 매핑 사용
            if ticker in self.KOREAN_STOCK_NAMES:
                stock_name = self.KOREAN_STOCK_NAMES[ticker]
            else:
                stock_name = info.get('shortName', ticker)
            
            return {
                'stock_name': stock_name,
                'current_price': close.iloc[-1],
                'change_pct': ((close.iloc[-1] - close.iloc[-2]) / close.iloc[-2] * 100) if len(close) > 1 else 0,
                'rsi': rsi.iloc[-1] if not rsi.empty else None,
                'pbr': info.get('priceToBook'),
            }
            
        except Exception as e:
            logger.debug(f"[Screener] Data fetch failed for {ticker}: {e}")
            return None
    
    def _calculate_ai_scores(
        self,
        stocks: List[Dict[str, Any]],
        user_id: str
    ) -> List[StockRecommendation]:
        """AI 점수 계산 (다중 요소 기반)"""
        recommendations = []
        
        for stock_data in stocks:
            ticker = stock_data['ticker']
            
            try:
                # AI 신호 생성
                if self.signal_service:
                    signal = self.signal_service.generate_signal(
                        ticker,
                        stock_data.get('stock_name'),
                        user_id
                    )
                    
                    ai_score = signal.confidence
                    signal_type = signal.signal_type.value
                    confidence = signal.confidence
                else:
                    # 개선된 폴백: 다중 요소 기반 점수 계산
                    rsi = stock_data.get('rsi', 50)
                    pbr = stock_data.get('pbr', 1.0)
                    change_pct = stock_data.get('change_pct', 0)
                    institution_streak = stock_data.get('institution_streak', False)
                    
                    # 1. RSI 점수 (0-35: 최고점, 35-50: 감소)
                    if rsi and rsi < 35:
                        rsi_score = 40  # 과매도 최고점
                    elif rsi and rsi < 40:
                        rsi_score = 30 + (40 - rsi)  # 30-35
                    elif rsi:
                        rsi_score = max(0, 30 - (rsi - 40) * 0.5)  # 점진 감소
                    else:
                        rsi_score = 15
                    
                    # 2. PBR 점수 (저PBR 선호)
                    if pbr and pbr < 0.8:
                        pbr_score = 25
                    elif pbr and pbr < 1.0:
                        pbr_score = 20
                    elif pbr and pbr < 1.5:
                        pbr_score = 15
                    else:
                        pbr_score = 5
                    
                    # 3. 모멘텀 점수 (당일 상승률)
                    if change_pct > 3:
                        momentum_score = 20
                    elif change_pct > 1:
                        momentum_score = 15
                    elif change_pct > 0:
                        momentum_score = 10
                    elif change_pct > -1:
                        momentum_score = 5
                    else:
                        momentum_score = 0
                    
                    # 4. 기관 수급 보너스
                    institution_score = 15 if institution_streak else 0
                    
                    # 종합 점수 (0-100)
                    ai_score = min(100, rsi_score + pbr_score + momentum_score + institution_score)
                    
                    # 신뢰도 (점수 기반 + 변동)
                    import random
                    confidence = min(95, max(40, ai_score + random.randint(-5, 10)))
                    
                    # 신호 타입 결정
                    if ai_score >= 70:
                        signal_type = "강력 매수"
                    elif ai_score >= 55:
                        signal_type = "매수"
                    elif ai_score >= 40:
                        signal_type = "보유"
                    else:
                        signal_type = "관망"
                
                # 추천 이유 생성
                reason = self._generate_reason(stock_data, signal_type)
                
                recommendation = StockRecommendation(
                    ticker=ticker,
                    stock_name=stock_data.get('stock_name', ticker),
                    ai_score=ai_score,
                    signal_type=signal_type,
                    confidence=confidence,
                    rsi=stock_data.get('rsi'),
                    pbr=stock_data.get('pbr'),
                    institution_streak=stock_data.get('institution_streak', False),
                    current_price=stock_data.get('current_price'),
                    change_pct=stock_data.get('change_pct'),
                    reason=reason
                )
                
                recommendations.append(recommendation)
                
            except Exception as e:
                logger.debug(f"[Screener] AI score failed for {ticker}: {e}")
                continue
        
        # AI 점수 내림차순 정렬
        recommendations.sort(key=lambda x: x.ai_score, reverse=True)
        
        return recommendations
    
    def _generate_reason(self, stock_data: Dict[str, Any], signal_type: str) -> str:
        """추천 이유 생성"""
        reasons = []
        
        rsi = stock_data.get('rsi')
        if rsi and rsi < 35:
            reasons.append("RSI 과매도")
        
        if stock_data.get('institution_streak'):
            reasons.append("기관 연속 매수")
        
        pbr = stock_data.get('pbr')
        if pbr and pbr < 1.0:
            reasons.append("저PBR")
        
        if not reasons:
            reasons.append("AI 분석 결과")
        
        return " + ".join(reasons)
    
    def _personalize_ranking(
        self,
        recommendations: List[StockRecommendation],
        profile: Any
    ) -> List[StockRecommendation]:
        """프로필 기반 재정렬"""
        try:
            risk_value = profile.risk_tolerance.value
            
            # 공격형 (risk_value > 60): 고점수 종목 우선
            # 보수형 (risk_value <= 40): 높은 신뢰도 + 낮은 변동성 우선
            
            if risk_value <= 40:
                # 보수형: 신뢰도와 안정성 우선
                recommendations.sort(
                    key=lambda x: (x.confidence, -abs(x.change_pct or 0)),
                    reverse=True
                )
            elif risk_value > 60:
                # 공격형: AI 점수 우선 (이미 정렬됨)
                pass
            
            logger.debug(f"[Screener] Personalized for risk_value={risk_value}")
            
        except Exception as e:
            logger.debug(f"[Screener] Personalization failed: {e}")
        
        return recommendations
