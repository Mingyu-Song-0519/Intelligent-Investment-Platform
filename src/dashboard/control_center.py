"""
Investment Control Center - Phase 13 (수정됨)
투자 컨트롤 센터 (통합 대시보드)

모든 분석을 한눈에: 시장 체력, 변동성, 팩터 TOP 5, 매크로 환경
"""
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from typing import Dict, List
import pandas as pd
from datetime import datetime


def render_control_center():
    """
    투자 컨트롤 센터 메인 뷰
    
    4분할 레이아웃:
    ┌─────────────────┬─────────────────┐
    │  📊 시장 체력    │  😱 변동성      │
    ├─────────────────┼─────────────────┤
    │  🏆 팩터 TOP 5   │  🌍 매크로 환경  │
    └─────────────────┴─────────────────┘
    """
    st.title("🎯 투자 컨트롤 센터")
    st.markdown("---")
    
    # 4분할 레이아웃
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📊 시장 체력 (Market Breadth)")
        render_market_health()
    
    with col2:
        st.subheader("😱 변동성 스트레스 (VIX)")
        render_volatility_stress()
    
    st.markdown("---")
    
    col3, col4 = st.columns(2)
    
    with col3:
        st.subheader("🏆 팩터 스코어 TOP 5")
        render_factor_top5()
    
    with col4:
        st.subheader("🌍 매크로 환경")
        render_macro_summary()


def render_market_health():
    """시장 체력 위젯 (Phase 9-1)"""
    try:
        from src.analyzers.market_breadth import MarketBreadthAnalyzer
        
        analyzer = MarketBreadthAnalyzer()
        
        # 실제 메서드: get_breadth_summary() 사용
        breadth_summary = analyzer.get_breadth_summary()
        
        # advance_decline 정보 추출
        ad_data = breadth_summary.get("advance_decline", {})
        ad_ratio = ad_data.get("ratio", 0)
        
        # 상승/하락 종목 수
        advancing = ad_data.get("advancing", 0)
        declining = ad_data.get("declining", 0)
        unchanged = ad_data.get("unchanged", 0)
        total = advancing + declining + unchanged
        
        # 색상 코드 (글씨 색상 포함)
        if ad_ratio > 1.5:
            color = "🟢"
            status = "강세"
            bg_color = "#e8f5e9"
            text_color = "#1b5e20"  # 진한 녹색
        elif ad_ratio > 0.8:
            color = "🟡"
            status = "중립"
            bg_color = "#fff9c4"
            text_color = "#f57f17"  # 진한 노랑/주황
        else:
            color = "🔴"
            status = "약세"
            bg_color = "#ffebee"
            text_color = "#c62828"  # 진한 빨강
        
        # 메트릭 표시
        st.markdown(f"""
        <div style="background-color: {bg_color}; padding: 20px; border-radius: 10px;">
            <h2 style="text-align: center; color: {text_color};">{color} {status}</h2>
            <p style="text-align: center; font-size: 24px; font-weight: bold; color: {text_color};">
                A/D Ratio: {ad_ratio:.2f}
            </p>
            <p style="text-align: center; color: #666;">
                상승 {advancing} | 하락 {declining} (총 {total})
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        # 간단한 차트
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=["상승", "하락"],
            y=[advancing, declining],
            marker_color=["#4caf50", "#f44336"]
        ))
        fig.update_layout(
            height=200,
            margin=dict(l=20, r=20, t=20, b=20),
            showlegend=False
        )
        st.plotly_chart(fig, use_container_width=True)
        
    except Exception as e:
        st.error(f"시장 체력 데이터 로드 실패: {e}")


def render_volatility_stress():
    """변동성 스트레스 위젯 (Phase 9-1)"""
    try:
        from src.analyzers.volatility_analyzer import VolatilityAnalyzer
        
        analyzer = VolatilityAnalyzer()
        vix = analyzer.get_current_vix()
        
        # 실제 메서드: volatility_regime() - 튜플 반환 (regime, color)
        if vix:
            regime, _ = analyzer.volatility_regime()
        else:
            regime = "알 수 없음"
        
        # 색상 코드 (글씨 색상 포함)
        if "저변동성" in regime:
            color = "🟢"
            bg_color = "#e8f5e9"
            text_color = "#1b5e20"  # 진한 녹색
        elif "중간" in regime or "중변동성" in regime:
            color = "🟡"
            bg_color = "#fff9c4"
            text_color = "#f57f17"  # 진한 노랑/주황
        else:
            color = "🔴"
            bg_color = "#ffebee"
            text_color = "#c62828"  # 진한 빨강
        
        # VIX 값 포맷팅
        vix_display = f"{vix:.2f}" if vix is not None else "N/A"
        
        # 메트릭
        st.markdown(f"""
        <div style="background-color: {bg_color}; padding: 20px; border-radius: 10px;">
            <h2 style="text-align: center; color: {text_color};">{color} {regime}</h2>
            <p style="text-align: center; font-size: 32px; font-weight: bold; color: {text_color};">
                VIX: {vix_display}
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        # VIX 히스토리 차트 (실제 메서드: get_vix_data)
        vix_history = analyzer.get_vix_data(period="1mo")
        
        if vix_history is not None and not vix_history.empty:
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=vix_history['date'] if 'date' in vix_history.columns else vix_history.index,
                y=vix_history['close'],
                mode='lines',
                fill='tozeroy',
                line=dict(color='#ff9800', width=2)
            ))
            
            # 임계선
            fig.add_hline(y=20, line_dash="dash", line_color="red", annotation_text="공포")
            fig.add_hline(y=12, line_dash="dash", line_color="green", annotation_text="안정")
            
            fig.update_layout(
                height=200,
                margin=dict(l=20, r=20, t=20, b=20),
                showlegend=False,
                xaxis_title="",
                yaxis_title="VIX"
            )
            st.plotly_chart(fig, use_container_width=True)
        
    except Exception as e:
        st.error(f"VIX 데이터 로드 실패: {e}")


def render_factor_top5():
    """팩터 스코어 TOP 5 위젯 (Phase 11)"""
    try:
        from src.analyzers.factor_analyzer import FactorScreener
        from src.infrastructure.repositories.stock_repository import YFinanceStockRepository
        
        # DI
        repo = YFinanceStockRepository()
        screener = FactorScreener(stock_repo=repo, market="US")
        
        # 유명 종목 스크리닝 (캐싱 필요)
        if "factor_top5_cache" not in st.session_state:
            with st.spinner("팩터 분석 중..."):
                popular_tickers = [
                    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA",
                    "TSLA", "META", "BRK-B", "JPM", "V",
                    "JNJ", "WMT", "PG", "MA", "HD"
                ]
                top_stocks = screener.screen_top_stocks(popular_tickers, top_n=5)
                st.session_state["factor_top5_cache"] = top_stocks
        
        top_stocks = st.session_state.get("factor_top5_cache", [])
        
        if top_stocks:
            # 표 형식
            data = []
            for i, scores in enumerate(top_stocks, 1):
                data.append({
                    "순위": f"{i}위",
                    "티커": scores.ticker,
                    "종합": f"{scores.composite:.1f}",
                    "모멘텀": f"{scores.momentum:.0f}",
                    "가치": f"{scores.value:.0f}",
                    "품질": f"{scores.quality:.0f}"
                })
            
            df = pd.DataFrame(data)
            st.dataframe(df, use_container_width=True, hide_index=True)
            
            # 레이더 차트 (1위 종목)
            best = top_stocks[0]
            
            fig = go.Figure()
            fig.add_trace(go.Scatterpolar(
                r=[best.momentum, best.value, best.quality, best.size, best.volatility],
                theta=['모멘텀', '가치', '품질', '규모', '저변동성'],
                fill='toself',
                name=best.ticker
            ))
            
            fig.update_layout(
                polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
                height=250,
                margin=dict(l=20, r=20, t=40, b=20),
                title=f"🥇 {best.ticker} 팩터 프로필"
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # 새로고침 버튼
            if st.button("🔄 팩터 스코어 새로고침", key="refresh_factor"):
                del st.session_state["factor_top5_cache"]
                st.rerun()
        
    except Exception as e:
        st.error(f"팩터 분석 실패: {e}")


def render_macro_summary():
    """매크로 환경 요약 (Phase 9-6) - 수정됨"""
    try:
        from src.analyzers.macro_analyzer import MacroAnalyzer
        
        analyzer = MacroAnalyzer()
        macro_data = analyzer.get_macro_summary()
        
        if macro_data:
            # 금리 (실제 구조: treasury_yields -> us_10y)
            treasury_yields = macro_data.get("treasury_yields", {})
            us_10y_data = treasury_yields.get("us_10y", {})
            rate = us_10y_data.get("current")
            change_pct = us_10y_data.get("change_pct", 0)
            trend = f"+{change_pct:.2f}%" if change_pct > 0 else f"{change_pct:.2f}%" if change_pct != 0 else "→"
            
            st.metric(
                label="🇺🇸 미국 10년물 금리",
                value=f"{rate:.2f}%" if rate else "N/A",
                delta=trend if rate else None
            )
            
            # 달러 인덱스 (실제 구조: dollar_strength -> dxy)
            dollar_strength = macro_data.get("dollar_strength", {})
            dxy_data = dollar_strength.get("dxy", {})
            dxy = dxy_data.get("current")
            
            st.metric(
                label="💵 달러 인덱스 (DXY)",
                value=f"{dxy:.2f}" if dxy else "N/A"
            )
            
            # USD/KRW (실제 구조: dollar_strength -> usd_krw)
            usdkrw_data = dollar_strength.get("usd_krw", {})
            krw = usdkrw_data.get("current")
            
            st.metric(
                label="🇰🇷 USD/KRW",
                value=f"₩{krw:.0f}" if krw else "N/A"
            )
            
            # VIX (실제 구조: vix)
            vix_data = macro_data.get("vix", {})
            vix = vix_data.get("current")
            
            st.metric(
                label="😱 VIX (공포 지수)",
                value=f"{vix:.2f}" if vix else "N/A"
            )
            
            # 전체 해석
            environment = macro_data.get("environment", "분석 중...")
            yield_interp = treasury_yields.get("interpretation", "")
            dollar_interp = dollar_strength.get("interpretation", "")
            
            st.markdown("---")
            st.markdown(f"**📝 종합 해석**")
            st.info(f"{environment}\n\n금리: {yield_interp}\n달러: {dollar_interp}")
        
    except Exception as e:
        st.error(f"매크로 데이터 로드 실패: {e}")


# 탭에서 호출할 메인 함수
def show_control_center():
    """앱에서 호출"""
    # 배경색 설정
    st.markdown("""
    <style>
    .block-container {
        padding-top: 2rem;
    }
    </style>
    """, unsafe_allow_html=True)
    
    render_control_center()
    
    # 마지막 업데이트 시간
    st.markdown("---")
    st.caption(f"⏰ 마지막 업데이트: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
