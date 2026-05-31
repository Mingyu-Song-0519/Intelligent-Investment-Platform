"""
지표 표시 유틸리티 모듈

클린 아키텍처:
- Presentation Layer: Streamlit 메트릭 표시
"""
import logging
import streamlit as st
import pandas as pd
from src.dashboard.utils.data_cache import get_cached_exchange_rate
from src.utils.hints import get_hint_text

logger = logging.getLogger(__name__)


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
            logger.warning(f"환율 표시 실패: {e}")
    
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
