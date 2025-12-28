"""
Chart Utilities for Dashboard
인터랙티브 차트 (Plotly) 렌더링 지원
"""
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
from typing import Optional

def render_stock_chart(ticker: str, ohlcv: pd.DataFrame, stock_name: str = ""):
    """
    Plotly를 이용한 고성능 캔들스틱 차트 렌더링
    
    Args:
        ticker: 종목 코드
        ohlcv: OHLCV DataFrame (index: date)
        stock_name: 종목명
    """
    if ohlcv is None or ohlcv.empty:
        st.warning("차트 데이터를 불러오지 못했습니다.")
        return

    # subplots: Price (Candlestick) + Volume (Bar)
    fig = make_subplots(
        rows=2, cols=1, 
        shared_xaxes=True, 
        vertical_spacing=0.03, 
        row_heights=[0.7, 0.3]
    )

    # 1. 캔들스틱 (Price)
    fig.add_trace(
        go.Candlestick(
            x=ohlcv.index,
            open=ohlcv['open'],
            high=ohlcv['high'],
            low=ohlcv['low'],
            close=ohlcv['close'],
            name="Price",
            increasing_line_color='#00d775', # 단일종목분석과 통일 (초록)
            decreasing_line_color='#ff4b4b'  # 단일종목분석과 통일 (빨강)
        ),
        row=1, col=1
    )

    # 2. 이동평균선 (MA20)
    ma20 = ohlcv['close'].rolling(20).mean()
    fig.add_trace(
        go.Scatter(
            x=ohlcv.index,
            y=ma20,
            name="MA20",
            line=dict(color='orange', width=1.5)
        ),
        row=1, col=1
    )

    # 3. 거래량 (Volume -> 거래량)
    v_colors = ['#00d775' if c >= o else '#ff4b4b' for c, o in zip(ohlcv['close'], ohlcv['open'])]
    fig.add_trace(
        go.Bar(
            x=ohlcv.index,
            y=ohlcv['volume'],
            name="거래량",
            marker_color=v_colors,
            opacity=0.8
        ),
        row=2, col=1
    )

    # 스타일링
    fig.update_layout(
        title=f"📈 {stock_name or ticker} 가격 추이",
        template="plotly_dark",
        height=500,
        margin=dict(l=10, r=10, t=40, b=10),
        xaxis_rangeslider_visible=False,
        showlegend=True
    )

    # 마우스 호버 등 설정
    fig.update_xaxes(rangebreaks=[dict(bounds=["sat", "mon"])]) # 주말 제거

    st.plotly_chart(fig, use_container_width=True)
