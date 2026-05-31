import streamlit as st
import pandas as pd
import plotly.express as px
import time
import os

from src.collectors.kis_realtime_collector import KISRealtimeCollector

def display_realtime_data():
    """실시간 시세 탭 (REST API 기반)"""
    st.header("🔴 실시간 시세 (한국투자증권)")
    
    # 미국 시장 선택 시 비활성화
    current_market = st.session_state.get('current_market', 'KR')
    if current_market == 'US':
        st.warning("⚠️ 미국 시장 실시간 시세는 현재 지원하지 않습니다.")
        st.info("""
        **안내:**
        - 미국 주식 실시간 데이터는 유료 API 구독이 필요합니다.
        - 현재 단일 종목 분석 탭에서 15분 지연 데이터를 확인할 수 있습니다.
        - 한국 시장 전환 후 실시간 시세를 이용해 주세요.
        """)
        return

    # API 키 확인 (Secrets -> env 순서)
    import os
    from dotenv import load_dotenv
    
    APP_KEY = None
    APP_SECRET = None
    ACCOUNT_NO = None

    # 1. Streamlit Secrets 확인 (예외 처리 추가)
    try:
        if 'kis' in st.secrets:
            APP_KEY = st.secrets['kis']['APP_KEY']
            APP_SECRET = st.secrets['kis']['APP_SECRET']
            ACCOUNT_NO = st.secrets['kis']['ACCOUNT_NO']
    except Exception:
        # bit.ly/streamlit-secrets-error 등 비밀키 설정이 없을 때 발생 (로컬/클라우드 초기 상태)
        pass

    # 2. .env 파일 확인 (Secrets에서 못 찾았을 경우)
    if not all([APP_KEY, APP_SECRET, ACCOUNT_NO]):
        env_path = PROJECT_ROOT / ".env"
        if env_path.exists():
            load_dotenv(env_path)
            
            APP_KEY = os.getenv("KIS_APP_KEY")
            APP_SECRET = os.getenv("KIS_APP_SECRET")
            ACCOUNT_NO = os.getenv("KIS_ACCOUNT_NO")
    
    if not all([APP_KEY, APP_SECRET, ACCOUNT_NO]):
        st.warning("⚠️ 실시간 탭을 사용하려면 API 설정이 필요합니다.")
        st.info("Streamlit Cloud 배포 후 [Manage app] > [Settings] > [Secrets]에서 설정해주세요.")
        
        # Secrets 예시 표시
        with st.expander("설정 방법 보기"):
            st.code("""
            [kis]
            APP_KEY = "your_key"
            APP_SECRET = "your_secret"
            ACCOUNT_NO = "your_account"
            """, language="toml")
            
        # 키가 없으면 함수 종료
        return

    # 세션 상태 초기화
    if 'realtime_running' not in st.session_state:
        st.session_state.realtime_running = False
    if 'last_price_data' not in st.session_state:
        st.session_state.last_price_data = None
    if 'last_orderbook' not in st.session_state:
        st.session_state.last_orderbook = None
    
    # 사이드바 설정은 app.py의 tab_realtime 내부에서 처리됨
    # session_state에서 설정값 가져오기
    ticker = st.session_state.get('realtime_ticker', '005930')
    refresh_rate = st.session_state.get('realtime_refresh_rate', 2)
    
    # 버튼 상태 확인
    start_btn = st.session_state.get('realtime_start_clicked', False)
    stop_btn = st.session_state.get('realtime_stop_clicked', False)
    
    if start_btn:
        st.session_state.realtime_running = True
        st.session_state.realtime_start_clicked = False
        st.rerun()
    if stop_btn:
        st.session_state.realtime_running = False
        st.session_state.realtime_stop_clicked = False
        st.rerun()

    # 데이터 조회 함수
    def fetch_data():
        try:
            collector = KISRealtimeCollector(APP_KEY, APP_SECRET, ACCOUNT_NO, is_virtual=False)
            price_data = collector.get_current_price(ticker)
            orderbook = collector.get_orderbook(ticker)
            
            if price_data:
                st.session_state.last_price_data = price_data
            if orderbook:
                st.session_state.last_orderbook = orderbook
                
        except Exception as e:
            st.error(f"API 오류: {e}")

    # 실시간 조회 중이면 데이터 갱신
    if st.session_state.realtime_running:
        fetch_data()

    # 저장된 데이터 표시 (조회 중지해도 유지됨)
    price_data = st.session_state.last_price_data
    orderbook = st.session_state.last_orderbook
    
    if price_data:
        # CSS로 박스 크기 통일 (테마 적응형)
        st.markdown("""
        <style>
        div[data-testid="stMetric"] {
            background-color: var(--background-secondary-color, rgba(128, 128, 128, 0.1));
            padding: 15px;
            border-radius: 10px;
            height: 100px;
            overflow: hidden;
            border: 1px solid var(--border-color, rgba(128, 128, 128, 0.2));
        }
        </style>
        """, unsafe_allow_html=True)
        
        # 변동금액 색상 결정
        change_color = "#ff4b4b" if price_data['change'] > 0 else "#1e88e5" if price_data['change'] < 0 else "#808080"
        change_sign = "+" if price_data['change'] > 0 else ""
        
        # 1행: 현재가 (커스텀), 등락률, 거래량
        row1_col1, row1_col2, row1_col3 = st.columns(3)
        with row1_col1:
            st.markdown(f"""
            <div style="background-color:var(--background-secondary-color, rgba(128, 128, 128, 0.1)); padding:15px; border-radius:10px; height:100px; overflow:hidden; border:1px solid var(--border-color, rgba(128, 128, 128, 0.2));">
                <p style="font-size:0.875rem; color:var(--text-color, inherit); opacity:0.6; margin:0 0 0.25rem 0;">현재가</p>
                <p style="font-size:2.25rem; font-weight:400; margin:0; line-height:1.2;">
                    {price_data['price']:,}원 <span style="color:{change_color}; font-size:1rem;">({change_sign}{price_data['change']:,})</span>
                </p>
            </div>
            """, unsafe_allow_html=True)
        row1_col2.metric("등락률", f"{price_data['change_rate']:+.2f}%")
        row1_col3.metric("거래량", f"{price_data['volume']:,}주")
        
        # 2행: 시가, 고가, 저가
        row2_col1, row2_col2, row2_col3 = st.columns(3)
        row2_col1.metric("시가", f"{price_data['open']:,}원")
        row2_col2.metric("고가", f"{price_data['high']:,}원")
        row2_col3.metric("저가", f"{price_data['low']:,}원")
        
        # 마지막 조회 시간 표시
        st.caption(f"마지막 조회: {price_data['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}")
    
    if orderbook:
        st.subheader("매수/매도 호가")
        
        # 호가 데이터프레임 생성
        asks = pd.DataFrame({
            '가격': orderbook['ask_prices'][::-1],
            '잔량': orderbook['ask_volumes'][::-1],
            'type': '매도'
        })
        bids = pd.DataFrame({
            '가격': orderbook['bid_prices'],
            '잔량': orderbook['bid_volumes'],
            'type': '매수'
        })
        
        df_book = pd.concat([asks, bids])
        
        fig = px.bar(
            df_book, 
            y='가격', 
            x='잔량', 
            color='type', 
            orientation='h',
            color_discrete_map={'매도': '#E53935', '매수': '#1E88E5'},
            title="호가 잔량 (10단계)"
        )
        
        if price_data:
            fig.add_hline(y=price_data['price'], line_dash="dash", line_color="red", annotation_text="현재가")

        fig.update_layout(height=600, yaxis={'categoryorder':'category descending'})
        st.plotly_chart(fig, width='stretch', key=f"orderbook_chart")
    
    # 조회 중이면 자동 갱신
    if st.session_state.realtime_running:
        time.sleep(refresh_rate)
        st.rerun()
    elif not price_data:
        st.info("좌측 사이드바의 '▶️ 실시간 조회 시작' 버튼을 눌러주세요.")
