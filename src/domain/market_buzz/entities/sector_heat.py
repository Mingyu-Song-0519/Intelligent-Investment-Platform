"""
SectorHeat Entity - 섹터별 온도 정보
"""
from dataclasses import dataclass
from typing import List


@dataclass
class SectorHeat:
    """
    섹터별 온도 정보 엔티티
    
    Attributes:
        sector_name: 섹터명 (예: "Technology", "반도체")
        avg_change_pct: 섹터 평균 등락률 (%)
        top_gainers: 상위 상승 종목 리스트 (ticker, name, change%)
        top_losers: 상위 하락 종목 리스트
        heat_level: 온도 레벨 ("HOT", "WARM", "COLD")
        stock_count: 섹터 내 종목 수
        total_market_cap: 섹터 전체 시가총액 (Optional, Treemap 크기용)
    """
    sector_name: str
    avg_change_pct: float
    top_gainers: List[dict]  # [{"ticker": "...", "name": "...", "change_pct": 5.2}, ...]
    top_losers: List[dict]
    heat_level: str  # "HOT" | "WARM" | "COLD"
    stock_count: int
    total_market_cap: float = 0.0
    
    def is_hot(self) -> bool:
        """HOT 섹터 여부 (avg_change_pct > 3%)"""
        return self.avg_change_pct > 3.0
    
    def is_cold(self) -> bool:
        """COLD 섹터 여부 (avg_change_pct < -2%)"""
        return self.avg_change_pct < -2.0
    
    def get_heat_emoji(self) -> str:
        """온도 레벨별 이모지 반환"""
        if self.heat_level == "HOT":
            return "🔥"
        elif self.heat_level == "COLD":
            return "❄️"
        else:
            return "🌤️"
    
    def get_summary(self) -> str:
        """
        섹터 요약 문자열
        
        Returns:
            예: "🔥 Technology +4.2% (52개 종목)"
        """
        emoji = self.get_heat_emoji()
        return f"{emoji} {self.sector_name} {self.avg_change_pct:+.1f}% ({self.stock_count}개 종목)"
    
    def __lt__(self, other: 'SectorHeat') -> bool:
        """정렬용: avg_change_pct 기준 내림차순"""
        return self.avg_change_pct > other.avg_change_pct
