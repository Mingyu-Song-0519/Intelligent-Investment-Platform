"""
관심 종목(Watchlist) UI 뷰
Presentation Layer: Streamlit 기반 사용자 인터페이스
"""
import streamlit as st
import plotly.graph_objects as go
import logging
from typing import List, Optional

from src.domain.watchlist import WatchlistSummary, HeatLevel
from src.services.watchlist_service import WatchlistService
from src.infrastructure.repositories.watchlist_repository import SQLiteWatchlistRepository

logger = logging.getLogger(__name__)


def render_watchlist_tab():
    """관심 종목 탭 렌더링"""
    st.header("⭐ 관심 종목")
    
    # 서비스 초기화
    service = _get_watchlist_service()
    user_id = _get_user_id()
    
    # 상단 컨트롤
    col1, col2, col3 = st.columns([3, 1, 1])
    
    with col1:
        st.info("👈 **맞춤 종목 순위**에서 '관심 종목 추가' 버튼으로 종목을 추가할 수 있습니다.")
    
    with col2:
        if st.button("🔄 새로고침", use_container_width=True):
            st.rerun()
    
    with col3:
        if st.button("➕ 직접 추가", use_container_width=True):
            st.session_state.show_add_dialog = True
    
    # 직접 추가 다이얼로그
    if st.session_state.get('show_add_dialog', False):
        _render_add_dialog(service, user_id)
    
    # 관심 종목 로드
    with st.spinner("관심 종목 로딩 중..."):
        summaries = service.get_watchlist_with_prices(user_id)
    
    if not summaries:
        st.warning("📭 관심 종목이 없습니다. 맞춤 종목 순위에서 종목을 추가해보세요!")
        return
    
    # 필터 및 정렬 옵션
    filtered_summaries = _render_filter_controls(summaries)
    
    # 요약 통계
    _render_statistics(service, user_id)
    
    # 등락률 차트
    _render_change_chart(filtered_summaries)
    
    # 종목 테이블
    _render_watchlist_table(filtered_summaries, service, user_id)


def _get_watchlist_service() -> WatchlistService:
    """서비스 인스턴스 생성"""
    # 세션 캐싱 제거 - 매번 새로 생성하여 프로필 변경 반영
    repo = SQLiteWatchlistRepository()
    
    # Phase 20/21 서비스 연동 시도
    profile_repo = None
    buzz_service = None
    
    try:
        from src.infrastructure.repositories.profile_repository import SQLiteProfileRepository
        profile_repo = SQLiteProfileRepository()
        logger.info(f"[Watchlist] ProfileRepo loaded: {profile_repo}")
    except ImportError as e:
        logger.warning(f"[Watchlist] ProfileRepo import failed: {e}")
    except Exception as e:
        logger.warning(f"[Watchlist] ProfileRepo init failed: {e}")
    
    try:
        from src.services.market_buzz_service import MarketBuzzService
        from src.infrastructure.repositories.sector_repository import SectorRepository
        sector_repo = SectorRepository()
        buzz_service = MarketBuzzService(sector_repo)  # sector_repo만 전달
    except ImportError:
        pass
    except Exception as e:
        logger.warning(f"MarketBuzzService 초기화 실패: {e}")
    
    return WatchlistService(
        watchlist_repo=repo,
        profile_repo=profile_repo,
        buzz_service=buzz_service
    )


def _get_user_id() -> str:
    """사용자 ID 획득"""
    return st.session_state.get('user_id', 'default_user')


def _render_add_dialog(service: WatchlistService, user_id: str):
    """종목 직접 추가 다이얼로그"""
    with st.expander("➕ 종목 직접 추가", expanded=True):
        col1, col2 = st.columns(2)
        
        with col1:
            ticker = st.text_input(
                "종목 코드",
                placeholder="예: 005930.KS, AAPL",
                key="add_ticker"
            )
        
        with col2:
            stock_name = st.text_input(
                "종목명",
                placeholder="예: 삼성전자, Apple",
                key="add_name"
            )
        
        market = st.radio(
            "시장",
            options=["🇰🇷 한국", "🇺🇸 미국"],
            horizontal=True,
            key="add_market"
        )
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("✅ 추가", use_container_width=True):
                if ticker and stock_name:
                    try:
                        market_code = "KR" if "한국" in market else "US"
                        service.add_to_watchlist(user_id, ticker, stock_name, market_code)
                        st.success(f"✅ {stock_name}을(를) 추가했습니다!")
                        st.session_state.show_add_dialog = False
                        st.rerun()
                    except ValueError as e:
                        st.error(str(e))
                else:
                    st.warning("종목 코드와 종목명을 입력하세요.")
        
        with col2:
            if st.button("❌ 취소", use_container_width=True):
                st.session_state.show_add_dialog = False
                st.rerun()


def _render_filter_controls(summaries: List[WatchlistSummary]) -> List[WatchlistSummary]:
    """필터 및 정렬 컨트롤"""
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        sort_by = st.selectbox(
            "정렬 기준",
            options=["추가일", "등락률", "Buzz 점수", "성향 적합도"],
            key="watchlist_sort"
        )
    
    with col2:
        sort_order = st.radio(
            "순서",
            options=["내림차순", "오름차순"],
            horizontal=True,
            key="watchlist_order"
        )
    
    with col3:
        market_filter = st.selectbox(
            "시장",
            options=["전체", "🇰🇷 한국", "🇺🇸 미국"],
            key="watchlist_market"
        )
    
    # 필터링
    filtered = summaries
    if market_filter == "🇰🇷 한국":
        filtered = [s for s in filtered if s.item.market == 'KR']
    elif market_filter == "🇺🇸 미국":
        filtered = [s for s in filtered if s.item.market == 'US']
    
    # 정렬
    reverse = (sort_order == "내림차순")
    
    if sort_by == "등락률":
        filtered.sort(key=lambda x: x.change_pct, reverse=reverse)
    elif sort_by == "Buzz 점수":
        filtered.sort(key=lambda x: x.buzz_score or 0, reverse=reverse)
    elif sort_by == "성향 적합도":
        filtered.sort(key=lambda x: x.profile_fit_score or 0, reverse=reverse)
    else:  # 추가일
        filtered.sort(key=lambda x: x.item.added_at, reverse=reverse)
    
    return filtered


def _render_statistics(service: WatchlistService, user_id: str):
    """요약 통계"""
    stats = service.get_watchlist_statistics(user_id)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("📋 총 종목", f"{stats['total_count']}개")
    
    with col2:
        st.metric("📈 상승", f"{stats['rising_count']}개", delta="상승")
    
    with col3:
        st.metric("📉 하락", f"{stats['falling_count']}개", delta="하락", delta_color="inverse")
    
    with col4:
        avg_change = stats['avg_change_pct']
        delta_color = "normal" if avg_change >= 0 else "inverse"
        st.metric("📊 평균 등락률", f"{avg_change:+.2f}%")


def _render_change_chart(summaries: List[WatchlistSummary]):
    """등락률 바 차트"""
    if not summaries:
        return
    
    with st.expander("📊 등락률 차트", expanded=True):
        names = [s.item.stock_name for s in summaries]
        changes = [s.change_pct for s in summaries]
        colors = ['#4CAF50' if c >= 0 else '#F44336' for c in changes]
        
        fig = go.Figure(data=[
            go.Bar(
                x=names,
                y=changes,
                marker_color=colors,
                text=[f"{c:+.2f}%" for c in changes],
                textposition='auto'
            )
        ])
        
        fig.update_layout(
            height=300,
            margin=dict(t=20, l=20, r=20, b=40),
            xaxis_title="",
            yaxis_title="등락률 (%)",
            showlegend=False,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)'
        )
        
        st.plotly_chart(fig, key="watchlist_chart", use_container_width=True)


def _render_watchlist_table(
    summaries: List[WatchlistSummary],
    service: WatchlistService,
    user_id: str
):
    """관심 종목 테이블"""
    st.subheader("📋 상세 목록")
    
    # 컬럼 설명 (도움말)
    with st.expander("📖 컬럼 설명", expanded=False):
        st.markdown("""
| 컬럼 | 설명 |
|------|------|
| **종목명** | 종목 이름과 티커 코드 (🇰🇷 한국 / 🇺🇸 미국) |
| **현재가** | 실시간 또는 지연 시세 (한국: 원, 미국: 달러) |
| **등락률** | 전일 대비 가격 변동률 |
| **RSI** | 상대강도지수 (30 이하: 과매도 🟢, 70 이상: 과매수 🔴) |
| **Buzz** | 시장 관심도 점수 (🔥 HOT / 🌤️ WARM / ❄️ COLD) |
| **적합도** | 내 투자 성향과의 적합도 (🟢 70+ / 🟡 40-70 / 🔴 40-) |
""")
    
    # 헤더 행
    header_cols = st.columns([2, 1.5, 1, 1, 1, 1, 0.5])
    with header_cols[0]:
        st.caption("**종목명**")
    with header_cols[1]:
        st.caption("**현재가**")
    with header_cols[2]:
        st.caption("**등락률**")
    with header_cols[3]:
        st.caption("**RSI**")
    with header_cols[4]:
        st.caption("**Buzz**")
    with header_cols[5]:
        st.caption("**적합도**")
    with header_cols[6]:
        st.caption("")
    
    st.divider()
    
    for i, summary in enumerate(summaries):
        with st.container():
            cols = st.columns([2, 1.5, 1, 1, 1, 1, 0.5])
            
            # 종목명 + 시장
            with cols[0]:
                market_emoji = "🇰🇷" if summary.item.market == "KR" else "🇺🇸"
                st.markdown(f"**{market_emoji} {summary.item.stock_name}**")
                st.caption(summary.item.ticker)
            
            # 현재가
            with cols[1]:
                if summary.current_price > 0:
                    price_str = f"{summary.current_price:,.0f}" if summary.item.market == "KR" else f"${summary.current_price:,.2f}"
                    st.markdown(f"**{price_str}**")
                else:
                    st.markdown("**-**")
            
            # 등락률
            with cols[2]:
                change_color = "green" if summary.change_pct >= 0 else "red"
                st.markdown(
                    f"<span style='color:{change_color}'><b>{summary.change_pct:+.2f}%</b></span>",
                    unsafe_allow_html=True
                )
            
            # RSI
            with cols[3]:
                if summary.rsi:
                    rsi_color = "#4CAF50" if summary.rsi < 30 else ("#F44336" if summary.rsi > 70 else "#808080")
                    st.markdown(
                        f"<span style='color:{rsi_color}'>{summary.rsi:.0f}</span>",
                        unsafe_allow_html=True
                    )
                else:
                    st.markdown("-")
            
            # Buzz / Heat Level
            with cols[4]:
                if summary.buzz_score:
                    heat_emoji = summary.heat_emoji
                    st.markdown(f"{heat_emoji} {summary.buzz_score:.0f}")
                elif summary.volume_anomaly:
                    st.markdown("📈 급등")
                else:
                    st.markdown("-")
            
            # 성향 적합도
            with cols[5]:
                if summary.profile_fit_score:
                    fit_color = summary.profile_fit_color
                    st.markdown(
                        f"<span style='color:{fit_color}'>{summary.profile_fit_score:.0f}</span>",
                        unsafe_allow_html=True
                    )
                else:
                    st.markdown("-")
            
            # 삭제 버튼
            with cols[6]:
                if st.button("🗑️", key=f"delete_{summary.item.ticker}_{i}"):
                    service.remove_from_watchlist(user_id, summary.item.ticker)
                    st.success(f"✅ {summary.item.stock_name} 삭제됨")
                    st.rerun()
            
            # 경고 메시지
            if summary.profile_warning:
                st.caption(summary.profile_warning)
            
            st.divider()


# ==================== 사이드바 위젯 ====================

def render_watchlist_sidebar_widget():
    """사이드바 관심 종목 위젯"""
    service = _get_watchlist_service()
    user_id = _get_user_id()
    
    with st.expander("⭐ 관심 종목", expanded=False):
        items = service.get_watchlist(user_id)
        
        if not items:
            st.caption("관심 종목이 없습니다.")
            return
        
        st.caption(f"총 {len(items)}개")
        
        # 간략 목록 (최대 5개)
        for item in items[:5]:
            market_emoji = "🇰🇷" if item.market == "KR" else "🇺🇸"
            st.text(f"{market_emoji} {item.stock_name}")
        
        if len(items) > 5:
            st.caption(f"...외 {len(items) - 5}개")
