"""
ProfileAssessmentService
설문 처리 및 투자 성향 분석 서비스

Clean Architecture: Application Layer (Service)
"""
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import uuid

from src.domain.investment_profile.entities.investor_profile import InvestorProfile
from src.domain.investment_profile.entities.assessment import (
    Question, QuestionType, Answer, AssessmentSession
)
from src.domain.investment_profile.value_objects.risk_tolerance import RiskTolerance
from src.domain.repositories.profile_interfaces import IProfileRepository, IQuestionRepository


class ProfileAssessmentService:
    """
    투자 성향 진단 서비스
    
    책임:
    - 설문 질문 제공
    - 응답 처리 및 점수 계산
    - 프로필 생성/업데이트
    """
    
    def __init__(
        self,
        profile_repo: IProfileRepository,
        question_repo: IQuestionRepository
    ):
        self.profile_repo = profile_repo
        self.question_repo = question_repo
        self._sessions: Dict[str, AssessmentSession] = {}  # 메모리 세션 관리
    
    # ===== 설문 관리 =====
    
    def get_all_questions(self) -> List[Question]:
        """모든 설문 질문 반환"""
        return self.question_repo.load_questions()
    
    def get_questions_by_category(self, category: str) -> List[Question]:
        """카테고리별 질문 반환"""
        return self.question_repo.get_questions_by_category(category)
    
    def get_total_questions(self) -> int:
        """전체 질문 수 반환"""
        return len(self.question_repo.load_questions())
    
    # ===== 세션 관리 =====
    
    def start_assessment(self, user_id: str) -> AssessmentSession:
        """새 설문 세션 시작"""
        session_id = str(uuid.uuid4())[:8]
        session = AssessmentSession(
            session_id=session_id,
            user_id=user_id,
            started_at=datetime.now()
        )
        self._sessions[session_id] = session
        return session
    
    def get_session(self, session_id: str) -> Optional[AssessmentSession]:
        """세션 조회"""
        return self._sessions.get(session_id)
    
    def submit_answer(
        self,
        session_id: str,
        question_id: str,
        selected_option: str,
        selected_values: Optional[List[str]] = None
    ) -> bool:
        """답변 제출"""
        session = self._sessions.get(session_id)
        if not session:
            return False
        
        question = self.question_repo.get_question(question_id)
        if not question:
            return False
        
        # 점수 계산
        score = question.get_score_for_option(selected_option)
        
        answer = Answer(
            question_id=question_id,
            selected_option=selected_option,
            score=score,
            selected_values=selected_values or [],
            answered_at=datetime.now()
        )
        
        session.add_answer(answer)
        return True
    
    def get_progress(self, session_id: str) -> Tuple[int, int]:
        """진행 상황 (현재/전체)"""
        session = self._sessions.get(session_id)
        if not session:
            return (0, 0)
        
        total = self.get_total_questions()
        current = len(session.answers)
        return (current, total)
    
    # ===== 프로필 생성 =====
    
    def complete_assessment(self, session_id: str) -> Optional[InvestorProfile]:
        """
        설문 완료 및 프로필 생성
        
        점수 계산 방식:
        1. 카테고리별 가중 평균 점수 계산
        2. risk_tolerance = 위험 관련 카테고리 평균
        3. style_scores = 투자 스타일 카테고리에서 추출
        4. preferred_sectors = 섹터 선호 질문에서 추출
        """
        session = self._sessions.get(session_id)
        if not session:
            return None
        
        questions = self.question_repo.load_questions()
        
        # 1. 위험 감수 점수 계산 (여러 카테고리 종합)
        risk_categories = ['risk_tolerance', 'volatility_tolerance', 'expected_return']
        risk_score = self._calculate_composite_score(session, questions, risk_categories)
        
        # 2. 투자 기간 결정
        horizon_score = session.calculate_category_score('investment_horizon', questions)
        investment_horizon = self._score_to_horizon(horizon_score)
        
        # 3. 투자 스타일 점수
        style_scores = self._calculate_style_scores(session, questions)
        
        # 4. 선호 섹터 추출
        preferred_sectors = self._extract_preferred_sectors(session)
        
        # 프로필 생성
        profile = InvestorProfile(
            user_id=session.user_id,
            risk_tolerance=RiskTolerance(int(risk_score)),
            investment_horizon=investment_horizon,
            preferred_sectors=preferred_sectors,
            style_scores=style_scores,
            created_at=datetime.now(),
            last_updated=datetime.now()
        )
        
        # 저장
        self.profile_repo.save(profile)
        
        # 세션 완료 표시
        session.mark_complete()
        
        return profile
    
    def _calculate_composite_score(
        self,
        session: AssessmentSession,
        questions: List[Question],
        categories: List[str]
    ) -> float:
        """여러 카테고리의 복합 점수 계산"""
        total_score = 0.0
        total_weight = 0.0
        
        for category in categories:
            cat_questions = [q for q in questions if q.category == category]
            for question in cat_questions:
                answer = session.get_answer(question.question_id)
                if answer:
                    total_score += answer.score * question.weight
                    total_weight += question.weight
        
        if total_weight == 0:
            return 50.0  # 기본값
        
        return min(100, max(0, total_score / total_weight))
    
    def _score_to_horizon(self, score: float) -> str:
        """점수를 투자 기간으로 변환"""
        if score <= 33:
            return "short"
        elif score <= 66:
            return "medium"
        else:
            return "long"
    
    def _calculate_style_scores(
        self,
        session: AssessmentSession,
        questions: List[Question]
    ) -> Dict[str, float]:
        """투자 스타일 점수 계산"""
        style_questions = [q for q in questions if q.category == 'investment_style']
        
        # 기본값
        styles = {"value": 33.3, "growth": 33.3, "momentum": 33.4}
        
        for question in style_questions:
            answer = session.get_answer(question.question_id)
            if answer:
                # 선택한 옵션에서 스타일 추출
                for opt in question.options:
                    if opt.label == answer.selected_option:
                        style = getattr(opt, 'value', None) or 'balanced'
                        if style == 'value':
                            styles['value'] = min(100, styles['value'] + 20)
                        elif style == 'growth':
                            styles['growth'] = min(100, styles['growth'] + 20)
                        elif style == 'momentum':
                            styles['momentum'] = min(100, styles['momentum'] + 20)
                        break
        
        # 정규화 (합계 100으로)
        total = sum(styles.values())
        if total > 0:
            styles = {k: (v / total) * 100 for k, v in styles.items()}
        
        return styles
    
    def _extract_preferred_sectors(self, session: AssessmentSession) -> List[str]:
        """선호 섹터 추출"""
        sector_answer = session.get_answer('Q011')  # preferred_sectors 질문
        if sector_answer and sector_answer.selected_values:
            return sector_answer.selected_values
        
        # 기본 섹터
        return ["Technology", "Healthcare", "Financials"]
    
    # ===== 프로필 조회/관리 =====
    
    def get_profile(self, user_id: str) -> Optional[InvestorProfile]:
        """사용자 프로필 조회"""
        return self.profile_repo.load(user_id)
    
    def has_profile(self, user_id: str) -> bool:
        """프로필 존재 여부 확인"""
        return self.profile_repo.exists(user_id)
    
    def is_profile_outdated(self, user_id: str, threshold_days: int = 180) -> bool:
        """프로필 만료 여부 확인"""
        profile = self.profile_repo.load(user_id)
        if not profile:
            return True
        return profile.is_outdated(threshold_days)
    
    def create_default_profile(self, user_id: str) -> InvestorProfile:
        """기본 프로필 생성 (Cold Start 대응)"""
        profile = InvestorProfile.create_default(user_id)
        self.profile_repo.save(profile)
        return profile
    
    def delete_profile(self, user_id: str) -> bool:
        """프로필 삭제 (재진단용)"""
        return self.profile_repo.delete(user_id)
    
    # ===== 프로필 드리프트 감지 (Phase 20.6) =====
    
    def check_profile_drift(self, user_id: str) -> dict:
        """
        프로필 드리프트 감지
        
        Returns:
            {
                'needs_reassessment': bool,
                'reason': str,
                'days_since_update': int,
                'profile_age_months': float
            }
        """
        profile = self.profile_repo.load(user_id)
        
        if not profile:
            return {
                'needs_reassessment': True,
                'reason': 'no_profile',
                'days_since_update': 0,
                'profile_age_months': 0.0
            }
        
        days_since_update = (datetime.now() - profile.last_updated).days
        age_months = days_since_update / 30.0
        
        # 6개월 이상이면 재진단 권장
        if days_since_update > 180:
            return {
                'needs_reassessment': True,
                'reason': 'outdated',
                'days_since_update': days_since_update,
                'profile_age_months': age_months
            }
        
        # 3개월 이상이면 검토 권장
        if days_since_update > 90:
            return {
                'needs_reassessment': False,
                'reason': 'review_recommended',
                'days_since_update': days_since_update,
                'profile_age_months': age_months
            }
        
        return {
            'needs_reassessment': False,
            'reason': 'up_to_date',
            'days_since_update': days_since_update,
            'profile_age_months': age_months
        }
    
    def get_reassessment_message(self, user_id: str) -> str:
        """재진단 권장 메시지 생성"""
        drift_info = self.check_profile_drift(user_id)
        
        if drift_info['reason'] == 'no_profile':
            return "💡 투자 성향 진단이 필요합니다."
        
        if drift_info['reason'] == 'outdated':
            months = drift_info['profile_age_months']
            return f"⏰ 마지막 진단 후 {months:.1f}개월이 지났습니다. 재진단을 권장합니다."
        
        if drift_info['reason'] == 'review_recommended':
            months = drift_info['profile_age_months']
            return f"📋 프로필이 {months:.1f}개월 되었습니다. 투자 목표가 변경되었다면 재진단을 고려해주세요."
        
        return ""
