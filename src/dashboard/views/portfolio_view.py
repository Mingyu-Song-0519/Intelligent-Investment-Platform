"""
포트폴리오 최적화 뷰 모듈

클린 아키텍처:
- Presentation Layer: Streamlit UI 렌더링
- Application Layer: 포트폴리오 최적화 서비스
"""
import streamlit as st
import pandas as pd
from src.optimizers.portfolio_optimizer import PortfolioOptimizer
from src.dashboard.utils.data_cache import get_cached_multi_stock_data


def display_portfolio_optimization():
    """포트폴리오 최적화 뷰"""
    st.header("💼 포트폴리오 최적화")
    st.markdown("Markowitz 평균-분산 최적화를 통한 최적 포트폴리오 비중 계산")
    
    # 종목 선택
    active_stock_names = st.session_state.get('active_stock_names', [])
    active_stock_list = st.session_state.get('active_stock_list', {})
    
    if not active_stock_names:
        st.warning("종목 리스트를 불러오는 중입니다...")
        return
    
    selected_stocks = st.multiselect(
        "포트폴리오에 포함할 종목 선택 (최소 2개)",
        active_stock_names,
        default=active_stock_names[:4] if len(active_stock_names) >= 4 else active_stock_names[:2]
    )
    
    col1, col2 = st.columns(2)
    with col1:
        period = st.selectbox("분석 기간", ['6mo', '1y', '2y', '5y'], index=2)
    with col2:
        risk_free = st.number_input("무위험 수익률 (%)", value=3.5, min_value=0.0, max_value=10.0, step=0.1)
    
    if len(selected_stocks) < 2:
        st.warning("최소 2개 종목을 선택해주세요.")
        return
    
    if st.button("🎯 최적 포트폴리오 계산", type="primary"):
        with st.spinner("데이터 수집 및 최적화 중..."):
            try:
                # 데이터 수집
                tickers = [active_stock_list[name] for name in selected_stocks]
                results = get_cached_multi_stock_data(tickers, period)
                
                if len(results) < 2:
                    st.error("최소 2개 종목의 데이터가 필요합니다.")
                    return
                
                # 수익률 계산
                returns_data = {}
                for ticker, df in results.items():
                    if not df.empty:
                        name = next((n for n, t in active_stock_list.items() if t == ticker), ticker)
                        returns_data[name.split('(')[0].strip()] = df.set_index('date')['close'].pct_change()
                
                returns_df = pd.DataFrame(returns_data).dropna()
                
                if len(returns_df) < 30:
                    st.error("분석에 필요한 데이터가 부족합니다.")
                    return
                
                # 포트폴리오 최적화
                optimizer = PortfolioOptimizer(returns_df, risk_free_rate=risk_free/100)
                
                max_sharpe = optimizer.optimize_max_sharpe()
                min_vol = optimizer.optimize_min_volatility()
                equal_weight = optimizer.get_equal_weight_portfolio()
                
                # 결과 표시
                st.success("✅ 최적화 완료!")
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.markdown("### 📈 최대 샤프 비율")
                    if max_sharpe['success']:
                        st.metric("기대 수익률", f"{max_sharpe['return']*100:.2f}%")
                        st.metric("변동성", f"{max_sharpe['volatility']*100:.2f}%")
                        st.metric("샤프 비율", f"{max_sharpe['sharpe']:.2f}")
                
                with col2:
                    st.markdown("### 📉 최소 변동성")
                    if min_vol['success']:
                        st.metric("기대 수익률", f"{min_vol['return']*100:.2f}%")
                        st.metric("변동성", f"{min_vol['volatility']*100:.2f}%")
                        st.metric("샤프 비율", f"{min_vol['sharpe']:.2f}")
                
                with col3:
                    st.markdown("### ⚖️ 동일 비중")
                    st.metric("기대 수익률", f"{equal_weight['return']*100:.2f}%")
                    st.metric("변동성", f"{equal_weight['volatility']*100:.2f}%")
                    st.metric("샤프 비율", f"{equal_weight['sharpe']:.2f}")
                
                # 최적 비중
                st.subheader("💰 최적 비중 (최대 샤프 기준)")
                if max_sharpe['success']:
                    weights_df = pd.DataFrame({
                        '종목': list(max_sharpe['weights'].keys()),
                        '비중 (%)': [w*100 for w in max_sharpe['weights'].values()]
                    })
                    st.dataframe(weights_df, use_container_width=True, hide_index=True)
                
            except Exception as e:
                st.error(f"최적화 오류: {e}")
                import traceback
                st.code(traceback.format_exc())
