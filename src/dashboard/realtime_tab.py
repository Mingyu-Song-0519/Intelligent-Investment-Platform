import streamlit as st
import pandas as pd
import plotly.express as px
import time
from pathlib import Path
import os
import sys

# 프로젝트 루트 경로 설정
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.collectors.kis_realtime_collector import KISRealtimeCollector

def display_realtime_data():
    """실시간 시세 탭 (REST API 기반)"""
    st.header("🔴 실시간 시세 (한국투자증권)")

    # API 키 확인
    import os
    env_path = PROJECT_ROOT / ".env"
    from dotenv import load_dotenv
    if env_path.exists():
        load_dotenv(env_path)
    
    APP_KEY = os.getenv("KIS_APP_KEY")
    APP_SECRET = os.getenv("KIS_APP_SECRET")
    ACCOUNT_NO = os.getenv("KIS_ACCOUNT_NO")
    
    if not all([APP_KEY, APP_SECRET, ACCOUNT_NO]):
        st.error("⚠️ `.env` 파일에 한국투자증권 API 설정이 필요합니다.")
        st.code("""
        KIS_APP_KEY=your_key
        KIS_APP_SECRET=your_secret
        KIS_ACCOUNT_NO=your_account
        """, language="properties")
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
