"""
Recommendation 도메인 엔티티
추천 및 피드백 관련 엔티티 정의
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional
from enum import Enum


class RecommendationStatus(Enum):
    """추천 상태"""
    PENDING = "pending"       # 대기 중
    ACCEPTED = "accepted"     # 수락됨
    REJECTED = "rejected"     # 거절됨
    EXPIRED = "expired"       # 만료됨


@dataclass
class Recommendation:
    """
    종목 추천 엔티티
    
    사용자 성향에 맞춰 생성된 개별 종목 추천
    """
    recommendation_id: str
    user_id: str
    ticker: str
    stock_name: str
    sector: str
    
    # 점수
    fit_score: float          # 성향 적합도 (0-100)
    trend_score: float        # 트렌드 점수 (0-100)
    ai_score: float           # AI 예측 점수 (0-100)
    composite_score: float    # 종합 점수 (0-100)
    
    # 상세 정보
    ai_prediction: str        # "상승", "하락", "보합"
    confidence: float         # AI 신뢰도 (0-1)
    recommendation_reason: str # 추천 사유
    
    # 메타데이터
    status: RecommendationStatus = RecommendationStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def accept(self) -> None:
        """추천 수락"""
        self.status = RecommendationStatus.ACCEPTED
        self.updated_at = datetime.now()
    
    def reject(self) -> None:
        """추천 거절"""
        self.status = RecommendationStatus.REJECTED
        self.updated_at = datetime.now()
    
    def to_dict(self) -> Dict:
        return {
            "recommendation_id": self.recommendation_id,
            "user_id": self.user_id,
            "ticker": self.ticker,
            "stock_name": self.stock_name,
            "sector": self.sector,
            "fit_score": self.fit_score,
            "trend_score": self.trend_score,
            "ai_score": self.ai_score,
            "composite_score": self.composite_score,
            "ai_prediction": self.ai_prediction,
            "confidence": self.confidence,
            "recommendation_reason": self.recommendation_reason,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "Recommendation":
        return cls(
            recommendation_id=data["recommendation_id"],
            user_id=data["user_id"],
            ticker=data["ticker"],
            stock_name=data["stock_name"],
            sector=data["sector"],
            fit_score=data["fit_score"],
            trend_score=data["trend_score"],
            ai_score=data["ai_score"],
            composite_score=data["composite_score"],
            ai_prediction=data["ai_prediction"],
            confidence=data["confidence"],
            recommendation_reason=data["recommendation_reason"],
            status=RecommendationStatus(data.get("status", "pending")),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"])
        )


@dataclass
class RecommendationFeedback:
    """
    추천 피드백 엔티티
    
    사용자의 추천 수락/거절 피드백을 기록
    프로필 학습에 활용
    """
    feedback_id: str
    recommendation_id: str
    user_id: str
    action: str  # "accept" or "reject"
    reason: str = ""  # 거절 사유 (자유 텍스트)
    
    # 추천 컨텍스트 (분석용)
    ticker: str = ""
    sector: str = ""
    
    created_at: datetime = field(default_factory=datetime.now)
    
    @property
    def is_accept(self) -> bool:
        return self.action == "accept"
    
    @property
    def is_reject(self) -> bool:
        return self.action == "reject"
    
    def to_dict(self) -> Dict:
        return {
            "feedback_id": self.feedback_id,
            "recommendation_id": self.recommendation_id,
            "user_id": self.user_id,
            "action": self.action,
            "reason": self.reason,
            "ticker": self.ticker,
            "sector": self.sector,
            "created_at": self.created_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "RecommendationFeedback":
        return cls(
            feedback_id=data["feedback_id"],
            recommendation_id=data["recommendation_id"],
            user_id=data["user_id"],
            action=data["action"],
            reason=data.get("reason", ""),
            ticker=data.get("ticker", ""),
            sector=data.get("sector", ""),
            created_at=datetime.fromisoformat(data["created_at"])
        )


@dataclass
class RankedStock:
    """
    순위가 매겨진 종목
    최종 사용자에게 표시되는 순위 리스트 항목
    """
    rank: int
    ticker: str
    stock_name: str
    sector: str
    
    # 점수
    composite_score: float
    profile_fit: float
    trend_score: float
    ai_score: float
    
    # 추가 정보
    ai_prediction: str
    confidence: float
    volatility: float = 0.0
    
    # 변화
    price_change_1d: float = 0.0
    price_change_1w: float = 0.0
    
    def to_dict(self) -> Dict:
        return {
            "rank": self.rank,
            "ticker": self.ticker,
            "stock_name": self.stock_name,
            "sector": self.sector,
            "composite_score": self.composite_score,
            "profile_fit": self.profile_fit,
            "trend_score": self.trend_score,
            "ai_score": self.ai_score,
            "ai_prediction": self.ai_prediction,
            "confidence": self.confidence,
            "volatility": self.volatility,
            "price_change_1d": self.price_change_1d,
            "price_change_1w": self.price_change_1w
        }
