"""
Streamlit 기반 주식 분석 대시보드 - Phase 2 통합
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px
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

from config import DEFAULT_TICKERS, US_TICKERS, DASHBOARD_CONFIG, ENSEMBLE_CONFIG, MARKET_CONFIG, EXCHANGE_RATE_CONFIG
from src.collectors.stock_collector import StockDataCollector
from src.collectors.multi_stock_collector import MultiStockCollector

# Phase 2: 모듈화된 유틸리티 및 상태 관리
from src.dashboard.utils.data_cache import (
    get_cached_stock_data, 
    get_cached_multi_stock_data,
    get_cached_exchange_rate
)
from src.dashboard.utils.metric_utils import display_metrics
from src.dashboard.utils.signal_utils import display_signals
from src.dashboard.state.session_manager import SessionManager, initialize_stock_lists, on_stock_change

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

# 팩터 투자 뷰
try:
    from src.dashboard.views.factor_view import display_factor_investing
    FACTOR_INVESTING_AVAILABLE = True
except ImportError:
    FACTOR_INVESTING_AVAILABLE = False
    def display_factor_investing():
        st.error("팩터 투자 모듈을 로드할 수 없습니다.")

# Phase D: AI 챗봇
try:
    from src.dashboard.components.sidebar_chat import render_sidebar_chat
    CHATBOT_AVAILABLE = True
except ImportError:
    CHATBOT_AVAILABLE = False

# Phase 2: Views 모듈
from src.dashboard.views import (
    display_multi_stock_comparison,
    display_news_sentiment,
    display_ai_prediction,
    display_backtest,
    display_portfolio_optimization,
    display_risk_analysis,
    display_market_breadth
)


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
        
        /* Plotly 차트 터치 인터랙션 활성화 */
        .js-plotly-plot, .plot-container, .main-svg {
            touch-action: pan-x pan-y pinch-zoom !important; /* 줌/팬 허용 */
        }
        /* Range slider 터치 영역 */
        .rangeslider-container {
            touch-action: pan-x !important;
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
        
        /* 🔧 Issue #6 수정: Disabled 체크박스/버튼 시각화 개선 */
        div[data-testid="stCheckbox"][aria-disabled="true"] label,
        div[data-testid="stCheckbox"] input:disabled + label,
        .stCheckbox > label:has(input:disabled) {
            opacity: 0.5 !important;
            color: #888888 !important;
            cursor: not-allowed !important;
        }
        div[data-testid="stCheckbox"] input:disabled + label::before {
            background-color: #555555 !important;
            border-color: #666666 !important;
        }
        /* Disabled 버튼 스타일 */
        button:disabled, .stButton button:disabled {
            opacity: 0.4 !important;
            cursor: not-allowed !important;
            background-color: #444444 !important;
        }
        </style>
    """, unsafe_allow_html=True)


# [Phase 2] 데이터 캐싱 함수들은 src/dashboard/utils/data_cache.py로 이동됨
# get_cached_stock_data, get_cached_multi_stock_data, get_cached_stock_listing, get_cached_exchange_rate

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
        # 🔧 인터랙티브 차트: rangeslider 활성화 (기간 선택 슬라이더)
        xaxis_rangeslider_visible=True,
        xaxis_rangeslider_thickness=0.05,  # 슬라이더 두께
        xaxis_rangeslider_bgcolor='rgba(50,50,50,0.3)',
        # 드래그 모드: pan 또는 zoom 선택 가능
        dragmode='pan',  # 기본은 팬 (드래그로 이동), 더블클릭으로 리셋
        hovermode="x unified"  # 터치 시 호버 정보 표시
    )
    
    # X축 날짜 형식 한글화 + 줌/팬 활성화
    # 🔧 모든 차트 하단에 날짜 표시
    fig.update_xaxes(tickformat="%Y년 %m월 %d일", row=1, col=1, fixedrange=False, showticklabels=True)
    fig.update_xaxes(tickformat="%Y년 %m월 %d일", row=2, col=1, fixedrange=False, showticklabels=True)
    fig.update_xaxes(tickformat="%Y년 %m월 %d일", row=3, col=1, fixedrange=False, showticklabels=True)
    fig.update_xaxes(tickformat="%Y년 %m월 %d일", row=4, col=1, fixedrange=False, showticklabels=True)
    
    # Y축은 자동 조정 (X축 줌에 따라 Y축 범위 조정)
    fig.update_yaxes(fixedrange=False, autorange=True)
    
    return fig



# [Phase 2] display_metrics는 src/dashboard/utils/metric_utils.py로 이동됨




# [Phase 2] display_signals는 src/dashboard/utils/signal_utils.py로 이동됨




# [Phase 2] display_multi_stock_comparison은 src/dashboard/views/multi_stock_view.py로 이동됨




# [Phase 2] display_news_sentiment는 src/dashboard/views/news_sentiment_view.py로 이동됨





    
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
    
    # 감성 분석 방법 선택
    if current_market == 'KR':
        analysis_method = st.radio(
            "📊 감성 분석 방법",
            ["⚡ 키워드 기반 (빠름)", "🧠 딥러닝 (KR-FinBert-SC)", "🤖 Gemini LLM (고급)"],
            horizontal=True,
            help="키워드: 빠르지만 단순 / 딥러닝: GPU 활용 정확 / Gemini: API 기반 고급 분석"
        )
        use_deep_learning = (analysis_method == "🧠 딥러닝 (KR-FinBert-SC)")
        use_gemini_llm = (analysis_method == "🤖 Gemini LLM (고급)")
        
        # Gemini 선택 시 API 키 확인
        if use_gemini_llm and not st.session_state.get('gemini_api_key'):
            st.warning("⚠️ 사이드바 상단 '🔑 AI API 설정'에서 Gemini API 키를 먼저 입력해주세요.")
    else:
        use_deep_learning = False
        use_gemini_llm = False
        st.info("💡 미국 종목은 VADER 기반 영문 감성 분석을 사용합니다.")

    if st.button("📥 뉴스 수집 및 분석", type="primary"):
        with st.spinner(f"'{search_query}' 관련 뉴스 수집 중..."):
            try:
                news_collector = NewsCollector()
                sentiment_analyzer = SentimentAnalyzer(use_deep_learning=use_deep_learning, use_llm=use_gemini_llm)
                
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
                        analysis_method_label = "VADER (영문)"
                    elif use_deep_learning:
                        analysis_method_label = "딥러닝 (KR-FinBert-SC)"
                    elif use_gemini_llm:
                        analysis_method_label = "🤖 Gemini LLM (배치)"
                    else:
                        analysis_method_label = "키워드 기반"
                    
                    with st.spinner(f"감성 분석 중... ({analysis_method_label})"):
                        # Gemini LLM 배치 분석 (효율적)
                        if use_gemini_llm and sentiment_analyzer.llm_analyzer:
                            texts = [a['title'] + ' ' + a.get('content', '')[:200] for a in all_articles]
                            
                            try:
                                # 배치 분석: 10개씩 묶어서 1번의 API 호출
                                results = sentiment_analyzer.llm_analyzer.analyze_batch_single_call(texts, batch_size=10)
                                
                                for idx, article in enumerate(all_articles):
                                    if idx < len(results):
                                        article['sentiment'] = results[idx].score
                                        article['analysis_method'] = 'gemini_llm_batch'
                                        article['sentiment_details'] = {
                                            'confidence': results[idx].confidence,
                                            'source': results[idx].source
                                        }
                                    else:
                                        article['sentiment'] = 0.0
                                        article['analysis_method'] = 'gemini_fallback'
                            except Exception as e:
                                st.warning(f"Gemini 배치 분석 실패: {e}. 키워드 분석으로 대체합니다.")
                                for article in all_articles:
                                    text = article['title'] + ' ' + article.get('content', '')
                                    score, details = sentiment_analyzer.analyze_text(text)
                                    article['sentiment'] = score
                                    article['analysis_method'] = 'keyword_fallback'
                        else:
                            # 기존 분석 방식 (VADER / 딥러닝 / 키워드)
                            for article in all_articles:
                                text = article['title'] + ' ' + article.get('content', '')
                                
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
                        
                        # 감성 레이블 부여 (공통)
                        for article in all_articles:
                            score = article.get('sentiment', 0)
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



# [Phase 2] display_ai_prediction은 src/dashboard/views/ai_prediction_view.py로 이동됨


    # 전체 종목 검색
    stock_options = st.session_state.get('active_stock_names', list(DEFAULT_TICKERS.keys()))
    default_stock = "삼성전자 (005930)" if st.session_state.get('current_market') == "KR" else "Apple (AAPL)"
    selected = st.selectbox("종목 검색", stock_options, index=default_idx, key="ai_ticker", on_change=on_stock_change, help="종목명 또는 코드로 검색 (예: 삼성전자, 005930)")
    
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
                        # 감성 피처 개수 정확히 계산
                        from src.services.sentiment_analysis_service import SentimentAnalysisService
                        sentiment_feature_count = len(SentimentAnalysisService.get_sentiment_feature_columns())
                        st.success(f"✅ 감성 피처 {sentiment_feature_count}개 추가됨{llm_msg}")
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




# [Phase 2] display_backtest는 src/dashboard/views/backtest_view.py로 이동됨


    # 현재 시장
    current_market = st.session_state.get('current_market', 'KR')
    
    # 전체 종목 검색
    stock_options = st.session_state.get('active_stock_names', ["삼성전자 (005930)"])
    default_stock = "삼성전자 (005930)" if current_market == "KR" else "Apple (AAPL)"
    default_idx = stock_options.index(default_stock) if default_stock in stock_options else 0
    selected = st.selectbox("종목 검색", stock_options, index=default_idx, key="bt_ticker", on_change=on_stock_change, help="종목명 또는 코드로 검색 (예: 삼성전자, 005930)")
    
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
        df = st.session_state.get(f'mini_data_{panel_id}', pd.DataFrame())
        name = st.session_state.get(f'mini_name_{panel_id}', ticker_name)

        if df.empty:
            st.warning("데이터가 없습니다.")
            return

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
                except Exception:
                    pass
            st.session_state[f'multi_data_{panel_id}'] = data_dict
            st.success(f"✅ {len(data_dict)}개 종목 로드 완료!")
    
    if f'multi_data_{panel_id}' in st.session_state:
        data_dict = st.session_state.get(f'multi_data_{panel_id}', {})
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
        news_df = st.session_state.get(f'news_data_{panel_id}', pd.DataFrame())
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
        except Exception:
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
                    except Exception:
                        pass
                
                st.session_state[f'ai_result_{panel_id}'] = result
                status.update(label="✅ 예측 완료!", state="complete", expanded=False)
                st.success("✅ 예측 완료!")
            except Exception as e:
                st.error(f"오류: {e}")
    
    if f'ai_result_{panel_id}' in st.session_state:
        result = st.session_state.get(f'ai_result_{panel_id}', None)
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
        data = st.session_state.get(f'bt_result_{panel_id}', {})
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
        result = st.session_state.get(f'port_result_{panel_id}', {})
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
        summary = st.session_state.get(f'risk_result_{panel_id}', {})
        st.markdown("### 📉 VaR")
        st.metric("Historical VaR", f"₩{summary['historical_var']['var_amount']:,.0f}")
        st.metric("CVaR", f"₩{summary['cvar']['cvar_amount']:,.0f}")





def main():
    """메인 대시보드"""
    setup_page()
    
    # 🔧 버그 수정: 종목 리스트를 사이드바 렌더링 전에 초기화
    # Race Condition 방지 - active_stock_names가 먼저 설정되어야 함
    initialize_stock_lists()


    st.title("📈 스마트 투자 분석 플랫폼")
    st.markdown("실시간 시세 · AI 예측 · 백테스팅 · 포트폴리오 최적화 · 리스크 관리 통합 플랫폼")

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
            
            selected_stock = st.selectbox(
                "종목 검색",
                options=stock_options,
                index=default_idx,
                help="종목명을 입력하여 검색하세요",
                key="realtime_stock_select"
            )
            
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
            
            # AI 종목 추천에서 선택한 종목이 있으면 자동 선택
            if 'analysis_ticker' in st.session_state:
                analysis_ticker = st.session_state['analysis_ticker']
                # stock_options에서 해당 ticker를 포함하는 항목 찾기
                matching_stock = None
                for stock_option in stock_options:
                    if f"({analysis_ticker})" in stock_option:
                        matching_stock = stock_option
                        break
                
                if matching_stock:
                    default_stock = matching_stock
                    # analysis_ticker 사용 후 삭제 (한 번만 적용)
                    del st.session_state['analysis_ticker']
                else:
                    default_stock = "삼성전자 (005930)" if current_market == "KR" else "Apple (AAPL)"
            else:
                default_stock = "삼성전자 (005930)" if current_market == "KR" else "Apple (AAPL)"
            
            default_idx = stock_options.index(default_stock) if default_stock in stock_options else 0
            selected = st.selectbox("종목 검색", stock_options, index=default_idx, key="tab1_stock", on_change=on_stock_change, help="종목명 또는 코드로 검색 (예: 삼성전자, 005930)")
            
            if current_market == "US":
                ticker_code = st.session_state.get('active_stock_list', {}).get(selected, "AAPL")
            else:
                ticker_code = st.session_state.get('active_stock_list', {}).get(selected, "005930") + ".KS"
            ticker_name = selected.split(" (")[0] if "(" in selected else selected
            st.session_state.tab1_ticker_code = ticker_code
            st.session_state.tab1_ticker_name = ticker_name
            
            # 🔧 뷰 호환성: selected_ticker, selected_stock 키 동기화
            st.session_state.selected_ticker = ticker_code
            st.session_state.selected_stock = ticker_name
            
            period = st.selectbox(
                "조회 기간",
                ["1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "max"],
                index=3,
                format_func=lambda x: {
                    "1mo": "1개월", "3mo": "3개월", "6mo": "6개월", "1y": "1년",
                    "2y": "2년", "5y": "5년", "10y": "10년", "max": "전체"
                }.get(x, x),
                key="tab1_period"
            )
            
            # 🔧 봉 타입 선택 (일봉/주봉/월봉)
            candle_interval = st.selectbox(
                "봉 타입",
                ["1d", "1wk", "1mo"],
                index=0,
                format_func=lambda x: {
                    "1d": "📅 일봉", "1wk": "📆 주봉", "1mo": "🗓️ 월봉"
                }.get(x, x),
                key="tab1_interval",
                help="차트에 표시할 캔들 단위 (일/주/월)"
            )
            st.session_state.candle_interval = candle_interval
            
            if st.button("📥 데이터 수집", type="primary", key="tab1_fetch"):
                st.session_state.tab1_fetch_clicked = True
            
            st.caption("💡 기술적 지표는 자동으로 계산됩니다.")
            # divider 제거 - 불필요한 공간 절약
        else:
            # 🔧 수정: 기타 탭에도 종목 선택 기능 추가 (AI 예측, 백테스팅 등)
            st.header("⚙️ 설정")
            
            market_label = "🇰🇷 한국" if current_market == "KR" else "🇺🇸 미국"
            st.info(f"시장: {market_label}")
            
            # 종목 검색 (공통)
            stock_options = st.session_state.get('active_stock_names', ["삼성전자 (005930)"])
            default_stock = "삼성전자 (005930)" if current_market == "KR" else "Apple (AAPL)"
            default_idx = stock_options.index(default_stock) if default_stock in stock_options else 0
            
            selected = st.selectbox(
                "종목 검색", 
                stock_options, 
                index=default_idx, 
                key="general_tab_stock",
                help="분석할 종목을 선택하세요"
            )
            
            # 선택된 종목 정보 저장 (다른 탭에서 사용)
            if current_market == "US":
                ticker_code = st.session_state.get('active_stock_list', {}).get(selected, "AAPL")
            else:
                ticker_code = st.session_state.get('active_stock_list', {}).get(selected, "005930") + ".KS"
            ticker_name = selected.split(" (")[0] if "(" in selected else selected
            
            # 🔧 뷰 호환성: selected_ticker, selected_stock 키 동기화
            st.session_state.selected_ticker = ticker_code
            st.session_state.selected_stock = ticker_name
            
            # 공용 session_state 키에도 저장 (tab1과 호환)
            st.session_state.tab1_ticker_code = ticker_code
            st.session_state.tab1_ticker_name = ticker_name
            st.session_state.general_ticker_code = ticker_code
            st.session_state.general_ticker_name = ticker_name
            
            st.caption(f"선택: {ticker_name} ({ticker_code})")

        
        # ==========================================
        # Phase 3: 설정 통합 - 하나의 Expander + Tabs
        # ==========================================
        with st.expander("⚙️ 설정", expanded=False):
            tab_user, tab_api, tab_alert = st.tabs(["👤 사용자", "🔑 API", "🔔 알림"])
            
            # Tab 1: 사용자 식별
            with tab_user:
                st.markdown("**👤 사용자 식별**")
                email_input = st.text_input(
                    "이메일",
                    value=st.session_state.get('user_email', ''),
                    placeholder="example@email.com",
                    help="프로필 저장 및 불러오기에 사용됩니다",
                    key="email_input_field_unified"
                )
                
                if email_input and '@' in email_input:
                    st.session_state.user_id = email_input.lower().strip()
                    st.session_state.user_email = email_input
                    st.success(f"✅ {email_input}")
                elif email_input:
                    st.warning("올바른 이메일 형식을 입력해주세요")
                    st.session_state.user_id = "default_user"
                else:
                    st.session_state.user_id = "default_user"
                    st.caption("이메일을 입력하면 프로필이 저장됩니다")
            
            # Tab 2: AI API 설정
            with tab_api:
                st.markdown("**🔑 AI API 설정**")
                try:
                    from src.services.api_key_service import APIKeyService
                    from src.infrastructure.repositories.session_api_key_repository import SessionAPIKeyRepository
                    from src.infrastructure.external.gemini_client import GeminiClient
                    
                    repo = SessionAPIKeyRepository()
                    api_service = APIKeyService(repository=repo)
                    
                    current_key = st.session_state.get('gemini_api_key', '')
                    
                    if current_key:
                        st.success("✅ Gemini API 키 설정됨")
                        col1, col2 = st.columns([2, 1])
                        with col1:
                            if st.button("🔄 검증", key="validate_api_key_unified", width="stretch"):
                                is_valid, msg = repo.validate_key('gemini_api_key', current_key)
                                if is_valid:
                                    st.success(msg)
                                else:
                                    st.error(msg)
                        with col2:
                            if st.button("🗑️", key="clear_api_key_unified", width="stretch", help="API 키 삭제"):
                                api_service.delete_gemini_key()
                                if 'gemini_model_list' in st.session_state:
                                    del st.session_state['gemini_model_list']
                                st.rerun()
                        
                        # 모델 선택 UI
                        st.markdown("---")
                        st.markdown("**🤖 모델 선택**")
                        
                        # 모델 목록 캐싱 및 로드
                        if 'gemini_model_list' not in st.session_state:
                            with st.spinner("사용 가능한 모델 목록을 불러오는 중..."):
                                try:
                                    client = GeminiClient(api_key=current_key)
                                    models = client.get_available_models()
                                    if models:
                                        st.session_state['gemini_model_list'] = models
                                    else:
                                        st.warning("사용 가능한 모델을 찾을 수 없습니다.")
                                        st.session_state['gemini_model_list'] = []
                                except Exception as e:
                                    st.error(f"모델 목록 로드 실패: {e}")
                                    st.session_state['gemini_model_list'] = []
                        
                        models = st.session_state.get('gemini_model_list', [])
                        if models:
                            # 현재 선택된 모델 확인
                            current_selection = st.session_state.get('gemini_model_name', 'gemini-2.0-flash')
                            
                            # 목록에 없으면 첫 번째 모델 선택 (fallback)
                            index = 0
                            if current_selection in models:
                                index = models.index(current_selection)
                            elif 'gemini-2.0-flash' in models:
                                index = models.index('gemini-2.0-flash')
                            
                            selected_model = st.selectbox(
                                "사용할 Gemini 모델", 
                                models, 
                                index=index,
                                key="gemini_model_selector"
                            )
                            
                            # 선택 변경 시 session_state 업데이트
                            if selected_model != st.session_state.get('gemini_model_name'):
                                st.session_state['gemini_model_name'] = selected_model
                                st.rerun()
                        else:
                            st.info("모델 목록을 불러올 수 없습니다. 기본 모델이 사용됩니다.")
                    else:
                        st.info("💡 AI 챗봇, Gemini 감성분석 등에 필요합니다")
                        api_key_input = st.text_input(
                            "Gemini API Key",
                            type="password",
                            placeholder="AIza...",
                            help="Google AI Studio에서 발급받은 API 키",
                            key="central_api_key_input_unified"
                        )
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            validate_on_save = st.checkbox("저장 시 검증", value=True, key="validate_on_save_unified")
                        
                        if st.button("💾 저장", key="save_api_key_unified", width="stretch"):
                            if api_key_input:
                                success, msg = api_service.set_gemini_key(
                                    st.session_state.get('user_id', 'default_user'),
                                    api_key_input,
                                    validate=validate_on_save
                                )
                                if success:
                                    st.success(msg)
                                    if 'gemini_model_list' in st.session_state:
                                        del st.session_state['gemini_model_list']
                                    st.rerun()
                                else:
                                    st.error(msg)
                            else:
                                st.warning("API 키를 입력해주세요")
                        
                        st.caption("[🔗 API 키 발급받기](https://aistudio.google.com/apikey)")
                except Exception as e:
                    st.error(f"API 설정 로드 실패: {e}")
            
            # Tab 3: 알림 설정
            with tab_alert:
                st.markdown("**🔔 알림 설정**")
                st.markdown("**주요 이벤트 알림 설정**")
                
                alert_enabled = st.checkbox("알림 활성화", value=False, key="alert_enabled_unified")
                
                if alert_enabled:
                    st.markdown("---")
                    st.markdown("**📊 임계값 설정**")
                    
                    vix_threshold = st.slider(
                        "VIX 경고 임계값", 
                        min_value=15, max_value=50, value=25,
                        help="VIX가 이 값을 초과하면 경고 알림",
                        key="vix_threshold_unified"
                    )
                    
                    mdd_threshold = st.slider(
                        "MDD 경고 임계값 (%)", 
                        min_value=5, max_value=30, value=10,
                        help="최대 낙폭이 이 %를 초과하면 경고 알림",
                        key="mdd_threshold_unified"
                    )
                    
                    st.session_state.alert_config = {
                        "vix_threshold": vix_threshold,
                        "mdd_threshold": mdd_threshold,
                        "enabled": True
                    }
                    
                    st.markdown("---")
                    st.markdown("**📬 알림 채널**")
                    
                    telegram_enabled = st.checkbox("Telegram 알림", value=False, key="telegram_enabled_unified")
                    if telegram_enabled:
                        telegram_token = st.text_input(
                            "Bot Token", 
                            type="password",
                            help="BotFather에서 발급받은 토큰",
                            key="telegram_token_unified"
                        )
                        telegram_chat = st.text_input(
                            "Chat ID",
                            help="@userinfobot으로 확인 가능",
                            key="telegram_chat_unified"
                        )
                        st.session_state.telegram_config = {
                            "token": telegram_token,
                            "chat_id": telegram_chat
                        }
                    
                    email_alert_enabled = st.checkbox("Email 알림", value=False, key="email_alert_enabled_unified")
                    if email_alert_enabled:
                        st.text_input("SMTP 서버", placeholder="smtp.gmail.com", key="smtp_server_unified")
                        st.text_input("이메일 주소", placeholder="your@email.com", key="email_addr_unified")
                        st.text_input("앱 비밀번호", type="password", key="email_pwd_unified")
                        st.caption("※ Gmail은 앱 비밀번호 필요")
                else:
                    st.session_state.alert_config = {"enabled": False}
                    st.caption("알림을 활성화하면 VIX 급등, MDD 초과 등 주요 이벤트를 알려드립니다.")
        
        # 기존 API/사용자 식별 expander는 Phase 3에서 통합됨 (위 "⚙️ 설정" expander 참조)
    
    # ==========================================
    # Phase 2: 시장 선택 토글 버튼 (공간 50% 절약)
    # ==========================================
    
    # 🔧 수정: on_click 콜백으로 시장 전환 (rerun 전에 실행되어 즉시 반영)
    def switch_market(new_market: str):
        """시장 전환 콜백 - rerun 전에 실행됨"""
        current = st.session_state.get('current_market', 'KR')
        if current != new_market:
            # 이전 시장 저장 (상태 복원용)
            st.session_state.previous_market = current
            st.session_state.current_market = new_market
            st.session_state._market_just_changed = True  # 상태 복원 트리거
            
            # 🔧 Issue #7 수정: 시장 변경 시 현재 데이터 초기화
            # (이전 시장 데이터가 새 시장에 표시되는 것 방지)
            keys_to_clear = ['stock_data', 'last_fetched_ticker', 'ticker_code', 'ticker_name']
            for key in keys_to_clear:
                if key in st.session_state:
                    del st.session_state[key]
            
            # cache_version 증가로 캐시 무효화
            st.session_state.cache_version = st.session_state.get('cache_version', 0) + 1
    
    with st.sidebar:
        st.markdown("### 🌍 시장 선택")
        
        # 현재 시장 상태
        current_market_state = st.session_state.get('current_market', 'KR')
        
        # 가로 2열 토글 버튼 (on_click 사용)
        col1, col2 = st.columns(2)
        
        with col1:
            st.button(
                "🇰🇷 한국",
                width="stretch",
                type="primary" if current_market_state == "KR" else "secondary",
                key="market_btn_kr",
                on_click=switch_market,
                args=("KR",)
            )
        
        with col2:
            st.button(
                "🇺🇸 미국",
                width="stretch",
                type="primary" if current_market_state == "US" else "secondary",
                key="market_btn_us",
                on_click=switch_market,
                args=("US",)
            )
        
        # 선택된 시장 캡션 표시
        market_full_label = "🇰🇷 한국 (KRX)" if current_market_state == "KR" else "🇺🇸 미국 (NYSE/NASDAQ)"
        st.caption(f"선택: {market_full_label}")
        # divider 제거 - 불필요한 공간 절약
    
    # 시장 변경 후 상태 복원 처리 (on_click 콜백에서 current_market은 이미 업데이트됨)
    if st.session_state.get('_market_just_changed', False):
        new_market = st.session_state.current_market
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
        
        # 플래그 초기화
        st.session_state._market_just_changed = False
    
    # 기본 previous_market 초기화
    if 'previous_market' not in st.session_state:
        st.session_state.previous_market = st.session_state.get('current_market', 'KR')

    
    # ==========================================
    # 종목 리스트 초기화는 initialize_stock_lists()에서 처리됨
    # 시장 변경 처리만 유지
    # ==========================================


    # ==========================================
    # Phase 3-4: 기존 알림/경제 지표 expander 제거됨
    # - 알림 설정: 통합 설정 Expander (⚙️ 설정 → 🔔 알림 탭) 참조
    # - 경제 지표: 시장 현황 탭에서 확인 (사이드바 중복 제거)
    # ==========================================
    with st.sidebar:
        # Phase 1: AI 챗봇 - 하단 고정 (divider 제거하여 공간 절약)
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
            "🌐 시장 현황",
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
            "🌅 AI 종목 추천"
        ]
        default_tab = "📊 단일 종목 분석"
    else:
        tab_options = [
            "🌐 시장 현황",
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
            "🌅 AI 종목 추천"
        ]
        default_tab = "📊 단일 종목 분석"
    
    # Phase E: 챗봇에서 탭 전환 요청이 있으면 해당 탭을 default로 설정
    if 'pending_tab' in st.session_state:
        pending = st.session_state.pending_tab
        if pending in tab_options:
            # 🔧 수정: session_state에 직접 할당하지 않고 default만 변경
            default_tab = pending
            st.session_state.active_tab_name = pending  # 탭 상태 갱신
        del st.session_state.pending_tab
    else:
        # 기존 탭 상태 유지 (버튼 클릭 시에도 탭 유지)
        saved_tab = st.session_state.get('active_tab_name')
        if saved_tab and saved_tab in tab_options:
            default_tab = saved_tab
    
    # 🔧 수정: key가 이미 존재하면 default 대신 기존 값 사용
    if 'main_tab_selector' in st.session_state and st.session_state.main_tab_selector in tab_options:
        # 이미 key가 있으면 default를 무시 (충돌 방지)
        pass
    
    selected_tab = st.segmented_control(
        "분석 메뉴",
        tab_options,
        default=default_tab if 'main_tab_selector' not in st.session_state else None,
        selection_mode="single",
        label_visibility="collapsed",
        key="main_tab_selector"  # 고유 key로 상태 유지
    )

    
    # Phase D: 챗봇 Context 추적을 위해 현재 탭 저장
    st.session_state.active_tab_name = selected_tab
    
    # 사이드바: 이제 Phase 1에서 탭별 설정이 최상단에 렌더링됨 (Line 2192-2300)
    # 중복 코드 제거됨 - 기존 2차 사이드바 블록 삭제

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
        
        # 🔧 종목 변경 감지: 이전 ticker와 비교
        last_ticker = st.session_state.get('last_fetched_ticker', None)
        stock_changed = (last_ticker != ticker_code) if last_ticker else False
        
        # 데이터 갱신 조건: 버튼 클릭 OR 최초 로드 OR 종목 변경
        needs_refetch = fetch_data or 'stock_data' not in st.session_state or stock_changed
            
        if needs_refetch:
            with st.spinner(f'{ticker_name} 데이터를 불러오는 중...'):
                try:
                    df = get_cached_stock_data(ticker_code, period)
                    if not df.empty:
                        analyzer = TechnicalAnalyzer(df)
                        analyzer.add_all_indicators()
                        df = analyzer.get_dataframe()
                        st.session_state['stock_data'] = df
                        st.session_state['ticker_name'] = ticker_name
                        st.session_state['last_fetched_ticker'] = ticker_code  # 🔧 마지막 조회 ticker 저장
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
            
            # 🔧 봉 타입에 따른 리샘플링
            candle_interval = st.session_state.get('candle_interval', '1d')
            chart_df = resample_ohlcv(df, candle_interval)
            
            # 봉 타입 표시
            interval_labels = {"1d": "일봉", "1wk": "주봉", "1mo": "월봉"}
            st.caption(f"📊 {interval_labels.get(candle_interval, '일봉')} 차트 ({len(chart_df)}개 봉)")
            
            fig = create_candlestick_chart(chart_df, ticker_name)
            st.plotly_chart(fig, width="stretch")
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
                    st.markdown(f"**PBR**: 주가순자산비율. 주가 ÷ 주당순자산. 1 미만이면 저평가 가능성.")
                    st.markdown(f"**ROE**: {get_hint_text('ROE', 'short')}")
                    st.markdown(f"**부채비율**: 부채 ÷ 자기자본 × 100. 낮을수록 재무 안정성 높음.")
                    st.markdown(f"**배당률**: 배당금 ÷ 주가 × 100. 높을수록 배당 매력적.")
                
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
                            value=f"{per_val:.1f}" if per_val else "N/A",
                            help="주가수익비율 (Price to Earnings Ratio). 주가 ÷ 주당순이익. 낮을수록 저평가."
                        )
                    
                    with fcol2:
                        pbr_data = card_data['pbr']
                        pbr_val = pbr_data['value']
                        st.metric(
                            label=f"{pbr_data['color']} PBR",
                            value=f"{pbr_val:.2f}" if pbr_val else "N/A",
                            help="주가순자산비율 (Price to Book Ratio). 주가 ÷ 주당순자산. 1 미만이면 저평가 가능성."
                        )
                    
                    with fcol3:
                        roe_data = card_data['roe']
                        roe_val = roe_data['value']
                        st.metric(
                            label=f"{roe_data['color']} ROE",
                            value=f"{roe_val*100:.1f}%" if roe_val else "N/A",
                            help="자기자본이익률 (Return on Equity). 당기순이익 ÷ 자기자본 × 100. 높을수록 수익성 우수."
                        )
                    
                    with fcol4:
                        debt_data = card_data['debt_ratio']
                        debt_val = debt_data['value']
                        st.metric(
                            label=f"{debt_data['color']} 부채비율",
                            value=f"{debt_val:.0f}%" if debt_val else "N/A",
                            help="부채 ÷ 자기자본 × 100. 낮을수록 재무 안정성이 높음. 일반적으로 200% 이하가 안전."
                        )
                    
                    with fcol5:
                        div_data = card_data['dividend_yield']
                        div_val = div_data['value']
                        st.metric(
                            label=f"{div_data['color']} 배당률",
                            value=f"{div_val*100:.2f}%" if div_val else "N/A",
                            help="배당금 ÷ 주가 × 100. 높을수록 배당 매력적. 배당을 지급하지 않는 기업은 0%."
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
    elif selected_tab == "🌐 시장 현황":
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
    
    elif selected_tab == "🌅 AI 종목 추천":
        if SCREENER_AVAILABLE:
            render_morning_picks()
        else:
            st.warning("AI 스크리너 모듈을 불러올 수 없습니다.")



# [Phase 2] display_portfolio_optimization은 views 모듈로 이동됨


# [Phase 2] display_risk_management은 views 모듈로 이동됨


# [Phase 2] display_market_breadth은 views 모듈로 이동됨


# [Phase 2] display_social_trend은 views 모듈로 이동됨


# [Phase 2] display_factor_investing은 views 모듈로 이동됨


# 앱 실행
if __name__ == "__main__":
    main()
