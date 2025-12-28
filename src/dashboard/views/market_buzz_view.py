"""
Market Buzz View - Presentation Layer
Market Heat &  Buzz 탭 UI 렌더링

Features:
- Plotly Treemap 섹터 히트맵
- 거래량 급증 알림 카드
- 관심도 Top 10 Progress Bar
- 동적 Threshold 슬라이더
- "내 성향 맞춤" vs "전체" 토글
- 새로고침 버튼
- 에러 메시지 UI
"""
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from typing import List, Optional, Dict
import logging

from src.services.market_buzz_service import MarketBuzzService
from src.services.profile_aware_buzz_service import ProfileAwareBuzzService
from src.infrastructure.repositories.sector_repository import SectorRepository
from src.domain.market_buzz.entities.buzz_score import BuzzScore
from src.domain.market_buzz.entities.volume_anomaly import VolumeAnomaly
from src.domain.market_buzz.entities.sector_heat import SectorHeat

logger = logging.getLogger(__name__)


def _get_ticker_to_name_map() -> Dict[str, str]:
    """
    Session state에서 티커 -> 한글 이름 매핑 생성
    
    active_stock_list: {"삼성전자 (005930)": "005930", ...}
    → 역매핑: {"005930": "삼성전자", "005930.KS": "삼성전자", ...}
    """
    ticker_to_name = {}
    
    # Session state에서 종목 리스트 가져오기
    stock_list = st.session_state.get('active_stock_list', {})
    
    for display_name, ticker in stock_list.items():
        # "삼성전자 (005930)" → "삼성전자"
        name = display_name.split(' (')[0] if ' (' in display_name else display_name
        
        # 여러 형태로 매핑 (005930, 005930.KS, 005930.KQ)
        ticker_to_name[ticker] = name
        ticker_to_name[f"{ticker}.KS"] = name
        ticker_to_name[f"{ticker}.KQ"] = name
    
    return ticker_to_name


def _get_korean_name(ticker: str, ticker_map: Dict[str, str]) -> str:
    """티커에서 한글 이름 조회"""
    # 1. Session state 매핑에서 조회
    if ticker in ticker_map:
        return ticker_map[ticker]
    
    # 2. .KS/.KQ 제거 후 재시도
    clean_ticker = ticker.split('.')[0]
    if clean_ticker in ticker_map:
        return ticker_map[clean_ticker]
    
    # 3. 티커 그대로 반환
    return ticker


def render_market_buzz_tab():
    """Market Heat & Buzz 탭 메인 렌더링"""
    st.subheader("🔥 Market Heat & Buzz")
    
    # 설명 (접기 가능)
    with st.expander("💡 Market Heat & Buzz란?", expanded=False):
        st.markdown("""
        **Market Heat & Buzz**는 시장에서 **지금 가장 뜨거운 종목**을 찾아주는 기능입니다.
        
        - **Buzz Score**: 거래량 + 변동성 기반 관심도 점수 (0~100)
        - **Volume Anomaly**: 평소 대비 거래량 급증 종목 감지
        - **Sector Heatmap**: 업종별 온도 시각화
        
        **📊 뉴스 감성 분석과의 차이:**
        - 뉴스 감성: "이유(Why)" - 종목에 대한 긍정/부정 판단
        - Market Buzz: "현상(What)" - 지금 어느 종목에 돈이 몰리는지
        """)
    
    # 시장 선택
    col_market, col_refresh = st.columns([3, 1])
    with col_market:
        market = st.selectbox(
            "시장 선택",
            options=["KR", "US"],
            format_func=lambda x: "🇰🇷 한국 (KOSPI/KOSDAQ)" if x == "KR" else "🇺🇸 미국 (S&P 500)",
            key="market_buzz_market"
        )
    
    with col_refresh:
        st.write("")  # Spacing
        force_refresh = st.button("🔄 새로고침", key="buzz_refresh", help="캐시 무시하고 실시간 데이터 조회")
    
    # 서비스 초기화
    try:
        sector_repo = SectorRepository()
        buzz_service = MarketBuzzService(sector_repo)
        profile_buzz_service = ProfileAwareBuzzService(buzz_service)
    except Exception as e:
        st.error(f"❌ 서비스 초기화 실패: {e}")
        logger.error(f"[BuzzView] Service init failed: {e}")
        return
    
    # === 1. 섹터 히트맵 ===
    st.markdown("---")
    st.subheader("📊 섹터 히트맵")
    _render_sector_heatmap(buzz_service, market, force_refresh)
    
    # === 2. 거래량 급증 알림 ===
    st.markdown("---")
    st.subheader("🚀 거래량 급증 종목")
    _render_volume_anomalies(buzz_service, sector_repo, market, force_refresh)
    
    # === 3. 관심도 Top 10 ===
    st.markdown("---")
    _render_top_buzz_stocks(
        buzz_service,
        profile_buzz_service,
        market,
        force_refresh
    )
    
    # === 4. 조회 실패 종목 표시 ===
    failed_tickers = buzz_service.get_failed_tickers()
    if failed_tickers:
        with st.expander(f"⚠️ 조회 실패 종목 ({len(failed_tickers)}개)", expanded=False):
            ticker_map = _get_ticker_to_name_map()
            st.caption("yfinance API에서 데이터를 가져올 수 없는 종목들입니다.")
            
            # 3열로 표시
            cols = st.columns(3)
            for i, ticker in enumerate(failed_tickers):
                name = _get_korean_name(ticker, ticker_map)
                with cols[i % 3]:
                    st.text(f"❌ {name} ({ticker.split('.')[0]})")


def _render_sector_heatmap(
    buzz_service: MarketBuzzService,
    market: str,
    force_refresh: bool
):
    """섹터 히트맵 렌더링 (Finviz 스타일)"""
    try:
        with st.spinner("섹터 데이터 로딩 중..."):
            heatmap = buzz_service.get_sector_heatmap(market, force_refresh)
        
        if not heatmap:
            st.warning("⚠️ 섹터 데이터를 불러올 수 없습니다.")
            return
        
        # 등락률 기준 정렬 (높은 순)
        sorted_heatmap = sorted(heatmap, key=lambda x: x.avg_change_pct, reverse=True)
        
        # 데이터 준비
        labels = []
        parents = []
        values = []
        colors = []
        texts = []
        
        for sector in sorted_heatmap:
            labels.append(sector.sector_name)
            parents.append("")
            values.append(max(sector.stock_count, 3))  # 크기: 종목 수
            colors.append(sector.avg_change_pct)
            # 간결한 텍스트: 섹터명 + 등락률
            texts.append(f"{sector.sector_name}<br>{sector.avg_change_pct:+.2f}%")
        
        # Finviz 스타일 빨강-초록 (선명)
        colorscale = [
            [0.0, '#D32F2F'],   # 진한 빨강
            [0.35, '#EF5350'],  # 빨강
            [0.5, '#424242'],   # 어두운 회색 (0%)
            [0.65, '#66BB6A'], # 초록
            [1.0, '#2E7D32']    # 진한 초록
        ]
        
        fig = go.Figure(go.Treemap(
            labels=labels,
            parents=parents,
            values=values,
            text=texts,
            texttemplate="%{text}",
            textposition="middle center",
            marker=dict(
                colors=colors,
                colorscale=colorscale,
                cmin=-3,
                cmax=3,
                line=dict(color='#212121', width=1),
                showscale=False  # 컬러바 숨김
            ),
            textfont=dict(
                size=13,
                color='white'
            ),
            hovertemplate="<b>%{label}</b><br>등락률: %{color:+.2f}%<br>종목 수: %{value}<extra></extra>",
            pathbar=dict(visible=False)
        ))
        
        fig.update_layout(
            height=400,
            margin=dict(t=0, l=0, r=0, b=0),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)'
        )
        
        st.plotly_chart(fig, key="sector_heatmap", width="stretch")
        
        # 요약 메트릭
        rising = len([s for s in heatmap if s.avg_change_pct > 0])
        falling = len([s for s in heatmap if s.avg_change_pct < 0])
        avg_all = sum(s.avg_change_pct for s in heatmap) / len(heatmap) if heatmap else 0
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("📈 상승", f"{rising}개")
        with col2:
            st.metric("📉 하락", f"{falling}개")
        with col3:
            st.metric("📊 평균", f"{avg_all:+.2f}%")
        
    except Exception as e:
        st.error(f"❌ 히트맵 로딩 실패: {e}")
        logger.error(f"[Heatmap] Error: {e}")


def _render_volume_anomalies(
    buzz_service: MarketBuzzService,
    sector_repo: SectorRepository,
    market: str,
    force_refresh: bool
):
    """거래량 급증 종목 알림 카드 렌더링"""
    # Threshold 슬라이더 (동적 조정 가능)
    col1, col2 = st.columns([3, 1])
    with col1:
        threshold = st.slider(
            "거래량 급증 민감도",
            min_value=1.5,
            max_value=5.0,
            value=2.0,
            step=0.5,
            key="volume_threshold",
            help="낮을수록 민감 (더 많은 종목 감지), 높을수록 보수적 (급등만 감지)"
        )
    
    with col2:
        st.metric("현재 임계값", f"{threshold:.1f}x")
    
    try:
        # 전체 종목 조회 (상위 100개만)
        all_tickers = sector_repo.get_all_tickers(market)[:100]
        
        with st.spinner(f"거래량 이상 감지 중... (검사 종목: {len(all_tickers)}개)"):
            anomalies = buzz_service.detect_volume_anomalies(
                tickers=all_tickers,
                threshold=threshold
            )
        
        if not anomalies:
            st.info("📊 현재 거래량 급증 종목이 없습니다. (민감도를 낮춰보세요)")
            return
        
        # 한글 이름 매핑 가져오기
        ticker_map = _get_ticker_to_name_map()
        
        # 상위 5개만 카드 형태로 표시
        st.caption(f"총 {len(anomalies)}개 감지됨 (상위 5개 표시)")
        
        for i, anomaly in enumerate(anomalies[:5]):
            # 한글 이름 조회
            display_name = _get_korean_name(anomaly.ticker, ticker_map)
            
            with st.container():
                cols = st.columns([1, 3, 2, 2])
                
                with cols[0]:
                    # 순위
                    st.markdown(f"### {i+1}")
                
                with cols[1]:
                    # 종목명 + 알림 메시지 (한글 이름 사용)
                    st.markdown(f"**{display_name}** `{anomaly.ticker.split('.')[0]}`")
                    st.caption(anomaly.get_alert_message())
                
                with cols[2]:
                    # 거래량 비율
                    st.metric(
                        "거래량 비율",
                        f"{anomaly.volume_ratio:.1f}x",
                        delta=f"+{anomaly.volume_increase_pct:.0f}%"
                    )
                
                with cols[3]:
                    # 등락률
                    st.metric(
                        "당일 등락률",
                        f"{anomaly.price_change_pct:+.1f}%",
                        delta=None
                    )
                
                st.markdown("---")
        
    except Exception as e:
        st.error(f"❌ 거래량 이상 감지 실패: {e}")
        logger.error(f"[VolumeAnomaly] Rendering failed: {e}")


def _render_top_buzz_stocks(
    buzz_service: MarketBuzzService,
    profile_buzz_service: ProfileAwareBuzzService,
    market: str,
    force_refresh: bool
):
    """관심도 Top 10 렌더링 (Progress Bar + 프로필 토글)"""
    st.subheader("⚡ 관심 급상승 종목 Top 10")
    
    # 프로필 토글
    col1, col2 = st.columns([3, 1])
    
    with col1:
        use_profile = st.checkbox(
            "🎯 내 투자 성향에 맞는 종목만 보기",
            value=False,
            key="buzz_profile_toggle",
            help="Phase 20 투자 성향 프로필 기반 필터링 (변동성, 선호 섹터 고려)"
        )
    
    with col2:
        top_n = st.number_input(
            "표시 개수",
            min_value=5,
            max_value=20,
            value=10,
            step=5,
            key="buzz_top_n"
        )
    
    # 사용자 ID (Session state에서 가져오기)
    user_email = st.session_state.get("user_email", None)
    
    if use_profile and not user_email:
        st.warning("⚠️ 투자 성향 필터링을 사용하려면 먼저 사이드바에서 이메일을 입력해주세요.")
        use_profile = False
    
    # 프로필 요약 표시 (토글 ON 시)
    if use_profile and user_email:
        profile_summary = profile_buzz_service.get_profile_summary(user_email)
        if profile_summary:
            with st.expander("👤 내 투자 성향", expanded=False):
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("위험 감수 성향", profile_summary['risk_tolerance'])
                    st.caption(f"점수: {profile_summary['risk_value']}/100")
                with col2:
                    st.write("**선호 섹터:**")
                    for sector in profile_summary.get('preferred_sectors', []):
                        st.write(f"- {sector}")
        else:
            st.info("ℹ️ 투자 성향 프로필이 없습니다. '투자 성향 진단' 탭에서 먼저 진단해주세요.")
            use_profile = False
    
    # Buzz 종목 조회
    try:
        with st.spinner("관심 종목 분석 중..."):
            if use_profile and user_email:
                # 프로필 기반 맞춤 조회
                buzz_stocks = profile_buzz_service.get_personalized_buzz_stocks(
                    user_id=user_email,
                    market=market,
                    top_n=top_n,
                    force_refresh=force_refresh
                )
                st.success(f"✅ {user_email}님의 투자 성향에 맞는 종목 {len(buzz_stocks)}개 선별")
            else:
                # 전체 조회
                buzz_stocks = buzz_service.get_top_buzz_stocks(
                    market=market,
                    top_n=top_n,
                    force_refresh=force_refresh
                )
        
        if not buzz_stocks:
            st.warning("⚠️ 관심 종목 데이터를 불러올 수 없습니다.")
            return
        
        # 한글 이름 매핑 가져오기
        ticker_map = _get_ticker_to_name_map()
        
        # Progress Bar 형태로 표시
        for i, buzz in enumerate(buzz_stocks):
            # 한글 이름 조회
            display_name = _get_korean_name(buzz.ticker, ticker_map)
            
            with st.container():
                # 순위 + 종목 정보
                cols = st.columns([1, 4, 2, 2])
                
                with cols[0]:
                    st.markdown(f"### {i+1}")
                
                with cols[1]:
                    # 한글 이름 사용
                    st.markdown(f"**{display_name}** `{buzz.ticker.split('.')[0]}`")
                    if buzz.sector:
                        st.caption(f"섹터: {buzz.sector}")
                
                with cols[2]:
                    # Heat Level 뱃지
                    if buzz.heat_level == "HOT":
                        st.error(f"🔥 {buzz.heat_level}")
                    elif buzz.heat_level == "WARM":
                        st.warning(f"🌤️ {buzz.heat_level}")
                    else:
                        st.info(f"❄️ {buzz.heat_level}")
                
                with cols[3]:
                    # 최종 점수
                    if buzz.profile_fit_score is not None:
                        # 프로필 적합도 포함
                        st.metric("최종 점수", f"{buzz.final_score:.0f}", delta=f"적합도 +{buzz.profile_fit_score:.0f}")
                    else:
                        st.metric("Buzz 점수", f"{buzz.base_score:.0f}")
                
                # Progress Bar
                st.progress(buzz.final_score / 100)
                
                # 상세 정보 (접기 가능)
                with st.expander("📊 상세 정보"):
                    detail_cols = st.columns(3)
                    with detail_cols[0]:
                        st.metric("거래량 비율", f"{buzz.volume_ratio:.2f}x")
                    with detail_cols[1]:
                        st.metric("변동성 비율", f"{buzz.volatility_ratio:.2f}x")
                    with detail_cols[2]:
                        st.caption(f"최종 업데이트: {buzz.last_updated.strftime('%Y-%m-%d %H:%M')}")
                
                st.markdown("---")
        
    except Exception as e:
        st.error(f"❌ 관심 종목 조회 실패: {e}")
        logger.error(f"[TopBuzz] Rendering failed: {e}")
