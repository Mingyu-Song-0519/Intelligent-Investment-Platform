"""
InvestorProfile 엔티티
투자자의 투자 성향 프로필을 표현하는 핵심 도메인 엔티티
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional
import json

from src.domain.investment_profile.value_objects.risk_tolerance import RiskTolerance, RiskLevel


@dataclass
class InvestorProfile:
    """
    투자자 프로필 엔티티
    
    Clean Architecture: Domain Entity
    - 비즈니스 로직을 포함하는 Rich Domain Model
    - 외부 의존성 없음
    
    Attributes:
        user_id: 사용자 식별자
        risk_tolerance: 위험 감수 수준 (0-100)
        investment_horizon: 투자 기간 (short/medium/long)
        preferred_sectors: 선호 섹터 목록
        style_scores: 투자 스타일 점수 (value/growth/momentum)
        created_at: 프로필 생성 시간
        last_updated: 마지막 수정 시간
    """
    user_id: str
    risk_tolerance: RiskTolerance
    investment_horizon: str  # short, medium, long
    preferred_sectors: List[str] = field(default_factory=list)
    style_scores: Dict[str, float] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    last_updated: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        """초기화 후 검증"""
        valid_horizons = {"short", "medium", "long"}
        if self.investment_horizon not in valid_horizons:
            raise ValueError(f"investment_horizon must be one of {valid_horizons}")
        
        # 스타일 점수 기본값 설정
        if not self.style_scores:
            self.style_scores = {"value": 33.3, "growth": 33.3, "momentum": 33.4}
    
    @property
    def profile_type(self) -> str:
        """프로필 유형 이름 반환"""
        return self.risk_tolerance.level_name
    
    @property
    def risk_level(self) -> RiskLevel:
        """위험 수준 반환"""
        return self.risk_tolerance.level
    
    def adjust_risk_tolerance(self, delta: int) -> None:
        """위험 감수 점수 조정"""
        self.risk_tolerance = self.risk_tolerance.adjust(delta)
        self.last_updated = datetime.now()
    
    def add_preferred_sector(self, sector: str) -> None:
        """선호 섹터 추가"""
        if sector not in self.preferred_sectors:
            self.preferred_sectors.append(sector)
            self.last_updated = datetime.now()
    
    def remove_preferred_sector(self, sector: str) -> None:
        """선호 섹터 제거"""
        if sector in self.preferred_sectors:
            self.preferred_sectors.remove(sector)
            self.last_updated = datetime.now()
    
    def adjust_style_score(self, style: str, delta: float) -> None:
        """투자 스타일 점수 조정"""
        if style in self.style_scores:
            new_score = max(0, min(100, self.style_scores[style] + delta))
            self.style_scores[style] = new_score
            self.last_updated = datetime.now()
    
    def is_outdated(self, threshold_days: int = 180) -> bool:
        """프로필이 오래되었는지 확인 (기본 6개월)"""
        days_since_update = (datetime.now() - self.last_updated).days
        return days_since_update > threshold_days
    
    def to_dict(self) -> Dict:
        """딕셔너리로 변환 (직렬화용)"""
        return {
            "user_id": self.user_id,
            "risk_tolerance": self.risk_tolerance.value,
            "investment_horizon": self.investment_horizon,
            "preferred_sectors": self.preferred_sectors,
            "style_scores": self.style_scores,
            "created_at": self.created_at.isoformat(),
            "last_updated": self.last_updated.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "InvestorProfile":
        """딕셔너리에서 생성 (역직렬화용)"""
        return cls(
            user_id=data["user_id"],
            risk_tolerance=RiskTolerance(data["risk_tolerance"]),
            investment_horizon=data["investment_horizon"],
            preferred_sectors=data.get("preferred_sectors", []),
            style_scores=data.get("style_scores", {}),
            created_at=datetime.fromisoformat(data["created_at"]),
            last_updated=datetime.fromisoformat(data["last_updated"])
        )
    
    @classmethod
    def create_default(cls, user_id: str) -> "InvestorProfile":
        """
        기본 프로필 생성 (균형형)
        설문 미응답 사용자용 Cold Start 대응
        """
        return cls(
            user_id=user_id,
            risk_tolerance=RiskTolerance(50),  # 균형형
            investment_horizon="medium",
            preferred_sectors=["Technology", "Healthcare", "Financials"],
            style_scores={"value": 33.3, "growth": 33.3, "momentum": 33.4},
            created_at=datetime.now(),
            last_updated=datetime.now()
        )
    
    def get_ideal_volatility_range(self) -> tuple[float, float]:
        """프로필에 맞는 이상적인 변동성 범위 반환"""
        return self.risk_tolerance.ideal_volatility_range
    
    def calculate_sector_match_score(self, stock_sector: str) -> float:
        """종목 섹터와의 매칭 점수 계산 (0-100)"""
        if stock_sector in self.preferred_sectors:
            return 100.0
        return 30.0  # 선호 섹터가 아닌 경우 기본 점수
    
    def calculate_style_similarity(self, stock_style_scores: Dict[str, float]) -> float:
        """종목 투자 스타일과의 유사도 계산 (0-100)"""
        similarity = 0.0
        for style in ["value", "growth", "momentum"]:
            profile_score = self.style_scores.get(style, 33.3)
            stock_score = stock_style_scores.get(style, 33.3)
            # 코사인 유사도 기반 (단순화)
            similarity += (profile_score * stock_score) / 100
        return similarity
