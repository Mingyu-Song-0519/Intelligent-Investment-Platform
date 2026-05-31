"""
시장 폭 분석 뷰 모듈

클린 아키텍처:
- Presentation Layer: Streamlit UI 렌더링
- Application Layer: 시장 폭 분석 서비스
"""
import streamlit as st
from src.analyzers.market_breadth import MarketBreadthAnalyzer
from src.analyzers.volatility_analyzer import VolatilityAnalyzer
from src.utils.hints import get_hint_text


def display_market_breadth():
    """시장 폭 분석 뷰"""
    st.header("🏥 시장 체력 진단")
    st.markdown("시장 전체가 건강한지, 소수 종목만 오르는지 분석합니다.")
    
    # 힌트
    with st.expander("💡 시장 폭(Market Breadth)이란?", expanded=False):
        st.markdown(get_hint_text('breadth', 'detail'))
    
    current_market = st.session_state.get('current_market', 'KR')
    market_name = "한국 (KOSPI)" if current_market == "KR" else "미국 (NYSE/NASDAQ)"
    
    st.info(f"📊 현재 분석 대상: **{market_name}**")
    
    if st.button("🔍 시장 체력 분석 시작", type="primary"):
        with st.spinner("시장 데이터 수집 및 분석 중... (약 30초 소요)"):
            try:
                # 시장 폭 분석
                breadth_analyzer = MarketBreadthAnalyzer(market=current_market)
                summary = breadth_analyzer.get_breadth_summary()
                
                # 변동성 분석
                vol_analyzer = VolatilityAnalyzer()
                vix_current = vol_analyzer.get_current_vix()
                vix_regime, vix_color = vol_analyzer.volatility_regime()
                
                st.success("✅ 분석 완료!")
                
                # 종합 점수
                col1, col2 = st.columns(2)
                with col1:
                    st.metric(
                        label="🏆 시장 체력 점수",
                        value=f"{summary['breadth_score']}/100",
                        delta=summary['overall_status']
                    )
                with col2:
                    if vix_current:
                        st.metric(
                            label=f"😱 VIX (공포지수) {vix_color}",
                            value=f"{vix_current:.1f}",
                            delta=vix_regime
                        )
                
                st.markdown("---")
                
                # 상세 분석
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.markdown("### 📈 상승/하락 비율")
                    ad = summary['advance_decline']
                    if 'error' not in ad:
                        st.metric("상승 종목", f"{ad['advancing']}개")
                        st.metric("하락 종목", f"{ad['declining']}개")
                        st.metric("상승/하락 비율", f"{ad['ratio']:.2f}")
                        st.markdown(f"**{ad['breadth_status']}**")
                    else:
                        st.warning(ad['error'])
                
                with col2:
                    st.markdown("### 🔝 52주 신고가/신저가")
                    hl = summary['new_high_low']
                    if 'error' not in hl:
                        st.metric("신고가 종목", f"{hl['new_highs']}개")
                        st.metric("신저가 종목", f"{hl['new_lows']}개")
                        st.metric("신고가/신저가 비율", f"{hl['ratio']:.2f}")
                        st.markdown(f"**{hl['status']}**")
                    else:
                        st.warning(hl['error'])
                
                with col3:
                    st.markdown("### 🎯 시장 집중도")
                    conc = summary['concentration']
                    if 'error' not in conc:
                        st.metric("상위 10종목 수익률", f"{conc['top10_return']:.1f}%")
                        st.metric("전체 시장 수익률", f"{conc['market_return']:.1f}%")
                        st.metric("집중도 비율", f"{conc['concentration_ratio']:.1f}배")
                        st.markdown(f"**{conc['warning']}**")
                    else:
                        st.warning(conc['error'])
                
                # 해석 가이드
                st.markdown("---")
                st.markdown("### 📖 해석 가이드")
                st.markdown("""
                - **시장 체력 점수 70+**: 🟢 건강한 시장, 상승 종목이 많고 폭넓은 참여
                - **시장 체력 점수 40-70**: 🟡 중립, 일부 섹터만 강세
                - **시장 체력 점수 40 미만**: 🔴 취약, 소수 대형주만 지수 견인 (주의!)
                - **VIX 15 미만**: 🟢 안정, 시장 불안 낮음
                - **VIX 25 이상**: 🔴 공포, 변동성 확대 예상
                """)
                
            except Exception as e:
                st.error(f"분석 중 오류 발생: {str(e)}")
                import traceback
                st.code(traceback.format_exc())
