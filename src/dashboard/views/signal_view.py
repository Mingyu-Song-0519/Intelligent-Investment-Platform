"""
Signal View
매매 신호 UI 컴포넌트
Clean Architecture: Presentation Layer
"""
import streamlit as st
import logging

logger = logging.getLogger(__name__)


def _get_signal_service():
    """SignalGeneratorService 인스턴스 생성"""
    from src.services.signal_generator_service import SignalGeneratorService
    from src.services.investment_report_service import InvestmentReportService
    from src.infrastructure.external.gemini_client import Gemini Client
    from src.infrastructure.external.pykrx_gateway import PyKRXGateway, MockPyKRXGateway
    
    # 의존성 주입
    report_service = None
    sentiment_service = None
    pykrx_gateway = None
    market_buzz_service = None
    
    # AI Report Service
    try:
        llm_client = GeminiClient()
        if not llm_client.is_available():
            from src.infrastructure.external.gemini_client import MockLLMClient
            llm_client = MockLLMClient()
        
        report_service = InvestmentReportService(llm_client=llm_client)
    except Exception as e:
        logger.debug(f"Report service init failed: {e}")
    
    # Sentiment Service
    try:
        from src.services.sentiment_analysis_service import SentimentAnalysisService
        sentiment_service = SentimentAnalysisService()
    except ImportError:
        pass
    
    # PyKRX Gateway
    try:
        gateway = PyKRXGateway()
        if gateway.is_available():
            pykrx_gateway = gateway
        else:
            pykrx_gateway = MockPyKRXGateway()
    except Exception as e:
        logger.debug(f"PyKRX init failed: {e}")
        pykrx_gateway = MockPyKRXGateway()
    
    # Market Buzz Service
    try:
        from src.services.market_buzz_service import MarketBuzzService
        from src.infrastructure.repositories.sector_repository import SectorRepository
        sector_repo = SectorRepository()
        market_buzz_service = MarketBuzzService(sector_repo)
    except ImportError:
        pass
    
    return SignalGeneratorService(
        report_service=report_service,
        sentiment_service=sentiment_service,
        pykrx_gateway=pykrx_gateway,
        market_buzz_service=market_buzz_service
    )


def render_signal_card(ticker: str, stock_name: str, user_id: str = "default_user"):
    """
    매매 신호 카드 렌더링
    
    Args:
        ticker: 종목 코드
        stock_name: 종목명
        user_id: 사용자 ID
    """
    if st.button("📊 매매 신호 생성", key=f"signal_btn_{ticker}", width="stretch"):
        with st.spinner("매매 신호를 생성하는 중..."):
            try:
                service = _get_signal_service()
                signal = service.generate_signal(ticker, stock_name, user_id)
                
                # 세션에 저장
                st.session_state[f"signal_{ticker}"] = signal
                st.rerun()
                
            except Exception as e:
                st.error(f"신호 생성 실패: {e}")
    
    # 저장된 신호 표시
    signal_key = f"signal_{ticker}"
    if signal_key in st.session_state:
        signal = st.session_state[signal_key]
        _display_signal(signal)
        
        # 닫기 버튼
        if st.button("✖ 닫기", key=f"close_signal_{ticker}"):
            del st.session_state[signal_key]
            st.rerun()


def _display_signal(signal):
    """매매 신호 카드 UI"""
    from src.domain.signal import TradingSignal
    
    st.markdown("---")
    st.subheader(f"📊 매매 신호: {signal.stock_name}")
    
    # 신호 및 신뢰도
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        # 신호 타입에 따른 색상
        from src.domain.ai_report import InvestmentReport
        report_dummy = type('obj', (object,), {'signal': signal.signal_type})()
        signal_color = {
            'STRONG_BUY': "#00C853",
            'BUY': "#4CAF50",
            'HOLD': "#9E9E9E",
            'SELL': "#FF9800",
            'STRONG_SELL': "#F44336"
        }.get(signal.signal_type.name, "#9E9E9E")
        
        signal_html = f"""
        <div style="
            background-color: {signal_color}20;
            border-left: 4px solid {signal_color};
            padding: 10px 15px;
            border-radius: 5px;
        ">
            <span style="font-size: 20px; font-weight: bold; color: {signal_color};">
                {signal.signal_type.value}
            </span>
            <span style="color: gray; margin-left: 10px;">
                (신호 강도: {signal.signal_strength})
            </span>
        </div>
        """
        st.markdown(signal_html, unsafe_allow_html=True)
    
    with col2:
        st.metric("종합 신뢰도", f"{signal.confidence:.0f}점")
    
    with col3:
        st.caption("생성 시각")
        st.text(signal.generated_at.strftime("%H:%M:%S"))
    
    # 발동 조건
    if signal.triggers:
        st.markdown("#### ✅ 발동 조건")
        for trigger in signal.triggers:
            st.success(f"• {trigger}")
    else:
        st.info("발동된 강력 조건이 없습니다.")
    
    # 개별 점수 상세
    with st.expander("📈 세부 점수 분석", expanded=False):
        score_data = [
            ("AI 신뢰도 (35%)", signal.ai_score, signal.ai_prediction_confident),
            ("감성 분석 (25%)", signal.sentiment_score, signal.sentiment_positive),
            ("거래량 (20%)", signal.volume_score, signal.volume_spike_detected),
            ("기관 수급 (20%)", signal.institution_score, signal.institution_buying)
        ]
        
        for label, score, flag in score_data:
            col_label, col_score, col_flag = st.columns([2, 1, 1])
            with col_label:
                st.text(label)
            with col_score:
                st.text(f"{score:.0f}점")
            with col_flag:
                if flag:
                    st.success("✅")
                else:
                    st.text("—")
    
    # 시장 상황
    if signal.market_regime:
        regime_emoji = {"상승장": "🟢", "하락장": "🔴", "횡보장": "🟡"}.get(signal.market_regime.value, "")
        st.caption(f"{regime_emoji} 시장 상황: {signal.market_regime.value}")
    
    # 면책 조항
    st.caption("⚠️ 본 신호는 AI가 생성한 참고 자료이며, 투자 결정의 책임은 사용자에게 있습니다.")
