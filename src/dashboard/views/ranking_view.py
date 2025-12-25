"""
종목 순위 UI 뷰
맞춤 종목 추천 및 순위 표시

Clean Architecture: Presentation Layer
"""
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from typing import List

from src.services.recommendation_service import RecommendationService
from src.services.profile_assessment_service import ProfileAssessmentService
from src.domain.investment_profile.entities.recommendation import RankedStock, Recommendation
from src.domain.investment_profile.entities.investor_profile import InvestorProfile
from src.infrastructure.repositories.profile_repository import SQLiteProfileRepository
from src.infrastructure.repositories.question_repository import YAMLQuestionRepository


@st.cache_resource
def get_services():
    """서비스 인스턴스 생성 (캐싱)"""
    profile_repo = SQLiteProfileRepository()
    question_repo = YAMLQuestionRepository()
    
    assessment_service = ProfileAssessmentService(profile_repo, question_repo)
    recommendation_service = RecommendationService(profile_repo, use_ai_model=True)
    
    return assessment_service, recommendation_service


def show_ranking_page():
    """맞춤 종목 순위 페이지"""
    st.header("🏆 나의 맞춤 종목 순위")
    
    user_id = st.session_state.get('user_id', 'default_user')
    assessment_service, recommendation_service = get_services()
    
    # 프로필 확인
    profile = assessment_service.get_profile(user_id)
    
    if not profile:
        st.warning("⚠️ 투자 성향 진단이 필요합니다.")
        if st.button("📊 성향 진단하기", use_container_width=True):
            st.session_state.page = "assessment"
            st.rerun()
        return
    
    # 프로필 요약
    _show_profile_summary(profile)
    
    st.divider()
    
    # 순위 생성
    with st.spinner("맞춤 종목 분석 중..."):
        ranked_stocks = recommendation_service.get_ranked_stocks(profile, top_n=10)
    
    # 순위 표시
    _show_ranking_chart(ranked_stocks)
    _show_ranking_table(ranked_stocks, recommendation_service, user_id)


def _show_profile_summary(profile: InvestorProfile):
    """프로필 요약 표시"""
    col1, col2, col3 = st.columns(3)
    
    with col1:
        risk_emoji = (
            "🟢" if profile.risk_tolerance.value <= 30 else
            "🟡" if profile.risk_tolerance.value <= 60 else
            "🔴"
        )
        st.metric(
            "투자 성향",
            f"{profile.profile_type}",
            f"{risk_emoji} {profile.risk_tolerance.value}점"
        )
    
    with col2:
        horizon_text = {
            'short': '단기 (1년 이내)',
            'medium': '중기 (1-5년)',
            'long': '장기 (5년+)'
        }
        st.metric("투자 기간", horizon_text.get(profile.investment_horizon, ''))
    
    with col3:
        top_sector = profile.preferred_sectors[0] if profile.preferred_sectors else "없음"
        st.metric("선호 섹터", top_sector)


def _show_ranking_chart(ranked_stocks: List[RankedStock]):
    """순위 차트 표시"""
    if not ranked_stocks:
        return
    
    # 바 차트
    tickers = [f"{s.stock_name}" for s in ranked_stocks]
    scores = [s.composite_score for s in ranked_stocks]
    
    colors = ['#4CAF50' if s.ai_prediction == '상승' else 
              '#FFC107' if s.ai_prediction == '보합' else 
              '#F44336' for s in ranked_stocks]
    
    fig = go.Figure(data=[
        go.Bar(
            x=scores,
            y=tickers,
            orientation='h',
            marker_color=colors,
            text=[f"{s:.1f}점" for s in scores],
            textposition='auto'
        )
    ])
    
    fig.update_layout(
        title="📊 종합 점수 순위",
        xaxis_title="종합 점수",
        yaxis_title="종목",
        yaxis={'categoryorder': 'total ascending'},
        height=400,
        showlegend=False
    )
    
    # Streamlit 새로운 파라미터 사용 (warning 해결 + 전체 너비 유지)
    try:
        st.plotly_chart(fig, key="ranking_chart_main", width="stretch")
    except TypeError:
        # 구버전 호환성
        st.plotly_chart(fig, key="ranking_chart_main", use_container_width=True)


def _show_ranking_table(
    ranked_stocks: List[RankedStock],
    service: RecommendationService,
    user_id: str
):
    """순위 테이블 표시"""
    st.subheader("📋 상세 순위")
    
    for stock in ranked_stocks:
        with st.expander(f"**{stock.rank}위** {stock.stock_name} ({stock.ticker}) - {stock.composite_score:.1f}점"):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("성향 적합도", f"{stock.profile_fit:.1f}점")
            with col2:
                st.metric("트렌드 점수", f"{stock.trend_score:.1f}점")
            with col3:
                st.metric("AI 점수", f"{stock.ai_score:.1f}점")
            
            # AI 예측
            pred_emoji = "📈" if stock.ai_prediction == "상승" else "📊" if stock.ai_prediction == "보합" else "📉"
            st.write(f"**AI 예측**: {pred_emoji} {stock.ai_prediction} (신뢰도: {stock.confidence:.1%})")
            st.write(f"**섹터**: {stock.sector}")
            st.write(f"**변동성**: {stock.volatility:.1%}")
            
            # 피드백 버튼
            col1, col2 = st.columns(2)
            with col1:
                if st.button("✅ 관심 종목 추가", key=f"accept_{stock.ticker}", use_container_width=True):
                    # 1. 추천 수락 처리 (기존)
                    recs = service.get_user_recommendations(user_id)
                    for rec in recs:
                        if rec.ticker == stock.ticker:
                            service.process_feedback(user_id, rec.recommendation_id, "accept")
                            break
                    
                    # 2. Watchlist에 실제 추가 (NEW)
                    try:
                        from src.services.watchlist_service import WatchlistService
                        from src.infrastructure.repositories.watchlist_repository import SQLiteWatchlistRepository
                        
                        watchlist_service = WatchlistService(
                            watchlist_repo=SQLiteWatchlistRepository()
                        )
                        
                        # 시장 판별
                        market = "US" if not stock.ticker.endswith(".KS") and not stock.ticker.endswith(".KQ") else "KR"
                        
                        watchlist_service.add_to_watchlist(
                            user_id=user_id,
                            ticker=stock.ticker,
                            stock_name=stock.stock_name,
                            market=market
                        )
                        st.success(f"✅ {stock.stock_name}을(를) 관심 종목에 추가했습니다!")
                    except ValueError as e:
                        st.info(str(e))  # 이미 존재하는 경우
                    except Exception as e:
                        st.warning(f"관심 종목 추가 실패: {e}")
            
            with col2:
                if st.button("❌ 관심 없음", key=f"reject_{stock.ticker}", use_container_width=True):
                    reason = st.text_input(
                        "사유 (선택)",
                        key=f"reason_{stock.ticker}",
                        placeholder="예: 변동성이 큼, 해당 섹터에 관심 없음"
                    )
                    recs = service.get_user_recommendations(user_id)
                    for rec in recs:
                        if rec.ticker == stock.ticker:
                            service.process_feedback(user_id, rec.recommendation_id, "reject", reason)
                            st.info("피드백이 반영되었습니다.")
                            break


def show_recommendation_page():
    """개별 추천 페이지 (피드백 중심)"""
    st.header("📈 맞춤 추천")
    
    user_id = st.session_state.get('user_id', 'default_user')
    _, recommendation_service = get_services()
    
    pending_recs = recommendation_service.get_pending_recommendations(user_id)
    
    if not pending_recs:
        st.info("현재 대기 중인 추천이 없습니다.")
        if st.button("🔄 새 추천 받기"):
            assessment_service, _ = get_services()
            profile = assessment_service.get_profile(user_id)
            if profile:
                recommendation_service.generate_recommendations(profile)
                st.rerun()
        return
    
    st.write(f"**{len(pending_recs)}개**의 추천이 있습니다.")
    
    for rec in pending_recs:
        _display_recommendation_card(rec, recommendation_service, user_id)


def _display_recommendation_card(
    rec: Recommendation,
    service: RecommendationService,
    user_id: str
):
    """추천 카드 표시"""
    with st.container():
        st.subheader(f"📈 {rec.stock_name} ({rec.ticker})")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("종합 점수", f"{rec.composite_score:.1f}")
        with col2:
            st.metric("성향 적합도", f"{rec.fit_score:.1f}%")
        with col3:
            pred_emoji = "📈" if rec.ai_prediction == "상승" else "📊" if rec.ai_prediction == "보합" else "📉"
            st.metric("AI 예측", f"{pred_emoji} {rec.ai_prediction}")
        with col4:
            st.metric("신뢰도", f"{rec.confidence:.1%}")
        
        st.write(f"**추천 사유**: {rec.recommendation_reason}")
        st.write(f"**섹터**: {rec.sector}")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("✅ 수락", key=f"accept_{rec.recommendation_id}", use_container_width=True, type="primary"):
                service.process_feedback(user_id, rec.recommendation_id, "accept")
                st.success("✅ 추천을 수락했습니다! 프로필이 업데이트됩니다.")
                st.rerun()
        
        with col2:
            reject_reason = st.selectbox(
                "거절 사유",
                ["선택", "변동성이 너무 큼", "해당 섹터에 관심 없음", "투자 금액 부담", "기타"],
                key=f"reject_reason_{rec.recommendation_id}"
            )
            if st.button("❌ 거절", key=f"reject_{rec.recommendation_id}", use_container_width=True):
                reason = reject_reason if reject_reason != "선택" else ""
                service.process_feedback(user_id, rec.recommendation_id, "reject", reason)
                st.info("피드백이 반영되었습니다.")
                st.rerun()
        
        st.divider()


# 메인 대시보드 통합 함수
def render_ranking_tab():
    """순위 탭 렌더링"""
    show_ranking_page()
