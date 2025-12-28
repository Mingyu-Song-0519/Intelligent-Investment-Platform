"""
Screener View
AI 종목 발굴 UI
Clean Architecture: Presentation Layer
"""
import streamlit as st
import pandas as pd
import logging
from .chart_utils import render_stock_chart

logger = logging.getLogger(__name__)


def _get_screener_service():
    """ScreenerService 인스턴스 생성"""
    from src.services.screener_service import ScreenerService
    from src.services.signal_generator_service import SignalGeneratorService
    from src.infrastructure.external.pykrx_gateway import PyKRXGateway, MockPyKRXGateway

    # Signal Service
    signal_service = None
    try:
        from src.services.investment_report_service import InvestmentReportService
        from src.infrastructure.external.gemini_client import GeminiClient
        from src.services.sentiment_analysis_service import SentimentAnalysisService

        # session_state에서 API 키 가져오기
        user_api_key = st.session_state.get('gemini_api_key', None)
        llm_client = GeminiClient(api_key=user_api_key)

        if not llm_client.is_available():
            from src.infrastructure.external.gemini_client import MockLLMClient
            llm_client = MockLLMClient()
        
        report_service = InvestmentReportService(llm_client=llm_client)
        sentiment_service = SentimentAnalysisService(use_llm=True)
        signal_service = SignalGeneratorService(report_service=report_service, sentiment_service=sentiment_service)
    except Exception as e:
        logger.debug(f"Signal service init failed: {e}")
    
    # Profile Repo
    profile_repo = None
    try:
        from src.infrastructure.repositories.profile_repository import SQLiteProfileRepository
        profile_repo = SQLiteProfileRepository()
    except ImportError:
        pass
    
    # PyKRX Gateway
    pykrx_gateway = None
    try:
        gateway = PyKRXGateway()
        if gateway.is_available():
            pykrx_gateway = gateway
        else:
            pykrx_gateway = MockPyKRXGateway()
    except Exception as e:
        pykrx_gateway = MockPyKRXGateway()
    
    return ScreenerService(
        signal_service=signal_service,
        profile_repo=profile_repo,
        pykrx_gateway=pykrx_gateway,
        sentiment_service=sentiment_service if 'sentiment_service' in locals() else None
    )


def render_morning_picks():
    """오늘의 AI 추천주"""
    st.header("🌅 AI 종목 추천")
    st.markdown("**AI가 발굴한 오늘의 추천 종목입니다.**")
    
    # 설정
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        market = st.selectbox(
            "시장 선택",
            ["KR", "US"],
            format_func=lambda x: "🇰🇷 한국" if x == "KR" else "🇺🇸 미국",
            key="screener_market"
        )
    
    with col2:
        top_n = st.number_input("추천 개수", min_value=3, max_value=10, value=5, key="screener_top_n")
    
    with col3:
        if st.button("🔍 종목 발굴", type="primary", width="stretch"):
            st.session_state.screener_run = True
    
    # 필터 조건 안내
    with st.expander("📋 발굴 알고리즘 및 필터 조건", expanded=False):
        st.markdown("""
        **1단계: 시장 스캔 및 우선순위 선정**
        - KOSPI, KOSDAQ 전 종목 대상
        - 거래대금 상위 1000개 종목 우선 분석 (유동성 확보)
        
        **2단계: 기술적 저평가 필터링**
        - RSI < 50: 과매도권 또는 반등 초입 종목 선별
        
        **3단계: 수급 및 뉴스 분석**
        - 기관 투자자 3일 연속 순매수 여부 확인
        - **최근 7일 뉴스 감성 분석 (Gemini)**: 실적, 수주, 호재 등 맥락 분석
        
        **최종 평가 (AI Scoring)**
        - **저평가 매력**: RSI 깊이 및 PBR(주가순자산비율) 지표 종합
        - **성장 및 심리**: 기관 수급 및 **AI 뉴스 감성 점수(가산점)** 반영
        - **상승 모멘텀**: 이동평균선(MA) 추세 분석
        """)
    
    # 서비스 초기화 (공통 사용)
    service = _get_screener_service()
    
    # 스크리닝 실행
    if st.session_state.get('screener_run', False):
        st.session_state.screener_run = False
        
        # market 값은 위젯의 key로 자동 저장되므로 session_state에서 직접 가져옴
        market = st.session_state.get('screener_market', 'KR')
        
        with st.spinner(f"AI가 {market} 시장을 분석하는 중... (30초~1분 소요)"):
            try:
                user_id = st.session_state.get('user_id', 'default_user')
                
                picks = service.run_daily_screen(
                    user_id=user_id,
                    market=market,
                    top_n=top_n
                )
                
                st.session_state.screener_picks = picks
                # st.session_state.screener_market = market  ← 삭제! (위젯이 자동 관리)
                st.success(f"✅ {len(picks)}개 종목 발굴 완료!")
                
            except Exception as e:
                import traceback
                st.error(f"스크리닝 실패: {e}")
                logger.error(f"Screener failed: {e}")
                logger.error(f"Traceback:\n{traceback.format_exc()}")
                return
    
    # 결과 표시
    if 'screener_picks' in st.session_state:
        picks = st.session_state.screener_picks
        
        if not picks:
            st.info("조건을 만족하는 종목이 없습니다. 다른 시장을 선택하거나 나중에 다시 시도하세요.")
            return
        
        # 종목 리스트 표시 (return 삭제!)
        st.markdown("---")
        st.subheader(f"📊 추천 종목 ({len(picks)}개)")
        
        # 테이블 형식
        for i, pick in enumerate(picks, 1):
            with st.container():
                # 순위 배지 (4등부터 연한 하늘색)
                rank_color = "#FFD700" if i == 1 else "#C0C0C0" if i == 2 else "#CD7F32" if i == 3 else "#B3E5FC"
                
                # 간격 조절: 종목명 옆 빈 공간을 줄이고 점수와 매수/매도 사이를 조절
                col_rank, col_info, col_score, col_detail = st.columns([0.4, 1.6, 1, 1.2])
                
                with col_rank:
                    st.markdown(f"""
                    <div style="
                        background-color: {rank_color};
                        border-radius: 50%;
                        width: 40px;
                        height: 40px;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        font-weight: bold;
                        font-size: 18px;
                    ">
                        {i}
                    </div>
                    """, unsafe_allow_html=True)
                
                with col_info:
                    st.markdown(f"### {pick.stock_name}")
                    st.caption(f"📌 {pick.ticker}")
                    
                    if pick.current_price:
                        change_color = "red" if pick.change_pct and pick.change_pct > 0 else "blue"
                        st.markdown(f"가격: **{pick.current_price:,.0f}원** "
                                  f"<span style='color:{change_color}'>({pick.change_pct:+.2f}%)</span>",
                                  unsafe_allow_html=True)
                
                with col_score:
                    st.metric("AI 점수", f"{pick.ai_score:.0f}")
                    st.caption(f"신뢰도: {pick.confidence:.0f}%")
                
                with col_detail:
                    st.markdown(f"**{pick.signal_type}**")
                    st.caption(pick.reason)
                
                # 세부 정보
                with st.expander(f"📊 {pick.stock_name} 상세 분석 및 리포트"):
                    # 1. 펀더멘털 & 기술적 지표 (2x3 Grid)
                    st.markdown("#### 🔍 핵심 펀더멘털 & 지표")
                    f_col1, f_col2, f_col3 = st.columns(3)
                    with f_col1:
                        val_cap = f"{pick.marketcap/1e8:,.0f}억" if pick.marketcap else "정보없음"
                        st.metric("시가총액", val_cap, help="기업의 발행 주식 수에 현재 주가를 곱한 값으로, 기업의 전체 시장 가치를 나타냅니다.")
                        val_rsi = f"{pick.rsi:.1f}" if pick.rsi else "정보없음"
                        st.metric("RSI", val_rsi, help="가격 상승/하락 폭의 상대적 강도를 나타내는 지표인 RSI(14)입니다. 보통 30 이하는 과매도(매수 신호), 70 이상은 과매수(매도 신호)로 해석합니다.")
                    with f_col2:
                        val_per = f"{pick.per:.1f}배" if pick.per else "정보없음"
                        st.metric("PER", val_per, help="주가를 1주당 순이익(EPS)으로 나눈 값입니다. 낮을수록 기업 이익 대비 주가가 저렴함을 의미합니다.")
                        val_pbr = f"{pick.pbr:.2f}배" if pick.pbr else "정보없음"
                        st.metric("PBR", val_pbr, help="주가를 1주당 순자산(BPS)으로 나눈 값입니다. 1보다 작으면 주가가 장부 가치보다 낮게 거래되고 있음을 의미합니다.")
                    with f_col3:
                        val_div = f"{pick.dividend_yield:.1f}%" if pick.dividend_yield else "0.0%"
                        st.metric("배당수익률", val_div, help="주가 대비 연간 배당금의 비율입니다. 배당 투자의 수익성을 나타내는 주요 지표입니다.")
                        st.write(f"추세: **{pick.ma_status}**")
                        if pick.institution_streak:
                            st.success("🔥 기관 3일 연속 매수")
                    
                    st.markdown("---")
                    
                    # 2. 거래량 및 기타 정보 (52주 고/저)
                    if pick.week52_high and pick.week52_low:
                        st.markdown(f"**52주 가격 범위**: {pick.week52_low:,.0f} ~ {pick.week52_high:,.0f}")
                    
                    # 3. 차트 렌더링
                    if pick.ticker and service.pykrx_gateway:
                        ohlcv = service.pykrx_gateway.fetch_ohlcv(pick.ticker, period="3mo")
                        render_stock_chart(pick.ticker, ohlcv, pick.stock_name)

                    # 4. 상세 분석 페이지 이동 링크
                    if st.button(f"🔍 {pick.stock_name} 상세 분석 보기", key=f"btn_detail_{pick.ticker}"):
                        st.session_state.selected_ticker = pick.ticker
                        st.session_state.pending_tab = "🔬 AI 종목 분석"
                        st.rerun()

                st.markdown("---")
                
                st.markdown("---")
        
        # 내보내기 버튼
        if st.button("📥 CSV로 내보내기"):
            df = pd.DataFrame([
                {
                    '순위': i,
                    '종목명': p.stock_name,
                    '종목코드': p.ticker,
                    'AI점수': p.ai_score,
                    '신호': p.signal_type,
                    '현재가': p.current_price,
                    '등락률': p.change_pct,
                    'RSI': p.rsi,
                    'PBR': p.pbr,
                    '추천이유': p.reason
                }
                for i, p in enumerate(picks, 1)
            ])
            
            csv = df.to_csv(index=False, encoding='utf-8-sig')
            st.download_button(
                label="📥 다운로드",
                data=csv,
                file_name=f"ai_morning_picks_{st.session_state.get('screener_market', 'KR')}.csv",
                mime="text/csv"
            )
