"""
Question 및 Answer 엔티티
설문 질문과 응답을 표현하는 도메인 엔티티
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Any, Optional


class QuestionType(Enum):
    """설문 질문 유형"""
    LIKERT_SCALE = "likert"      # 1-5 척도
    SCENARIO = "scenario"         # 시나리오 선택
    MULTI_SELECT = "multi_select" # 복수 선택 (섹터 등)


@dataclass
class QuestionOption:
    """설문 선택지"""
    label: str
    score: float = 0.0
    value: Optional[str] = None  # MULTI_SELECT용 값
    
    def to_dict(self) -> Dict:
        return {
            "label": self.label,
            "score": self.score,
            "value": self.value
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "QuestionOption":
        return cls(
            label=data["label"],
            score=data.get("score", 0.0),
            value=data.get("value")
        )


@dataclass
class Question:
    """
    설문 질문 엔티티
    
    Attributes:
        question_id: 질문 고유 ID (Q001, Q002, ...)
        category: 질문 카테고리 (risk_tolerance, investment_horizon 등)
        question_text: 질문 텍스트
        question_type: 질문 유형
        options: 선택지 목록
        weight: 질문 가중치 (중요도)
    """
    question_id: str
    category: str
    question_text: str
    question_type: QuestionType
    options: List[QuestionOption] = field(default_factory=list)
    weight: float = 1.0
    
    def get_max_score(self) -> float:
        """최대 점수 반환"""
        if not self.options:
            return 0.0
        return max(opt.score for opt in self.options)
    
    def get_score_for_option(self, selected_label: str) -> float:
        """선택한 옵션의 점수 반환"""
        for opt in self.options:
            if opt.label == selected_label:
                return opt.score
        return 0.0
    
    def to_dict(self) -> Dict:
        return {
            "id": self.question_id,
            "category": self.category,
            "text": self.question_text,
            "type": self.question_type.value,
            "options": [opt.to_dict() for opt in self.options],
            "weight": self.weight
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "Question":
        return cls(
            question_id=data["id"],
            category=data["category"],
            question_text=data["text"],
            question_type=QuestionType(data["type"]),
            options=[QuestionOption.from_dict(opt) for opt in data.get("options", [])],
            weight=data.get("weight", 1.0)
        )


@dataclass
class Answer:
    """
    설문 응답 엔티티
    
    Attributes:
        question_id: 질문 ID
        selected_option: 선택한 옵션 레이블
        score: 획득 점수
        selected_values: MULTI_SELECT인 경우 선택된 값들
        answered_at: 응답 시간
    """
    question_id: str
    selected_option: str
    score: float
    selected_values: List[str] = field(default_factory=list)
    answered_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict:
        return {
            "question_id": self.question_id,
            "selected_option": self.selected_option,
            "score": self.score,
            "selected_values": self.selected_values,
            "answered_at": self.answered_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "Answer":
        return cls(
            question_id=data["question_id"],
            selected_option=data["selected_option"],
            score=data["score"],
            selected_values=data.get("selected_values", []),
            answered_at=datetime.fromisoformat(data["answered_at"])
        )


@dataclass
class AssessmentSession:
    """
    설문 세션 엔티티
    사용자의 전체 설문 응답 세션을 관리
    """
    session_id: str
    user_id: str
    answers: List[Answer] = field(default_factory=list)
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    
    def add_answer(self, answer: Answer) -> None:
        """응답 추가"""
        # 기존 응답 업데이트
        for i, existing in enumerate(self.answers):
            if existing.question_id == answer.question_id:
                self.answers[i] = answer
                return
        self.answers.append(answer)
    
    def get_answer(self, question_id: str) -> Optional[Answer]:
        """특정 질문에 대한 응답 조회"""
        for answer in self.answers:
            if answer.question_id == question_id:
                return answer
        return None
    
    def calculate_category_score(self, category: str, questions: List[Question]) -> float:
        """특정 카테고리의 총점 계산"""
        total_score = 0.0
        total_weight = 0.0
        
        category_questions = [q for q in questions if q.category == category]
        
        for question in category_questions:
            answer = self.get_answer(question.question_id)
            if answer:
                total_score += answer.score * question.weight
                total_weight += question.weight
        
        if total_weight == 0:
            return 0.0
        
        return total_score / total_weight
    
    def is_complete(self, total_questions: int) -> bool:
        """설문 완료 여부"""
        return len(self.answers) >= total_questions
    
    def mark_complete(self) -> None:
        """설문 완료 표시"""
        self.completed_at = datetime.now()
    
    @property
    def progress_percentage(self) -> float:
        """진행률 (0-100)"""
        # 이 값은 총 질문 수를 알아야 정확히 계산 가능
        # 여기서는 현재 응답 수만 반환
        return len(self.answers)
    
    def to_dict(self) -> Dict:
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "answers": [a.to_dict() for a in self.answers],
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "AssessmentSession":
        return cls(
            session_id=data["session_id"],
            user_id=data["user_id"],
            answers=[Answer.from_dict(a) for a in data.get("answers", [])],
            started_at=datetime.fromisoformat(data["started_at"]),
            completed_at=datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None
        )
