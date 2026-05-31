"""
다중 종목 비교 뷰 모듈

클린 아키텍처:
- Presentation Layer: Streamlit UI 렌더링
"""
import logging
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from src.dashboard.utils.data_cache import get_cached_multi_stock_data

logger = logging.getLogger(__name__)


def display_multi_stock_comparison():
    """다중 종목 비교 뷰"""
    st.header("🔀 다중 종목 비교")
    
    # 종목 선택
    active_stock_names = st.session_state.get('active_stock_names', [])
    active_stock_list = st.session_state.get('active_stock_list', {})
    
    if not active_stock_names:
        st.warning("종목 리스트를 불러오는 중입니다...")
        return
    
    selected_stocks = st.multiselect(
        "비교할 종목 선택 (최대 5개)",
        options=active_stock_names,
        default=active_stock_names[:3] if len(active_stock_names) >= 3 else active_stock_names,
        max_selections=5
    )
    
    if not selected_stocks:
        st.info("비교할 종목을 선택해주세요.")
        return
    
    period = st.selectbox(
        "기간 선택",
        options=['1mo', '3mo', '6mo', '1y', '2y', '5y'],
        index=2,
        key='multi_period'
    )
    
    # 데이터 수집
    # 🔧 수정: 한국 종목은 .KS suffix 추가 필요 (yfinance 호환)
    current_market = st.session_state.get('current_market', 'KR')
    raw_tickers = [active_stock_list[name] for name in selected_stocks]
    
    if current_market == 'KR':
        tickers = [f"{t}.KS" for t in raw_tickers]
    else:
        tickers = raw_tickers
    
    # 종목명 → 사용된 티커 매핑 (차트/통계에서 활용)
    name_to_ticker = {name: tickers[i] for i, name in enumerate(selected_stocks)}
    
    # 디버그 로그
    logger.debug(f"Multi-stock tickers: {tickers}")
    
    with st.spinner("데이터 로딩 중..."):
        stock_data = get_cached_multi_stock_data(tickers, period)
    
    if not stock_data:
        st.error("데이터를 불러올 수 없습니다.")
        return
    
    # 수익률 비교 차트
    st.subheader("📊 수익률 비교")
    fig = go.Figure()
    
    for stock_name in selected_stocks:
        ticker = name_to_ticker[stock_name]
        if ticker in stock_data and not stock_data[ticker].empty:
            df = stock_data[ticker]
            # 수익률 계산 (첫 날 종가 기준 정규화)
            normalized = (df['close'] / df['close'].iloc[0] - 1) * 100
            fig.add_trace(go.Scatter(
                x=df['date'],
                y=normalized,
                mode='lines',
                name=stock_name.split('(')[0].strip()
            ))
    
    fig.update_layout(
        title="기간별 수익률 비교 (%)",
        xaxis_title="날짜",
        yaxis_title="수익률 (%)",
        hovermode='x unified',
        height=500
    )
    st.plotly_chart(fig, use_container_width=True)
    
    # 통계 비교 테이블
    st.subheader("📈 통계 비교")
    
    stats_data = []
    for stock_name in selected_stocks:
        ticker = name_to_ticker[stock_name]
        if ticker in stock_data and not stock_data[ticker].empty:
            df = stock_data[ticker]
            latest = df.iloc[-1]
            first = df.iloc[0]
            
            total_return = ((latest['close'] - first['close']) / first['close']) * 100
            volatility = df['close'].pct_change().std() * 100
            avg_volume = df['volume'].mean()
            
            stats_data.append({
                '종목': stock_name.split('(')[0].strip(),
                '현재가': f"{latest['close']:,.0f}",
                '수익률 (%)': f"{total_return:+.2f}%",
                '변동성 (%)': f"{volatility:.2f}%",
                '평균 거래량': f"{avg_volume:,.0f}"
            })
    
    if stats_data:
        stats_df = pd.DataFrame(stats_data)
        st.dataframe(stats_df, use_container_width=True, hide_index=True)
    
    # 개별 차트
    st.subheader("📉 개별 차트")
    cols = st.columns(min(len(selected_stocks), 2))
    
    for idx, stock_name in enumerate(selected_stocks):
        ticker = name_to_ticker[stock_name]
        if ticker in stock_data and not stock_data[ticker].empty:
            df = stock_data[ticker]
            
            with cols[idx % 2]:
                mini_fig = go.Figure(data=[go.Candlestick(
                    x=df['date'],
                    open=df['open'],
                    high=df['high'],
                    low=df['low'],
                    close=df['close'],
                    name=stock_name.split('(')[0].strip()
                )])
                mini_fig.update_layout(
                    title=stock_name,
                    height=300,
                    xaxis_rangeslider_visible=False
                )
                st.plotly_chart(mini_fig, use_container_width=True)
