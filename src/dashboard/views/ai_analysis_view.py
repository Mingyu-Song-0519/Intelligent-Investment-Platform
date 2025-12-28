"""
AI Analysis View
AI 투자 분석 UI 컴포넌트
Clean Architecture: Presentation Layer
"""
import streamlit as st
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def _get_report_service():
    """InvestmentReportService 인스턴스 생성"""
    from src.services.investment_report_service import InvestmentReportService
    from src.infrastructure.external.gemini_client import GeminiClient
    
    # 의존성 주입
    llm_client = None
    sentiment_service = None
    profile_repo = None
    market_buzz_service = None
    
    # Gemini 클라이언트
    try:
        llm_client = GeminiClient()
        if not llm_client.is_available():
            logger.warning("GeminiClient not available, using mock")
            from src.infrastructure.external.gemini_client import MockLLMClient
            llm_client = MockLLMClient()
    except Exception as e:
        logger.warning(f"Failed to create GeminiClient: {e}")
        from src.infrastructure.external.gemini_client import MockLLMClient
        llm_client = MockLLMClient()
    
    # 감성 분석 서비스 (Phase 18)
    try:
        from src.services.sentiment_analysis_service import SentimentAnalysisService
        sentiment_service = SentimentAnalysisService()
    except ImportError:
        pass
    
    # 프로필 저장소 (Phase 20)
    try:
        from src.infrastructure.repositories.profile_repository import SQLiteProfileRepository
        profile_repo = SQLiteProfileRepository()
    except ImportError:
        pass
    
    # Market Buzz 서비스 (Phase 21)
    try:
        from src.services.market_buzz_service import MarketBuzzService
        from src.infrastructure.repositories.sector_repository import SectorRepository
        sector_repo = SectorRepository()
        market_buzz_service = MarketBuzzService(sector_repo)
    except ImportError:
        pass
    
    return InvestmentReportService(
        llm_client=llm_client,
        sentiment_service=sentiment_service,
        profile_repo=profile_repo,
        market_buzz_service=market_buzz_service
    )


def render_ai_analysis_button(ticker: str, stock_name: str, user_id: str = "default_user"):
    """
    AI 분석 버튼 렌더링
    
    Args:
        ticker: 종목 코드
        stock_name: 종목명
        user_id: 사용자 ID (프로필 기반 개인화용)
    """
    col1, col2 = st.columns([3, 1])
    
    with col2:
        if st.button("🤖 AI 분석", key=f"ai_btn_{ticker}", width="stretch"):
            with st.spinner("AI가 분석 중입니다..."):
                try:
                    service = _get_report_service()
                    report = service.generate_report(
                        ticker=ticker,
                        stock_name=stock_name,
                        user_id=user_id
                    )
                    
                    # 세션에 저장
                    st.session_state[f"ai_report_{ticker}"] = report
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"AI 분석 실패: {e}")
    
    # 저장된 리포트 표시
    report_key = f"ai_report_{ticker}"
    if report_key in st.session_state:
        report = st.session_state[report_key]
        _display_report(report)
        
        # 닫기 버튼
        if st.button("✖ 닫기", key=f"close_report_{ticker}"):
            del st.session_state[report_key]
            st.rerun()


def _display_report(report):
    """AI 리포트 카드 UI"""
    from src.domain.ai_report import InvestmentReport, SignalType
    
    st.markdown("---")
    st.subheader(f"🤖 AI 분석 리포트: {report.stock_name}")
    
    # 신호 및 신뢰도
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        signal_html = f"""
        <div style="
            background-color: {report.signal_color}20;
            border-left: 4px solid {report.signal_color};
            padding: 10px 15px;
            border-radius: 5px;
        ">
            <span style="font-size: 24px;">{report.signal_emoji}</span>
            <span style="font-size: 20px; font-weight: bold; color: {report.signal_color};">
                {report.signal.value}
            </span>
        </div>
        """
        st.markdown(signal_html, unsafe_allow_html=True)
    
    with col2:
        # 신뢰도 게이지
        confidence_color = "#4CAF50" if report.confidence_score >= 70 else "#FFC107" if report.confidence_score >= 40 else "#F44336"
        st.metric("신뢰도", f"{report.confidence_score:.0f}점")
    
    with col3:
        st.caption("생성 시각")
        st.text(report.generated_at.strftime("%H:%M:%S"))
    
    # 프로필 경고 (Phase 20)
    if report.profile_warning:
        st.warning(report.profile_warning)
    
    # 요약
    st.markdown("#### 📝 분석 요약")
    st.info(report.summary)
    
    # 상세 논리 (접기)
    with st.expander("📊 상세 분석 논리", expanded=False):
        st.markdown(report.reasoning)
    
    # 데이터 소스
    if report.data_sources:
        st.caption(f"📌 분석 데이터: {', '.join(report.data_sources)}")
    
    # 면책 조항
    st.caption("⚠️ 본 분석은 AI가 생성한 참고 자료이며, 투자 결정의 책임은 사용자에게 있습니다.")


def render_ai_analysis_tab(ticker: str, stock_name: str, user_id: str = "default_user"):
    """
    AI 분석 전용 탭 렌더링
    
    개별 종목 상세 페이지에서 사용
    """
    st.header("🤖 AI 투자 분석")
    
    # 분석 요청 버튼
    if st.button("📊 AI 분석 시작", key=f"ai_start_{ticker}", width="stretch"):
        with st.spinner("AI가 분석 중입니다... (약 5-10초 소요)"):
            try:
                service = _get_report_service()
                report = service.generate_report(
                    ticker=ticker,
                    stock_name=stock_name,
                    user_id=user_id
                )
                
                st.session_state[f"ai_report_{ticker}"] = report
                st.success("✅ 분석 완료!")
                st.rerun()
                
            except Exception as e:
                st.error(f"AI 분석 실패: {e}")
                logger.error(f"AI analysis failed for {ticker}: {e}")
    
    # 저장된 리포트 표시
    report_key = f"ai_report_{ticker}"
    if report_key in st.session_state:
        report = st.session_state[report_key]
        _display_report(report)
    else:
        st.info("🔍 'AI 분석 시작' 버튼을 클릭하여 AI의 투자 분석을 받아보세요.")
        
        # 분석 내용 미리보기
        with st.expander("📖 AI 분석에 포함되는 내용"):
            st.markdown("""
            - **기술적 분석**: RSI, 변동성, 거래량 분석
            - **뉴스 감성 분석**: 최근 7일 뉴스 감성 점수
            - **시장 관심도**: Market Buzz 점수 및 열기
            - **개인화 분석**: 사용자 투자 성향에 맞춘 조언
            """)
