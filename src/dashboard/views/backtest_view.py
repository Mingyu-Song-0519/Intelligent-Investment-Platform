"""
백테스팅 뷰 모듈

클린 아키텍처:
- Presentation Layer: Streamlit UI 렌더링
- Application Layer: 백테스팅 엔진 호출
"""
import streamlit as st
import plotly.graph_objects as go
from src.backtest import Backtester, PerformanceMetrics
from src.backtest.strategies import RSIStrategy, MACDStrategy, MovingAverageStrategy
from src.analyzers.technical_analyzer import TechnicalAnalyzer
from src.dashboard.utils.data_cache import get_cached_stock_data


def display_backtest():
    """백테스팅 뷰"""
    st.header("⏮️ 백테스팅")
    
    selected_ticker = st.session_state.get('selected_ticker')
    selected_stock = st.session_state.get('selected_stock')
    
    if not selected_ticker:
        st.warning("종목을 먼저 선택해주세요.")
        return
    
    # 설정
    col1, col2, col3 = st.columns(3)
    with col1:
        strategy_type = st.selectbox(
            "전략 선택",
            ["RSI", "MACD", "이동평균"]
        )
    with col2:
        period = st.selectbox(
            "테스트 기간",
            ['1y', '2y', '3y', '5y'],
            index=1
        )
    with col3:
        initial_capital = st.number_input(
            "초기 자본 (원)",
            min_value=1000000,
            value=10000000,
            step=1000000
        )
    
    if st.button("▶️ 백테스트 실행", type="primary"):
        with st.spinner("백테스트 진행 중..."):
            try:
                # 데이터 수집
                df = get_cached_stock_data(selected_ticker, period)
                
                if df.empty:
                    st.error("데이터를 불러올 수 없습니다.")
                    return
                
                # 기술적 지표 추가
                analyzer = TechnicalAnalyzer(df)
                analyzer.add_all_indicators()
                df = analyzer.get_dataframe()
                df = df.set_index('date')
                
                # 전략 선택
                if strategy_type == "RSI":
                    strategy = RSIStrategy()
                elif strategy_type == "MACD":
                    strategy = MACDStrategy()
                else:
                    strategy = MovingAverageStrategy()
                
                # 백테스트 실행
                backtester = Backtester(df, initial_capital=initial_capital)
                results = backtester.run(strategy)
                
                # 성과 지표
                metrics = PerformanceMetrics(results['equity'], initial_capital)
                trades_df = backtester.get_trades_df()
                metrics_dict = metrics.get_all_metrics(trades_df)
                
                # 결과 표시
                st.success(f"✅ 백테스트 완료 (거래 횟수: {len(trades_df)})")
                
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("총 수익률", f"{metrics_dict['total_return']*100:.2f}%")
                with col2:
                    st.metric("연환산 수익률", f"{metrics_dict['cagr']*100:.2f}%")
                with col3:
                    st.metric("최대 낙폭 (MDD)", f"{metrics_dict['max_drawdown']*100:.2f}%")
                with col4:
                    st.metric("샤프 비율", f"{metrics_dict['sharpe_ratio']:.2f}")
                
                # 수익률 곡선
                st.subheader("📈 포트폴리오 가치 변화")
                dates = backtester.df.index.tolist()
                
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=dates,
                    y=results['equity'],
                    name='전략 수익',
                    line=dict(color='#00d775', width=2)
                ))
                fig.add_trace(go.Scatter(
                    x=dates,
                    y=results['buy_hold_equity'],
                    name='Buy & Hold',
                    line=dict(color='#ffa726', width=2, dash='dash')
                ))
                
                fig.update_layout(
                    title="포트폴리오 가치 변화",
                    xaxis_title="날짜",
                    yaxis_title="가치 (원)",
                    template='plotly_dark',
                    height=400
                )
                st.plotly_chart(fig, use_container_width=True)
                
                # 거래 내역
                if not trades_df.empty:
                    st.subheader("📋 거래 내역")
                    st.dataframe(trades_df, use_container_width=True)
                
            except Exception as e:
                st.error(f"백테스트 오류: {e}")
                import traceback
                st.code(traceback.format_exc())
