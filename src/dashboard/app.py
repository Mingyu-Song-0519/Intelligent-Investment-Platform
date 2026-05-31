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

from src.dashboard.views.chart_utils import create_candlestick_chart, resample_ohlcv
from src.dashboard.views.mini_views import (
    display_single_stock_analysis_mini,
    display_multi_stock_comparison_mini,
    display_news_sentiment_mini,
    display_ai_prediction_mini,
    display_backtest_mini,
    display_portfolio_optimization_mini,
    display_risk_management_mini,
)


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
