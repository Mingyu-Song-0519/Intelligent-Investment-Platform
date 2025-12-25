"""
Repository 인터페이스 정의
Clean Architecture: Domain Layer - Port
"""
from abc import ABC, abstractmethod
from typing import List, Optional

from src.domain.investment_profile.entities.investor_profile import InvestorProfile
from src.domain.investment_profile.entities.assessment import Question, AssessmentSession


class IProfileRepository(ABC):
    """투자자 프로필 저장소 인터페이스"""
    
    @abstractmethod
    def save(self, profile: InvestorProfile) -> bool:
        """프로필 저장"""
        pass
    
    @abstractmethod
    def load(self, user_id: str) -> Optional[InvestorProfile]:
        """프로필 조회"""
        pass
    
    @abstractmethod
    def delete(self, user_id: str) -> bool:
        """프로필 삭제"""
        pass
    
    @abstractmethod
    def exists(self, user_id: str) -> bool:
        """프로필 존재 여부 확인"""
        pass
    
    @abstractmethod
    def list_all_users(self) -> List[str]:
        """모든 사용자 ID 목록 반환"""
        pass


class IQuestionRepository(ABC):
    """설문 질문 저장소 인터페이스"""
    
    @abstractmethod
    def load_questions(self) -> List[Question]:
        """모든 질문 로드"""
        pass
    
    @abstractmethod
    def get_question(self, question_id: str) -> Optional[Question]:
        """특정 질문 조회"""
        pass
    
    @abstractmethod
    def get_questions_by_category(self, category: str) -> List[Question]:
        """카테고리별 질문 조회"""
        pass


class ISessionRepository(ABC):
    """설문 세션 저장소 인터페이스"""
    
    @abstractmethod
    def save(self, session: AssessmentSession) -> bool:
        """세션 저장"""
        pass
    
    @abstractmethod
    def load(self, session_id: str) -> Optional[AssessmentSession]:
        """세션 조회"""
        pass
    
    @abstractmethod
    def find_by_user(self, user_id: str) -> List[AssessmentSession]:
        """사용자별 세션 목록 조회"""
        pass
    
    @abstractmethod
    def get_latest_session(self, user_id: str) -> Optional[AssessmentSession]:
        """사용자의 최신 세션 조회"""
        pass
