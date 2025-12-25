"""
YAML 기반 설문 질문 저장소 구현
"""
import yaml
from pathlib import Path
from typing import List, Optional

from src.domain.repositories.profile_interfaces import IQuestionRepository
from src.domain.investment_profile.entities.assessment import Question, QuestionType, QuestionOption


# 모듈 수준 캐시 (싱글톤 패턴)
_QUESTIONS_CACHE: List[Question] = []
_QUESTIONS_LOADED: bool = False


def _load_questions_once(yaml_path: Path) -> List[Question]:
    """질문을 한 번만 로드 (모듈 수준 캐싱)"""
    global _QUESTIONS_CACHE, _QUESTIONS_LOADED
    
    if _QUESTIONS_LOADED:
        return _QUESTIONS_CACHE
    
    if not yaml_path.exists():
        _QUESTIONS_LOADED = True
        return []
    
    try:
        with open(yaml_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        if not data or 'questions' not in data:
            _QUESTIONS_LOADED = True
            return []
        
        for q_data in data['questions']:
            options = [
                QuestionOption(
                    label=opt['label'],
                    score=opt.get('score', 0.0),
                    value=opt.get('value')
                )
                for opt in q_data.get('options', [])
            ]
            
            question = Question(
                question_id=q_data['id'],
                category=q_data['category'],
                question_text=q_data['text'],
                question_type=QuestionType(q_data['type']),
                options=options,
                weight=q_data.get('weight', 1.0)
            )
            _QUESTIONS_CACHE.append(question)
        
        _QUESTIONS_LOADED = True
        
    except Exception as e:
        print(f"[ERROR] 설문 로드 실패: {e}")
        _QUESTIONS_LOADED = True
    
    return _QUESTIONS_CACHE


class YAMLQuestionRepository(IQuestionRepository):
    """
    YAML 파일에서 설문 문항을 로드하는 Repository
    
    싱글톤 패턴: 질문은 모듈 수준에서 한 번만 로드됨
    """
    
    def __init__(self, yaml_path: str = "config/assessment_questions.yaml"):
        self.yaml_path = Path(yaml_path)
        self._questions = _load_questions_once(self.yaml_path)
    
    def load_questions(self) -> List[Question]:
        """모든 질문 반환"""
        return self._questions
    
    def get_question(self, question_id: str) -> Optional[Question]:
        """특정 질문 조회"""
        for q in self._questions:
            if q.question_id == question_id:
                return q
        return None
    
    def get_questions_by_category(self, category: str) -> List[Question]:
        """카테고리별 질문 조회"""
        return [q for q in self._questions if q.category == category]
    
    def get_categories(self) -> List[str]:
        """모든 카테고리 목록 반환"""
        categories = set(q.category for q in self._questions)
        return list(categories)
    
    def get_total_questions(self) -> int:
        """전체 질문 수 반환"""
        return len(self._questions)

