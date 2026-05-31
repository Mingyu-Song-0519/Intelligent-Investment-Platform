"""
차트 생성 유틸리티 모듈

클린 아키텍처:
- Presentation Layer: Plotly 차트 생성
- 재사용 가능한 차트 컴포넌트
"""
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def create_candlestick_chart(df: pd.DataFrame, ticker_name: str) -> go.Figure:
    """
    캔들스틱 차트 생성 (거래량 + 이동평균선 포함)
    
    Args:
        df: OHLCV 데이터프레임 (date, open, high, low, close, volume 컬럼 필요)
        ticker_name: 차트 제목용 종목명
    
    Returns:
        plotly Figure 객체
    """
    # 서브플롯 생성 (캔들스틱 + 거래량)
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.7, 0.3],
        subplot_titles=(f'{ticker_name} 주가', '거래량')
    )
    
    # 캔들스틱 차트
    fig.add_trace(
        go.Candlestick(
            x=df['date'],
            open=df['open'],
            high=df['high'],
            low=df['low'],
            close=df['close'],
            name='OHLC',
            increasing_line_color='#FF4B4B',
            decreasing_line_color='#4B4BFF'
        ),
        row=1, col=1
    )
    
    # 이동평균선 (5일, 20일, 60일)
    if 'MA5' in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df['date'],
                y=df['MA5'],
                mode='lines',
                name='MA5',
                line=dict(color='orange', width=1)
            ),
            row=1, col=1
        )
    
    if 'MA20' in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df['date'],
                y=df['MA20'],
                mode='lines',
                name='MA20',
                line=dict(color='green', width=1)
            ),
            row=1, col=1
        )
    
    if 'MA60' in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df['date'],
                y=df['MA60'],
                mode='lines',
                name='MA60',
                line=dict(color='purple', width=1)
            ),
            row=1, col=1
        )
    
    # 볼린저 밴드
    if 'BB_upper' in df.columns and 'BB_lower' in df.columns:
        fig.add_trace(
            go.Scatter(
                x=df['date'],
                y=df['BB_upper'],
                mode='lines',
                name='BB Upper',
                line=dict(color='gray', width=1, dash='dot')
            ),
            row=1, col=1
        )
        fig.add_trace(
            go.Scatter(
                x=df['date'],
                y=df['BB_lower'],
                mode='lines',
                name='BB Lower',
                line=dict(color='gray', width=1, dash='dot'),
                fill='tonexty',
                fillcolor='rgba(128,128,128,0.1)'
            ),
            row=1, col=1
        )
    
    # 거래량 바 차트
    colors = ['red' if close < open_ else 'blue' 
              for close, open_ in zip(df['close'], df['open'])]
    
    fig.add_trace(
        go.Bar(
            x=df['date'],
            y=df['volume'],
            name='Volume',
            marker_color=colors,
            showlegend=False
        ),
        row=2, col=1
    )
    
    # 레이아웃 설정
    fig.update_layout(
        title=f'{ticker_name} 차트 분석',
        xaxis_rangeslider_visible=False,
        height=700,
        hovermode='x unified',
        template='plotly_white',
        legend=dict(
            orientation='h',
            yanchor='bottom',
            y=1.02,
            xanchor='right',
            x=1
        )
    )
    
    # X축 날짜 포맷
    fig.update_xaxes(
        title_text="날짜",
        row=2, col=1
    )
    
    # Y축 레이블
    fig.update_yaxes(
        title_text="가격",
        row=1, col=1
    )
    fig.update_yaxes(
        title_text="거래량",
        row=2, col=1
    )
    
    return fig
