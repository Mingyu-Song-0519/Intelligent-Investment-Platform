"""
Investment Report Service
AI 기반 투자 분석 리포트 생성 서비스
Clean Architecture: Application Layer

Phase 20 투자 성향 프로필 통합
Phase 21 Market Buzz 통합
기존 SentimentAnalysisService 재사용
"""
import logging
import re
from datetime import datetime
from typing import Optional, Dict, Any

from src.domain.ai_report import InvestmentReport, SignalType
from src.infrastructure.external.gemini_client import ILLMClient, GeminiClient

logger = logging.getLogger(__name__)


class InvestmentReportService:
    """
    AI 투자 분석 리포트 생성 서비스
    
    기능:
    1. Gemini API를 통한 종목 분석 리포트 생성
    2. Phase 20 투자 성향 프로필 기반 개인화
    3. Phase 21 Market Buzz 데이터 통합
    4. 기존 SentimentAnalysisService 재사용
    """
    
    def __init__(
        self,
        llm_client: Optional[ILLMClient] = None,
        stock_repo: Optional[Any] = None,
        sentiment_service: Optional[Any] = None,
        profile_repo: Optional[Any] = None,
        market_buzz_service: Optional[Any] = None
    ):
        """
        Args:
            llm_client: LLM 클라이언트 (None이면 GeminiClient 자동 생성)
            stock_repo: 주식 데이터 저장소
            sentiment_service: 감성 분석 서비스 (Phase 18)
            profile_repo: 투자 성향 프로필 저장소 (Phase 20)
            market_buzz_service: Market Buzz 서비스 (Phase 21)
        """
        self.llm = llm_client or self._create_default_llm()
        self.stock_repo = stock_repo
        self.sentiment_service = sentiment_service
        self.profile_repo = profile_repo
        self.market_buzz_service = market_buzz_service
    
    def _create_default_llm(self) -> ILLMClient:
        """기본 LLM 클라이언트 생성"""
        try:
            return GeminiClient()
        except Exception as e:
            logger.error(f"Failed to create GeminiClient: {e}")
            # 폴백: MockLLMClient
            from src.infrastructure.external.gemini_client import MockLLMClient
            return MockLLMClient()
    
    def generate_report(
        self,
        ticker: str,
        stock_name: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> InvestmentReport:
        """
        종목 분석 리포트 생성
        
        Args:
            ticker: 종목 코드
            stock_name: 종목명 (None이면 조회)
            user_id: 사용자 ID (프로필 기반 개인화용)
            
        Returns:
            InvestmentReport 객체
        """
        # 1. 종목명 조회
        if stock_name is None:
            stock_name = self._get_stock_name(ticker)
        
        # 2. 데이터 수집
        technical_data = self._get_technical_data(ticker)
        sentiment_data = self._get_sentiment_data(ticker)
        buzz_data = self._get_buzz_data(ticker)
        
        # 3. 사용자 프로필 로드 (Phase 20)
        profile = None
        if user_id and self.profile_repo:
            try:
                profile = self.profile_repo.load(user_id)
            except Exception as e:
                logger.warning(f"Failed to load profile for {user_id}: {e}")
        
        # 4. 프롬프트 구성
        prompt = self._build_analyst_prompt(
            ticker=ticker,
            stock_name=stock_name,
            technical=technical_data,
            sentiment=sentiment_data,
            buzz=buzz_data,
            profile=profile
        )
        
        # 5. AI 생성
        try:
            response = self.llm.generate(prompt)
            report = self._parse_response(ticker, stock_name, response)
        except Exception as e:
            logger.error(f"AI generation failed for {ticker}: {e}")
            report = self._create_fallback_report(ticker, stock_name)
        
        # 6. 프로필 기반 후처리 (Phase 20)
        if profile:
            report = self._adjust_for_profile(report, profile)
        
        # 7. 데이터 소스 기록
        report.data_sources = self._get_data_sources(
            technical_data, sentiment_data, buzz_data
        )
        
        return report
    
    def _get_stock_name(self, ticker: str) -> str:
        """종목명 조회"""
        if self.stock_repo:
            try:
                info = self.stock_repo.get_stock_info(ticker)
                return info.get('name', ticker)
            except:
                pass
        
        # yfinance 폴백
        try:
            import yfinance as yf
            stock = yf.Ticker(ticker)
            info = stock.info
            return info.get('shortName', info.get('longName', ticker))
        except:
            return ticker
    
    def _get_technical_data(self, ticker: str) -> Dict[str, Any]:
        """기술적 분석 데이터 수집"""
        try:
            import yfinance as yf
            stock = yf.Ticker(ticker)
            hist = stock.history(period="1mo")
            
            if hist.empty:
                return {}
            
            # RSI 계산
            close = hist['Close']
            delta = close.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            
            # 현재가 및 변동률
            current_price = close.iloc[-1]
            prev_close = close.iloc[-2] if len(close) > 1 else current_price
            change_pct = ((current_price - prev_close) / prev_close * 100)
            
            # 변동성 계산
            returns = close.pct_change().dropna()
            volatility = returns.std() * 100
            
            return {
                'current_price': current_price,
                'change_pct': change_pct,
                'rsi': rsi.iloc[-1] if not rsi.empty else None,
                'volatility': volatility,
                'volume': hist['Volume'].iloc[-1],
                'avg_volume': hist['Volume'].mean()
            }
        except Exception as e:
            logger.warning(f"Failed to get technical data for {ticker}: {e}")
            return {}
    
    def _get_sentiment_data(self, ticker: str) -> Optional[Dict[str, Any]]:
        """감성 분석 데이터 수집 (Phase 18)"""
        if not self.sentiment_service:
            return None
        
        try:
            features = self.sentiment_service.get_sentiment_features(
                ticker=ticker,
                lookback_days=7
            )
            return features
        except Exception as e:
            logger.warning(f"Failed to get sentiment data for {ticker}: {e}")
            return None
    
    def _get_buzz_data(self, ticker: str) -> Optional[Dict[str, Any]]:
        """Market Buzz 데이터 수집 (Phase 21)"""
        if not self.market_buzz_service:
            return None
        
        try:
            buzz_score_obj = self.market_buzz_service.calculate_buzz_score(ticker)
            if buzz_score_obj:
                return {
                    'base_score': buzz_score_obj.base_score,
                    'heat_level': buzz_score_obj.heat_level,
                    'volume_ratio': getattr(buzz_score_obj, 'volume_ratio', 1.0),
                    'volatility_ratio': getattr(buzz_score_obj, 'volatility_ratio', 1.0)
                }
        except Exception as e:
            logger.debug(f"Failed to get buzz data for {ticker}: {e}")
        
        return None
    
    def _build_analyst_prompt(
        self,
        ticker: str,
        stock_name: str,
        technical: Dict[str, Any],
        sentiment: Optional[Dict[str, Any]],
        buzz: Optional[Dict[str, Any]],
        profile: Optional[Any]
    ) -> str:
        """투자 분석가 스타일 프롬프트 구성"""
        
        prompt = f"""당신은 전문 주식 애널리스트입니다. 아래 데이터를 분석하여 투자 의견을 제시하세요.

종목: {stock_name} ({ticker})

"""
        
        # 기술적 분석 데이터
        if technical:
            # RSI 값 포맷팅 (f-string 외부에서 처리)
            rsi_val = technical.get('rsi')
            rsi_str = f"{rsi_val:.1f}" if rsi_val is not None else "N/A"
            
            prompt += f"""기술적 분석:
- 현재가: {technical.get('current_price', 0):,.0f}
- 등락률: {technical.get('change_pct', 0):+.2f}%
- RSI: {rsi_str}
- 변동성: {technical.get('volatility', 0):.2f}%
- 거래량: {technical.get('volume', 0):,.0f} (평균: {technical.get('avg_volume', 0):,.0f})

"""
        
        # 감성 분석 데이터 (Phase 18)
        if sentiment:
            score = sentiment.get('sentiment_score', 0.5)
            prompt += f"""뉴스 감성 분석:
- 감성 점수: {score:.2f} (0=매우 부정적, 1=매우 긍정적)
- 판정: {"긍정적 📈" if score > 0.6 else "부정적 📉" if score < 0.4 else "중립 ➡️"}

"""
        
        # Market Buzz 데이터 (Phase 21)
        if buzz:
            heat_emoji = "🔥" if buzz['heat_level'] == "HOT" else "🌤️" if buzz['heat_level'] == "WARM" else "❄️"
            prompt += f"""시장 관심도 (Market Buzz):
- Buzz 점수: {buzz['base_score']:.0f}/100
- 시장 열기: {buzz['heat_level']} {heat_emoji}
- 거래량 비율: {buzz['volume_ratio']:.2f}x (평균 대비)

"""
            if buzz['volume_ratio'] > 2.0:
                prompt += "⚠️ 주의: 최근 거래량이 급증했습니다. 단기 모멘텀이 강합니다.\n\n"
        
        # 프로필 기반 지시 (Phase 20)
        if profile:
            try:
                risk_value = profile.risk_tolerance.value
                profile_type = profile.profile_type
                
                prompt += f"""[사용자 투자 성향: {profile_type}]
"""
                
                if risk_value <= 40:  # 안정형
                    prompt += """- 이 사용자는 안정적인 투자를 선호합니다.
- 변동성이 큰 종목은 신중하게 평가하세요.
- 리스크 요인을 명확히 강조하세요.

"""
                elif risk_value > 60:  # 공격형
                    prompt += """- 이 사용자는 공격적인 투자를 선호합니다.
- 성장 가능성과 모멘텀을 중심으로 분석하세요.
- 높은 수익률 기회를 강조하세요.

"""
                
                if hasattr(profile, 'preferred_sectors') and profile.preferred_sectors:
                    sectors_str = ", ".join(profile.preferred_sectors[:3])
                    prompt += f"[선호 섹터: {sectors_str}]\n\n"
                    
            except Exception as e:
                logger.debug(f"Failed to add profile to prompt: {e}")
        
        # 분석 요청
        prompt += """[분석 요청]
위 데이터를 종합하여 다음 형식으로 투자 의견을 제시하세요:

```
신호: [STRONG_BUY/BUY/HOLD/SELL/STRONG_SELL 중 하나]
신뢰도: [0-100 사이 숫자]
요약: [3-5줄 핵심 분석 요약]
논리: [상세 분석 논리 - 기술적/감성적/시장 관심도 종합]
```
"""
        
        return prompt
    
    def _parse_response(
        self,
        ticker: str,
        stock_name: str,
        response: str
    ) -> InvestmentReport:
        """AI 응답 파싱"""
        
        # 기본값
        signal = SignalType.HOLD
        confidence = 50.0
        summary = "분석 결과를 파싱할 수 없습니다."
        reasoning = response
        
        try:
            # 신호 추출
            signal_match = re.search(r'신호:\s*(\w+)', response)
            if signal_match:
                signal = SignalType.from_string(signal_match.group(1))
            
            # 신뢰도 추출
            confidence_match = re.search(r'신뢰도:\s*(\d+)', response)
            if confidence_match:
                confidence = float(confidence_match.group(1))
            
            # 요약 추출
            summary_match = re.search(r'요약:\s*(.+?)(?=논리:|$)', response, re.DOTALL)
            if summary_match:
                summary = summary_match.group(1).strip()
            
            # 논리 추출
            reasoning_match = re.search(r'논리:\s*(.+?)(?=```|$)', response, re.DOTALL)
            if reasoning_match:
                reasoning = reasoning_match.group(1).strip()
                
        except Exception as e:
            logger.warning(f"Failed to parse AI response: {e}")
        
        return InvestmentReport(
            ticker=ticker,
            stock_name=stock_name,
            signal=signal,
            confidence_score=confidence,
            summary=summary,
            reasoning=reasoning,
            generated_at=datetime.now()
        )
    
    def _create_fallback_report(
        self,
        ticker: str,
        stock_name: str
    ) -> InvestmentReport:
        """AI 실패 시 폴백 리포트"""
        return InvestmentReport(
            ticker=ticker,
            stock_name=stock_name,
            signal=SignalType.HOLD,
            confidence_score=0,
            summary="AI 분석에 실패했습니다. 잠시 후 다시 시도해주세요.",
            reasoning="API 호출 실패 또는 응답 파싱 오류",
            generated_at=datetime.now()
        )
    
    def _adjust_for_profile(
        self,
        report: InvestmentReport,
        profile: Any
    ) -> InvestmentReport:
        """프로필에 맞지 않는 추천 조정 (Phase 20)"""
        try:
            risk_value = profile.risk_tolerance.value
            
            # 변동성 추정 (간이)
            technical = self._get_technical_data(report.ticker)
            volatility = technical.get('volatility', 2.0) / 100  # 0~1 스케일
            
            # 안정형 + 고변동성 → 신호 하향 조정
            if risk_value <= 40 and volatility > 0.035:
                if report.signal == SignalType.STRONG_BUY:
                    report.signal = SignalType.BUY
                    report.confidence_score *= 0.8
                    report.profile_warning = "⚠️ 이 종목은 변동성이 높아 안정형 투자자에게는 신중한 접근이 필요합니다."
                    report.profile_adjusted = True
            
            # 공격형 + 저변동성 → 경고 추가
            if risk_value > 60 and volatility < 0.015:
                report.profile_warning = "💡 이 종목은 안정적이지만 단기 수익률은 제한적일 수 있습니다."
                report.profile_adjusted = True
                
        except Exception as e:
            logger.debug(f"Failed to adjust for profile: {e}")
        
        return report
    
    def _get_data_sources(
        self,
        technical: Dict[str, Any],
        sentiment: Optional[Dict[str, Any]],
        buzz: Optional[Dict[str, Any]]
    ) -> list:
        """사용된 데이터 소스 목록"""
        sources = []
        
        if technical:
            sources.append("기술적 분석 (yfinance)")
        if sentiment:
            sources.append("뉴스 감성 분석 (Phase 18)")
        if buzz:
            sources.append("Market Buzz (Phase 21)")
        
        return sources
