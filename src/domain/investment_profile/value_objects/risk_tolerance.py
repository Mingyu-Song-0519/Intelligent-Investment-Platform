"""
RiskTolerance Value Object
투자 위험 감수 수준을 표현하는 값 객체
"""
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class RiskLevel(Enum):
    """위험 감수 수준 유형"""
    CONSERVATIVE = "안정형"
    MODERATELY_CONSERVATIVE = "안정추구형"
    BALANCED = "균형형"
    GROWTH_SEEKING = "성장추구형"
    AGGRESSIVE = "공격투자형"


@dataclass(frozen=True)
class RiskTolerance:
    """
    위험 감수 수준 Value Object
    
    Attributes:
        value: 0-100 사이의 점수
        
    0-20: 안정형
    21-40: 안정추구형
    41-60: 균형형
    61-80: 성장추구형
    81-100: 공격투자형
    """
    value: int
    
    def __post_init__(self):
        if not 0 <= self.value <= 100:
            raise ValueError(f"RiskTolerance value must be 0-100, got {self.value}")
    
    @property
    def level(self) -> RiskLevel:
        """위험 수준 유형 반환"""
        if self.value <= 20:
            return RiskLevel.CONSERVATIVE
        elif self.value <= 40:
            return RiskLevel.MODERATELY_CONSERVATIVE
        elif self.value <= 60:
            return RiskLevel.BALANCED
        elif self.value <= 80:
            return RiskLevel.GROWTH_SEEKING
        else:
            return RiskLevel.AGGRESSIVE
    
    @property
    def level_name(self) -> str:
        """한글 레벨 이름 반환"""
        return self.level.value
    
    @property
    def ideal_volatility_range(self) -> tuple[float, float]:
        """성향에 맞는 이상적인 변동성 범위 반환"""
        if self.value <= 20:
            return (0.0, 0.15)
        elif self.value <= 40:
            return (0.10, 0.25)
        elif self.value <= 60:
            return (0.20, 0.35)
        elif self.value <= 80:
            return (0.30, 0.50)
        else:
            return (0.40, 1.00)
    
    def adjust(self, delta: int) -> "RiskTolerance":
        """위험 감수 점수 조정 (새 인스턴스 반환)"""
        new_value = max(0, min(100, self.value + delta))
        return RiskTolerance(new_value)
    
    def to_dict(self) -> dict:
        """딕셔너리로 변환"""
        return {
            "value": self.value,
            "level": self.level.name,
            "level_name": self.level_name
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "RiskTolerance":
        """딕셔너리에서 생성"""
        return cls(value=data["value"])
