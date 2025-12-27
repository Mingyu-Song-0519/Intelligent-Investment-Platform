"""
Streamlit 기반 주식 분석 대시보드 - Phase 2 통합
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px
import sys
from pathlib import Path
from datetime import datetime, timedelta
import numpy as np
import warnings
import os

# TensorFlow/Keras 경고 억제
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
warnings.filterwarnings('ignore', category=FutureWarning, module='keras')
warnings.filterwarnings('ignore', category=UserWarning, module='tensorflow')
warnings.filterwarnings('ignore', category=DeprecationWarning, module='tensorflow')

# 프로젝트 루트 경로 설정
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config import DEFAULT_TICKERS, US_TICKERS, DASHBOARD_CONFIG, ENSEMBLE_CONFIG, MARKET_CONFIG, EXCHANGE_RATE_CONFIG
from src.collectors.stock_collector import StockDataCollector
from src.collectors.multi_stock_collector import MultiStockCollector

# Phase F: New MarketDataService with caching and fallback
try:
    from src.services.market_data_service import MarketDataService
    from src.services.feature_engineering_service import FeatureEngineeringService
    MARKET_SERVICE_AVAILABLE = True
except ImportError:
    MARKET_SERVICE_AVAILABLE = False
from src.collectors.news_collector import NewsCollector
from src.analyzers.technical_analyzer import TechnicalAnalyzer
from src.utils.hints import get_hint_text, INDICATOR_HINTS
from src.analyzers.sentiment_analyzer import SentimentAnalyzer
from src.analyzers.risk_manager import RiskManager
from src.models.ensemble_predictor import EnsemblePredictor
from src.optimizers.portfolio_optimizer import PortfolioOptimizer
from src.backtest import Backtester, PerformanceMetrics
from src.backtest import Backtester, PerformanceMetrics
from src.backtest.strategies import RSIStrategy, MACDStrategy, MovingAverageStrategy
from src.dashboard.realtime_tab import display_realtime_data
from src.analyzers.volatility_analyzer import VolatilityAnalyzer
from src.analyzers.market_breadth import MarketBreadthAnalyzer
from src.analyzers.fundamental_analyzer import FundamentalAnalyzer
from src.dashboard.dependencies import yfinance_repo
from src.services.incremental_learning_service import IncrementalLearningService
from src.infrastructure.repositories.model_repository import ModelRepository

# Phase 20: 투자 성향 분석 뷰
try:
    from src.dashboard.views import render_investment_profile_tab, render_ranking_tab
    INVESTMENT_PROFILE_AVAILABLE = True
except ImportError:
    INVESTMENT_PROFILE_AVAILABLE = False

# Phase A: AI 분석 뷰
try:
    from src.dashboard.views.ai_analysis_view import render_ai_analysis_button
    AI_ANALYSIS_AVAILABLE = True
except ImportError:
    AI_ANALYSIS_AVAILABLE = False

# Phase C: AI 스크리너 뷰
try:
    from src.dashboard.views.screener_view import render_morning_picks
    SCREENER_AVAILABLE = True
except ImportError:
    SCREENER_AVAILABLE = False

# Phase D: AI 챗봇
try:
    from src.dashboard.components.sidebar_chat import render_sidebar_chat
    CHATBOT_AVAILABLE = True
except ImportError:
    CHATBOT_AVAILABLE = False


def setup_page():
    """페이지 기본 설정"""
    st.set_page_config(
        page_title=DASHBOARD_CONFIG['page_title'],
        page_icon=DASHBOARD_CONFIG['page_icon'],
        layout=DASHBOARD_CONFIG['layout']
    )
    
    # 커스텀 CSS (테마 적응형)
    st.markdown("""
        <style>
        .main {
            padding: 1rem;
        }
        /* 모바일 텍스트 잘림 방지 - 반응형 폰트 크기 */
        div[data-testid="stMetricValue"] {
            font-size: clamp(0.8rem, 3vw, 1.2rem) !important; /* 화면 크기에 따라 자동 조정 */
            word-wrap: break-word !important;
            white-space: normal !important;
            overflow-wrap: anywhere !important;
            line-height: 1.2 !important;
        }
        div[data-testid="stMetricLabel"] {
            font-size: clamp(0.65rem, 2.5vw, 0.9rem) !important; /* 라벨도 반응형 */
            word-wrap: break-word !important;
            white-space: normal !important;
            overflow-wrap: anywhere !important;
        }
        div[data-testid="stMetricDelta"] {
            font-size: clamp(0.6rem, 2vw, 0.8rem) !important; /* 변동값도 반응형 */
        }
        .stMetric {
            background-color: var(--background-secondary-color, rgba(128, 128, 128, 0.1));
            padding: 0.3rem !important; /* 패딩 더 축소 */
            border-radius: 0.5rem;
            border: 1px solid var(--border-color, rgba(128, 128, 128, 0.2));
            min-height: 80px; /* 높이 줄임 */
            overflow: hidden;
        }
        
        /* Plotly 차트 모바일 스크롤 강제 허용 (핵심) */
        .js-plotly-plot, .plot-container, .main-svg {
            touch-action: pan-y !important; /* 수직 스크롤 허용 */
        }
        
        /* 모바일 당겨서 새로고침 방지 (스크롤 개선) */
        html, body {
            overscroll-behavior-y: none !important; /* Pull-to-refresh 차단 */
        }
        
        .positive {
            color: #00d775;
        }
        .negative {
            color: #ff4b4b;
        }
        </style>
    """, unsafe_allow_html=True)


@st.cache_data(ttl=3600, show_spinner=False)
def get_cached_stock_data(ticker: str, period: str) -> pd.DataFrame:
    """주식 데이터 수집 (MarketDataService + 캐싱 적용)"""
    try:
        # Phase F: MarketDataService 우선 사용 (Fallback + SQLite 캐싱)
        if MARKET_SERVICE_AVAILABLE:
            market = st.session_state.get('current_market', 'KR')
            service = MarketDataService(market=market)
            ohlcv = service.get_ohlcv(ticker, period=period)
            df = ohlcv.to_dataframe()
            
            # 차트 호환성: index를 date 컬럼으로 변환
            if 'date' not in df.columns:
                df = df.reset_index()
                # 컬럼명 정규화 (Date, index 등 → date)
                if 'Date' in df.columns:
                    df = df.rename(columns={'Date': 'date'})
                elif 'index' in df.columns:
                    df = df.rename(columns={'index': 'date'})
                elif df.columns[0] != 'date':
                    df = df.rename(columns={df.columns[0]: 'date'})
            
            return df
        else:
            # Fallback: 기존 StockDataCollector
            collector = StockDataCollector()
            return collector.fetch_stock_data(ticker, period)
    except Exception as e:
        st.error(f"데이터 수집 오류: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=3600, show_spinner=False)
def get_cached_multi_stock_data(tickers: list, period: str) -> dict:
    """다중 종목 데이터 수집 (캐싱 적용, 1시간)"""
    try:
        collector = MultiStockCollector()
        # MultiStockCollector 메서드가 collect_multiple인지 확인 필요
        if hasattr(collector, 'collect_multiple'):
            return collector.collect_multiple(tickers, period)
        else:
            return collector.fetch_multiple_stocks(tickers, period)
    except Exception as e:
        st.error(f"다중 데이터 수집 오류: {e}")
        return {}


@st.cache_data(ttl=86400, show_spinner=False)
def get_cached_stock_listing(market: str) -> tuple:
    """종목 리스트 수집 (캐싱 적용, 24시간)"""
    try:
        import FinanceDataReader as fdr
        
        if market == 'US':
            df_nyse = fdr.StockListing('NYSE')
            df_nasdaq = fdr.StockListing('NASDAQ')
            df = pd.concat([df_nyse, df_nasdaq], ignore_index=True)
            df = df.dropna(subset=['Symbol', 'Name'])
            df = df.drop_duplicates(subset=['Symbol'])
            stock_dict = dict(zip(
                df['Name'] + ' (' + df['Symbol'] + ')',
                df['Symbol']
            ))
        else:  # KR
            df = fdr.StockListing('KRX')
            stock_dict = dict(zip(
                df['Name'] + ' (' + df['Code'] + ')',
                df['Code']
            ))
        
        return stock_dict, list(stock_dict.keys())
    except Exception as e:
        print(f"[ERROR] 종목 리스트 로딩 실패: {e}")
        return {}, []


@st.cache_data(ttl=3600, show_spinner=False)
def get_cached_exchange_rate() -> float:
    """환율 데이터 수집 (캐싱 적용, 1시간)"""
    try:
        import yfinance as yf
        usdkrw = yf.Ticker("USDKRW=X")
        rate = usdkrw.info.get('regularMarketPrice', None)
        if rate is None:
            rate = usdkrw.history(period="1d")['Close'].iloc[-1]
        return float(rate)
    except Exception as e:
        print(f"[ERROR] 환율 데이터 수집 실패: {e}")
        return 1350.0  # 기본값

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
        xaxis_rangeslider_visible=False,
        dragmode=False, # 모바일 스크롤 위해 드래그 비활성화
        hovermode="x unified" # 터치 시 호버 정보 표시
    )
    
    # X축 날짜 형식 한글화 및 모바일 스크롤 지원 (fixedrange=True)
    # fixedrange=True를 설정하면 차트 줌/팬이 비활성화되어 자연스럽게 페이지 스크롤이 가능해짐
    fig.update_xaxes(tickformat="%Y년 %m월", row=1, col=1, fixedrange=True)
    fig.update_xaxes(tickformat="%Y년 %m월", row=2, col=1, fixedrange=True)
    fig.update_xaxes(tickformat="%Y년 %m월", row=3, col=1, fixedrange=True)
    fig.update_xaxes(tickformat="%Y년 %m월", row=4, col=1, fixedrange=True)
    
    # Y축도 고정
    fig.update_yaxes(fixedrange=True)
    
    return fig


def display_metrics(df: pd.DataFrame):
    """주요 지표 표시"""
    if df.empty:
        return
    
    latest = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 1 else latest
    
    price_change = latest['close'] - prev['close']
    price_change_pct = (price_change / prev['close']) * 100
    
    # 통화 기호
    currency = st.session_state.get('currency_symbol', '₩')
    current_market = st.session_state.get('current_market', 'KR')
    
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    
    with col1:
        st.metric(
            label="현재가",
            value=f"{currency}{latest['close']:,.2f}" if currency == "$" else f"{currency}{latest['close']:,.0f}",
            delta=f"{price_change:+,.2f} ({price_change_pct:+.2f}%)" if currency == "$" else f"{price_change:+,.0f} ({price_change_pct:+.2f}%)"
        )
    
    with col2:
        st.metric(
            label="거래량",
            value=f"{latest['volume']:,.0f}",
        )
    
    with col3:
        if 'rsi' in df.columns and pd.notna(latest.get('rsi')):
            rsi_val = latest['rsi']
            rsi_status = "과매수" if rsi_val > 70 else "과매도" if rsi_val < 30 else "중립"
            st.metric(
                label=f"RSI ({rsi_status})",
                value=f"{rsi_val:.1f}"
            )
    
    with col4:
        if 'macd' in df.columns and pd.notna(latest.get('macd')):
            macd_val = latest['macd']
            st.metric(
                label="MACD",
                value=f"{macd_val:.2f}"
            )
    
    with col5:
        # ADX 추세 강도 표시
        if 'adx' in df.columns and pd.notna(latest.get('adx')):
            adx_val = latest['adx']
            if adx_val < 25:
                adx_status = "약함🔵"
            elif adx_val < 50:
                adx_status = "강함🟢"
            else:
                adx_status = "매우강함🔴"
            st.metric(
                label=f"ADX ({adx_status})",
                value=f"{adx_val:.1f}"
            )
    
    with col6:
        # 52주 고가/저가 대비
        high_52w = df['high'].tail(252).max()
        low_52w = df['low'].tail(252).min()
        current_pos = (latest['close'] - low_52w) / (high_52w - low_52w) * 100
        st.metric(
            label="52주 범위 위치",
            value=f"{current_pos:.1f}%"
        )
    
    # 미국 주식일 경우 환율 정보 추가 표시
    if current_market == 'US':
        try:
            exchange_rate = get_cached_exchange_rate()
            krw_price = latest['close'] * exchange_rate
            krw_change = price_change * exchange_rate
            
            st.markdown("---")
            ecol1, ecol2, ecol3 = st.columns(3)
            with ecol1:
                st.metric(
                    label="💱 USD/KRW 환율",
                    value=f"₩{exchange_rate:,.2f}"
                )
            with ecol2:
                st.metric(
                    label="🇰🇷 원화 환산가",
                    value=f"₩{krw_price:,.0f}",
                    delta=f"{krw_change:+,.0f}"
                )
            with ecol3:
                st.caption("※ 환율 데이터: Yahoo Finance (1시간 캐싱)")
        except Exception as e:
            print(f"[WARNING] 환율 표시 실패: {e}")
    
    # 초보자 힌트 섹션
    with st.expander("💡 지표 설명 보기 (초보자용)", expanded=False):
        hint_col1, hint_col2, hint_col3 = st.columns(3)
        with hint_col1:
            st.markdown(f"**RSI**: {get_hint_text('RSI', 'short')}")
            st.markdown(f"**MACD**: {get_hint_text('MACD', 'short')}")
        with hint_col2:
            st.markdown(f"**ADX**: {get_hint_text('ADX', 'short')}")
            st.markdown(f"**VWAP**: {get_hint_text('VWAP', 'short')}")
        with hint_col3:
            st.markdown(f"**ATR**: {get_hint_text('ATR', 'short')}")
            st.markdown(f"**볼린저밴드**: 주가의 변동 범위를 보여주는 밴드입니다.")


def display_signals(df: pd.DataFrame):
    """매매 시그널 표시"""
    st.subheader("📊 매매 시그널")
    
    # 지표 확인
    if 'rsi' not in df.columns or 'macd' not in df.columns:
        st.warning("기술적 지표가 계산되지 않았습니다.")
        return
    
    latest = df.iloc[-1]
    
    # 첫 번째 행: RSI, MACD, 볼린저밴드
    st.markdown("#### 기술적 지표 시그널")
    signal_cols = st.columns(3)

    with signal_cols[0]:
        rsi_val = latest.get('rsi', 50)
        if pd.notna(rsi_val):
            if rsi_val < 30:
                st.success(f"🟢 RSI 과매도 구간 ({rsi_val:.1f})")
                st.caption("💡 **매수 검토**: RSI 30 미만은 과매도 상태로, 반등 가능성이 높습니다.")
            elif rsi_val > 70:
                st.error(f"🔴 RSI 과매수 구간 ({rsi_val:.1f})")
                st.caption("💡 **매도 검토**: RSI 70 초과는 과매수 상태로, 조정 가능성이 있습니다.")
            else:
                st.info(f"⚪ RSI 중립 ({rsi_val:.1f})")
                st.caption("💡 **관망**: RSI 30~70 사이는 중립 구간으로, 다른 지표를 함께 확인하세요.")
        else:
            st.info("⚪ RSI 데이터 없음")

    with signal_cols[1]:
        macd_val = latest.get('macd', 0)
        macd_signal = latest.get('macd_signal', 0)
        if pd.notna(macd_val) and pd.notna(macd_signal):
            macd_diff = macd_val - macd_signal
            if macd_val > macd_signal:
                st.success(f"🟢 MACD 상승 추세 (+{macd_diff:.2f})")
                st.caption("💡 **매수 신호**: MACD가 시그널선 위에 있어 상승 모멘텀입니다.")
            else:
                st.error(f"🔴 MACD 하락 추세 ({macd_diff:.2f})")
                st.caption("💡 **매도 신호**: MACD가 시그널선 아래로 하락 모멘텀입니다.")
        else:
            st.info("⚪ MACD 데이터 없음")

    with signal_cols[2]:
        close = latest.get('close', 0)
        bb_lower = latest.get('bb_lower', 0)
        bb_upper = latest.get('bb_upper', 0)
        bb_middle = latest.get('bb_middle', 0)
        if pd.notna(bb_lower) and pd.notna(bb_upper) and bb_upper > bb_lower:
            bb_position = (close - bb_lower) / (bb_upper - bb_lower) * 100
            if close < bb_lower:
                st.success("🟢 볼린저밴드 하단 터치")
                st.caption("💡 **매수 검토**: 하단 밴드 터치는 과매도 신호로, 반등 가능성이 있습니다.")
            elif close > bb_upper:
                st.error("🔴 볼린저밴드 상단 터치")
                st.caption("💡 **매도 검토**: 상단 밴드 터치는 과매수 신호로, 조정 가능성이 있습니다.")
            else:
                st.info(f"⚪ 볼린저밴드 중립 ({bb_position:.0f}%)")
                st.caption("💡 **관망**: 밴드 내 중간 위치로, 추세 방향을 확인하세요.")
        else:
            st.info("⚪ 볼린저밴드 데이터 없음")
    
    # 두 번째 행: 이동평균 교차, 거래량 분석
    st.markdown("#### 추가 시그널")
    signal_cols2 = st.columns(3)
    
    with signal_cols2[0]:
        # 이동평균 교차 (골든크로스/데드크로스)
        ma5 = latest.get('ma5', None)
        ma20 = latest.get('ma20', None)
        if pd.notna(ma5) and pd.notna(ma20):
            if ma5 > ma20:
                # 이전 데이터와 비교하여 교차 여부 확인
                prev = df.iloc[-2] if len(df) > 1 else latest
                prev_ma5 = prev.get('ma5', 0)
                prev_ma20 = prev.get('ma20', 0)
                if pd.notna(prev_ma5) and pd.notna(prev_ma20) and prev_ma5 <= prev_ma20:
                    st.success("🟢 골든크로스 발생!")
                    st.caption("💡 **강력 매수 신호**: 단기 MA가 장기 MA를 상향 돌파했습니다.")
                else:
                    st.success("🟢 상승 추세 (MA5 > MA20)")
                    st.caption("💡 **매수 우위**: 단기 이동평균이 장기 이동평균 위에 있습니다.")
            else:
                prev = df.iloc[-2] if len(df) > 1 else latest
                prev_ma5 = prev.get('ma5', 0)
                prev_ma20 = prev.get('ma20', 0)
                if pd.notna(prev_ma5) and pd.notna(prev_ma20) and prev_ma5 >= prev_ma20:
                    st.error("🔴 데드크로스 발생!")
                    st.caption("💡 **강력 매도 신호**: 단기 MA가 장기 MA를 하향 돌파했습니다.")
                else:
                    st.error("🔴 하락 추세 (MA5 < MA20)")
                    st.caption("💡 **매도 우위**: 단기 이동평균이 장기 이동평균 아래에 있습니다.")
        else:
            st.info("⚪ 이동평균 데이터 없음")
    
    with signal_cols2[1]:
        # 거래량 분석
        current_volume = latest.get('volume', 0)
        if pd.notna(current_volume) and 'volume' in df.columns:
            avg_volume = df['volume'].tail(20).mean()
            volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1
            if volume_ratio > 2.0:
                st.success(f"🟢 거래량 급증 ({volume_ratio:.1f}배)")
                st.caption("💡 **주목**: 평균 대비 2배 이상 거래량은 큰 움직임 신호입니다.")
            elif volume_ratio > 1.5:
                st.info(f"⚪ 거래량 증가 ({volume_ratio:.1f}배)")
                st.caption("💡 **관심**: 평균보다 높은 거래량으로 관심이 집중되고 있습니다.")
            elif volume_ratio < 0.5:
                st.warning(f"🟡 거래량 감소 ({volume_ratio:.1f}배)")
                st.caption("💡 **주의**: 낮은 거래량은 추세 지속력이 약할 수 있습니다.")
            else:
                st.info(f"⚪ 거래량 보통 ({volume_ratio:.1f}배)")
                st.caption("💡 **정상**: 평균 수준의 거래량입니다.")
        else:
            st.info("⚪ 거래량 데이터 없음")
    
    with signal_cols2[2]:
        # 종합 판단
        score = 0
        signals = []
        
        # RSI 점수
        if pd.notna(latest.get('rsi')):
            if latest['rsi'] < 30:
                score += 2
                signals.append("RSI 과매도")
            elif latest['rsi'] > 70:
                score -= 2
                signals.append("RSI 과매수")
        
        # MACD 점수
        if pd.notna(latest.get('macd')) and pd.notna(latest.get('macd_signal')):
            if latest['macd'] > latest['macd_signal']:
                score += 1
                signals.append("MACD 상승")
            else:
                score -= 1
                signals.append("MACD 하락")
        
        # 이동평균 점수
        if pd.notna(latest.get('ma5')) and pd.notna(latest.get('ma20')):
            if latest['ma5'] > latest['ma20']:
                score += 1
                signals.append("MA 상승추세")
            else:
                score -= 1
                signals.append("MA 하락추세")
        
        if score >= 3:
            st.success(f"📈 종합: 강력 매수 ({score}점)")
            st.caption(f"💡 {', '.join(signals)}")
        elif score >= 1:
            st.success(f"📈 종합: 매수 우위 ({score}점)")
            st.caption(f"💡 {', '.join(signals)}")
        elif score <= -3:
            st.error(f"📉 종합: 강력 매도 ({score}점)")
            st.caption(f"💡 {', '.join(signals)}")
        elif score <= -1:
            st.error(f"📉 종합: 매도 우위 ({score}점)")
            st.caption(f"💡 {', '.join(signals)}")
        else:
            st.info(f"⚖️ 종합: 중립 ({score}점)")
            st.caption(f"💡 {', '.join(signals) if signals else '시그널 없음'}")


def display_multi_stock_comparison():
    """다중 종목 비교 뷰"""
    st.subheader("📊 다중 종목 비교")

    # 현재 시장
    current_market = st.session_state.get('current_market', 'KR')
    
    # 종목 선택 (전체 종목 검색)
    col1, col2 = st.columns([3, 1])
    with col1:
        stock_options = st.session_state.get('active_stock_names', ["삼성전자 (005930)"])
        selected_stocks = st.multiselect(
            "비교할 종목 선택 (검색 가능)",
            stock_options,
            default=stock_options[:3] if len(stock_options) >= 3 else stock_options,
            key="multi_stock_select"
        )

    with col2:
        period = st.selectbox(
            "기간",
            ["1mo", "3mo", "6mo", "1y", "3y", "5y", "10y"],
            index=3,
            key="multi_period"
        )

    if st.button("🔄 데이터 수집 및 비교", type="primary", key="multi_fetch"):
        if not selected_stocks:
            st.warning("최소 1개 종목을 선택해주세요")
            return

        with st.spinner("데이터 수집 중..."):
            try:
                # 시장에 따른 ticker 생성
                active_stock_list = st.session_state.get('active_stock_list', {})
                if current_market == "US":
                    tickers_to_fetch = [active_stock_list.get(name, "AAPL") for name in selected_stocks]
                else:
                    tickers_to_fetch = [active_stock_list.get(name, "005930") + ".KS" for name in selected_stocks]
                # 캐싱 적용
                results = get_cached_multi_stock_data(tickers_to_fetch, period)

                if results:
                    # 수익률 비교 차트
                    st.markdown("### 📈 수익률 비교")
                    fig = go.Figure()

                    # ticker -> name 매핑 생성 (선택된 종목에서)
                    ticker_to_name = {}
                    for name in selected_stocks:
                        if current_market == "US":
                            ticker = active_stock_list.get(name, "AAPL")
                        else:
                            ticker = active_stock_list.get(name, "005930") + ".KS"
                        ticker_to_name[ticker] = name.split(" (")[0]
                    
                    for ticker, df in results.items():
                        if not df.empty:
                            name = ticker_to_name.get(ticker, ticker)
                            # 정규화된 수익률 계산
                            normalized = (df['close'] / df['close'].iloc[0] - 1) * 100
                            fig.add_trace(go.Scatter(
                                x=df['date'],
                                y=normalized,
                                name=name,
                                mode='lines'
                            ))

                    fig.update_layout(
                        title="종목별 수익률 비교 (기준일 대비 %)",
                        xaxis_title="날짜",
                        yaxis_title="수익률 (%)",
                        template='plotly_dark',
                        height=500,
                        xaxis_tickformat="%Y년 %m월",
                        dragmode=False # 드래그 비활성화
                    )
                    fig.update_xaxes(fixedrange=True)
                    fig.update_yaxes(fixedrange=True)
                    
                    st.plotly_chart(fig, width='stretch', config={'displayModeBar': False, 'scrollZoom': False})

                    # 상관관계 매트릭스
                    st.markdown("### 🔗 상관관계 분석")
                    close_prices = pd.DataFrame({
                        ticker_to_name.get(ticker, ticker): df.set_index('date')['close']
                        for ticker, df in results.items()
                    })
                    corr_matrix = close_prices.corr()

                    fig_corr = px.imshow(
                        corr_matrix,
                        text_auto='.2f',
                        color_continuous_scale='RdBu',
                        aspect='auto',
                        title="종목 간 상관관계"
                    )
                    fig_corr.update_layout(template='plotly_dark', height=400, dragmode=False)
                    fig_corr.update_xaxes(fixedrange=True)
                    fig_corr.update_yaxes(fixedrange=True)
                    st.plotly_chart(fig_corr, width='stretch', config={'displayModeBar': False, 'scrollZoom': False})

                    # 통계 요약
                    st.markdown("### 📊 통계 요약")
                    currency = MARKET_CONFIG[current_market]['currency_symbol']
                    summary_data = []
                    for ticker, df in results.items():
                        name = ticker_to_name.get(ticker, ticker)
                        total_return = (df['close'].iloc[-1] / df['close'].iloc[0] - 1) * 100
                        volatility = df['close'].pct_change().std() * np.sqrt(252) * 100

                        summary_data.append({
                            '종목': name,
                            '현재가': f"{currency}{df['close'].iloc[-1]:,.2f}" if current_market == 'US' else f"{currency}{df['close'].iloc[-1]:,.0f}",
                            '수익률': f"{total_return:+.2f}%",
                            '변동성(연)': f"{volatility:.2f}%",
                            '평균거래량': f"{df['volume'].mean():,.0f}"
                        })

                    st.dataframe(pd.DataFrame(summary_data), width='stretch')
                    
                    # 미국 시장일 경우 환율 정보 표시
                    if current_market == 'US':
                        try:
                            exchange_rate = get_cached_exchange_rate()
                            st.info(f"💱 현재 환율: 1 USD = ₩{exchange_rate:,.2f} (1시간 캐싱)")
                        except Exception:
                            pass

            except Exception as e:
                st.error(f"오류 발생: {str(e)}")


def display_news_sentiment():
    """뉴스 감성 분석 뷰"""
    st.subheader("📰 뉴스 & 감성 분석")
    
    # 현재 시장 확인
    current_market = st.session_state.get('current_market', 'KR')

    # 시장에 따른 종목 목록 선택
    if current_market == 'US':
        stock_options = st.session_state.get('us_stock_names', ["Apple (AAPL)"])
        default_stock = "Apple (AAPL)"
        stock_list = st.session_state.get('us_stock_list', {"Apple (AAPL)": "AAPL"})
    else:
        stock_options = st.session_state.get('krx_stock_names', list(DEFAULT_TICKERS.keys()))
        default_stock = "삼성전자 (005930)"
        stock_list = st.session_state.get('krx_stock_list', {"삼성전자 (005930)": "005930"})
    
    default_idx = stock_options.index(default_stock) if default_stock in stock_options else 0
    selected = st.selectbox("종목 검색", stock_options, index=default_idx, key="news_stock")
    ticker_code = stock_list.get(selected, "005930" if current_market == 'KR' else "AAPL")
    ticker_name = selected.split(" (")[0] if "(" in selected else selected

    # 검색어 설정 (구글 뉴스용)
    if current_market == 'US':
        search_query = st.text_input(
            "영문 뉴스 검색어 (수정 가능)", 
            value=f"{ticker_name} stock",
            help="Yahoo Finance 및 Google News (EN) 뉴스 수집 시 사용할 키워드입니다."
        )
    else:
        search_query = st.text_input(
            "구글 뉴스 검색어 (수정 가능)", 
            value=ticker_name,
            help="Google News 수집 시 사용할 키워드입니다. 네이버 금융 뉴스는 종목 코드로 자동 수집됩니다."
        )
    
    # 딥러닝 분석 옵션 (한국어 전용)
    if current_market == 'KR':
        use_deep_learning = st.checkbox(
            "🧠 딥러닝 감성 분석 (KR-FinBert-SC)",
            value=False,
            help="GPU 활용 딥러닝 모델로 더 정확한 감성 분석을 수행합니다. 첫 실행 시 모델 다운로드가 필요합니다."
        )
    else:
        use_deep_learning = False
        st.info("💡 미국 종목은 VADER 기반 영문 감성 분석을 사용합니다.")

    if st.button("📥 뉴스 수집 및 분석", type="primary"):
        with st.spinner(f"'{search_query}' 관련 뉴스 수집 중..."):
            try:
                news_collector = NewsCollector()
                sentiment_analyzer = SentimentAnalyzer(use_deep_learning=use_deep_learning)
                
                if current_market == 'US':
                    # 미국 종목: Yahoo Finance + Google News (EN)
                    yahoo_articles = news_collector.fetch_yahoo_finance_news_rss(ticker_code, max_items=30)
                    google_articles = news_collector.fetch_google_news_en_rss(search_query, max_items=30)
                    all_articles_raw = yahoo_articles + google_articles
                else:
                    # 한국 종목: 네이버 금융 + 구글 뉴스 (KR)
                    naver_articles = news_collector.fetch_naver_finance_news(ticker_code, max_pages=5)
                    google_articles = news_collector.fetch_google_news_rss(search_query, max_items=50)
                    all_articles_raw = naver_articles + google_articles
                
                # 제목 유사도 기반 중복 필터링
                def filter_similar_titles(articles, threshold=0.4):
                    if not articles:
                        return []
                    filtered = [articles[0]]
                    for article in articles[1:]:
                        is_duplicate = False
                        title_words = set(article['title'].lower().split())
                        for existing in filtered:
                            existing_words = set(existing['title'].lower().split())
                            if not title_words or not existing_words:
                                continue
                            intersection = len(title_words & existing_words)
                            union = len(title_words | existing_words)
                            similarity = intersection / union if union > 0 else 0
                            if similarity >= threshold:
                                is_duplicate = True
                                break
                        if not is_duplicate:
                            filtered.append(article)
                    return filtered
                
                all_articles = filter_similar_titles(all_articles_raw, threshold=0.4)
                
                if all_articles:
                    # 감성 점수 계산
                    if current_market == 'US':
                        analysis_method = "VADER (영문)"
                    elif use_deep_learning:
                        analysis_method = "딥러닝 (KR-FinBert-SC)"
                    else:
                        analysis_method = "키워드 기반"
                    
                    with st.spinner(f"감성 분석 중... ({analysis_method})"):
                        for article in all_articles:
                            text = article['title'] + ' ' + article.get('content', '')
                            
                            # 시장에 따른 분석 방법 선택
                            if current_market == 'US':
                                score, details = sentiment_analyzer.analyze_text_en(text)
                                article['analysis_method'] = 'vader_en'
                            elif use_deep_learning:
                                score, details = sentiment_analyzer.analyze_text_deep(text)
                                article['analysis_method'] = 'deep_learning'
                            else:
                                score, details = sentiment_analyzer.analyze_text(text)
                                article['analysis_method'] = 'keyword'
                            
                            article['sentiment'] = score
                            
                            if score > 0.5:
                                article['sentiment_label'] = 'VERY_POSITIVE'
                            elif score > 0.2:
                                article['sentiment_label'] = 'POSITIVE'
                            elif score < -0.5:
                                article['sentiment_label'] = 'VERY_NEGATIVE'
                            elif score < -0.2:
                                article['sentiment_label'] = 'NEGATIVE'
                            else:
                                article['sentiment_label'] = 'NEUTRAL'
                            article['published_date'] = article.get('date', '')
                    
                    # session_state에 저장
                    st.session_state['news_articles'] = all_articles
                    
                    # 시장별 수집 결과 표시
                    if current_market == 'US':
                        st.session_state['news_yahoo_count'] = len(yahoo_articles)
                        st.session_state['news_google_count'] = len(google_articles)
                        st.success(f"✅ 총 {len(all_articles)}개 뉴스 (Yahoo: {len(yahoo_articles)}, Google: {len(google_articles)}, 중복 제거: {len(all_articles_raw) - len(all_articles)}개)")
                    else:
                        st.session_state['news_naver_count'] = len(naver_articles)
                        st.session_state['news_google_count'] = len(google_articles)
                        st.success(f"✅ 총 {len(all_articles)}개 뉴스 (네이버: {len(naver_articles)}, 구글: {len(google_articles)}, 중복 제거: {len(all_articles_raw) - len(all_articles)}개)")
                    st.session_state['news_filtered_count'] = len(all_articles_raw) - len(all_articles)
                else:
                    st.warning("수집된 뉴스가 없습니다")
                    st.session_state['news_articles'] = []
                    
            except Exception as e:
                st.error(f"오류 발생: {str(e)}")
                import traceback
                st.code(traceback.format_exc())

    # 저장된 뉴스 표시 (session_state에서 가져옴)
    if 'news_articles' in st.session_state and st.session_state['news_articles']:
        all_articles = st.session_state['news_articles']
        
        st.caption(f"ℹ️ 수집된 뉴스: {len(all_articles)}개")
        
        # 감성 분포 차트
        st.markdown("### 📊 감성 분포")
        sentiments = [a['sentiment'] for a in all_articles]
        fig_sent = go.Figure(data=[go.Histogram(
            x=sentiments,
            nbinsx=20,
            marker_color='lightblue'
        )])
        fig_sent.update_layout(
            title="뉴스 감성 점수 분포",
            xaxis_title="감성 점수 (-1: 부정, +1: 긍정)",
            yaxis_title="뉴스 개수",
            template='plotly_dark',
            height=300,
            dragmode=False
        )
        fig_sent.update_xaxes(fixedrange=True)
        fig_sent.update_yaxes(fixedrange=True)
        st.plotly_chart(fig_sent, width='stretch', config={'displayModeBar': False, 'scrollZoom': False})

        # 평균 감성
        avg_sentiment = np.mean(sentiments)
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("평균 감성 점수", f"{avg_sentiment:.3f}")
        with col2:
            positive_pct = len([s for s in sentiments if s > 0]) / len(sentiments) * 100
            st.metric("긍정 뉴스 비율", f"{positive_pct:.1f}%")
        with col3:
            negative_pct = len([s for s in sentiments if s < 0]) / len(sentiments) * 100
            st.metric("부정 뉴스 비율", f"{negative_pct:.1f}%")

        # 뉴스 목록 헤더 + 정렬 버튼 (한 줄에 배치)
        col_title, col_sort = st.columns([3, 2])
        with col_title:
            st.markdown("### 📰 뉴스 목록")
        with col_sort:
            sort_option = st.radio(
                "정렬",
                ["최신순", "긍정↑", "부정↑"],
                horizontal=True,
                key="news_sort_radio",
                label_visibility="collapsed"
            )
        
        # 정렬 적용
        if sort_option == "긍정↑":
            sorted_articles = sorted(all_articles, key=lambda x: x['sentiment'], reverse=True)
        elif sort_option == "부정↑":
            sorted_articles = sorted(all_articles, key=lambda x: x['sentiment'])
        else:
            sorted_articles = all_articles
        
        # 감성별 아이콘 함수
        def get_sentiment_icon(score):
            if score > 0.5:
                return "🟢"
            elif score > 0.2:
                return "🔵"
            elif score >= -0.2:
                return "⚪"
            elif score > -0.5:
                return "🟠"
            else:
                return "🔴"
        
        # 전체 뉴스 표시
        for i, article in enumerate(sorted_articles, 1):
            icon = get_sentiment_icon(article['sentiment'])
            title_display = article['title'][:80] + "..." if len(article['title']) > 80 else article['title']
            
            with st.expander(f"{icon} [{i}] {title_display}"):
                col_a, col_b = st.columns([1, 1])
                with col_a:
                    if article['published_date']:
                        st.write(f"**발행일:** {article['published_date']}")
                    st.write(f"**출처:** {article.get('source', 'Naver Finance')}")
                with col_b:
                    st.write(f"**감성 점수:** {article['sentiment']:.3f}")
                    st.write(f"**분류:** {article['sentiment_label']}")
                st.write(f"🔗 [기사 링크]({article['url']})")


def display_ai_prediction():
    """AI 예측 뷰 (앙상블)"""
    st.subheader("🤖 AI 예측 (앙상블 모델)")

    # 전체 종목 검색
    stock_options = st.session_state.get('active_stock_names', list(DEFAULT_TICKERS.keys()))
    default_stock = "삼성전자 (005930)" if st.session_state.get('current_market') == "KR" else "Apple (AAPL)"
    default_idx = stock_options.index(default_stock) if default_stock in stock_options else 0
    selected = st.selectbox("종목 검색", stock_options, index=default_idx, key="ai_ticker")
    
    # 시장에 따른 ticker 코드 생성
    if st.session_state.get('current_market') == "US":
        ticker_code = st.session_state.get('active_stock_list', {}).get(selected, "AAPL")
    else:
        ticker_code = st.session_state.get('active_stock_list', {}).get(selected, "005930") + ".KS"
    ticker_name = selected.split(" (")[0] if "(" in selected else selected

    col1, col2 = st.columns(2)
    with col1:
        strategy = st.selectbox(
            "앙상블 전략 (마우스를 올려보세요)",
            ["weighted_average", "voting", "stacking"],
            format_func=lambda x: {
                "weighted_average": "가중평균 (Weighted Average)",
                "voting": "투표 (Voting)",
                "stacking": "스태킹 (Stacking)"
            }[x],
            help="""
            🤖 앙상블 전략 설명:
            
            1. 가중평균: 각 모델의 예측값에 비중을 두어 합산합니다.
            2. 투표: 모델들의 다수결로 상승/하락을 결정합니다.
            3. 스태킹: 모델들의 예측 결과를 AI가 다시 학습하여 최종 판단합니다.
            """
        )
        
        # 선택된 전략 상세 설명
        strategy_desc = {
            "weighted_average": "💡 **가중평균:** 성과가 좋은 모델에 더 높은 비중을 주어 예측 오차를 줄입니다.",
            "voting": "💡 **투표:** 여러 전문가의 의견을 듣고 다수결로 결정하는 것과 같습니다.",
            "stacking": "💡 **스태킹:** 여러 모델의 장점을 결합해 시너지를 내는 고도화된 방식입니다."
        }
        st.caption(strategy_desc[strategy])

    with col2:
        period = st.selectbox(
            "학습 기간 (데이터가 많을수록 정확도 향상)", 
            ["1y", "2y", "5y", "10y", "max"], 
            index=2, 
            key="ai_period",
            help="Transformer 등 딥러닝 모델은 데이터가 많을수록(기간이 길수록) 성능이 좋아집니다."
        )

    # 저장된 모델 검색
    import os
    saved_models_dir = PROJECT_ROOT / "src" / "models" / "saved_models"
    use_saved_model = False
    use_incremental = False  # 점진적 학습 플래그 초기화
    latest_model_prefix = None
    
    if saved_models_dir.exists():
        safe_ticker = ticker_code.replace(":", "").replace("/", "")
        # 해당 종목의 파일 찾기 (예: 005930.KS_20251225_lstm)
        try:
            files = os.listdir(saved_models_dir)
            candidates = set()
            for f in files:
                if f.startswith(safe_ticker) and any(x in f for x in ["_lstm", "_xgboost", "_transformer"]):
                    # prefix 추출: 모델 타입 전까지 (_lstm, _xgboost, _transformer 앞까지)
                    # 예: "005930.KS_20251225_lstm.keras" → "005930.KS_20251225"
                    for suffix in ["_lstm", "_xgboost", "_transformer"]:
                        if suffix in f:
                            prefix = f.split(suffix)[0]
                            candidates.add(prefix)
                            break
            
            # 날짜 기준으로 정렬 (최신이 앞으로)
            sorted_candidates = sorted(list(candidates), reverse=True)
            
            if sorted_candidates:
                latest_model_prefix = sorted_candidates[0]
                # 날짜 추출: 마지막 _ 뒤의 숫자
                parts = latest_model_prefix.split('_')
                latest_date = parts[-1] if parts[-1].isdigit() and len(parts[-1]) == 8 else "Unknown"
                formatted_date = f"{latest_date[:4]}-{latest_date[4:6]}-{latest_date[6:]}" if latest_date != "Unknown" else latest_date
                
                st.info(f"📅 최근 학습된 모델이 있습니다 ({formatted_date})")
                use_saved_model = st.checkbox(
                    "💾 저장된 모델 불러오기 (재학습 건너뛰기)", 
                    value=True,
                    help=f"체크하면 '{formatted_date}'에 학습된 모델을 불러와서 예측만 수행합니다. 시간이 절약됩니다."
                )
                
                
                # 점진적 학습 옵션 (저장된 모델이 있을 때만 표시)
                if use_saved_model:
                    # Service Layer 초기화
                    model_repo = ModelRepository(storage_path="src/models/saved_models")
                    incremental_service = IncrementalLearningService(model_repo)
                    
                    # 현재 데이터로 점진적 학습 가능 여부 확인
                    df_check = get_cached_stock_data(ticker_code, period)
                    if not df_check.empty:
                        available, info = incremental_service.check_incremental_availability(
                            ticker=ticker_code,
                            current_data=df_check
                        )
                        
                        if available and info and 'error' not in info:
                            with st.expander("🔄 **점진적 학습 옵션**", expanded=False):
                                st.markdown(f"""
                                **감지된 신규 데이터**: {info['new_data_count']}일치  
                                📅 {info['new_data_start']} ~ {info['new_data_end']}
                                
                                점진적 학습은 **기존 모델에 새 데이터만 추가로 학습**합니다.
                                - ⚡ **장점**: 빠른 학습 (전체 학습의 약 1/5 시간)
                                - 🎯 **적합**: 신규 데이터가 3일 이상일 때
                                """)
                                
                                # Distribution Shift 경고
                                if info['shift_detected']:
                                    st.warning(f"""
                                    ⚠️ **시장 급변 감지됨**
                                    - KL Divergence: {info['shift_info']['kl_divergence']:.3f} (임계값: {info['shift_info']['kl_threshold']})
                                    - 변동성 변화: {info['shift_info']['volatility_change_ratio']:.1%}
                                    
                                    **권장**: 전체 재학습 (점진적 학습은 성능 저하 가능)
                                    """)
                                    default_incremental = False
                                else:
                                    default_incremental = True if info['new_data_count'] >= 3 else False
                                
                                use_incremental = st.checkbox(
                                    "🔄 점진적 학습 사용",
                                    value=default_incremental,
                                    help="체크 해제 시 전체 데이터로 처음부터 재학습합니다."
                                )
                                
                                if use_incremental and info.get('new_data_count', 0) < 3:
                                    st.caption("💡 신규 데이터가 적어 효과가 제한적일 수 있습니다.")
                        elif info and 'error' in info:
                            st.info(f"ℹ️ 점진적 학습 불가: {info['error']}")
                            use_incremental = False
                        elif info is None:
                            # 메타데이터가 없는 구 버전 모델
                            st.info("""
                            ℹ️ **구 버전 모델 감지**
                            
                            현재 저장된 모델은 메타데이터가 없어 점진적 학습을 지원하지 않습니다.
                            
                            💡 **해결 방법**:
                            - "💾 저장된 모델 불러오기" 체크를 **해제**하고
                            - "💾 학습된 모델 저장" 체크를 **유지**한 상태에서
                            - 한 번 전체 재학습을 진행하면, 이후부터 점진적 학습이 가능합니다.
                            """)
                            use_incremental = False
                        else:
                            # 신규 데이터가 없음
                            st.info("ℹ️ 신규 데이터가 없습니다. 저장된 모델을 그대로 사용합니다.")
                            use_incremental = False
                    else:
                        use_incremental = False
                else:
                    use_incremental = False
        except Exception as e:
            st.warning(f"모델 검색 중 오류: {e}")
            use_incremental = False

    # Transformer 모델 및 저장 옵션
    st.markdown("##### ⚙️ 고급 설정")
    col_opt1, col_opt2, col_opt3, col_opt4 = st.columns(4)
    with col_opt1:
        use_transformer = st.checkbox("🤖 Transformer 포함", value=False, 
                                       disabled=use_saved_model,
                                       help="Transformer(Attention) 모델을 포함하여 예측합니다. (시간이 더 소요됨)")
    with col_opt2:
        use_regime = st.checkbox("🌍 시장 국면 반영", value=True,
                                 help="현재 시장 상황(강세/약세/횡보)을 감지하고, 이에 맞춰 AI 모델 가중치를 자동으로 조절합니다.")
    with col_opt3:
        use_sentiment = st.checkbox("📰 감성 분석 포함", value=False,
                                    help="뉴스 감성 점수를 AI 모델 입력으로 추가합니다.")
    with col_opt4:
        start_save = st.checkbox("💾 학습된 모델 저장", value=True, 
                                 disabled=use_saved_model,
                                 help="새로 학습한 모델을 저장하여 나중에 재사용합니다.")
    
    # Phase F: LLM 감성 분석 옵션 (감성 분석 활성화 시에만 표시)
    use_llm_sentiment = False
    if use_sentiment:
        use_llm_sentiment = st.checkbox(
            "🧠 Gemini LLM 감성 분석", 
            value=False,
            help="Gemini AI를 활용한 고급 감성 분석을 사용합니다. API 키 필요."
        )

    if st.button("🚀 예측 실행", type="primary"):
        with st.status("🚀 AI 심층 분석 진행 중...", expanded=True) as status:
            status.write("📊 시장 데이터 수집 중...")
            try:
                # Phase F: MarketDataService 우선 사용 (Fallback + 캐싱)
                if MARKET_SERVICE_AVAILABLE:
                    market = st.session_state.get('current_market', 'KR')
                    service = MarketDataService(market=market)
                    ohlcv = service.get_ohlcv(ticker_code, period=period)
                    df = ohlcv.to_dataframe()
                    
                    # 차트 호환성: index를 date 컬럼으로 변환
                    if 'date' not in df.columns:
                        df = df.reset_index()
                        if 'Date' in df.columns:
                            df = df.rename(columns={'Date': 'date'})
                        elif 'index' in df.columns:
                            df = df.rename(columns={'index': 'date'})
                        elif df.columns[0] != 'date':
                            df = df.rename(columns={df.columns[0]: 'date'})
                else:
                    # Fallback: 기존 StockDataCollector
                    collector = StockDataCollector()
                    df = collector.fetch_stock_data(ticker_code, period=period)

                if df.empty:
                    st.error("데이터를 가져올 수 없습니다")
                    return

                # 기술적 지표 추가
                analyzer = TechnicalAnalyzer(df)
                analyzer.add_all_indicators()
                df = analyzer.get_dataframe()

                # 감성 분석 피처 통합 (옵션)
                feature_cols = None
                if use_sentiment:
                    llm_msg = " (🧠 Gemini LLM)" if use_llm_sentiment else ""
                    st.info(f"📰 뉴스 감성 분석 중...{llm_msg}")
                    try:
                        from src.models.sentiment_feature_integrator import create_enhanced_features
                        current_market = st.session_state.get('current_market', 'KR')
                        df, feature_cols = create_enhanced_features(
                            df, ticker_code, ticker_name, current_market, 
                            include_sentiment=True,
                            use_llm=use_llm_sentiment  # Phase F: Gemini LLM 옵션
                        )
                        st.success(f"✅ 감성 피처 {len([c for c in feature_cols if 'sentiment' in c])}개 추가됨{llm_msg}")
                    except Exception as e:
                        st.warning(f"감성 분석 생략: {str(e)}")

                # 앙상블 예측 (LSTM + XGBoost + Transformer)
                ensemble = EnsemblePredictor(strategy=strategy)

                if use_saved_model and latest_model_prefix:
                    st.info(f"💾 저장된 모델을 불러오는 중입니다... ({latest_model_prefix})")
                    try:
                        load_path = saved_models_dir / latest_model_prefix
                        # load_models에 prefix 전달 (절대 경로 포함)
                        ensemble.load_models(str(load_path))
                        st.success("✅ 모델 로드 완료!")
                    except Exception as e:
                        st.error(f"모델 로드에 실패했습니다: {str(e)}")
                        st.warning("⚠️ '저장된 모델 불러오기' 체크를 해제하고 다시 시도하여 새로 학습해주세요.")
                        return
                else:
                    # 모델 학습 또는 점진적 학습
                    if use_incremental and latest_model_prefix:
                        # 점진적 학습 모드
                        st.info("🔄 점진적 학습 모드: 신규 데이터로 Fine-tuning 중...")
                        status.write(f"🔄 점진적 학습 중... (신규 데이터 {info.get('new_data_count', 'N/A')}일치)")
                        
                        # 기존 모델 로드
                        load_path = saved_models_dir / latest_model_prefix
                        ensemble.load_models(str(load_path))
                        
                        # 신규 데이터 추출
                        data_end_date = pd.to_datetime(info['metadata']['data_end_date'])
                        df['date'] = pd.to_datetime(df['date'])
                        new_data = df[df['date'] > data_end_date].copy()
                        old_data = df[df['date'] <= data_end_date].copy()
                        
                        # Replay Buffer 생성
                        model_repo = ModelRepository(storage_path="src/models/saved_models")
                        incremental_service = IncrementalLearningService(model_repo)
                        replay_buffer = incremental_service.create_replay_buffer(old_data, new_data, replay_ratio=0.1)
                        
                        st.caption(f"📦 Replay Buffer: {len(replay_buffer)}개 데이터 샘플")
                        
                        # 점진적 학습
                        ensemble.train_models(
                            new_data,
                            train_lstm=True,
                            train_xgboost=True,
                            train_transformer=use_transformer,
                            verbose=0,
                            incremental=True,
                            replay_buffer=replay_buffer
                        )
                        
                    else:
                        # 전체 학습 모드 (기존 로직)
                        train_size = int(len(df) * 0.8)
                        train_df = df.iloc[:train_size].copy()

                        model_name = "LSTM + XGBoost" + (" + Transformer" if use_transformer else "")
                        st.info(f"새 모델 학습 중... ({model_name})")
                        status.write("📊 전체 데이터 재학습 중...")
                        
                        # 모델 학습
                        ensemble.train_models(
                            train_df, 
                            train_lstm=True, 
                            train_xgboost=True, 
                            train_transformer=use_transformer,
                            verbose=0
                        )
                    
                    # 모델 저장 (점진적/전체 공통)
                    if start_save or use_incremental:
                        import os
                        save_dir = (PROJECT_ROOT / "src" / "models" / "saved_models").resolve()
                        os.makedirs(save_dir, exist_ok=True)
                        
                        # 파일명 안전하게 처리 (특수문자 제거 및 .KS 제거)
                        safe_ticker = ticker_code.replace(":", "").replace("/", "").replace(".KS", "")
                        today = datetime.now().strftime("%Y%m%d")
                        save_path = save_dir / f"{safe_ticker}_{today}"
                        
                        # 메타데이터 생성
                        save_metadata = {
                            'last_train_date': datetime.now().isoformat(),
                            'data_end_date': df['date'].max().isoformat(),
                            'total_samples': len(df),
                            'feature_cols': df.columns.tolist(),
                            'ticker': ticker_code,
                            'incremental_training': use_incremental
                        }
                        
                        ensemble.save_models(str(save_path), metadata=save_metadata)
                        st.success(f"💾 모델 저장 완료: {save_path}")

                # 예측
                current_price = df['close'].iloc[-1]
                
                if use_regime:
                    # RegimeAwarePredictor 사용
                    from src.models.regime_predictor import RegimeAwarePredictor
                    
                    st.info("🌍 시장 국면 분석 및 적응형 예측 수행 중...")
                    regime_predictor = RegimeAwarePredictor(ensemble_predictor=ensemble)
                    
                    # feature_cols는 1100 라인에서 받아오지 않았다면 None일 수 있음. 
                    # create_enhanced_features 결과를 쓰려면 feature_cols 변수가 필요. 
                    # 문맥상 feature_cols는 감성분석 할때만 생성됨.
                    
                    regime_result = regime_predictor.predict(df, use_regime_weights=True)
                    
                    # 결과 매핑
                    predicted_price = regime_result['prediction']
                    final_confidence = regime_result['confidence']
                    regime_info = regime_result['regime']
                    
                    # 호환성 유지
                    price_pred = {'ensemble_prediction': predicted_price, 'individual_predictions': {}}
                    direction_pred = {
                        'ensemble_prediction': 'up' if predicted_price and predicted_price > current_price else 'down',
                        'confidence_score': final_confidence,
                        'individual_predictions': {}
                    }
                    
                    status.update(label="✅ 예측 완료!", state="complete", expanded=False)
                    st.success(f"✅ 시장 국면: {regime_info.description} (신뢰도 {regime_info.confidence:.0%})")
                    st.info(f"💡 투자 권고: {regime_result['recommendation']}")
                    with st.expander("🔍 상세 가중치 및 설명"):
                        st.write(f"VIX 수준: {regime_info.vix_level:.2f}")
                        st.write(f"추세 강도: {regime_info.trend}")
                        st.json(regime_result['model_weights'])
                else:
                    st.info("예측 수행 중...")
                    price_pred = ensemble.predict_price(df)
                    direction_pred = ensemble.predict_direction(df)

                # 결과 표시 (현재가 변수는 위에서 이미 선언됨)
                
                # 예측 대상 날짜 계산 (마지막 데이터 날짜 + 1 영업일)
                last_date = pd.to_datetime(df['date'].iloc[-1])
                next_date = last_date + pd.Timedelta(days=1)
                while next_date.weekday() > 4:  # 주말이면 평일까지 이동
                    next_date += pd.Timedelta(days=1)
                
                prediction_date_str = next_date.strftime("%m/%d")
                
                # 가격 기반으로 방향 결정 (예측 종가와 현재가 비교)
                predicted_price = price_pred.get('ensemble_prediction')
                if predicted_price:
                    price_based_direction = 'up' if predicted_price > current_price else 'down'
                    price_change_pct = ((predicted_price - current_price) / current_price) * 100
                else:
                    # 가격 예측이 없으면 앙상블 방향 사용
                    price_based_direction = direction_pred['ensemble_prediction']
                    price_change_pct = 0
                
                confidence = direction_pred['confidence_score']
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("현재가", f"₩{current_price:,.0f}", f"{last_date.strftime('%Y-%m-%d')}")

                with col2:
                    if predicted_price:
                        st.metric(
                            f"예측 종가 ({prediction_date_str}, 앙상블)",
                            f"₩{predicted_price:,.0f}",
                            f"{price_change_pct:+.2f}%"
                        )
                    else:
                        st.metric("예측 종가", "N/A")

                with col3:
                    direction_emoji = "📈" if price_based_direction == 'up' else "📉"
                    direction_label = "상승" if price_based_direction == 'up' else "하락"
                    st.metric(
                        f"예측 방향 {direction_emoji}",
                        direction_label,
                        f"신뢰도: {confidence:.1%}"
                    )

                # 개별 모델 예측
                st.markdown("### 🔍 개별 모델 예측")
                model_data = []
                if price_pred.get('individual_predictions'):
                    for k, v in price_pred['individual_predictions'].items():
                        model_data.append({'모델': k, '예측값': f"₩{v:,.0f}" if isinstance(v, (int, float)) else str(v)})
                if direction_pred.get('individual_predictions'):
                    for k, v in direction_pred['individual_predictions'].items():
                        if k not in [d['모델'] for d in model_data]:
                            model_data.append({'모델': k, '예측값': '상승' if v == 1 else '하락'})
                
                if model_data:
                    st.dataframe(pd.DataFrame(model_data), width='stretch')

                # 신뢰도 분석
                st.markdown("### 📊 신뢰도 분석")
                confidence_level = "높음" if confidence > ENSEMBLE_CONFIG['confidence_threshold']['high'] else \
                                  "중간" if confidence > ENSEMBLE_CONFIG['confidence_threshold']['medium'] else "낮음"

                st.info(f"**신뢰도 수준:** {confidence_level} ({confidence:.1%})")
                
                # 모델별 가중치
                st.caption(f"모델 가중치: {ensemble.weights}")

            except Exception as e:
                st.error(f"예측 중 오류 발생: {str(e)}")
                import traceback
                st.code(traceback.format_exc())



def display_backtest():
    """백테스팅 뷰"""
    st.subheader("⏮️ 백테스팅")

    # 현재 시장
    current_market = st.session_state.get('current_market', 'KR')
    
    # 전체 종목 검색
    stock_options = st.session_state.get('active_stock_names', ["삼성전자 (005930)"])
    default_stock = "삼성전자 (005930)" if current_market == "KR" else "Apple (AAPL)"
    default_idx = stock_options.index(default_stock) if default_stock in stock_options else 0
    selected = st.selectbox("종목 검색", stock_options, index=default_idx, key="bt_ticker")
    
    # 시장에 따른 ticker 코드 생성
    if current_market == "US":
        ticker_code = st.session_state.get('active_stock_list', {}).get(selected, "AAPL")
    else:
        ticker_code = st.session_state.get('active_stock_list', {}).get(selected, "005930") + ".KS"
    ticker_name = selected.split(" (")[0] if "(" in selected else selected

    col1, col2, col3 = st.columns(3)
    with col1:
        strategy_type = st.selectbox(
            "전략 선택",
            ["RSI", "MACD", "이동평균"],
        )

    with col2:
        period = st.selectbox("테스트 기간", ["1y", "2y", "3y", "5y", "10y"], index=1, key="bt_period")

    with col3:
        initial_capital = st.number_input(
            "초기 자본 (원)",
            min_value=1000000,
            max_value=100000000,
            value=10000000,
            step=1000000
        )

    if st.button("▶️ 백테스트 실행", type="primary"):
        with st.spinner("백테스트 진행 중..."):
            try:
                # 데이터 수집
                # 데이터 수집 (캐싱 적용)
                df = get_cached_stock_data(ticker_code, period)

                if df.empty:
                    st.error("데이터를 가져올 수 없습니다")
                    return

                # 기술적 지표 추가
                analyzer = TechnicalAnalyzer(df)
                analyzer.add_all_indicators()
                df = analyzer.get_dataframe()
                # date를 인덱스로 설정하고 컬럼에서 제거
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

                # 성과 지표 계산
                metrics = PerformanceMetrics(results['equity'], initial_capital)
                trades_df = backtester.get_trades_df()
                metrics_dict = metrics.get_all_metrics(trades_df)

                # 결과 표시
                st.success(f"✅ 백테스트 완료 (거래 횟수: {len(trades_df)})")

                # 주요 성과 지표
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric(
                        "총 수익률",
                        f"{metrics_dict['total_return']*100:.2f}%"
                    )
                with col2:
                    st.metric(
                        "연환산 수익률",
                        f"{metrics_dict['cagr']*100:.2f}%"
                    )
                with col3:
                    st.metric(
                        "최대 낙폭 (MDD)",
                        f"{metrics_dict['max_drawdown']*100:.2f}%"
                    )
                with col4:
                    st.metric(
                        "샤프 비율",
                        f"{metrics_dict['sharpe_ratio']:.2f}"
                    )

                # 수익률 곡선
                st.markdown("### 📈 포트폴리오 가치 변화")
                # 날짜 데이터 가져오기
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
                    height=400,
                    xaxis_tickformat="%Y년 %m월"
                )
                st.plotly_chart(fig, width='stretch', config={'scrollZoom': False})

                # 상세 성과 지표 (한글 키만 표시, 스크롤 없이 전체 표시)
                with st.expander("📊 상세 성과 지표", expanded=True):
                    # 용어 설명 딕셔너리 (회색 물음표 툴팁용)
                    tooltips = {
                        '총 수익률': '투자 기간 동안의 전체 수익률 (최종자산/초기자산 - 1)',
                        '연환산 수익률 (CAGR)': '연평균 복리 수익률. 투자 기간을 1년 기준으로 환산한 수익률',
                        '최종 자산': '백테스트 종료 시점의 포트폴리오 가치',
                        '최대 낙폭 (MDD)': '최고점 대비 최대 하락폭. 투자 위험을 나타내는 핵심 지표',
                        'MDD 기간 (일)': '최대 낙폭이 지속된 거래일 수',
                        '연환산 변동성': '수익률의 표준편차를 연간 기준으로 환산. 위험도를 나타냄',
                        '샤프 비율': '(수익률-무위험수익률)/변동성. 1 이상이면 양호, 2 이상이면 우수',
                        '소르티노 비율': '샤프 비율과 유사하나 하락 변동성만 고려. 더 정확한 위험조정 수익률',
                        '칼마 비율': 'CAGR/MDD. 낙폭 대비 수익률을 측정. 높을수록 좋음',
                        '총 거래 횟수': '백테스트 기간 동안 실행된 총 매매 횟수',
                        '승률': '수익을 낸 거래의 비율',
                        '수익 팩터': '총이익/총손실. 1보다 크면 수익, 2 이상이면 우수한 전략',
                        '평균 수익': '수익 거래의 평균 수익금액',
                        '평균 손실': '손실 거래의 평균 손실금액',
                    }
                    
                    # 한글 키만 필터링
                    korean_keys = [k for k in metrics_dict.keys() if any('\uAC00' <= c <= '\uD7A3' for c in str(k))]
                    korean_metrics = {k: metrics_dict[k] for k in korean_keys}
                    
                    # 값 포맷팅
                    formatted_metrics = {}
                    for key, value in korean_metrics.items():
                        if '수익률' in key or '승률' in key or '낙폭' in key or '변동성' in key:
                            formatted_metrics[key] = f"{value*100:.2f}%"
                        elif '자산' in key or '수익' in key or '손실' in key:
                            formatted_metrics[key] = f"₩{value:,.0f}"
                        elif '횟수' in key or '기간' in key:
                            formatted_metrics[key] = f"{value:,.0f}"
                        else:
                            formatted_metrics[key] = f"{value:.2f}"
                    
                    # 표 형식으로 표시 (스크롤 없이 전체 표시)
                    metrics_df = pd.DataFrame([formatted_metrics]).T
                    metrics_df.columns = ['값']
                    
                    # 설명 컬럼 추가
                    metrics_df['설명'] = metrics_df.index.map(lambda x: tooltips.get(x, ''))
                    
                    # 전체 높이로 표시 (스크롤 없음)
                    st.dataframe(metrics_df, width='stretch', height=(len(metrics_df) + 1) * 35 + 3)

                # 거래 내역 (컬럼명 한글화)
                with st.expander("📋 거래 내역"):
                    if not trades_df.empty:
                        # 컬럼명 한글화
                        column_map = {
                            'entry_date': '진입일',
                            'entry_price': '진입가',
                            'exit_date': '청산일',
                            'exit_price': '청산가',
                            'shares': '수량',
                            'pnl': '손익',
                            'pnl_pct': '수익률'
                        }
                        trades_display = trades_df.rename(columns=column_map)
                        
                        # 포맷팅 (모든 숫자를 문자열로 변환하여 좌측 정렬 통일)
                        if '수량' in trades_display.columns:
                            trades_display['수량'] = trades_display['수량'].apply(lambda x: f"{x:,}")
                        if '손익' in trades_display.columns:
                            trades_display['손익'] = trades_display['손익'].apply(lambda x: f"₩{x:,.0f}")
                        if '수익률' in trades_display.columns:
                            trades_display['수익률'] = trades_display['수익률'].apply(lambda x: f"{x*100:.2f}%")
                        if '진입가' in trades_display.columns:
                            trades_display['진입가'] = trades_display['진입가'].apply(lambda x: f"₩{x:,.0f}")
                        if '청산가' in trades_display.columns:
                            trades_display['청산가'] = trades_display['청산가'].apply(lambda x: f"₩{x:,.0f}")
                        
                        st.dataframe(trades_display, width='stretch', hide_index=True)
                    else:
                        st.info("거래 내역이 없습니다")

            except Exception as e:
                st.error(f"오류 발생: {str(e)}")
                import traceback
                st.code(traceback.format_exc())


def display_single_stock_analysis_mini(panel_id: str):
    """분할 모드용 간소화된 단일 종목 분석"""
    # 종목 선택
    stock_options = st.session_state.get('krx_stock_names', ["삼성전자 (005930)"])
    default_idx = stock_options.index("삼성전자 (005930)") if "삼성전자 (005930)" in stock_options else 0
    
    col1, col2 = st.columns([2, 1])
    with col1:
        selected = st.selectbox("종목 선택", stock_options, index=default_idx, key=f"mini_stock_{panel_id}")
    with col2:
        period = st.selectbox("기간", ["1mo", "3mo", "6mo", "1y"], index=2, 
                             format_func=lambda x: {"1mo": "1개월", "3mo": "3개월", "6mo": "6개월", "1y": "1년"}.get(x),
                             key=f"mini_period_{panel_id}")
    
    ticker_code = st.session_state.get('krx_stock_list', {}).get(selected, "005930") + ".KS"
    ticker_name = selected.split(" (")[0] if "(" in selected else selected
    
    # 데이터 로드 버튼
    if st.button("📥 데이터 로드", key=f"mini_fetch_{panel_id}", type="primary"):
        with st.spinner(f'{ticker_name} 데이터 로드 중...'):
            try:
                df = get_cached_stock_data(ticker_code, period)
                if not df.empty:
                    analyzer = TechnicalAnalyzer(df)
                    analyzer.add_all_indicators()
                    df = analyzer.get_dataframe()
                    st.session_state[f'mini_data_{panel_id}'] = df
                    st.session_state[f'mini_name_{panel_id}'] = ticker_name
                    st.success(f"✅ {len(df)}개 데이터 로드 완료!")
            except Exception as e:
                st.error(f"오류: {e}")
    
    # 차트 표시
    if f'mini_data_{panel_id}' in st.session_state:
        df = st.session_state[f'mini_data_{panel_id}']
        name = st.session_state.get(f'mini_name_{panel_id}', ticker_name)
        
        # 주요 지표
        latest = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else latest
        change = latest['close'] - prev['close']
        change_pct = (change / prev['close']) * 100
        
        m1, m2, m3 = st.columns(3)
        m1.metric("현재가", f"₩{latest['close']:,.0f}", f"{change:+,.0f} ({change_pct:+.2f}%)")
        m2.metric("RSI", f"{latest.get('rsi', 0):.1f}" if pd.notna(latest.get('rsi')) else "N/A")
        m3.metric("거래량", f"{latest['volume']:,.0f}")
        
        # 간소화된 차트
        fig = create_candlestick_chart(df, name)
        st.plotly_chart(fig, width='stretch', config={'scrollZoom': False})


def display_multi_stock_comparison_mini(panel_id: str):
    """분할 모드용 간소화된 다중 종목 비교"""
    stock_options = st.session_state.get('krx_stock_names', ["삼성전자 (005930)"])
    
    selected_stocks = st.multiselect(
        "종목 선택 (최대 5개)",
        stock_options,
        default=["삼성전자 (005930)"] if "삼성전자 (005930)" in stock_options else [],
        max_selections=5,
        key=f"multi_stocks_{panel_id}"
    )
    
    period = st.selectbox("기간", ["1mo", "3mo", "6mo", "1y"], index=2,
                         format_func=lambda x: {"1mo": "1개월", "3mo": "3개월", "6mo": "6개월", "1y": "1년"}.get(x),
                         key=f"multi_period_{panel_id}")
    
    if st.button("📥 비교 데이터 로드", key=f"multi_fetch_{panel_id}", type="primary"):
        if selected_stocks:
            data_dict = {}
            for stock in selected_stocks:
                ticker = st.session_state.get('krx_stock_list', {}).get(stock, "005930") + ".KS"
                name = stock.split(" (")[0]
                try:
                    df = get_cached_stock_data(ticker, period)
                    if not df.empty:
                        data_dict[name] = df
                except:
                    pass
            st.session_state[f'multi_data_{panel_id}'] = data_dict
            st.success(f"✅ {len(data_dict)}개 종목 로드 완료!")
    
    if f'multi_data_{panel_id}' in st.session_state:
        data_dict = st.session_state[f'multi_data_{panel_id}']
        if data_dict:
            # 수익률 비교 차트
            fig = go.Figure()
            for name, df in data_dict.items():
                if not df.empty:
                    returns = (df['close'] / df['close'].iloc[0] - 1) * 100
                    fig.add_trace(go.Scatter(x=df['date'], y=returns, name=name, mode='lines'))
            fig.update_layout(
                title="수익률 비교 (%)",
                template='plotly_dark',
                height=400,
                dragmode=False
            )
            fig.update_xaxes(tickformat="%Y년 %m월")
            st.plotly_chart(fig, width='stretch', config={'scrollZoom': False})


def display_news_sentiment_mini(panel_id: str):
    """분할 모드용 간소화된 뉴스 감성 분석"""
    current_market = st.session_state.get('current_market', 'KR')
    stock_options = st.session_state.get('active_stock_names', ["삼성전자 (005930)"])
    selected = st.selectbox("종목 선택", stock_options, key=f"news_stock_{panel_id}")
    
    # 종목 코드 추출 (시장별)
    stock_list = st.session_state.get('active_stock_list', {})
    if current_market == 'US':
        ticker = stock_list.get(selected, "AAPL")
    else:
        ticker = stock_list.get(selected, "005930")
    keyword = selected.split(" (")[0] if "(" in selected else selected
    
    if st.button("📰 뉴스 수집", key=f"news_fetch_{panel_id}", type="primary"):
        with st.spinner("뉴스 수집 중..."):
            try:
                from src.collectors.news_collector import NewsCollector
                collector = NewsCollector()
                
                if current_market == 'US':
                    # 미국: Yahoo Finance + Google EN
                    news_list = collector.fetch_yahoo_finance_news_rss(ticker, max_items=10)
                else:
                    # 한국: 네이버 금융
                    news_list = collector.fetch_naver_finance_news(ticker, max_pages=2)
                
                # DataFrame으로 변환
                import pandas as pd
                news_df = pd.DataFrame(news_list) if news_list else pd.DataFrame()
                st.session_state[f'news_data_{panel_id}'] = news_df
                st.success(f"✅ {len(news_df)}개 뉴스 수집!")
            except Exception as e:
                st.error(f"오류: {e}")
    
    if f'news_data_{panel_id}' in st.session_state:
        news_df = st.session_state[f'news_data_{panel_id}']
        if not news_df.empty:
            for _, row in news_df.head(5).iterrows():
                st.markdown(f"**{row.get('title', 'N/A')}**")
                st.caption(f"📅 {row.get('date', 'N/A')}")


def display_ai_prediction_mini(panel_id: str):
    """분할 모드용 AI 예측 (전체 화면과 동일)"""
    import os
    
    current_market = st.session_state.get('current_market', 'KR')
    stock_options = st.session_state.get('active_stock_names', ["삼성전자 (005930)"])
    selected = st.selectbox("종목 선택", stock_options, key=f"ai_stock_{panel_id}")
    
    stock_list = st.session_state.get('active_stock_list', {})
    if current_market == 'US':
        ticker_code = stock_list.get(selected, "AAPL")
    else:
        ticker_code = stock_list.get(selected, "005930") + ".KS"
    ticker_name = selected.split(" (")[0] if "(" in selected else selected
    
    col1, col2 = st.columns(2)
    with col1:
        strategy = st.selectbox(
            "앙상블 전략",
            ["weighted_average", "voting", "stacking"],
            format_func=lambda x: {
                "weighted_average": "가중평균",
                "voting": "투표",
                "stacking": "스태킹"
            }[x],
            key=f"ai_strategy_{panel_id}",
            help="가중평균: 비중 합산 / 투표: 다수결 / 스태킹: AI 재학습"
        )
    with col2:
        period = st.selectbox(
            "학습 기간", 
            ["1y", "2y", "5y", "10y", "max"], 
            index=2, 
            key=f"ai_period_{panel_id}",
            help="데이터가 많을수록 정확도 향상"
        )
    
    # 저장된 모델 검색
    saved_models_dir = PROJECT_ROOT / "src" / "models" / "saved_models"
    use_saved_model = False
    
    if saved_models_dir.exists():
        safe_ticker = ticker_code.replace(":", "").replace("/", "")
        try:
            files = os.listdir(saved_models_dir)
            candidates = set()
            for f in files:
                if f.startswith(safe_ticker) and any(x in f for x in ["_lstm", "_xgboost", "_transformer"]):
                    parts = f.split('_')
                    if len(parts) >= 2:
                        candidates.add(f"{parts[0]}_{parts[1]}")
            
            sorted_candidates = sorted(list(candidates), key=lambda x: x.split('_')[1], reverse=True)
            
            if sorted_candidates:
                latest_date = sorted_candidates[0].split('_')[1]
                formatted_date = f"{latest_date[:4]}-{latest_date[4:6]}-{latest_date[6:]}"
                st.info(f"📅 저장된 모델: {formatted_date}")
                use_saved_model = st.checkbox(
                    "💾 저장된 모델 사용", 
                    value=True,
                    key=f"ai_use_saved_{panel_id}",
                    help="재학습 없이 예측만 수행"
                )
        except:
            pass
    
    # Transformer 및 저장 옵션
    # Transformer 및 저장 옵션
    col_opt1, col_opt2, col_opt3 = st.columns(3)
    with col_opt1:
        use_transformer = st.checkbox(
            "🤖 Transformer", 
            value=False, 
            disabled=use_saved_model,
            key=f"ai_transformer_{panel_id}",
            help="딥러닝 Transformer 모델 포함"
        )
    with col_opt2:
        use_regime = st.checkbox(
            "🌍 Regime", 
            value=True,
            disabled=use_saved_model,
            key=f"ai_regime_{panel_id}",
            help="시장 국면(Regime)에 따른 가중치 조절"
        )
    with col_opt3:
        save_model = st.checkbox(
            "💾 저장", 
            value=True, 
            disabled=use_saved_model,
            key=f"ai_save_{panel_id}",
            help="학습된 모델을 저장"
        )
    
    if st.button("🚀 예측 실행", key=f"ai_run_{panel_id}", type="primary"):
        with st.status("🚀 AI 예측 수행 중...", expanded=True) as status:
            status.write("🔄 데이터 분석 및 모델 로딩...")
            try:
                from src.models.ensemble_predictor import EnsemblePredictor
                
                # 데이터 수집
                df = get_cached_stock_data(ticker_code, period)
                if df.empty:
                    st.error("데이터를 가져올 수 없습니다")
                    return
                
                # 기술적 지표 추가
                analyzer = TechnicalAnalyzer(df)
                analyzer.add_all_indicators()
                df = analyzer.get_dataframe()
                
                # 앙상블 예측 (1차)
                predictor = EnsemblePredictor(include_transformer=use_transformer)
                result = predictor.train_and_predict(df, strategy=strategy)
                
                if use_regime:
                    from src.models.regime_predictor import RegimeAwarePredictor
                    regime_predictor = RegimeAwarePredictor(ensemble_predictor=predictor)
                    regime_result = regime_predictor.predict(df, use_regime_weights=True)
                    
                    # 결과 갱신
                    last_close = df['close'].iloc[-1]
                    pred_close = regime_result['prediction']
                    result['direction'] = "상승" if pred_close and pred_close > last_close else "하락"
                    result['confidence'] = regime_result['confidence']
                    result['regime'] = regime_result['regime'].description
                else:
                    result['regime'] = "N/A"
                
                # 모델 저장
                if save_model and not use_saved_model:
                    try:
                        safe_ticker = ticker_code.replace(":", "").replace("/", "").replace(".KS", "")
                        predictor.save_models(safe_ticker)
                    except:
                        pass
                
                st.session_state[f'ai_result_{panel_id}'] = result
                status.update(label="✅ 예측 완료!", state="complete", expanded=False)
                st.success("✅ 예측 완료!")
            except Exception as e:
                st.error(f"오류: {e}")
    
    if f'ai_result_{panel_id}' in st.session_state:
        result = st.session_state[f'ai_result_{panel_id}']
        if result:
            direction = result.get('direction', 'N/A')
            confidence = result.get('confidence', 0) * 100
            color = "🟢" if direction == "상승" else "🔴" if direction == "하락" else "⚪"
            st.markdown(f"### {color} 예측: **{direction}** (신뢰도: {confidence:.1f}%)")
            if 'regime' in result and result.get('regime') != "N/A":
                 st.caption(f"🌍 시장 국면: {result['regime']}")


def display_backtest_mini(panel_id: str):
    """분할 모드용 백테스팅"""
    stock_options = st.session_state.get('krx_stock_names', ["삼성전자 (005930)"])
    selected = st.selectbox("종목 선택", stock_options, key=f"bt_stock_{panel_id}")
    ticker_code = st.session_state.get('krx_stock_list', {}).get(selected, "005930") + ".KS"
    
    col1, col2 = st.columns(2)
    with col1:
        strategy_type = st.selectbox("전략", ["RSI", "MACD", "이동평균"], key=f"bt_strategy_{panel_id}")
    with col2:
        period = st.selectbox("기간", ["1y", "2y", "5y"], index=1, key=f"bt_period_{panel_id}")
    
    initial_capital = st.number_input("초기 자본 (원)", value=10000000, step=1000000, key=f"bt_capital_{panel_id}")
    
    if st.button("▶️ 백테스트 실행", key=f"bt_run_{panel_id}", type="primary"):
        with st.spinner("백테스트 중..."):
            try:
                df = get_cached_stock_data(ticker_code, period)
                if df.empty:
                    st.error("데이터를 가져올 수 없습니다")
                    return
                
                analyzer = TechnicalAnalyzer(df)
                analyzer.add_all_indicators()
                df = analyzer.get_dataframe().set_index('date')
                
                # 전략 선택
                if strategy_type == "RSI":
                    strategy = RSIStrategy()
                elif strategy_type == "MACD":
                    strategy = MACDStrategy()
                else:
                    strategy = MovingAverageStrategy()
                
                backtester = Backtester(df, initial_capital=initial_capital)
                results = backtester.run(strategy)
                
                metrics = PerformanceMetrics(results['equity'], initial_capital)
                trades_df = backtester.get_trades_df()
                metrics_dict = metrics.get_all_metrics(trades_df)
                
                st.session_state[f'bt_result_{panel_id}'] = {
                    'results': results,
                    'metrics': metrics_dict,
                    'dates': backtester.df.index.tolist()
                }
                st.success(f"✅ 완료 (거래: {len(trades_df)}회)")
            except Exception as e:
                st.error(f"오류: {e}")
    
    if f'bt_result_{panel_id}' in st.session_state:
        data = st.session_state[f'bt_result_{panel_id}']
        m = data['metrics']
        
        c1, c2 = st.columns(2)
        c1.metric("총 수익률", f"{m['total_return']*100:.2f}%")
        c2.metric("MDD", f"{m['max_drawdown']*100:.2f}%")


def display_portfolio_optimization_mini(panel_id: str):
    """분할 모드용 포트폴리오 최적화"""
    stock_options = st.session_state.get('krx_stock_names', ["삼성전자 (005930)"])
    
    selected_stocks = st.multiselect(
        "종목 선택 (최소 2개)",
        stock_options,
        default=["삼성전자 (005930)"] if "삼성전자 (005930)" in stock_options else [],
        max_selections=5,
        key=f"port_stocks_{panel_id}"
    )
    
    period = st.selectbox("분석 기간", ["1y", "2y", "5y"], index=1, key=f"port_period_{panel_id}")
    
    if len(selected_stocks) < 2:
        st.warning("최소 2개 종목을 선택해주세요.")
        return
    
    if st.button("🎯 최적화 실행", key=f"port_run_{panel_id}", type="primary"):
        with st.spinner("최적화 중..."):
            try:
                tickers = [st.session_state.get('krx_stock_list', {}).get(s, "005930") + ".KS" for s in selected_stocks]
                results = get_cached_multi_stock_data(tickers, period)
                
                if len(results) < 2:
                    st.error("최소 2개 종목의 데이터가 필요합니다.")
                    return
                
                returns_data = {}
                for ticker, df in results.items():
                    if not df.empty:
                        returns_data[ticker] = df.set_index('date')['close'].pct_change()
                
                returns_df = pd.DataFrame(returns_data).dropna()
                
                optimizer = PortfolioOptimizer(returns_df, risk_free_rate=0.035)
                max_sharpe = optimizer.optimize_max_sharpe()
                
                st.session_state[f'port_result_{panel_id}'] = max_sharpe
                st.success("✅ 최적화 완료!")
            except Exception as e:
                st.error(f"오류: {e}")
    
    if f'port_result_{panel_id}' in st.session_state:
        result = st.session_state[f'port_result_{panel_id}']
        if result.get('success'):
            st.metric("기대 수익률", f"{result['return']*100:.2f}%")
            st.metric("샤프 비율", f"{result['sharpe']:.2f}")


def display_risk_management_mini(panel_id: str):
    """분할 모드용 리스크 관리"""
    stock_options = st.session_state.get('krx_stock_names', ["삼성전자 (005930)"])
    selected = st.selectbox("종목 선택", stock_options, key=f"risk_stock_{panel_id}")
    ticker_code = st.session_state.get('krx_stock_list', {}).get(selected, "005930") + ".KS"
    
    col1, col2 = st.columns(2)
    with col1:
        portfolio_value = st.number_input("포트폴리오 가치 (원)", value=100000000, step=10000000, key=f"risk_value_{panel_id}")
    with col2:
        confidence = st.slider("신뢰수준 (%)", 90, 99, 95, key=f"risk_conf_{panel_id}") / 100
    
    if st.button("📊 리스크 분석", key=f"risk_run_{panel_id}", type="primary"):
        with st.spinner("분석 중..."):
            try:
                df = get_cached_stock_data(ticker_code, "2y")
                if df.empty:
                    st.error("데이터를 가져올 수 없습니다")
                    return
                
                returns = df['close'].pct_change().dropna()
                rm = RiskManager(returns, portfolio_value)
                summary = rm.get_risk_summary(confidence, horizon=10)
                
                st.session_state[f'risk_result_{panel_id}'] = summary
                st.success("✅ 분석 완료!")
            except Exception as e:
                st.error(f"오류: {e}")
    
    if f'risk_result_{panel_id}' in st.session_state:
        summary = st.session_state[f'risk_result_{panel_id}']
        st.markdown("### 📉 VaR")
        st.metric("Historical VaR", f"₩{summary['historical_var']['var_amount']:,.0f}")
        st.metric("CVaR", f"₩{summary['cvar']['cvar_amount']:,.0f}")


def main():
    """메인 대시보드"""
    setup_page()

    st.title("📈 스마트 투자 분석 플랫폼")
    st.markdown("실시간 시세 · AI 예측 · 백테스팅 · 포트폴리오 최적화 · 리스크 관리 통합 플랫폼")

    # 사이드바 - 사용자 식별 + 시장 선택
    with st.sidebar:
        # 사용자 이메일 입력 (프로필 저장용)
        st.markdown("### 👤 사용자 식별")
        email_input = st.text_input(
            "이메일",
            value=st.session_state.get('user_email', ''),
            placeholder="example@email.com",
            help="프로필 저장 및 불러오기에 사용됩니다",
            key="email_input_field"
        )
        
        if email_input and '@' in email_input:
            st.session_state.user_id = email_input.lower().strip()
            st.session_state.user_email = email_input
            st.success(f"✅ {email_input}")
        elif email_input:
            st.warning("올바른 이메일 형식을 입력해주세요")
    # 사이드바 - 탭별 설정 최상단 + 사용자 식별 + 시장 선택 (Phase 1: 사용성 개선)
    with st.sidebar:
        # ==========================================
        # Phase 1: 탭별 설정 - 최상단 배치 (사용 빈도 최고)
        # ==========================================
        # NOTE: main_tab_selector 위젯 key를 먼저 확인 (실제 사용자 선택값)
        # active_tab_name보다 우선순위가 높음 (위젯 상태가 먼저 업데이트됨)
        current_selected_tab = st.session_state.get('main_tab_selector', 
                                st.session_state.get('active_tab_name', '📊 단일 종목 분석'))
        current_market = st.session_state.get('current_market', 'KR')
        
        if current_selected_tab == "🔴 실시간 시세" and current_market == "KR":
            # 실시간 시세 사이드바 (한국 모드만)
            st.header("⚙️ 실시간 설정")
            st.success("🇰🇷 한국 시장")
            
            stock_options = st.session_state.get('active_stock_names', ["삼성전자 (005930)"])
            default_idx = stock_options.index("삼성전자 (005930)") if "삼성전자 (005930)" in stock_options else 0
            
            selected_stock = st.selectbox("종목 검색", options=stock_options, index=default_idx, key="realtime_stock_select")
            ticker = st.session_state.get('active_stock_list', {}).get(selected_stock, "005930")
            st.session_state.realtime_ticker = ticker
            st.caption(f"종목코드: {ticker}")
            
            refresh_rate = st.slider("갱신 주기 (초)", 1, 10, 2, key="realtime_refresh_rate_slider")
            st.session_state.realtime_refresh_rate = refresh_rate
            
            st.markdown("---")
            if st.session_state.get('realtime_running', False):
                st.success("🟢 실시간 조회 중...")
                if st.button("⏹️ 중지", type="primary", key="realtime_stop_btn"):
                    st.session_state.realtime_stop_clicked = True
            else:
                st.warning("🔴 조회 중지됨")
                if st.button("▶️ 실시간 조회 시작", type="primary", key="realtime_start_btn"):
                    st.session_state.realtime_start_clicked = True
            # divider 제거 - 불필요한 공간 절약
                    
        elif current_selected_tab == "📊 단일 종목 분석":
            # 단일 종목 분석 사이드바
            st.header("⚙️ 설정")
            market_label = "🇰🇷 한국" if current_market == "KR" else "🇺🇸 미국"
            st.info(f"시장: {market_label}")
            
            stock_options = st.session_state.get('active_stock_names', ["삼성전자 (005930)"])
            
            if 'analysis_ticker' in st.session_state:
                analysis_ticker = st.session_state['analysis_ticker']
                matching_stock = next((s for s in stock_options if f"({analysis_ticker})" in s), None)
                default_stock = matching_stock or ("삼성전자 (005930)" if current_market == "KR" else "Apple (AAPL)")
                if matching_stock: del st.session_state['analysis_ticker']
            else:
                default_stock = "삼성전자 (005930)" if current_market == "KR" else "Apple (AAPL)"
            
            default_idx = stock_options.index(default_stock) if default_stock in stock_options else 0
            selected = st.selectbox("종목 검색", stock_options, index=default_idx, key="tab1_stock")
            
            ticker_code = st.session_state.get('active_stock_list', {}).get(selected, "005930")
            if current_market == "KR": ticker_code += ".KS"
            
            st.session_state.tab1_ticker_code = ticker_code
            st.session_state.tab1_ticker_name = selected.split(" (")[0] if "(" in selected else selected
            
            period = st.selectbox("조회 기간", ["1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "max"], index=3, format_func=lambda x: {"1mo":"1개월","3mo":"3개월","6mo":"6개월","1y":"1년","2y":"2년","5y":"5년","10y":"10년","max":"전체"}.get(x,x), key="tab1_period")
            
            if st.button("📥 데이터 수집", type="primary", key="tab1_fetch"):
                st.session_state.tab1_fetch_clicked = True
            st.caption("💡 기술적 지표는 자동으로 계산됩니다.")
            # divider 제거 - 불필요한 공간 절약
        else:
            # 기타 탭 - 간단한 시장 표시만
            market_label = "🇰🇷 한국" if current_market == "KR" else "🇺🇸 미국"
            st.info(f"현재 시장: {market_label}")
            # divider 제거 - 불필요한 공간 절약
    # ==========================================
    # Phase 2: 시장 선택 토글 버튼 (공간 50% 절약)
    # ==========================================
    with st.sidebar:
        st.markdown("### 🌍 시장 선택")
        
        # 현재 시장 상태
        current_market_state = st.session_state.get('current_market', 'KR')
        
        # 가로 2열 토글 버튼
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button(
                "🇰🇷 한국",
                use_container_width=True,
                type="primary" if current_market_state == "KR" else "secondary",
                key="market_btn_kr"
            ):
                if current_market_state != "KR":
                    st.session_state.market_changed = True
                    st.session_state.new_market = "KR"
                    st.rerun()
        
        with col2:
            if st.button(
                "🇺🇸 미국",
                use_container_width=True,
                type="primary" if current_market_state == "US" else "secondary",
                key="market_btn_us"
            ):
                if current_market_state != "US":
                    st.session_state.market_changed = True
                    st.session_state.new_market = "US"
                    st.rerun()
        
        # 선택된 시장 캡션 표시
        market_full_label = "🇰🇷 한국 (KRX)" if current_market_state == "KR" else "🇺🇸 미국 (NYSE/NASDAQ)"
        st.caption(f"선택: {market_full_label}")
        # divider 제거 - 불필요한 공간 절약
    
    # 시장 변경 처리 (Phase 2: 버튼 클릭 기반)
    if st.session_state.get('market_changed', False):
        new_market = st.session_state.new_market
        previous_market = st.session_state.get('previous_market', None)
        
        if previous_market is not None and previous_market != new_market:
            # 이전 시장의 상태 저장 (stock_data 포함)
            state_keys = ['stock_data', 'ticker_name', 'mini_data', 'mini_stock', 'ai_result', 'bt_result', 'port_result', 'risk_result']
            for base_key in state_keys:
                for panel in ['', '_left', '_right']:
                    key = f"{base_key}{panel}"
                    if key in st.session_state:
                        st.session_state[f"{previous_market}_{key}"] = st.session_state[key]
        
        # 새 시장의 이전 상태 복원
        for base_key in state_keys:
            for panel in ['', '_left', '_right']:
                key = f"{base_key}{panel}"
                saved_key = f"{new_market}_{key}"
                if saved_key in st.session_state:
                    st.session_state[key] = st.session_state[saved_key]
                elif key in st.session_state:
                    del st.session_state[key]
        
        # 시장 상태 업데이트
        if new_market == "US":
            st.session_state.current_market = "US"
            st.session_state.currency_symbol = "$"
            st.session_state.ticker_suffix = ""
            
            if 'us_stock_list' not in st.session_state:
                # 미국 종목 리스트 로직 생략 (이미 정의됨)
                pass
            st.session_state.active_stock_list = st.session_state.get('us_stock_list', {})
            st.session_state.active_stock_names = st.session_state.get('us_stock_names', [])
        else:
            st.session_state.current_market = "KR"
            st.session_state.currency_symbol = "₩"
            st.session_state.ticker_suffix = ".KS"
            st.session_state.active_stock_list = st.session_state.get('krx_stock_list', {})
            st.session_state.active_stock_names = st.session_state.get('krx_stock_names', [])
            
        st.session_state.previous_market = new_market
        st.session_state.market_changed = False
        st.rerun()

    # ==========================================
    # Phase 3: 설정 통합 - 하나의 Expander + Tabs
    # ==========================================
    with st.sidebar:
        with st.expander("⚙️ 설정", expanded=False):
            tab_user, tab_api, tab_alert = st.tabs(["👤 사용자", "🔑 API", "🔔 알림"])
            
            # Tab 1: 사용자 식별
            with tab_user:
                st.markdown("**사용자 식별**")
                user_id = st.text_input(
                    "유저 ID", 
                    value=st.session_state.get('user_id', 'user_default'),
                    key="user_id_unified"
                )
                st.session_state.user_id = user_id
                st.caption("※ 대화 기록 저장 및 맞춤 분석에 사용됩니다.")
            
            # Tab 2: AI API 설정
            with tab_api:
                st.markdown("**Gemini API 설정**")
                api_key = st.text_input(
                    "Gemini API Key", 
                    value=st.session_state.get('gemini_api_key', ""),
                    type="password",
                    key="gemini_api_key_unified"
                )
                if api_key:
                    st.session_state.gemini_api_key = api_key
                st.caption("※ AI 챗봇 및 감성 분석을 위해 필요합니다.")
            
            # Tab 3: 알림 설정
            with tab_alert:
                st.markdown("**주요 이벤트 알림**")
                alert_enabled = st.toggle("알림 활성화", value=st.session_state.get('alert_config', {}).get('enabled', False), key="alert_enabled_unified")
                
                if alert_enabled:
                    vix_val = st.slider("VIX 임계값", 15, 50, st.session_state.get('alert_config', {}).get('vix_threshold', 25), key="vix_unified")
                    mdd_val = st.slider("MDD 임계값 (%)", 5, 30, st.session_state.get('alert_config', {}).get('mdd_threshold', 10), key="mdd_unified")
                    st.session_state.alert_config = {"enabled": True, "vix_threshold": vix_val, "mdd_threshold": mdd_val}
                    
                    st.markdown("---")
                    st.markdown("**📬 수신 채널**")
                    if st.checkbox("Telegram", key="tele_enabled_unified"):
                        st.text_input("Bot Token", type="password", key="tele_token_unified")
                        st.text_input("Chat ID", key="tele_chat_unified")
                    if st.checkbox("Email", key="email_enabled_unified"):
                        st.text_input("이메일 주소", placeholder="your@email.com", key="email_addr_unified")
                        st.text_input("앱 비밀번호", type="password", key="email_pwd_unified")
                        st.caption("※ Gmail은 앱 비밀번호 필요")
                else:
                    st.session_state.alert_config = {"enabled": False}
                    st.caption("알림을 활성화하면 주요 이벤트를 알려드립니다.")

    # ==========================================
    # Phase 1: AI 챗봇 - 사이드바 하단 고정
    # ==========================================
    with st.sidebar:
        if CHATBOT_AVAILABLE:
            render_sidebar_chat()

    # 화면 분할 모드 토글
    split_mode = st.toggle("🖥️ 화면 분할 모드", value=False, help="⚠️ 실험적 기능: 두 개의 화면을 나란히 표시합니다 (와이드 모드 권장). 일부 기능이 정상 작동하지 않을 수 있습니다.")
    
    if split_mode:
        # 분할 모드: segmented_control로 탭 선택
        st.warning("⚠️ **실험적 기능**: 화면 분할 모드는 아직 개발 중인 기능입니다. 일부 기능이 정상 작동하지 않을 수 있습니다.")
        st.markdown("**💡 좌측/우측 패널에서 각각 다른 항목을 선택하세요. (단일 종목 분석은 양쪽 선택 가능)**")
        
        all_tabs = {
            "📊 단일 종목": 1,
            "🔀 다중 종목": 2,
            "📰 뉴스": 3,
            "🤖 AI 예측": 4,
            "⏮️ 백테스트": 5,
            "💼 포트폴리오": 6,
            "⚠️ 리스크": 7,
            "👤 투자 성향": 8
        }
        tab_names = list(all_tabs.keys())
        
        # 초기값 설정
        if 'split_left_tab' not in st.session_state:
            st.session_state.split_left_tab = "📊 단일 종목"
        if 'split_right_tab' not in st.session_state:
            st.session_state.split_right_tab = "📊 단일 종목"
        
        col_select_left, col_select_right = st.columns(2)
        
        with col_select_left:
            st.markdown("##### 📌 좌측 패널")
            # 우측에서 선택된 항목 제외 (단일 종목은 예외)
            left_options = [t for t in tab_names if t != st.session_state.split_right_tab or t == "📊 단일 종목"]
            left_tab = st.segmented_control(
                "좌측", left_options, 
                default=st.session_state.split_left_tab if st.session_state.split_left_tab in left_options else left_options[0],
                key="split_left_segment",
                label_visibility="collapsed"
            )
            if left_tab:
                st.session_state.split_left_tab = left_tab
        
        with col_select_right:
            st.markdown("##### 📌 우측 패널")
            # 좌측에서 선택된 항목 제외 (단일 종목은 예외)
            right_options = [t for t in tab_names if t != st.session_state.split_left_tab or t == "📊 단일 종목"]
            right_tab = st.segmented_control(
                "우측", right_options,
                default=st.session_state.split_right_tab if st.session_state.split_right_tab in right_options else right_options[0],
                key="split_right_segment",
                label_visibility="collapsed"
            )
            if right_tab:
                st.session_state.split_right_tab = right_tab
        
        st.divider()
        
        col_left, col_right = st.columns(2)
        
        def render_panel(panel_id: str, tab_name: str):
            """선택된 탭 렌더링"""
            tab_idx = all_tabs.get(tab_name, 1)
            st.markdown(f"### {tab_name} {'(A)' if panel_id == 'left' and tab_name == '📊 단일 종목' else '(B)' if panel_id == 'right' and tab_name == '📊 단일 종목' else ''}")
            if tab_idx == 1:
                display_single_stock_analysis_mini(panel_id)
            elif tab_idx == 2:
                display_multi_stock_comparison_mini(panel_id)
            elif tab_idx == 3:
                display_news_sentiment_mini(panel_id)
            elif tab_idx == 4:
                display_ai_prediction_mini(panel_id)
            elif tab_idx == 5:
                display_backtest_mini(panel_id)
            elif tab_idx == 6:
                display_portfolio_optimization_mini(panel_id)
            elif tab_idx == 7:
                display_risk_management_mini(panel_id)
            elif tab_idx == 8:
                if INVESTMENT_PROFILE_AVAILABLE:
                    render_investment_profile_tab() # Assuming mini version is not needed or handled internally
                else:
                    st.warning("투자 성향 모듈을 불러올 수 없습니다.")
            elif tab_idx == 9: # Added AI Screener rendering for split mode
                if SCREENER_AVAILABLE:
                    render_morning_picks_mini(panel_id) # Assuming a mini version for split mode
                else:
                    st.warning("AI 스크리너 모듈을 불러올 수 없습니다.")
        
        with col_left:
            render_panel("left", st.session_state.split_left_tab)
        
        with col_right:
            render_panel("right", st.session_state.split_right_tab)
        
        return  # 분할 모드에서는 여기서 종료

    # 일반 모드: 탭 선택 UI (현재 탭 추적 가능)
    current_market = st.session_state.get('current_market', 'KR')
    
    # 미국 모드에서는 실시간 시세 탭 제외
    if current_market == "US":
        tab_options = [
            "🎯 투자 컨트롤 센터",
            "📊 단일 종목 분석",
            "🔀 다중 종목 비교",
            "⭐ 관심 종목",
            "📰 뉴스 감성 분석",
            "🤖 AI 예측",
            "⏮️ 백테스팅",
            "💼 포트폴리오 최적화",
            "⚠️ 리스크 관리",
            "🏥 시장 체력 진단",
            "🔥 Market Buzz",
            "💎 팩터 투자",
            "👤 투자 성향",
            "🌅 AI 스크리너"
        ]
        default_tab = "📊 단일 종목 분석"
    else:
        tab_options = [
            "🎯 투자 컨트롤 센터",
            "🔴 실시간 시세",
            "📊 단일 종목 분석",
            "🔀 다중 종목 비교",
            "⭐ 관심 종목",
            "📰 뉴스 감성 분석",
            "🤖 AI 예측",
            "⏮️ 백테스팅",
            "💼 포트폴리오 최적화",
            "⚠️ 리스크 관리",
            "🏥 시장 체력 진단",
            "🔥 Market Buzz",
            "💎 팩터 투자",
            "👤 투자 성향",
            "🌅 AI 스크리너"
        ]
        default_tab = "📊 단일 종목 분석"
    
    # Phase E: 챗봇에서 탭 전환 요청이 있으면 해당 탭을 default로 설정
    if 'pending_tab' in st.session_state:
        pending = st.session_state.pending_tab
        if pending in tab_options:
            default_tab = pending
        del st.session_state.pending_tab
    
    selected_tab = st.segmented_control(
        "분석 메뉴",
        tab_options,
        default=default_tab,
        selection_mode="single",
        label_visibility="collapsed"
    )

    
    # Phase D: 챗봇 Context 추적을 위해 현재 탭 저장
    st.session_state.active_tab_name = selected_tab
    
    # 탭 콘텐츠 렌더링
    if selected_tab == "🔴 실시간 시세" and current_market == "KR":
        display_realtime_data()

    elif selected_tab == "📊 단일 종목 분석":
        # 사이드바 안내 메시지
        st.info("👈 **사이드바**에서 종목을 선택하고 '데이터 조회' 버튼을 클릭하세요.")
        # 단일 종목 분석 콘텐츠
        ticker_code = st.session_state.get('tab1_ticker_code', '005930.KS')
        ticker_name = st.session_state.get('tab1_ticker_name', '삼성전자')
        period = st.session_state.get('tab1_period', '1y')
        fetch_data = st.session_state.get('tab1_fetch_clicked', False)
        
        if fetch_data:
            st.session_state.tab1_fetch_clicked = False
            
        if fetch_data or 'stock_data' not in st.session_state:
            with st.spinner(f'{ticker_name} 데이터를 불러오는 중...'):
                try:
                    df = get_cached_stock_data(ticker_code, period)
                    if not df.empty:
                        analyzer = TechnicalAnalyzer(df)
                        analyzer.add_all_indicators()
                        df = analyzer.get_dataframe()
                        st.session_state['stock_data'] = df
                        st.session_state['ticker_name'] = ticker_name
                        st.success(f"✅ {len(df)}개 데이터 로드 완료!")
                    else:
                        st.error("데이터를 가져올 수 없습니다.")
                        return
                except Exception as e:
                    st.error(f"오류 발생: {str(e)}")
                    return

        if 'stock_data' in st.session_state:
            df = st.session_state['stock_data']
            ticker_name = st.session_state.get('ticker_name', ticker_name)
            display_metrics(df)
            st.divider()
            
            col_title, col_settings = st.columns([0.9, 0.1])
            with col_title:
                st.subheader(f"📊 {ticker_name} 차트")
            with col_settings:
                with st.popover("⚙️"):
                    st.markdown("**📈 이동평균선 설정**")
                    ma_options = {"MA 5": 5, "MA 10": 10, "MA 20": 20, "MA 60": 60, "MA 120": 120, "MA 200": 200}
                    selected_periods = []
                    for name, p in ma_options.items():
                        if st.checkbox(name, value=p in [5, 10, 20, 60], key=f"ma_cb_{p}"):
                            selected_periods.append(p)
                    st.session_state['selected_ma_periods'] = selected_periods
            
            fig = create_candlestick_chart(df, ticker_name)
            st.plotly_chart(fig, use_container_width=True)
            display_signals(df)
            
            # AI 분석 버튼 (Phase A)
            st.divider()
            with st.expander("🤖 AI 투자 분석", expanded=False):
                st.markdown("**Gemini AI가 종목을 분석합니다.**")
                if AI_ANALYSIS_AVAILABLE:
                    user_id = st.session_state.get('user_id', 'default_user')
                    render_ai_analysis_button(ticker_code, ticker_name, user_id)
                else:
                    st.warning("AI 분석 모듈을 불러올 수 없습니다.")
            
            # 펀더멘털 카드 (기업 가치 분석)
            st.divider()
            with st.expander("💰 펀더멘털 분석 (기업 가치)", expanded=False):
                st.markdown("**기업의 재무 상태와 가치 평가 지표입니다.**")
                
                # 초보자 힌트
                with st.popover("💡 용어 설명"):
                    st.markdown(f"**PER**: {get_hint_text('PER', 'short')}")
                    st.markdown(f"**ROE**: {get_hint_text('ROE', 'short')}")
                
                try:
                    fund_analyzer = FundamentalAnalyzer(ticker_code)
                    card_data = fund_analyzer.get_fundamental_card_data()
                    
                    # 종합 점수
                    st.metric(
                        label=f"📊 펀더멘털 점수 {card_data['grade']}",
                        value=f"{card_data['score']}/100"
                    )
                    
                    # 상세 지표
                    fcol1, fcol2, fcol3, fcol4, fcol5 = st.columns(5)
                    
                    with fcol1:
                        per_data = card_data['per']
                        per_val = per_data['value']
                        st.metric(
                            label=f"{per_data['color']} PER",
                            value=f"{per_val:.1f}" if per_val else "N/A"
                        )
                    
                    with fcol2:
                        pbr_data = card_data['pbr']
                        pbr_val = pbr_data['value']
                        st.metric(
                            label=f"{pbr_data['color']} PBR",
                            value=f"{pbr_val:.2f}" if pbr_val else "N/A"
                        )
                    
                    with fcol3:
                        roe_data = card_data['roe']
                        roe_val = roe_data['value']
                        st.metric(
                            label=f"{roe_data['color']} ROE",
                            value=f"{roe_val*100:.1f}%" if roe_val else "N/A"
                        )
                    
                    with fcol4:
                        debt_data = card_data['debt_ratio']
                        debt_val = debt_data['value']
                        st.metric(
                            label=f"{debt_data['color']} 부채비율",
                            value=f"{debt_val:.0f}%" if debt_val else "N/A"
                        )
                    
                    with fcol5:
                        div_data = card_data['dividend_yield']
                        div_val = div_data['value']
                        st.metric(
                            label=f"{div_data['color']} 배당률",
                            value=f"{div_val*100:.2f}%" if div_val else "N/A"
                        )
                    
                except Exception as e:
                    st.warning(f"펀더멘털 데이터를 가져올 수 없습니다: {str(e)}")
            
            with st.expander("📋 원본 데이터 보기"):
                st.dataframe(df[['date', 'open', 'high', 'low', 'close', 'volume', 'rsi', 'macd']].tail(30))

    elif selected_tab == "🔀 다중 종목 비교":
        st.info("👈 **사이드바**에서 비교할 종목들을 선택하세요.")
        display_multi_stock_comparison()

    elif selected_tab == "📰 뉴스 감성 분석":
        display_news_sentiment()

    elif selected_tab == "🤖 AI 예측":
        st.info("👈 **사이드바**에서 예측할 종목을 선택하세요.")
        display_ai_prediction()

    elif selected_tab == "⏮️ 백테스팅":
        display_backtest()

    elif selected_tab == "💼 포트폴리오 최적화":
        display_portfolio_optimization()

    elif selected_tab == "⚠️ 리스크 관리":
        display_risk_management()
    
    elif selected_tab == "🏥 시장 체력 진단":
        display_market_breadth()
    elif selected_tab == "🎯 투자 컨트롤 센터":
        from src.dashboard.control_center import show_control_center
        show_control_center()
    elif selected_tab == "⭐ 관심 종목":
        from src.dashboard.views.watchlist_view import render_watchlist_tab
        render_watchlist_tab()
    elif selected_tab == "🔥 Market Buzz":
        from src.dashboard.views.market_buzz_view import render_market_buzz_tab
        render_market_buzz_tab()
    elif selected_tab == "💎 팩터 투자":
        display_factor_investing()
    elif selected_tab == "👤 투자 성향":
        if INVESTMENT_PROFILE_AVAILABLE:
            from src.dashboard.views import render_investment_profile_tab, render_ranking_tab
            st.subheader("👤 투자 성향 분석")
            profile_tab, ranking_tab = st.tabs(["📊 성향 진단", "🏆 맞춤 종목 순위"])
            with profile_tab:
                render_investment_profile_tab()
            with ranking_tab:
                render_ranking_tab()
        else:
            st.error("투자 성향 모듈을 로드할 수 없습니다.")
    
    elif selected_tab == "🌅 AI 스크리너":
        if SCREENER_AVAILABLE:
            render_morning_picks()
        else:
            st.warning("AI 스크리너 모듈을 불러올 수 없습니다.")


def display_portfolio_optimization():
    """포트폴리오 최적화 뷰"""
    st.subheader("💼 포트폴리오 최적화")
    st.markdown("Markowitz 평균-분산 최적화를 통한 최적 포트폴리오 비중 계산")

    # 현재 시장
    current_market = st.session_state.get('current_market', 'KR')
    
    # 전체 종목 검색
    stock_options = st.session_state.get('active_stock_names', ["삼성전자 (005930)"])
    selected_stocks = st.multiselect(
        "포트폴리오에 포함할 종목 선택 (검색 가능, 최소 2개)",
        stock_options,
        default=stock_options[:4] if len(stock_options) >= 4 else stock_options[:2],
        key="portfolio_stocks"
    )

    col1, col2 = st.columns(2)
    with col1:
        period = st.selectbox("분석 기간", ["6mo", "1y", "2y", "5y", "10y"], index=3, key="port_period")
    with col2:
        risk_free = st.number_input("무위험 수익률 (%)", value=3.5, min_value=0.0, max_value=10.0, step=0.1)

    if len(selected_stocks) < 2:
        st.warning("최소 2개 종목을 선택해주세요.")
        return

    if st.button("🎯 최적 포트폴리오 계산", type="primary"):
        with st.spinner("데이터 수집 및 최적화 중..."):
            try:
                # 시장에 따른 ticker 생성
                tickers = []
                active_stock_list = st.session_state.get('active_stock_list', {})
                for name in selected_stocks:
                    if current_market == "US":
                        ticker = active_stock_list.get(name, "AAPL")
                    else:
                        ticker = active_stock_list.get(name, "005930") + ".KS"
                    tickers.append(ticker)
                
                results = get_cached_multi_stock_data(tickers, period)

                if len(results) < 2:
                    st.error("최소 2개 종목의 데이터가 필요합니다.")
                    return

                # 수익률 계산 - ticker_to_name 매핑
                ticker_to_name = {}
                for full_name in selected_stocks:
                    if current_market == "US":
                        ticker = active_stock_list.get(full_name, "AAPL")
                    else:
                        ticker = active_stock_list.get(full_name, "005930") + ".KS"
                    ticker_to_name[ticker] = full_name.split(" (")[0]
                
                returns_data = {}
                for ticker, df in results.items():
                    if not df.empty:
                        name = ticker_to_name.get(ticker, ticker)
                        returns_data[name] = df.set_index('date')['close'].pct_change()

                returns_df = pd.DataFrame(returns_data).dropna()

                if len(returns_df) < 30:
                    st.error("분석에 필요한 데이터가 부족합니다.")
                    return

                # 포트폴리오 최적화
                optimizer = PortfolioOptimizer(returns_df, risk_free_rate=risk_free/100)

                # 최대 샤프 비율 포트폴리오
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

                # 최적 비중 표시
                st.markdown("### 💰 최적 비중 (최대 샤프 기준)")
                if max_sharpe['success']:
                    currency = MARKET_CONFIG[current_market]['currency_symbol']
                    base_amount = 100_000_000 if current_market == 'KR' else 100_000  # 1억원 or 10만불
                    amount_label = "금액 (1억원 기준)" if current_market == 'KR' else "금액 ($100K 기준)"
                    
                    weights_df = pd.DataFrame({
                        '종목': list(max_sharpe['weights'].keys()),
                        '비중': [f"{w*100:.1f}%" for w in max_sharpe['weights'].values()],
                        amount_label: [f"{currency}{w*base_amount:,.0f}" for w in max_sharpe['weights'].values()]
                    })
                    st.dataframe(weights_df, width='stretch', hide_index=True)
                    
                    # 미국 시장일 경우 환율 정보 추가
                    if current_market == 'US':
                        try:
                            exchange_rate = get_cached_exchange_rate()
                            st.info(f"💱 현재 환율: 1 USD = ₩{exchange_rate:,.2f} | 원화 환산 시 약 ₩{100_000 * exchange_rate:,.0f} 기준")
                        except Exception:
                            pass

                    # 파이 차트
                    fig = px.pie(
                        values=list(max_sharpe['weights'].values()),
                        names=list(max_sharpe['weights'].keys()),
                        title="최적 포트폴리오 구성"
                    )
                    fig.update_layout(template='plotly_dark', height=400, dragmode=False)
                    st.plotly_chart(fig, width='stretch', config={'scrollZoom': False})


                # 효율적 투자선
                col_title1, col_help1 = st.columns([10, 1])
                with col_title1:
                    st.markdown("### 📊 효율적 투자선")
                with col_help1:
                    with st.popover("ℹ️"):
                        st.markdown("""
                        **효율적 투자선 (Efficient Frontier) 해석:**
                        
                        - **각 점** = 가능한 포트폴리오 조합
                        - **⭐ 빨간 별** = 최대 샤프 비율
                        - **◆ 초록 다이아** = 최소 변동성
                        - **왼쪽 위로 갈수록** 좋음
                        - 색상이 밝을수록 샤프 비율이 높음
                        """)
                random_portfolios = optimizer.generate_random_portfolios(3000)

                fig = go.Figure()

                # 랜덤 포트폴리오
                fig.add_trace(go.Scatter(
                    x=random_portfolios['volatility'] * 100,
                    y=random_portfolios['return'] * 100,
                    mode='markers',
                    marker=dict(
                        size=4,
                        color=random_portfolios['sharpe'],
                        colorscale='Viridis',
                        showscale=True,
                        colorbar=dict(title='샤프 비율')
                    ),
                    name='가능한 포트폴리오'
                ))

                # 최대 샤프
                if max_sharpe['success']:
                    fig.add_trace(go.Scatter(
                        x=[max_sharpe['volatility'] * 100],
                        y=[max_sharpe['return'] * 100],
                        mode='markers',
                        marker=dict(size=15, color='red', symbol='star'),
                        name='최대 샤프 비율'
                    ))

                # 최소 변동성
                if min_vol['success']:
                    fig.add_trace(go.Scatter(
                        x=[min_vol['volatility'] * 100],
                        y=[min_vol['return'] * 100],
                        mode='markers',
                        marker=dict(size=15, color='green', symbol='diamond'),
                        name='최소 변동성'
                    ))

                fig.update_layout(
                    title="효율적 투자선 (Efficient Frontier)",
                    xaxis_title="변동성 (%)",
                    yaxis_title="기대 수익률 (%)",
                    template='plotly_dark',
                    height=500,
                    legend=dict(
                        orientation="h",
                        yanchor="bottom",
                        y=1.02,
                        xanchor="left",
                        x=0
                    )
                )
                st.plotly_chart(fig, width='stretch', config={'scrollZoom': False})

                # 상관관계 매트릭스
                col_title2, col_help2 = st.columns([10, 1])
                with col_title2:
                    st.markdown("### 🔗 종목 간 상관관계")
                with col_help2:
                    with st.popover("ℹ️"):
                        st.markdown("""
                        **상관계수 해석:**
                        
                        - **+1.0 (빨강)** = 같은 방향으로 움직임
                        - **0.0 (흰색)** = 무관하게 움직임
                        - **-1.0 (파랑)** = 반대로 움직임
                        
                        상관관계가 낮을수록 분산 효과 ↑
                        """)
                corr_matrix = optimizer.get_correlation_matrix()
                fig_corr = px.imshow(
                    corr_matrix,
                    text_auto='.2f',
                    color_continuous_scale='RdBu',
                    title="상관계수 행렬"
                )
                fig_corr.update_layout(template='plotly_dark', height=400, dragmode=False)
                st.plotly_chart(fig_corr, width='stretch', config={'scrollZoom': False})

            except Exception as e:
                st.error(f"오류 발생: {str(e)}")
                import traceback
                st.code(traceback.format_exc())


def display_risk_management():
    """리스크 관리 뷰"""
    st.subheader("⚠️ 리스크 관리")
    st.markdown("VaR, CVaR, 스트레스 테스팅을 통한 위험 분석")

    # 현재 시장
    current_market = st.session_state.get('current_market', 'KR')
    currency = st.session_state.get('currency_symbol', '₩')
    
    # 전체 종목 검색
    stock_options = st.session_state.get('active_stock_names', ["삼성전자 (005930)"])
    default_stock = "삼성전자 (005930)" if current_market == "KR" else "Apple (AAPL)"
    default_idx = stock_options.index(default_stock) if default_stock in stock_options else 0
    selected = st.selectbox("종목 검색", stock_options, index=default_idx, key="risk_ticker")
    
    # 시장에 따른 ticker 코드 생성
    if current_market == "US":
        ticker_code = st.session_state.get('active_stock_list', {}).get(selected, "AAPL")
    else:
        ticker_code = st.session_state.get('active_stock_list', {}).get(selected, "005930") + ".KS"
    ticker_name = selected.split(" (")[0] if "(" in selected else selected

    col1, col2, col3 = st.columns(3)
    with col1:
        portfolio_value = st.number_input(
            "포트폴리오 가치 (원)",
            min_value=1_000_000,
            max_value=1_000_000_000,
            value=100_000_000,
            step=10_000_000
        )
    with col2:
        confidence = st.slider("신뢰수준 (%)", 90, 99, 95) / 100
    with col3:
        horizon = st.selectbox("분석 기간 (일)", [1, 5, 10, 20], index=2)

    if st.button("📊 리스크 분석 실행", type="primary"):
        with st.spinner("리스크 분석 중..."):
            try:
                # 데이터 수집 (캐싱 적용, 2년 고정)
                df = get_cached_stock_data(ticker_code, "2y")

                if df.empty:
                    st.error("데이터를 가져올 수 없습니다")
                    return

                # 수익률 계산
                returns = df['close'].pct_change().dropna()

                # 리스크 분석
                rm = RiskManager(returns, portfolio_value)
                summary = rm.get_risk_summary(confidence, horizon)

                st.success("✅ 리스크 분석 완료!")

                # VaR 결과
                st.markdown("### 📉 VaR (Value at Risk)")
                col1, col2, col3 = st.columns(3)

                with col1:
                    st.markdown("**Historical VaR**")
                    st.metric("최대 예상 손실", f"₩{summary['historical_var']['var_amount']:,.0f}")

                with col2:
                    st.markdown("**Parametric VaR**")
                    st.metric("최대 예상 손실", f"₩{summary['parametric_var']['var_amount']:,.0f}")

                with col3:
                    st.markdown("**Monte Carlo VaR**")
                    st.metric("최대 예상 손실", f"₩{summary['monte_carlo_var']['var_amount']:,.0f}")

                # CVaR
                st.markdown("### 🔻 CVaR (Expected Shortfall)")
                st.info(f"최악의 {(1-confidence)*100:.0f}% 시나리오에서 **평균 ₩{summary['cvar']['cvar_amount']:,.0f}** 손실 예상")

                # VaR 시각화
                st.markdown("### 📊 수익률 분포 및 VaR")
                fig = go.Figure()

                # 히스토그램
                fig.add_trace(go.Histogram(
                    x=returns * 100,
                    nbinsx=50,
                    name='일별 수익률 분포',
                    marker_color='rgba(0, 150, 255, 0.6)'
                ))

                # VaR 선
                var_return = summary['historical_var']['var_return'] * 100 / np.sqrt(horizon)
                fig.add_vline(
                    x=var_return,
                    line_dash="dash",
                    line_color="red",
                    annotation_text=f"VaR ({confidence*100:.0f}%)"
                )

                fig.update_layout(
                    title="일별 수익률 분포",
                    xaxis_title="수익률 (%)",
                    yaxis_title="빈도",
                    template='plotly_dark',
                    height=400
                )
                st.plotly_chart(fig, width='stretch', config={'scrollZoom': False})

                # 통계
                st.markdown("### 📈 수익률 통계")
                stats = summary['statistics']
                stats_df = pd.DataFrame({
                    '지표': ['일평균 수익률', '일별 변동성', '왜도', '첨도', '최소 수익률', '최대 수익률'],
                    '값': [
                        f"{stats['mean_daily_return']*100:.3f}%",
                        f"{stats['std_daily_return']*100:.3f}%",
                        f"{stats['skewness']:.2f}",
                        f"{stats['kurtosis']:.2f}",
                        f"{stats['min_return']*100:.2f}%",
                        f"{stats['max_return']*100:.2f}%"
                    ],
                    '설명': [
                        '하루 평균 수익률',
                        '수익률의 표준편차',
                        '분포의 비대칭성 (0이면 대칭)',
                        '분포의 뾰족함 (3 초과면 두꺼운 꼬리)',
                        '관측된 최저 수익률',
                        '관측된 최고 수익률'
                    ]
                })
                st.dataframe(stats_df, width='stretch', hide_index=True)

                # 스트레스 테스트
                st.markdown("### 💥 스트레스 테스트")
                stress_results = rm.stress_test()
                st.dataframe(stress_results, width='stretch', hide_index=True)

            except Exception as e:
                st.error(f"오류 발생: {str(e)}")
                import traceback
                st.code(traceback.format_exc())


def display_market_breadth():
    """시장 체력 진단 뷰"""
    st.subheader("🏥 시장 체력 진단")
    st.markdown("시장 전체가 건강한지, 소수 종목만 오르는지 분석합니다.")
    
    # 초보자 힌트
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
                
                # 변동성 분석 (VIX)
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
                
                # 상승/하락 비율
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
                
                # 신고가/신저가
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
                
                # 집중도
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


def display_social_trend():
    """
    [DEPRECATED] 소셜 트렌드 분석 뷰 (Google Trends 기반)
    
    ⚠️ DEPRECATED: Phase 21에서 Market Buzz로 대체됨
    이 함수는 더 이상 사용되지 않으며, 향후 버전에서 제거될 예정입니다.
    새로운 기능: src.dashboard.views.market_buzz_view.render_market_buzz_tab()
    """
    st.warning("⚠️ 이 기능은 더 이상 사용되지 않습니다. '🔥 Market Buzz' 탭을 이용해주세요.")
    st.subheader("📈 소셜 트렌드 분석")
    st.markdown("Google Trends를 활용하여 종목의 검색 관심도와 밈주식 가능성을 분석합니다.")
    
    # 초보자 힌트
    with st.expander("💡 소셜 트렌드 분석이란?", expanded=False):
        st.markdown("""
        **소셜 트렌드 분석**은 특정 종목이 얼마나 많은 관심을 받고 있는지 측정합니다.
        
        - **Google Trends**: 검색량 변화를 추적
        - **밈주식 감지**: 갑작스러운 관심 폭발 감지
        - **투자 타이밍**: 관심도 급등 시 주의 필요 (이미 늦었을 수 있음)
        
        ⚠️ **주의**: 관심도 급등 ≠ 매수 신호. 오히려 과열 신호일 수 있습니다.
        """)
    
    # 종목 선택
    stock_options = st.session_state.get('active_stock_names', ["삼성전자 (005930)"])
    selected_stock = st.selectbox(
        "분석할 종목 선택",
        options=stock_options[:50],  # 상위 50개만
        key="social_trend_stock"
    )
    
    # 종목 코드 추출
    stock_dict = st.session_state.get('active_stock_list', {})
    ticker = stock_dict.get(selected_stock, "005930")
    
    # 분석 기간
    period_options = {"1개월": "today 1-m", "3개월": "today 3-m", "12개월": "today 12-m"}
    period = st.selectbox("분석 기간", list(period_options.keys()), index=1)
    
    if st.button("🔍 트렌드 분석 시작", type="primary"):
        with st.spinner("Google Trends 데이터 수집 중..."):
            try:
                from src.services.social_trend_service import GoogleTrendsAnalyzer, SocialTrendAnalyzer
                
                # 종목명 추출 (괄호 앞)
                stock_name = selected_stock.split(" (")[0] if " (" in selected_stock else selected_stock
                
                # Google Trends 분석
                trends = GoogleTrendsAnalyzer()
                timeframe = period_options[period]
                
                # 시장별 지역 설정
                current_market = st.session_state.get('current_market', 'KR')
                geo = "KR" if current_market == "KR" else "US"
                
                # 1차 검색: 종목명
                trend_data = trends.get_interest_over_time(
                    stock_name, 
                    timeframe=timeframe,
                    geo=geo
                )
                
                # 실패 시 2차 검색: 티커
                if trend_data.empty:
                    ticker_clean = ticker.split('.')[0]  # .KS, .T 제거
                    st.warning(f"'{stock_name}' 검색 결과가 없어 '{ticker_clean}'(으)로 재시도합니다.")
                    trend_data = trends.get_interest_over_time(
                        ticker_clean, 
                        timeframe=timeframe, 
                        geo=geo
                    )
                    stock_name = ticker_clean  # 차트 라벨 변경
                
                if trend_data is not None and not trend_data.empty:
                    # 관심도 차트
                    st.markdown("### 📊 검색 관심도 추이")
                    
                    import plotly.express as px
                    fig = px.line(
                        trend_data, 
                        x=trend_data.index, 
                        y=stock_name,
                        title=f"'{stock_name}' Google 검색 관심도"
                    )
                    fig.update_layout(
                        template='plotly_dark',
                        xaxis_title="날짜",
                        yaxis_title="관심도 (0-100)"
                    )
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # 통계
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        current = trend_data[stock_name].iloc[-1]
                        avg = trend_data[stock_name].mean()
                        st.metric(
                            label="현재 관심도",
                            value=f"{current:.0f}",
                            delta=f"{current - avg:.1f} (평균 대비)"
                        )
                    
                    with col2:
                        max_interest = trend_data[stock_name].max()
                        st.metric(
                            label="최고 관심도",
                            value=f"{max_interest:.0f}"
                        )
                    
                    with col3:
                        # 밈주식 경고
                        recent_spike = current > avg * 2
                        if recent_spike:
                            st.metric(
                                label="🚨 밈주식 경고",
                                value="주의!"
                            )
                            st.warning("관심도가 평균의 2배 이상입니다. 과열 가능성!")
                        else:
                            st.metric(
                                label="상태",
                                value="정상"
                            )
                    
                    # 소셜 트렌드 분석
                    st.markdown("---")
                    st.markdown("### 🎯 투자 타이밍 분석")
                    
                    social = SocialTrendAnalyzer()
                    analysis = social.analyze_stock_buzz(ticker)
                    
                    if analysis:
                        col1, col2 = st.columns(2)
                        with col1:
                            st.metric("종합 점수", f"{analysis.get('buzz_score', 'N/A')}/100")
                        with col2:
                            sentiment = analysis.get('sentiment', 'neutral')
                            sentiment_emoji = "🟢" if sentiment == "positive" else "🔴" if sentiment == "negative" else "🟡"
                            st.metric("감성", f"{sentiment_emoji} {sentiment}")
                        
                        # 추천
                        if analysis.get('is_meme_stock', False):
                            st.error("🚨 **밈주식 가능성 높음!** 투기적 움직임에 주의하세요.")
                        elif current > avg * 1.5:
                            st.warning("⚠️ 관심도가 높습니다. 이미 상승했을 수 있으니 신중하게 접근하세요.")
                        else:
                            st.success("✅ 관심도가 정상 범위입니다.")
                else:
                    st.error("❌ Google Trends 데이터 검색 실패")
                    st.markdown("""
                    **데이터를 찾지 못하는 가능한 원인:**
                    1. **API 호출 제한 (429 Error)**: 짧은 시간 내 과도한 요청 시 Google이 일시 차단할 수 있습니다.
                    2. **데이터 부족**: 해당 키워드의 검색량이 너무 적을 수 있습니다.
                    3. **검색어 불일치**: 종목명이 Google Trends 주제와 다를 수 있습니다.
                    
                    💡 **팁**: 1~2분 정도 기다렸다가 다시 시도하거나, 아래 버튼을 통해 **Google Trends 웹사이트에서 직접 확인**하실 수 있습니다.
                    """)
                    
                    try:
                        import urllib.parse
                        encoded_term = urllib.parse.quote(stock_name)
                        # 기본 기간: 3개월, 국가: KR
                        url = f"https://trends.google.co.kr/trends/explore?date=today%203-m&geo=KR&q={encoded_term}"
                        st.link_button("🌏 Google Trends 웹사이트에서 결과 보기", url, type="primary")
                    except:
                        pass
                    
            except Exception as e:
                st.error(f"분석 중 오류 발생: {str(e)}")
                import traceback
                st.code(traceback.format_exc())


def display_factor_investing():
    """팩터 투자 분석 뷰 (Fama-French 5 Factor)"""
    st.subheader("💎 팩터 투자 (Factor Investing)")
    st.markdown("Fama-French 5팩터 모델과 저변동성 팩터를 기반으로 종목을 분석합니다.")
    
    # 팩터 설명
    with st.expander("💡 팩터(Factor)란?", expanded=False):
        st.markdown("""
        **주식 수익률을 설명하는 공통적인 요인**입니다.
        
        1. **Momentum (모멘텀)**: 최근 12개월 수익률이 높은 주식 (추세 추종)
        2. **Value (가치)**: PER, PBR이 낮은 저평가 주식
        3. **Quality (품질)**: ROE, 이익률이 높은 우량 주식
        4. **Size (규모)**: 시가총액이 작은 중소형주 (성장 잠재력)
        5. **Volatility (저변동성)**: 주가 변동폭이 작은 안정적인 주식
        """)
    
    current_market = st.session_state.get('current_market', 'KR')
    market_code = "US" if current_market == "US" else "KR"
    
    tab1, tab2 = st.tabs(["📊 개별 종목 분석", "🔍 팩터 스크리닝"])
    
    with tab1:
        st.markdown("##### 개별 종목 팩터 점수")
        
        stock_options = st.session_state.get('active_stock_names', ["삼성전자 (005930)"])
        selected_stock = st.selectbox(
            "분석할 종목 선택",
            options=stock_options,
            key="factor_stock_select"
        )
        
        # 종목 코드 추출
        stock_dict = st.session_state.get('active_stock_list', {})
        if current_market == "US":
            ticker = stock_dict.get(selected_stock, "AAPL")
        else:
            ticker = stock_dict.get(selected_stock, "005930") + ".KS"
            
        if st.button("🧬 팩터 분석 실행", key="run_factor_single", type="primary"):
            with st.status("🧬 5팩터 분석 모델 가동 중...", expanded=True) as status:
                status.write("📊 재무/주가 데이터 수집 중...")
                try:
                    from src.services.factor_analysis_service import FactorAnalyzer
                    
                    # Repository에서 데이터 조회 (yfinance_repo 사용)
                    stock = yfinance_repo.get_stock_data(ticker, period="2y") # 모멘텀 위해 1년 이상 필요
                    stock_info = yfinance_repo.get_stock_info(ticker)
                    
                    if not stock:
                        st.error("데이터를 가져올 수 없습니다.")
                        return
                        
                    analyzer = FactorAnalyzer(market=market_code)
                    scores = analyzer.analyze(stock, stock_info)
                    
                    # 결과 시각화 (Radar Chart)
                    st.markdown(f"### {selected_stock.split(' (')[0]} 팩터 점수: **{scores.composite:.1f}**")
                    
                    categories = ['Momentum', 'Value', 'Quality', 'Size', 'Volatility']
                    values = [scores.momentum, scores.value, scores.quality, scores.size, scores.volatility]
                    
                    fig = go.Figure()
                    fig.add_trace(go.Scatterpolar(
                        r=values,
                        theta=categories,
                        fill='toself',
                        name=selected_stock
                    ))
                    fig.update_layout(
                        polar=dict(
                            radialaxis=dict(
                                visible=True,
                                range=[0, 100]
                            )),
                        showlegend=False,
                        template="plotly_dark",
                        title="5-Factor Radar Chart"
                    )
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # 세부 점수 카드
                    c1, c2, c3, c4, c5 = st.columns(5)
                    c1.metric("🚀 모멘텀", f"{scores.momentum:.0f}")
                    c2.metric("💰 가치", f"{scores.value:.0f}")
                    c3.metric("💎 품질", f"{scores.quality:.0f}")
                    c4.metric("🐜 규모", f"{scores.size:.0f}")
                    c5.metric("🛡️ 저변동성", f"{scores.volatility:.0f}")
                    status.update(label="✅ 분석 완료!", state="complete", expanded=False)
                    
                except Exception as e:
                    st.error(f"분석 중 오류 발생: {str(e)}")
                    # import traceback
                    # st.code(traceback.format_exc())

    with tab2:
        st.markdown("##### 팩터 기반 유망 종목 발굴")
        st.info("상위 10개 종목을 분석하여 팩터 점수 순위를 매깁니다. (속도를 위해 샘플 종목만 분석)")
        
        # 샘플 종목 (속도 문제로 전체 스크리닝은 제한)
        sample_stocks = stock_options[:20] # 상위 20개만
        target_stocks = st.multiselect(
            "분석 대상 종목 (최대 10개)",
            sample_stocks,
            default=sample_stocks[:5],
            max_selections=10
        )
        
        sort_by = st.selectbox(
            "정렬 기준", 
            ["composite", "momentum", "value", "quality", "size", "volatility"],
            format_func=lambda x: {
                "composite": "종합 점수", "momentum": "모멘텀", "value": "가치", 
                "quality": "품질", "size": "규모", "volatility": "저변동성"
            }[x]
        )
        
        if st.button("🔍 스크리닝 실행", key="run_factor_screen", type="primary"):
            with st.spinner(f"{len(target_stocks)}개 종목 분석 중..."):
                try:
                    from src.services.factor_analysis_service import FactorScreener
                    
                    # Repository 주입
                    screener = FactorScreener(stock_repo=yfinance_repo, market=market_code)
                    
                    # Ticker 변환
                    tickers = []
                    name_map = {}
                    for s in target_stocks:
                        if current_market == "US":
                            t = stock_dict.get(s, "AAPL")
                        else:
                            t = stock_dict.get(s, "005930") + ".KS"
                        tickers.append(t)
                        name_map[t] = s.split(" (")[0]
                    
                    results = screener.screen_top_stocks(tickers, top_n=len(tickers), sort_by=sort_by)
                    
                    # 결과 테이블
                    data = []
                    for r in results:
                        data.append({
                            "종목명": name_map.get(r.ticker, r.ticker),
                            "종합 점수": r.composite,
                            "모멘텀": r.momentum,
                            "가치": r.value,
                            "품질": r.quality,
                            "규모": r.size,
                            "저변동성": r.volatility
                        })
                    
                    df = pd.DataFrame(data)
                    st.dataframe(
                        df.style.background_gradient(cmap="RdYlGn", subset=["종합 점수"]),
                        hide_index=True,
                        use_container_width=True
                    )
                    
                except Exception as e:
                    st.error(f"스크리닝 오류: {str(e)}")


if __name__ == "__main__":
    main()
