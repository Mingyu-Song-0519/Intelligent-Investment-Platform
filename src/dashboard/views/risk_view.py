"""
리스크 분석 뷰 모듈

클린 아키텍처:
- Presentation Layer: Streamlit UI 렌더링
- Application Layer: 리스크 분석 서비스
"""
import streamlit as st
from src.analyzers.risk_manager import RiskManager
from src.dashboard.utils.data_cache import get_cached_stock_data


def display_risk_analysis():
    """리스크 분석 뷰"""
    st.header("⚠️ 리스크 분석")
    
    selected_ticker = st.session_state.get('selected_ticker')
    selected_stock = st.session_state.get('selected_stock')
    
    if not selected_ticker:
        st.warning("종목을 먼저 선택해주세요.")
        return
    
    period = st.selectbox("분석 기간", ['3mo', '6mo', '1y', '2y'], index=2)
    
    if st.button("📊 리스크 분석 시작", type="primary"):
        with st.spinner("리스크 분석 중..."):
            try:
                # 데이터 수집
                df = get_cached_stock_data(selected_ticker, period)
                
                if df.empty:
                    st.error("데이터를 불러올 수 없습니다.")
                    return
                
                # 리스크 분석
                risk_manager = RiskManager(df)
                risk_metrics = risk_manager.get_risk_metrics()
                
                # 결과 표시
                st.success("✅ 리스크 분석 완료")
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("VaR (95%)", f"{risk_metrics.get('var_95', 0)*100:.2f}%")
                    st.caption("95% 확률로 발생 가능한 최대 손실")
                
                with col2:
                    st.metric("CVaR (95%)", f"{risk_metrics.get('cvar_95', 0)*100:.2f}%")
                    st.caption("극단적 손실 시나리오 평균")
                
                with col3:
                    st.metric("변동성 (연환산)", f"{risk_metrics.get('volatility', 0)*100:.2f}%")
                    st.caption("가격 변동 폭")
                
                # 리스크 등급
                st.subheader("🎯 리스크 등급")
                risk_level = risk_manager.get_risk_level()
                risk_colors = {
                    '매우 낮음': 'success',
                    '낮음': 'info',
                    '보통': 'warning',
                    '높음': 'error',
                    '매우 높음': 'error'
                }
                risk_color = risk_colors.get(risk_level, 'info')
                
                if risk_color == 'success':
                    st.success(f"리스크 등급: {risk_level}")
                elif risk_color == 'info':
                    st.info(f"리스크 등급: {risk_level}")
                elif risk_color == 'warning':
                    st.warning(f"리스크 등급: {risk_level}")
                else:
                    st.error(f"리스크 등급: {risk_level}")
                
            except Exception as e:
                st.error(f"리스크 분석 오류: {e}")
                import traceback
                st.code(traceback.format_exc())
