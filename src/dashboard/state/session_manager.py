"""
세션 상태 관리 모듈

클린 아키텍처:
- Application Layer: Streamlit 세션 상태 초기화 및 관리
"""
import logging
import streamlit as st
from src.dashboard.utils.data_cache import get_cached_stock_listing_v3

logger = logging.getLogger(__name__)


def on_stock_change():
    """
    종목 변경 시 캐시 무효화 콜백
    
    st.selectbox의 on_change 핸들러로 사용:
    - cache_version 증가로 캐시 무효화 트리거
    - selected_stock/selected_ticker 세션 상태 업데이트
    
    Note: 여러 selectbox가 다른 키를 사용하므로 모두 체크
    """
    # 캐시 버전 증가 (캐시 무효화)
    if 'cache_version' not in st.session_state:
        st.session_state.cache_version = 0
    st.session_state.cache_version += 1
    
    # 여러 selectbox 키 중 존재하는 것에서 종목명 추출
    selectbox_keys = ['tab1_stock', 'ai_ticker', 'bt_ticker', 'news_stock', 'stock_selectbox_value']
    
    name = None
    for key in selectbox_keys:
        if key in st.session_state and st.session_state[key]:
            name = st.session_state[key]
            break
    
    if name:
        ticker = st.session_state.get('active_stock_list', {}).get(name, None)
        if ticker:
            st.session_state.selected_stock = name
            st.session_state.selected_ticker = ticker


class SessionManager:
    """Streamlit 세션 상태 관리 클래스"""
    
    @staticmethod
    def initialize_stock_lists():
        """
        앱 시작 시 종목 리스트 초기화 (사이드바 렌더링 전)
        
        Race Condition 방지:
        - 사이드바의 selectbox가 렌더링되기 전에 active_stock_names를 미리 설정
        - 기본값 ["삼성전자 (005930)"]만 표시되는 버그 해결
        """
        market = st.session_state.get('current_market', 'KR')
        
        if market == "US":
            # 미국 시장 종목 로딩 (캐싱 적용)
            if 'us_stock_list' not in st.session_state:
                with st.spinner("🇺🇸 미국 종목 목록 로딩 중... (최초 1회 시간이 소요될 수 있습니다)"):
                    try:
                        us_dict, us_names = get_cached_stock_listing_v3('US')
                        if us_dict and len(us_dict) > 0:
                            st.session_state.us_stock_list = us_dict
                            st.session_state.us_stock_names = us_names
                            logger.info(f"미국 종목 리스트 로딩: {len(us_dict)}개")
                        else:
                            raise Exception("Empty list returned")
                    except Exception as e:
                        # Fallback: 주요 빅테크 및 인기 종목
                        logger.error(f"미국 종목 로딩 실패: {e}")
                        fallback_us = {
                            "Apple (AAPL)": "AAPL", "Microsoft (MSFT)": "MSFT", "Google (GOOGL)": "GOOGL",
                            "Amazon (AMZN)": "AMZN", "Meta (META)": "META", "Tesla (TSLA)": "TSLA",
                            "Nvidia (NVDA)": "NVDA", "Netflix (NFLX)": "NFLX", "AMD (AMD)": "AMD"
                        }
                        st.session_state.us_stock_list = fallback_us
                        st.session_state.us_stock_names = list(fallback_us.keys())
            
            st.session_state.active_stock_list = st.session_state.us_stock_list
            st.session_state.active_stock_names = st.session_state.us_stock_names
            st.session_state.currency_symbol = "$"
            st.session_state.ticker_suffix = ""
        
        else:  # 한국 시장
            # KRX 종목 로딩 (FinanceDataReader)
            if 'krx_stock_list' not in st.session_state:
                krx_dict, krx_names = get_cached_stock_listing_v3('KR')
                if krx_dict and len(krx_dict) > 0:  # 🔧 수정: 빈 딕셔너리 체크 추가
                    st.session_state.krx_stock_list = krx_dict
                    st.session_state.krx_stock_names = krx_names
                    logger.info(f"KRX 종목 리스트 로딩: {len(krx_dict)}개")
                else:
                    # Fallback: 기본 종목 리스트
                    fallback_stocks = {
                        "삼성전자 (005930)": "005930",
                        "SK하이닉스 (000660)": "000660",
                        "LG에너지솔루션 (373220)": "373220",
                        "현대차 (005380)": "005380",
                        "기아 (000270)": "000270",
                        "POSCO홀딩스 (005490)": "005490",
                        "KB금융 (105560)": "105560",
                        "신한지주 (055550)": "055550",
                        "네이버 (035420)": "035420",
                        "카카오 (035720)": "035720",
                    }
                    st.session_state.krx_stock_list = fallback_stocks
                    st.session_state.krx_stock_names = list(fallback_stocks.keys())
                    logger.warning(f"KRX 로딩 실패, 기본 종목 리스트 사용 ({len(fallback_stocks)}개)")
            
            st.session_state.active_stock_list = st.session_state.krx_stock_list
            st.session_state.active_stock_names = st.session_state.krx_stock_names
            st.session_state.currency_symbol = "₩"
            st.session_state.ticker_suffix = ".KS"
    
    @staticmethod
    def initialize():
        """전체 세션 상태 초기화"""
        # 시장 기본값 설정
        if 'current_market' not in st.session_state:
            st.session_state.current_market = 'KR'
        
        # 종목 리스트 초기화 (Race Condition 방지)
        SessionManager.initialize_stock_lists()
        
        # 기타 기본값 설정
        if 'split_mode' not in st.session_state:
            st.session_state.split_mode = False
        
        if 'panel_a_tab' not in st.session_state:
            st.session_state.panel_a_tab = "📊 단일 종목 분석"
        
        if 'panel_b_tab' not in st.session_state:
            st.session_state.panel_b_tab = "🔀 다중 종목 비교"


# 이전 호환성을 위한 함수
def initialize_stock_lists():
    """[DEPRECATED] SessionManager.initialize_stock_lists() 사용 권장"""
    SessionManager.initialize_stock_lists()
