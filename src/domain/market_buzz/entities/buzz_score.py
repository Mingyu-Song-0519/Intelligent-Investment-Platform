"""
BuzzScore Entity - 종목별 관심도 점수

Phase 20 투자 성향 프로필 연동 지원:
- profile_fit_score: 사용자 성향과의 적합도 (0~100)
- final_score: 종합 점수 (base_score * 0.6 + profile_fit * 0.4)
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class BuzzScore:
    """
    종목별 관심도 점수 엔티티
    
    Attributes:
        ticker: 종목 코드 (예: "005930.KS", "AAPL")
        name: 종목명
        base_score: 기본 Buzz 점수 (0~100) - 거래량/변동성 기반
        profile_fit_score: 프로필 적합도 (0~100) - Phase 20 연동, Optional
        final_score: 종합 점수 - profile_fit이 있으면 가중 평균, 없으면 base_score
        volume_ratio: 평소 대비 거래량 비율 (예: 3.2 = 320%)
        volatility_ratio: 평소 대비 변동성 비율
        heat_level: 관심도 레벨 ("HOT", "WARM", "COLD")
        sector: 소속 섹터 (Optional, Phase 20 필터링용)
        last_updated: 마지막 계산 시각
    """
    ticker: str
    name: str
    base_score: float  # 0~100
    volume_ratio: float
    volatility_ratio: float
    heat_level: str  # "HOT" | "WARM" | "COLD"
    last_updated: datetime
    
    # Phase 20 Integration (Optional)
    profile_fit_score: Optional[float] = None  # 0~100
    sector: Optional[str] = None
    
    @property
    def final_score(self) -> float:
        """
        최종 점수 계산
        
        - profile_fit이 있으면: base_score * 0.6 + profile_fit * 0.4
        - 없으면: base_score 그대로 사용
        """
        if self.profile_fit_score is not None:
            return self.base_score * 0.6 + self.profile_fit_score * 0.4
        return self.base_score
    
    def is_hot(self) -> bool:
        """HOT 등급 여부 (final_score >= 70)"""
        return self.final_score >= 70
    
    def is_warm(self) -> bool:
        """WARM 등급 여부 (40 <= final_score < 70)"""
        return 40 <= self.final_score < 70
    
    def is_cold(self) -> bool:
        """COLD 등급 여부 (final_score < 40)"""
        return self.final_score < 40
    
    def __lt__(self, other: 'BuzzScore') -> bool:
        """정렬용: final_score 기준 내림차순"""
        return self.final_score > other.final_score
