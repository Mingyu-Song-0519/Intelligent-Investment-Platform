"""
HeatLevel Value Object - 관심도 레벨
"""
from enum import Enum


class HeatLevel(str, Enum):
    """
    관심도/온도 레벨 열거형
    
    - HOT: 매우 높은 관심도 (score >= 70 또는 avg_change >= 3%)
    - WARM: 보통 관심도 (40 <= score < 70)
    - COLD: 낮은 관심도 (score < 40 또는 avg_change < -2%)
    """
    HOT = "HOT"
    WARM = "WARM"
    COLD = "COLD"
    
    @classmethod
    def from_score(cls, score: float) -> 'HeatLevel':
        """점수 기반 레벨 판정 (BuzzScore용)"""
        if score >= 70:
            return cls.HOT
        elif score >= 40:
            return cls.WARM
        else:
            return cls.COLD
    
    @classmethod
    def from_change_pct(cls, change_pct: float) -> 'HeatLevel':
        """등락률 기반 레벨 판정 (SectorHeat용)"""
        if change_pct > 3.0:
            return cls.HOT
        elif change_pct < -2.0:
            return cls.COLD
        else:
            return cls.WARM
    
    def to_emoji(self) -> str:
        """레벨별 이모지 반환"""
        if self == HeatLevel.HOT:
            return "🔥"
        elif self == HeatLevel.COLD:
            return "❄️"
        else:
            return "🌤️"
    
    def to_color(self) -> str:
        """Plotly 차트용 색상 코드 반환"""
        if self == HeatLevel.HOT:
            return "#FF4444"  # 빨강
        elif self == HeatLevel.COLD:
            return "#4444FF"  # 파랑
        else:
            return "#FFA500"  # 주황
