"""
Screener View
AI 종목 발굴 UI
Clean Architecture: Presentation Layer
"""
import streamlit as st
import pandas as pd
import logging

logger = logging.getLogger(__name__)


def _get_screener_service():
    """ScreenerService 인스턴스 생성"""
    from src.services.screener_service import ScreenerService
    from src.services.signal_generator_service import SignalGeneratorService
    from src.infrastructure.external.pykrx_gateway import PyKRXGateway, MockPyKRXGateway
    
    # Signal Service - 비활성화하여 다중 요소 폴백 점수 사용
    # TODO: SignalGeneratorService가 동일한 점수만 반환하는 문제 해결 후 다시 활성화
    signal_service = None
    # try:
    #     from src.services.investment_report_service import InvestmentReportService
    #     from src.infrastructure.external.gemini_client import GeminiClient
    #     
    #     llm_client = GeminiClient()
    #     if not llm_client.is_available():
    #         from src.infrastructure.external.gemini_client import MockLLMClient
    #         llm_client = MockLLMClient()
    #     
    #     report_service = InvestmentReportService(llm_client=llm_client)
    #     signal_service = SignalGeneratorService(report_service=report_service)
    # except Exception as e:
    #     logger.debug(f"Signal service init failed: {e}")
    
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
        pykrx_gateway=pykrx_gateway
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
        top_n = st.number_input("추천 개수", min_value=3, max_value=50, value=10, key="screener_top_n")
    
    with col3:
        if st.button("🔍 종목 발굴", type="primary", use_container_width=True):
            st.session_state.screener_run = True
    
    # 필터 조건 안내
    with st.expander("📋 필터 조건", expanded=False):
        st.markdown("""
        ### 🎯 AI가 이렇게 종목을 골라요
        
        **1단계: 기본 조건** (약 2,800개 → 800개)
        - 💰 **시가총액**: 1,000억원 이상 (안정적인 중대형주)
        - 📊 **거래량**: 10만주 이상 (활발하게 거래되는 종목)
        
        **2단계: 저가 매수 기회 포착** (800개 → 450개)
        - 📉 **RSI 50 이하**: 과열되지 않은 종목 (낮을수록 저가 매수 기회)
          - RSI 30 이하 = 강한 저가 구간
          - RSI 30~50 = 적정~저가 구간
        
        **3단계: 기관 수급 확인** (450개 → 50개) *한국 주식만*
        - 🏢 **기관 3일 연속 매수**: 큰 손들이 주목하는 종목
        
        **최종 선별**
        - 🤖 **AI 종합 점수 순위**: 위 조건을 모두 통과한 종목 중 상위 50개
        - ⏱️ 전체 분석 시간: 약 20초
        """)
    
    # 스크리닝 실행
    if st.session_state.get('screener_run', False):
        st.session_state.screener_run = False
        
        # market 값은 위젯의 key로 자동 저장되므로 session_state에서 직접 가져옴
        market = st.session_state.get('screener_market', 'KR')
        
        # Phase G: 전체 시장 스크리닝 표시
        import time
        spinner_msg = f"🚀 AI가 {'전체 KOSPI/KOSDAQ' if market == 'KR' else market} 시장을 분석 중... (5-10초 소요)"
        
        with st.spinner(spinner_msg):
            start_time = time.time()
            try:
                service = _get_screener_service()
                user_id = st.session_state.get('user_id', 'default_user')
                
                picks = service.run_daily_screen(
                    user_id=user_id,
                    market=market,
                    top_n=top_n
                )
                
                elapsed_time = time.time() - start_time
                st.session_state.screener_picks = picks
                # st.session_state.screener_market = market  ← 삭제! (위젯이 자동 관리)
                st.success(f"✅ {len(picks)}개 종목 발굴 완료! (소요 시간: {elapsed_time:.1f}초)")
                
            except Exception as e:
                st.error(f"스크리닝 실패: {e}")
                logger.error(f"Screener failed: {e}")
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
                # 순위 배지 (색상: 1등 금색, 2등 은색, 3등 동색, 4등이하 하늘색)
                rank_color = "#FFD700" if i == 1 else "#C0C0C0" if i == 2 else "#CD7F32" if i == 3 else "#ADD8E6"
                
                col_rank, col_info, col_score, col_detail = st.columns([0.5, 2, 1, 1])
                
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
                    # 매매 신호를 사용자 친화적으로 표시
                    signal_display = {
                        '매수': '🔥 매수 추천',
                        '보유': '💎 보유 추천',
                        '매도': '⚠️ 매도 검토',
                        '관망': '👀 관망 추천'
                    }.get(pick.signal_type, pick.signal_type)
                    
                    # 추천 이유를 쉬운 말로 변환
                    reason_display = pick.reason
                    if '기관' in pick.reason and '연속' in pick.reason:
                        reason_display = '기관 3일 연속 매수'
                    elif 'RSI' in pick.reason and '과매도' in pick.reason:
                        reason_display = '과매도 구간 (저가 매수 기회)'
                    elif 'PBR' in pick.reason:
                        reason_display = '저평가 종목'
                    
                    st.text(signal_display)
                    st.caption(reason_display)
                
                # 세부 정보
                with st.expander(f"📈 {pick.stock_name} 상세 정보"):
                    # Phase 1: 2행 × 3열 그리드로 확장
                    st.markdown("#### 📊 기본 정보")
                    detail_row1_col1, detail_row1_col2, detail_row1_col3 = st.columns(3)
                    
                    with detail_row1_col1:
                        if pick.marketcap:
                            # 시가총액을 조 단위로 표시
                            marketcap_trillion = pick.marketcap / 1_000_000_000_000
                            st.metric("시가총액", f"{marketcap_trillion:.1f}조원", help="기업의 총 가치 (발행주식수 × 주가). 기업 규모를 나타냅니다.")
                        else:
                            st.metric("시가총액", "—", help="데이터를 가져올 수 없습니다.")
                    
                    with detail_row1_col2:
                        if pick.per:
                            st.metric("PER", f"{pick.per:.1f}", help="주가수익비율 (Price to Earnings Ratio). 주가 ÷ 주당순이익. 낮을수록 저평가.")
                        else:
                            st.metric("PER", "—", help="데이터를 가져올 수 없습니다.")
                    
                    with detail_row1_col3:
                        if pick.pbr:
                            st.metric("PBR", f"{pick.pbr:.2f}", help="주가순자산비율 (Price to Book Ratio). 주가 ÷ 주당순자산. 1 미만이면 저평가 가능성.")
                        else:
                            st.metric("PBR", "—", help="데이터를 가져올 수 없습니다.")
                    
                    detail_row2_col1, detail_row2_col2, detail_row2_col3 = st.columns(3)
                    
                    with detail_row2_col1:
                        if pick.dividend_yield:
                            st.metric("배당수익률", f"{pick.dividend_yield:.2f}%", help="1년간 받을 배당금 ÷ 주가. 높을수록 배당 매력적. (단위: %)")
                        else:
                            st.metric("배당수익률", "—", help="배당을 지급하지 않거나 데이터가 없습니다.")
                    
                    with detail_row2_col2:
                        if pick.week52_high:
                            st.metric("52주 최고", f"{pick.week52_high:,.0f}원", help="최근 52주(1년) 동안의 최고 주가. 저항선 참고.")
                        else:
                            st.metric("52주 최고", "—", help="데이터를 가져올 수 없습니다.")
                    
                    with detail_row2_col3:
                        if pick.week52_low:
                            st.metric("52주 최저", f"{pick.week52_low:,.0f}원", help="최근 52주(1년) 동안의 최저 주가. 지지선 참고.")
                        else:
                            st.metric("52주 최저", "—", help="데이터를 가져올 수 없습니다.")
                    
                    # 기술적 지표 및 수급 정보
                    st.markdown("#### 📉 기술적 분석")
                    tech_col1, tech_col2, tech_col3 = st.columns(3)
                    
                    with tech_col1:
                        if pick.rsi:
                            st.metric("RSI", f"{pick.rsi:.1f}")
                        else:
                            st.metric("RSI", "—")
                    
                    with tech_col2:
                        if pick.institution_streak:
                            st.success("✅ 기관 연속 매수")
                        else:
                            st.info("— 수급 정보 없음")
                    
                    with tech_col3:
                        # Phase 2: MA 지표 표시
                        if pick.ma_status:
                            st.metric("MA 신호", pick.ma_status)
                        elif pick.ma_5 and pick.ma_20:
                            if pick.current_price and pick.ma_5 > pick.ma_20:
                                st.metric("MA 신호", "정배열 🟢")
                            else:
                                st.metric("MA 신호", "역배열 🔴")
                        else:
                            st.metric("MA 신호", "—")
                    
                    # Phase 3: 가격 차트 시각화
                    st.markdown("#### 📈 가격 추이")
                    
                    # 차트 기간 선택
                    period_options = {
                        "1개월": 20,
                        "3개월": 60,
                        "6개월": 120,
                        "1년": 250
                    }
                    selected_period = st.selectbox(
                        "기간 선택",
                        options=list(period_options.keys()),
                        index=1,  # 기본 3개월
                        key=f"period_{i}"
                    )
                    days = period_options[selected_period]
                    
                    # OHLCV 데이터 조회 및 차트 렌더링
                    try:
                        from src.dashboard.views.chart_utils import render_stock_chart
                        ticker_code = pick.ticker.replace('.KS', '').replace('.KQ', '')
                        render_stock_chart(ticker_code, days, pick.stock_name)
                    except Exception as chart_e:
                        st.warning(f"차트 렌더링 실패: {str(chart_e)}")

                    
                    # Phase 4: 상세 분석 바로가기
                    st.markdown("---")
                    if st.button(f"🔍 {pick.stock_name} 상세 분석 보기", key=f"detail_{i}"):
                        st.session_state['analysis_ticker'] = pick.ticker.replace('.KS', '').replace('.KQ', '')
                        st.session_state['active_tab_name'] = '📊 단일 종목 분석'
                        st.rerun()
                
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
