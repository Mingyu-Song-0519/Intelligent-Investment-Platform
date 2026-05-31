"""
Chart Utilities for Dashboard
인터랙티브 차트 (Plotly) 렌더링 지원

resample_ohlcv, create_candlestick_chart 함수 포함 (app.py에서 추출)
"""
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px
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


def resample_ohlcv(df: pd.DataFrame, interval: str) -> pd.DataFrame:
    """
    OHLCV 데이터를 주간/월간 봉으로 리샘플링

    Args:
        df: 일봉 데이터 (date, open, high, low, close, volume 컬럼 필요)
        interval: "1d" (일봉), "1wk" (주봉), "1mo" (월봉)

    Returns:
        리샘플링된 DataFrame
    """
    if interval == "1d":
        return df  # 일봉은 그대로 반환

    # date 컬럼을 인덱스로 설정
    df_copy = df.copy()
    if 'date' in df_copy.columns:
        df_copy['date'] = pd.to_datetime(df_copy['date'])
        df_copy = df_copy.set_index('date')

    # 리샘플링 규칙
    resample_rule = 'W' if interval == "1wk" else 'ME'  # W=주간, ME=월말

    # OHLCV 리샘플링
    agg_dict = {
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    }

    # 존재하는 컬럼만 집계
    agg_dict = {k: v for k, v in agg_dict.items() if k in df_copy.columns}

    resampled = df_copy.resample(resample_rule).agg(agg_dict).dropna()

    # 기술적 지표 재계산 (필요 시)
    # RSI, MACD 등은 리샘플링된 데이터에서 다시 계산해야 정확함
    # 여기서는 간단히 마지막 값만 사용
    for col in ['rsi', 'macd', 'macd_signal', 'macd_hist', 'bb_upper', 'bb_lower', 'bb_mid']:
        if col in df_copy.columns:
            resampled[col] = df_copy[col].resample(resample_rule).last()

    # date를 컬럼으로 되돌림
    resampled = resampled.reset_index()
    resampled = resampled.rename(columns={'index': 'date'})
    if resampled.columns[0] != 'date':
        resampled = resampled.rename(columns={resampled.columns[0]: 'date'})

    return resampled


def create_candlestick_chart(df: pd.DataFrame, ticker_name: str) -> go.Figure:
    """캔들스틱 차트 생성"""
    fig = make_subplots(
        rows=4, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.15,  # 간격 대폭 확대 (0.08 -> 0.15)
        row_heights=[0.40, 0.15, 0.20, 0.25],
        subplot_titles=(f'{ticker_name} 주가', 'RSI (14일)', 'MACD', '거래량')
    )

    # 캔들스틱 (범례 숨김 - 제목에 설명 포함)
    fig.add_trace(
        go.Candlestick(
            x=df['date'],
            open=df['open'],
            high=df['high'],
            low=df['low'],
            close=df['close'],
            name='주가',
            increasing_line_color='#00d775',
            decreasing_line_color='#ff4b4b',
            showlegend=True
        ),
        row=1, col=1
    )

    # 이동평균선 (동적 선택)
    ma_colors = {
        5: '#ff6b6b',    # 빨간색 (단기)
        10: '#ffa726',   # 주황색 (단기)
        20: '#ffeb3b',   # 노란색 (중기)
        60: '#4caf50',   # 녹색 (중기)
        120: '#42a5f5',  # 파란색 (장기)
        200: '#ab47bc'   # 보라색 (장기)
    }
    selected_ma_periods = st.session_state.get('selected_ma_periods', [5, 10, 20, 60])

    for period in selected_ma_periods:
        col_name = f'sma_{period}'
        if col_name not in df.columns:
            # 이동평균 계산
            df[col_name] = df['close'].rolling(window=period).mean()

        if col_name in df.columns:
            fig.add_trace(
                go.Scatter(
                    x=df['date'],
                    y=df[col_name],
                    name=f'MA {period}',
                    line=dict(color=ma_colors.get(period, '#888888'), width=1),
                    showlegend=True
                ),
                row=1, col=1
            )

    # 볼린저 밴드
    if 'bb_upper' in df.columns:
        fig.add_trace(
            go.Scatter(x=df['date'], y=df['bb_upper'], name='BB Upper',
                      line=dict(color='rgba(128,128,128,0.5)', width=1, dash='dash'),
                      showlegend=True),
            row=1, col=1
        )
        fig.add_trace(
            go.Scatter(x=df['date'], y=df['bb_lower'], name='BB Lower',
                      line=dict(color='rgba(128,128,128,0.5)', width=1, dash='dash'),
                      fill='tonexty', fillcolor='rgba(128,128,128,0.1)',
                      showlegend=True),
            row=1, col=1
        )

    # VWAP (Volume Weighted Average Price) - 기관 매입 기준선
    if 'vwap' in df.columns:
        fig.add_trace(
            go.Scatter(x=df['date'], y=df['vwap'], name='VWAP',
                      line=dict(color='#ff9800', width=2, dash='dot'),
                      showlegend=True),
            row=1, col=1
        )

    # RSI
    if 'rsi' in df.columns:
        fig.add_trace(
            go.Scatter(x=df['date'], y=df['rsi'], name='RSI',
                      line=dict(color='#ab47bc', width=1),
                      showlegend=False),
            row=2, col=1
        )
        # 과매수/과매도 라인
        fig.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="green", row=2, col=1)

    # MACD
    if 'macd' in df.columns:
        fig.add_trace(
            go.Scatter(x=df['date'], y=df['macd'], name='MACD',
                      line=dict(color='#26a69a', width=1),
                      showlegend=False),
            row=3, col=1
        )
        fig.add_trace(
            go.Scatter(x=df['date'], y=df['macd_signal'], name='Signal',
                      line=dict(color='#ef5350', width=1),
                      showlegend=False),
            row=3, col=1
        )
        # 히스토그램
        colors = ['#00d775' if v >= 0 else '#ff4b4b' for v in df['macd_hist']]
        fig.add_trace(
            go.Bar(x=df['date'], y=df['macd_hist'], name='Histogram',
                  marker_color=colors,
                  showlegend=False),
            row=3, col=1
        )

    # 거래량
    colors = ['#00d775' if c >= o else '#ff4b4b'
              for c, o in zip(df['close'], df['open'])]
    fig.add_trace(
        go.Bar(x=df['date'], y=df['volume'], name='거래량',
              marker_color=colors,
              showlegend=False),
        row=4, col=1
    )

    fig.update_layout(
        height=1000,  # 높이 증가
        template='plotly_dark',
        showlegend=True,
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
        # 인터랙티브 차트: rangeslider 활성화 (기간 선택 슬라이더)
        xaxis_rangeslider_visible=True,
        xaxis_rangeslider_thickness=0.05,  # 슬라이더 두께
        xaxis_rangeslider_bgcolor='rgba(50,50,50,0.3)',
        # 드래그 모드: pan 또는 zoom 선택 가능
        dragmode='pan',  # 기본은 팬 (드래그로 이동), 더블클릭으로 리셋
        hovermode="x unified"  # 터치 시 호버 정보 표시
    )

    # X축 날짜 형식 한글화 + 줌/팬 활성화
    # 모든 차트 하단에 날짜 표시
    fig.update_xaxes(tickformat="%Y년 %m월 %d일", row=1, col=1, fixedrange=False, showticklabels=True)
    fig.update_xaxes(tickformat="%Y년 %m월 %d일", row=2, col=1, fixedrange=False, showticklabels=True)
    fig.update_xaxes(tickformat="%Y년 %m월 %d일", row=3, col=1, fixedrange=False, showticklabels=True)
    fig.update_xaxes(tickformat="%Y년 %m월 %d일", row=4, col=1, fixedrange=False, showticklabels=True)

    # Y축은 자동 조정 (X축 줌에 따라 Y축 범위 조정)
    fig.update_yaxes(fixedrange=False, autorange=True)

    return fig
