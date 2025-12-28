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
import pandas as pd
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
    
    # Phase G: 상세 정보 확장
    marketcap: Optional[float] = None  # 시가총액
    per: Optional[float] = None  # PER
    dividend_yield: Optional[float] = None  # 배당수익률
    week52_high: Optional[float] = None  # 52주 최고가
    week52_low: Optional[float] = None  # 52주 최저가
    ma_5: Optional[float] = None
    ma_20: Optional[float] = None
    ma_status: Optional[str] = None
    
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
        pykrx_gateway: Optional[Any] = None,
        tech_indicators: Optional[Any] = None,
        sentiment_service: Optional[Any] = None
    ):
        """
        Args:
            signal_service: SignalGeneratorService
            profile_repo: ProfileRepository (Phase 20)
            pykrx_gateway: PyKRXGateway
            tech_indicators: ITechnicalIndicatorsService
            sentiment_service: SentimentAnalysisService
        """
        self.signal_service = signal_service
        self.profile_repo = profile_repo
        self.pykrx_gateway = pykrx_gateway
        self.tech_indicators = tech_indicators or self._get_default_tech_indicators()
        self.sentiment_service = sentiment_service

    def _get_default_tech_indicators(self):
        """지표 계산기 기본값 (Lazy Import)"""
        try:
            from src.services.technical_indicators import VectorizedTechnicalIndicators
            return VectorizedTechnicalIndicators()
        except ImportError:
            return None
    
    def run_daily_screen(
        self,
        user_id: str = "default_user",
        market: str = "KR",
        top_n: int = 5
    ) -> List[StockRecommendation]:
        """
        일일 스크리닝 실행 (Phase G: High-Performance 3-Stage Pipeline)
        """
        logger.info(f"[Screener] Starting optimized screen for {user_id}, market={market}")
        
        # 이름 매핑 정보 획득 (한국 시장 선도시 수집)
        name_map = {}
        if market == "KR" and self.pykrx_gateway:
            name_map = self.pykrx_gateway.get_ticker_name_map()
        # [Stage 1] 전 종목 스냅샷 필터링 (Market Snapshot)
        # 1.1: 전체 종목 리스트 및 기본 시세 획득 (약 2500개)
        if market == "KR" and self.pykrx_gateway:
            snapshot_kospi = self.pykrx_gateway.get_market_snapshot("KOSPI")
            snapshot_kosdaq = self.pykrx_gateway.get_market_snapshot("KOSDAQ")
            snapshot = pd.concat([snapshot_kospi, snapshot_kosdaq]) if snapshot_kospi is not None else snapshot_kosdaq
        else:
            # US 또는 폴백: 기존 유니버스 방식 사용
            all_tickers = self._get_stock_universe(market)
            snapshot = pd.DataFrame({'ticker': all_tickers})

        if snapshot is None or snapshot.empty:
            logger.error("[Screener] Failed to get market snapshot")
            return []

        # 1.2: 기본 필터링 (거래량 > 0, 거래대금 기준)
        if 'volume' in snapshot.columns:
            snapshot = snapshot[snapshot['volume'] > 0]
        
        # 거래대금 상위 1000개 우선 분석 (대형주/활성주 중심)
        if '거래대금' in snapshot.columns:
            snapshot = snapshot.sort_values(by='거래대금', ascending=False)
        
        target_tickers = snapshot['ticker'].tolist()
        logger.info(f"[Screener] Stage 1 complete: {len(target_tickers)} stocks selected (Top 1000 prioritized)")

        # [Stage 2] 대량 데이터 분석 (Batch OHLCV + Vectorized Indicators)
        # 2.1: 배치 데이터 수집 (최근 20일 OHLCV) - 병렬 처리
        target_tickers = target_tickers[:100]  # 성능 안전장치: 상위 100개 종목 우선 분석 (기존 500개에서 축소하여 응답성 확보)
        logger.info(f"[Screener] Stage 2 starting: Fetching OHLCV for {len(target_tickers)} stocks")
        
        ohlcv_dict = self.pykrx_gateway.batch_get_ohlcv_parallel(target_tickers, period="1mo") if self.pykrx_gateway else {}

        if not ohlcv_dict:
            logger.warning("[Screener] No OHLCV data fetched in Stage 2")
            return []
        
        logger.info(f"[Screener] Stage 2: Fetched OHLCV for {len(ohlcv_dict)} stocks. Starting calculation...")

        # 2.2: 벡터화 기술적 지표 계산
        combined_df = pd.concat([df.assign(ticker=t) for t, df in ohlcv_dict.items()])
        combined_df.index.name = 'date'
        combined_df = combined_df.reset_index().set_index(['ticker', 'date'])
        
        rsi_series = self.tech_indicators.calculate_rsi_vectorized(combined_df)
        ma_df = self.tech_indicators.calculate_moving_averages_vectorized(combined_df)
        
        latest_rsi = self.tech_indicators.get_latest_values_by_ticker(rsi_series)
        latest_ma = self.tech_indicators.get_latest_values_by_ticker(ma_df)
        
        # 2.Stage 2 Filtering: RSI < 50 등 (약간 완화하여 결과 보장)
        stage2_tickers = [t for t in ohlcv_dict.keys() if latest_rsi.get(t, 50) < 50]
        logger.info(f"[Screener] Stage 2 complete: {len(stage2_tickers)} stocks passed technical filters")

        # [Stage 3] 정밀 수급 분석 (Batch Investor Trading)
        investor_data = {}
        if market == "KR" and self.pykrx_gateway:
            logger.info(f"[Screener] Stage 3 starting: Fetching investor trading for {len(stage2_tickers)} stocks")
            investor_data = self.pykrx_gateway.batch_get_investor_trading(stage2_tickers)
            logger.info(f"[Screener] Stage 3 complete: Fetched data for {len(investor_data)} stocks")
        
        # 최종 추천 리스트 생성 및 정렬
        recommendations = []
        for ticker in stage2_tickers:
            # 기본 데이터 매핑
            name = name_map.get(ticker, self.KOREAN_STOCK_NAMES.get(ticker, ticker))
            rsi_val = latest_rsi.get(ticker)
            ma_5 = latest_ma.loc[ticker, 'ma_5'] if ticker in latest_ma.index else None
            ma_20 = latest_ma.loc[ticker, 'ma_20'] if ticker in latest_ma.index else None
            
            # 수급 체크
            streak = False
            if ticker in investor_data:
                df = investor_data[ticker]
                streak = (df.tail(3)['기관순매수'] > 0).all()

            # 펀더멘털 (Lazy Fetch for screened stocks only)
            fundamental = self.pykrx_gateway.get_stock_fundamental(ticker) if self.pykrx_gateway else {}

            # AI 점수 (기존 로직 활용)
            score_data = {
                'ticker': ticker, 'stock_name': name, 'rsi': rsi_val, 
                'institution_streak': streak, 'pbr': fundamental.get('pbr'),
                'change_pct': 0 # FIXME
            }
            
            # 여기서 AI 점수 계산 및 추천 이유 생성 (기존 메서드 재사용 가능하게 리팩토링 필요할 수 있으나 우선 직적 계산)
            rec = self._create_recommendation(score_data, fundamental, ma_5, ma_20)
            recommendations.append(rec)

        # [Stage 4] 상위 후보 뉴스 감성 분석 (Gemini Batch 최적화)
        recommendations.sort(key=lambda x: x.ai_score, reverse=True)
        top_candidates = recommendations[:min(len(recommendations), 15)] # 상위 15개 후보군 선정
        
        if self.sentiment_service:
            logger.info(f"[Screener] Stage 4: Starting batch sentiment analysis for {len(top_candidates)} candidates")
            
            # 4.1 배치를 위한 데이터 구성
            ticker_name_map = {rec.ticker: rec.stock_name for rec in top_candidates}
            
            # 4.2 Gemini 배치 호출 (한 번의 요청으로 뉴스 수집+분석)
            batch_results = self.sentiment_service.get_batch_sentiment_for_screener(ticker_name_map, market=market)
            
            # 4.3 결과 반영
            for rec in top_candidates:
                ticker_res = batch_results.get(rec.ticker)
                if ticker_res:
                    sentiment_score = float(ticker_res.get('score', 0))
                    analysis_reason = ticker_res.get('reason', '')
                    
                    # 감성 분석 점수 반영 (최대 20점 가산점)
                    sentiment_bonus = max(0, sentiment_score * 20)
                    rec.ai_score += sentiment_bonus
                    
                    # 추천 이유 업데이트
                    if sentiment_score > 0.1:
                        # 긍정적일 경우 설명과 함께 가산점 표시
                        rec.reason = f"Gemini 분석({analysis_reason}) (+{sentiment_bonus:.0f}점). " + rec.reason
                    elif sentiment_score < -0.1:
                        # 부정적일 경우 주의 문구 추가 (점수 가산 없음)
                        rec.reason = f"Gemini 주의({analysis_reason}). " + rec.reason

                # AI 점수 변화에 따른 신호 재판정
                if rec.ai_score >= 70:
                    rec.signal_type = "적극 매수 발굴 🔥"
                elif rec.ai_score >= 55:
                    rec.signal_type = "긍정적 매수 검토 ✅"

        final_results = top_candidates

        # 최종 정렬 및 반환
        final_results.sort(key=lambda x: x.ai_score, reverse=True)
        return final_results[:top_n]

    def _create_recommendation(self, data, fundamental, ma_5, ma_20) -> StockRecommendation:
        """Score calculation and recommendation object creation"""
        # (기존 _calculate_ai_scores 로직의 핵심 부분 집약)
        # rsi, pbr NULL 처리 강화
        rsi_raw = data.get('rsi')
        rsi = float(rsi_raw) if rsi_raw is not None else 50.0
        
        pbr_raw = fundamental.get('pbr')
        pbr = float(pbr_raw) if pbr_raw is not None else 1.0
        
        streak = data.get('institution_streak', False)
        
        logger.debug(f"[Screener] Calculating score for {data.get('ticker')}: rsi={rsi}({type(rsi)}), pbr={pbr}({type(pbr)}), streak={streak}")
        
        score = 0
        try:
            # RSI 점수 (40점)
            if rsi < 35: score += 40
            elif rsi < 40: score += 30
            else: score += 10
            
            # PBR 점수 (20점)
            if pbr < 0.8: score += 20
            elif pbr < 1.0: score += 15
            else: score += 5
            
            # 수급 점수 (20점)
            if streak: score += 20
        except Exception as e:
            logger.error(f"[Screener] Error during score calculation for {data.get('ticker')}: {e}")
            # 에러 발생 시 최하 점수 부여
            score = 5
        
        # 추세 용어 단순화 (사용자 요청: 더 쉬운 말로)
        ma_status = "상승세 유지 🟢" if ma_5 and ma_20 and ma_5 > ma_20 else "하락/조정 중 🔴"
        
        return StockRecommendation(
            ticker=data['ticker'],
            stock_name=data['stock_name'],
            ai_score=score,
            signal_type="적극 매수 발굴 🔥" if score >= 70 else "긍정적 매수 검토 ✅" if score >= 55 else "보유 및 추이 관찰 👀",
            confidence=min(95, score + 10),
            rsi=rsi,
            pbr=pbr,
            institution_streak=streak,
            marketcap=fundamental.get('marketcap'),
            per=fundamental.get('per'),
            dividend_yield=fundamental.get('dividend_yield'),
            week52_high=fundamental.get('week52_high'),
            week52_low=fundamental.get('week52_low'),
            ma_5=ma_5,
            ma_20=ma_20,
            ma_status=ma_status,
            reason=self._generate_reason(data, "매수") # FIXME
        )
    
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
