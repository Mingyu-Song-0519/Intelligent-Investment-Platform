"""
Investment Control Center - Phase 13
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
        
        # 시장 폭 점수 계산
        breadth_score = analyzer.calculate_market_breadth_score()
        ad_ratio = breadth_score.get("advance_decline_ratio", 0)
        
        # 상승/하락 비율
        advancing = breadth_score.get("advancing_stocks", 0)
        declining = breadth_score.get("declining_stocks", 0)
        total = advancing + declining
        
        # 색상 코드
        if ad_ratio > 1.5:
            color = "🟢"
            status = "강세"
            bg_color = "#e8f5e9"
        elif ad_ratio > 0.8:
            color = "🟡"
            status = "중립"
            bg_color = "#fff9c4"
        else:
            color = "🔴"
            status = "약세"
            bg_color = "#ffebee"
        
        # 메트릭 표시
        st.markdown(f"""
        <div style="background-color: {bg_color}; padding: 20px; border-radius: 10px;">
            <h2 style="text-align: center;">{color} {status}</h2>
            <p style="text-align: center; font-size: 24px; font-weight: bold;">
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
        regime = analyzer.get_volatility_regime(vix) if vix else "알 수 없음"
        
        # 색상 코드
        if "저변동성" in regime:
            color = "🟢"
            bg_color = "#e8f5e9"
        elif "중간" in regime:
            color = "🟡"
            bg_color = "#fff9c4"
        else:
            color = "🔴"
            bg_color = "#ffebee"
        
        # 메트릭
        st.markdown(f"""
        <div style="background-color: {bg_color}; padding: 20px; border-radius: 10px;">
            <h2 style="text-align: center;">{color} {regime}</h2>
            <p style="text-align: center; font-size: 32px; font-weight: bold;">
                VIX: {vix:.2f if vix else 'N/A'}
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        # VIX 히스토리 차트
        vix_history = analyzer.get_vix_history(days=30)
        
        if vix_history is not None and not vix_history.empty:
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=vix_history.index,
                y=vix_history['Close'],
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
    """매크로 환경 요약 (Phase 9-6)"""
    try:
        from src.analyzers.macro_analyzer import MacroAnalyzer
        
        analyzer = MacroAnalyzer()
        macro_data = analyzer.get_macro_summary()
        
        if macro_data:
            # 금리
            treasury_10y = macro_data.get("treasury_10y", {})
            rate = treasury_10y.get("current")
            trend = treasury_10y.get("trend", "→")
            
            st.metric(
                label="🇺🇸 미국 10년물 금리",
                value=f"{rate:.2f}%" if rate else "N/A",
                delta=trend
            )
            
            # 달러 인덱스
            dollar_idx = macro_data.get("dollar_index", {})
            dxy = dollar_idx.get("current")
            
            st.metric(
                label="💵 달러 인덱스 (DXY)",
                value=f"{dxy:.2f}" if dxy else "N/A"
            )
            
            # USD/KRW
            usdkrw = macro_data.get("usdkrw", {})
            krw = usdkrw.get("current")
            
            st.metric(
                label="🇰🇷 USD/KRW",
                value=f"₩{krw:.0f}" if krw else "N/A"
            )
            
            # VIX
            vix_data = macro_data.get("vix", {})
            vix = vix_data.get("current")
            
            st.metric(
                label="😱 VIX (공포 지수)",
                value=f"{vix:.2f}" if vix else "N/A"
            )
            
            # 전체 해석
            interpretation = macro_data.get("interpretation", "데이터 분석 중...")
            
            st.markdown("---")
            st.markdown(f"**📝 종합 해석**")
            st.info(interpretation)
        
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
