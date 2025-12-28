"""
투자 성향 진단 UI 뷰
Streamlit 기반 설문 인터페이스

Clean Architecture: Presentation Layer
"""
import streamlit as st
from typing import Optional, List
from datetime import datetime

from src.services.profile_assessment_service import ProfileAssessmentService
from src.domain.investment_profile.entities.investor_profile import InvestorProfile
from src.domain.investment_profile.entities.assessment import Question, QuestionType, Answer
from src.domain.investment_profile.value_objects.risk_tolerance import RiskTolerance
from src.infrastructure.repositories.profile_repository import SQLiteProfileRepository
from src.infrastructure.repositories.question_repository import YAMLQuestionRepository


@st.cache_resource
def get_assessment_service() -> ProfileAssessmentService:
    """Assessment 서비스 인스턴스 생성 (캐싱)"""
    profile_repo = SQLiteProfileRepository()
    question_repo = YAMLQuestionRepository()
    return ProfileAssessmentService(profile_repo, question_repo)


def show_assessment_page():
    """투자 성향 진단 페이지"""
    st.header("📊 투자 성향 진단")
    
    # 사용자 ID (실제 환경에서는 로그인 시스템과 연동)
    if 'user_id' not in st.session_state:
        st.session_state.user_id = "default_user"
    
    user_id = st.session_state.user_id
    service = get_assessment_service()
    
    # 기존 프로필 확인
    existing_profile = service.get_profile(user_id)
    
    if existing_profile:
        _show_existing_profile(existing_profile, service)
    else:
        _show_new_assessment(user_id, service)


def _show_existing_profile(profile: InvestorProfile, service: ProfileAssessmentService):
    """기존 프로필 표시"""
    
    # 맞춤 종목 보기 모드
    if st.session_state.get('show_ranking_view', False):
        _show_inline_ranking(profile)
        return
    
    # 프로필 수정 모드
    if st.session_state.get('show_profile_edit', False):
        _show_profile_edit(profile, service)
        return
    
    st.success(f"✅ 기존 프로필이 있습니다: **{profile.profile_type}**")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric("위험 감수 수준", f"{profile.risk_tolerance.value}/100")
        st.metric("투자 기간", profile.investment_horizon.upper())
    
    with col2:
        st.write("**선호 섹터:**")
        for sector in profile.preferred_sectors[:5]:
            st.write(f"  • {sector}")
    
    # 스타일 점수 표시
    st.subheader("📈 투자 스타일")
    style_cols = st.columns(3)
    for i, (style, score) in enumerate(profile.style_scores.items()):
        with style_cols[i]:
            st.progress(score / 100)
            st.caption(f"{style.title()}: {score:.1f}%")
    
    # 프로필 만료 경고
    if profile.is_outdated():
        st.warning("⏰ 프로필이 6개월 이상 되었습니다. 재진단을 권장합니다.")
    
    st.divider()
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🔄 재진단 시작", width="stretch"):
            service.delete_profile(profile.user_id)
            # 세션 상태 초기화
            for key in ['assessment_answers', 'current_question_idx', 'assessment_session', 'show_ranking_view', 'show_profile_edit']:
                st.session_state.pop(key, None)
            st.rerun()
    
    with col2:
        if st.button("🏆 맞춤 종목 보기", width="stretch"):
            st.session_state.show_ranking_view = True
            st.rerun()
    
    with col3:
        if st.button("📝 프로필 수정", width="stretch"):
            st.session_state.show_profile_edit = True
            st.rerun()


def _show_inline_ranking(profile: InvestorProfile):
    """인라인 맞춤 종목 순위 표시"""
    import plotly.graph_objects as go
    
    st.subheader("🏆 맞춤 종목 순위")
    
    if st.button("◀ 프로필로 돌아가기", key="back_to_profile_btn"):
        st.session_state.show_ranking_view = False
        st.rerun()
    
    st.divider()
    
    try:
        from src.dashboard.views.ranking_view import get_services
        _, recommendation_service = get_services()
        
        with st.spinner("맞춤 종목 분석 중..."):
            ranked_stocks = recommendation_service.get_ranked_stocks(profile, top_n=10)
        
        if ranked_stocks:
            # 인라인 전용 차트 (고유 key 사용)
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
                yaxis={'categoryorder': 'total ascending'},
                height=350,
                showlegend=False
            )
            # Streamlit 새로운 파라미터 사용
            try:
                st.plotly_chart(fig, key="inline_ranking_chart", width="stretch")
            except TypeError:
                st.plotly_chart(fig, key="inline_ranking_chart", width="stretch")
            
            # 상세 정보
            for stock in ranked_stocks[:5]:
                with st.expander(f"**{stock.rank}위** {stock.stock_name} - {stock.composite_score:.1f}점"):
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("성향 적합도", f"{stock.profile_fit:.1f}")
                    with col2:
                        st.metric("트렌드", f"{stock.trend_score:.1f}")
                    with col3:
                        pred_emoji = "📈" if stock.ai_prediction == "상승" else "📊"
                        st.metric("AI 예측", f"{pred_emoji} {stock.ai_prediction}")
        else:
            st.info("추천 종목을 생성할 수 없습니다.")
    except Exception as e:
        st.error(f"순위 로딩 오류: {e}")


def _show_profile_edit(profile: InvestorProfile, service: ProfileAssessmentService):
    """프로필 수정 화면"""
    st.subheader("📝 프로필 수정")
    
    if st.button("◀ 프로필로 돌아가기"):
        st.session_state.show_profile_edit = False
        st.rerun()
    
    st.divider()
    
    # 위험 감수 수준 조정
    new_risk = st.slider(
        "위험 감수 수준",
        min_value=0,
        max_value=100,
        value=profile.risk_tolerance.value,
        help="낮을수록 안정적, 높을수록 공격적"
    )
    
    # 투자 기간 선택
    horizon_options = {"short": "단기 (1년 이내)", "medium": "중기 (1-5년)", "long": "장기 (5년 이상)"}
    current_horizon_idx = list(horizon_options.keys()).index(profile.investment_horizon)
    new_horizon = st.selectbox(
        "투자 기간",
        options=list(horizon_options.keys()),
        index=current_horizon_idx,
        format_func=lambda x: horizon_options[x]
    )
    
    # 선호 섹터 수정
    all_sectors = ["Technology", "Healthcare", "Financials", "Consumer", "Energy", "Communication", "Industrials", "Materials", "Utilities"]
    new_sectors = st.multiselect(
        "선호 섹터",
        options=all_sectors,
        default=profile.preferred_sectors[:5]
    )
    
    st.divider()
    
    if st.button("💾 변경사항 저장", type="primary", width="stretch"):
        # 프로필 업데이트
        profile.risk_tolerance = RiskTolerance(new_risk)
        profile.investment_horizon = new_horizon
        profile.preferred_sectors = new_sectors
        profile.last_updated = datetime.now()
        
        # 저장
        from src.infrastructure.repositories.profile_repository import SQLiteProfileRepository
        repo = SQLiteProfileRepository()
        repo.save(profile)
        
        st.success("✅ 프로필이 수정되었습니다!")
        st.session_state.show_profile_edit = False
        st.rerun()


def _show_new_assessment(user_id: str, service: ProfileAssessmentService):
    """새 설문 시작"""
    st.info("💡 투자 성향을 진단하여 맞춤 종목을 추천받으세요!")
    
    # 응답 저장소 초기화 (session_state에 저장)
    if 'assessment_answers' not in st.session_state:
        st.session_state.assessment_answers = {}
    if 'current_question_idx' not in st.session_state:
        st.session_state.current_question_idx = 0
    
    questions = service.get_all_questions()
    current_idx = st.session_state.get('current_question_idx', 0)
    
    if not questions:
        st.error("❌ 설문 질문을 불러올 수 없습니다.")
        return
    
    # 진행률 표시
    total = len(questions)
    progress = (current_idx) / total
    st.progress(progress)
    st.caption(f"질문 {current_idx + 1}/{total}")
    
    # 현재 질문 표시
    if current_idx < total:
        question = questions[current_idx]
        _display_question(question, user_id, service, current_idx, total)
    else:
        # 설문 완료
        _complete_assessment(user_id, service)


def _display_question(
    question: Question,
    user_id: str,
    service: ProfileAssessmentService,
    current_idx: int,
    total: int
):
    """개별 질문 표시"""
    st.subheader(f"Q{current_idx + 1}. {question.question_text}")
    
    # 카테고리 표시
    category_names = {
        'risk_tolerance': '위험 감수',
        'investment_horizon': '투자 기간',
        'expected_return': '기대 수익',
        'volatility_tolerance': '변동성 허용',
        'experience': '투자 경험',
        'preferred_sectors': '섹터 선호',
        'investment_style': '투자 스타일',
        'information_source': '정보 소스',
        'psychological': '투자 심리'
    }
    st.caption(f"📌 {category_names.get(question.category, question.category)}")
    
    st.divider()
    
    # 질문 유형별 UI
    if question.question_type == QuestionType.MULTI_SELECT:
        _display_multi_select(question, user_id, service, current_idx, total)
    else:
        _display_single_select(question, user_id, service, current_idx, total)


def _display_single_select(
    question: Question,
    user_id: str,
    service: ProfileAssessmentService,
    current_idx: int,
    total: int
):
    """단일 선택 질문"""
    options = [opt.label for opt in question.options]
    
    # 이전 응답 확인 (session_state에서)
    answers = st.session_state.get('assessment_answers', {})
    previous_answer = answers.get(question.question_id)
    default_idx = 0
    if previous_answer:
        try:
            default_idx = options.index(previous_answer.get('selected_option', ''))
        except ValueError:
            default_idx = 0
    
    selected = st.radio(
        "선택해주세요:",
        options,
        index=default_idx,
        key=f"q_{question.question_id}"
    )
    
    st.divider()
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col1:
        if current_idx > 0:
            if st.button("◀ 이전", width="stretch"):
                st.session_state.current_question_idx = current_idx - 1
                st.rerun()
    
    with col3:
        if current_idx < total - 1:
            if st.button("다음 ▶", width="stretch", type="primary"):
                # session_state에 응답 저장
                score = question.get_score_for_option(selected)
                st.session_state.assessment_answers[question.question_id] = {
                    'selected_option': selected,
                    'score': score,
                    'selected_values': []
                }
                st.session_state.current_question_idx = current_idx + 1
                st.rerun()
        else:
            if st.button("✅ 완료", width="stretch", type="primary"):
                score = question.get_score_for_option(selected)
                st.session_state.assessment_answers[question.question_id] = {
                    'selected_option': selected,
                    'score': score,
                    'selected_values': []
                }
                st.session_state.current_question_idx = current_idx + 1
                st.rerun()


def _display_multi_select(
    question: Question,
    user_id: str,
    service: ProfileAssessmentService,
    current_idx: int,
    total: int
):
    """복수 선택 질문"""
    st.write("원하는 항목을 모두 선택해주세요:")
    
    selected_values = []
    selected_label = ""
    
    # 체크박스로 표시
    cols = st.columns(2)
    for i, opt in enumerate(question.options):
        with cols[i % 2]:
            if st.checkbox(opt.label, key=f"q_{question.question_id}_{i}"):
                if opt.value:
                    selected_values.append(opt.value)
                selected_label = opt.label
    
    st.divider()
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col1:
        if current_idx > 0:
            if st.button("◀ 이전", width="stretch"):
                st.session_state.current_question_idx = current_idx - 1
                st.rerun()
    
    with col3:
        if current_idx < total - 1:
            if st.button("다음 ▶", width="stretch", type="primary"):
                st.session_state.assessment_answers[question.question_id] = {
                    'selected_option': selected_label,
                    'score': 0,
                    'selected_values': selected_values
                }
                st.session_state.current_question_idx = current_idx + 1
                st.rerun()
        else:
            if st.button("✅ 완료", width="stretch", type="primary"):
                st.session_state.assessment_answers[question.question_id] = {
                    'selected_option': selected_label,
                    'score': 0,
                    'selected_values': selected_values
                }
                st.session_state.current_question_idx = current_idx + 1
                st.rerun()


def _complete_assessment(user_id: str, service: ProfileAssessmentService):
    """설문 완료 및 프로필 직접 생성"""
    st.success("🎉 설문이 완료되었습니다!")
    
    with st.spinner("프로필 분석 중..."):
        try:
            answers = st.session_state.get('assessment_answers', {})
            questions = service.get_all_questions()
            
            # 1. 위험 감수 점수 계산
            risk_categories = ['risk_tolerance', 'volatility_tolerance', 'expected_return']
            risk_score = _calculate_score_from_answers(answers, questions, risk_categories)
            
            # 2. 투자 기간 결정
            horizon_score = _calculate_category_score(answers, questions, 'investment_horizon')
            if horizon_score <= 33:
                investment_horizon = "short"
            elif horizon_score <= 66:
                investment_horizon = "medium"
            else:
                investment_horizon = "long"
            
            # 3. 투자 스타일 점수
            style_scores = {"value": 33.3, "growth": 33.3, "momentum": 33.4}
            
            # 4. 선호 섹터 추출
            sector_answer = answers.get('Q011', {})
            preferred_sectors = sector_answer.get('selected_values', [])
            if not preferred_sectors:
                preferred_sectors = ["Technology", "Healthcare", "Financials"]
            
            # 프로필 생성
            profile = InvestorProfile(
                user_id=user_id,
                risk_tolerance=RiskTolerance(int(risk_score)),
                investment_horizon=investment_horizon,
                preferred_sectors=preferred_sectors,
                style_scores=style_scores,
                created_at=datetime.now(),
                last_updated=datetime.now()
            )
            
            # 저장
            from src.infrastructure.repositories.profile_repository import SQLiteProfileRepository
            repo = SQLiteProfileRepository()
            repo.save(profile)
            
        except Exception as e:
            st.error(f"프로필 생성 중 오류: {e}")
            profile = None
    
    if profile:
        st.subheader(f"📊 당신의 투자 성향: **{profile.profile_type}**")
        
        # 결과 표시
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("위험 감수 수준", f"{profile.risk_tolerance.value}/100")
            
            # 위험 수준 게이지
            risk_color = (
                "🟢" if profile.risk_tolerance.value <= 30 else
                "🟡" if profile.risk_tolerance.value <= 60 else
                "🔴"
            )
            st.write(f"{risk_color} {profile.risk_tolerance.level_name}")
        
        with col2:
            st.metric("투자 기간", profile.investment_horizon.upper())
            horizon_desc = {
                'short': '단기 (1년 이내)',
                'medium': '중기 (1-5년)',
                'long': '장기 (5년 이상)'
            }
            st.caption(horizon_desc.get(profile.investment_horizon, ''))
        
        # 스타일 점수
        st.subheader("📈 투자 스타일 분석")
        style_cols = st.columns(3)
        style_icons = {'value': '💎', 'growth': '🚀', 'momentum': '📈'}
        for i, (style, score) in enumerate(profile.style_scores.items()):
            with style_cols[i]:
                st.write(f"{style_icons.get(style, '•')} **{style.title()}**")
                st.progress(score / 100)
                st.caption(f"{score:.1f}%")
        
        # 선호 섹터
        st.subheader("🏭 선호 섹터")
        if profile.preferred_sectors:
            sector_cols = st.columns(min(4, len(profile.preferred_sectors)))
            for i, sector in enumerate(profile.preferred_sectors[:4]):
                with sector_cols[i]:
                    st.info(sector)
        
        st.divider()
        
        if st.button("🏆 맞춤 종목 확인하기", width="stretch", type="primary"):
            st.session_state.page = "ranking"
            # 세션 정리
            for key in ['assessment_answers', 'current_question_idx']:
                st.session_state.pop(key, None)
            st.rerun()
    else:
        st.error("프로필 생성에 실패했습니다.")


def _calculate_score_from_answers(answers: dict, questions: list, categories: list) -> float:
    """session_state 응답에서 점수 계산"""
    total_score = 0.0
    total_weight = 0.0
    
    for q in questions:
        if q.category in categories:
            answer = answers.get(q.question_id)
            if answer:
                total_score += answer.get('score', 0) * q.weight
                total_weight += q.weight
    
    if total_weight == 0:
        return 50.0
    
    return min(100, max(0, total_score / total_weight))


def _calculate_category_score(answers: dict, questions: list, category: str) -> float:
    """특정 카테고리 점수 계산"""
    return _calculate_score_from_answers(answers, questions, [category])


def show_quick_profile_setup():
    """빠른 프로필 설정 (기본값 사용)"""
    st.subheader("⚡ 빠른 시작")
    st.write("설문 없이 기본 프로필로 시작할 수 있습니다.")
    
    if st.button("기본 프로필로 시작 (균형형)", width="stretch"):
        service = get_assessment_service()
        user_id = st.session_state.get('user_id', 'default_user')
        profile = service.create_default_profile(user_id)
        st.success(f"✅ 기본 프로필이 생성되었습니다: {profile.profile_type}")
        st.rerun()


# 메인 페이지 통합 함수
def render_investment_profile_tab():
    """투자 성향 탭 렌더링 (메인 대시보드에서 호출)"""
    service = get_assessment_service()
    user_id = st.session_state.get('user_id', 'default_user')
    
    if service.has_profile(user_id):
        profile = service.get_profile(user_id)
        if profile:
            _show_existing_profile(profile, service)
        else:
            _show_new_assessment(user_id, service)
    else:
        tab1, tab2 = st.tabs(["📝 설문 진단", "⚡ 빠른 시작"])
        
        with tab1:
            _show_new_assessment(user_id, service)
        
        with tab2:
            show_quick_profile_setup()
