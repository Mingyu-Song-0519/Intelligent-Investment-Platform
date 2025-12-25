"""
VolumeAnomaly Entity - 거래량 이상 감지 결과
"""
from dataclasses import dataclass
from datetime import datetime


@dataclass
class VolumeAnomaly:
    """
    거래량 이상 감지 결과 엔티티
    
    Attributes:
        ticker: 종목 코드
        name: 종목명
        current_volume: 현재 거래량
        avg_volume: 평균 거래량 (20일 기준)
        volume_ratio: 거래량 비율 (current / avg)
        is_spike: Spike 여부 (ratio > threshold, 기본 2.0)
        detected_at: 감지 시각
        price_change_pct: 당일 등락률 (Optional)
    """
    ticker: str
    name: str
    current_volume: int
    avg_volume: int
    volume_ratio: float
    is_spike: bool
    detected_at: datetime
    price_change_pct: float = 0.0
    
    @property
    def volume_increase_pct(self) -> float:
        """거래량 증가율 (%) = (ratio - 1) * 100"""
        return (self.volume_ratio - 1) * 100
    
    def get_alert_message(self) -> str:
        """
        사용자 알림 메시지 생성
        
        Returns:
            예: "🚀 삼성전자: 평소 대비 320% 거래량 폭발! (+5.2%)"
        """
        emoji = "🚀" if self.is_spike else "📊"
        change_str = f" ({self.price_change_pct:+.1f}%)" if self.price_change_pct != 0 else ""
        return f"{emoji} {self.name}: 평소 대비 {self.volume_increase_pct:.0f}% 거래량 급증!{change_str}"
    
    def __lt__(self, other: 'VolumeAnomaly') -> bool:
        """정렬용: volume_ratio 기준 내림차순"""
        return self.volume_ratio > other.volume_ratio
