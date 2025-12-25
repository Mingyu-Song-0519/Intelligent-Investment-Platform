"""
Watchlist 엔티티 정의
관심 종목 관리를 위한 도메인 엔티티
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from enum import Enum


class HeatLevel(Enum):
    """Market Buzz Heat Level"""
    HOT = "HOT"
    WARM = "WARM"
    COLD = "COLD"


@dataclass
class WatchlistItem:
    """
    관심 종목 항목
    
    사용자가 관심 목록에 추가한 개별 종목 정보
    """
    id: str
    user_id: str
    ticker: str
    stock_name: str
    market: str  # "KR" or "US"
    added_at: datetime
    notes: Optional[str] = None
    
    def __post_init__(self):
        """검증"""
        if self.market not in ("KR", "US"):
            raise ValueError(f"Invalid market: {self.market}. Must be 'KR' or 'US'")


@dataclass
class WatchlistSummary:
    """
    관심 종목 요약 정보
    
    관심 종목의 현재가, 기술지표, Phase 20/21 통합 정보를 포함
    """
    # 기본 정보
    item: WatchlistItem
    current_price: float
    prev_close: float
    change_pct: float
    volume: int
    
    # 기술 지표
    rsi: Optional[float] = None
    macd_signal: Optional[str] = None  # "매수", "중립", "매도"
    
    # === Phase 20 통합: 투자 성향 적합도 ===
    profile_fit_score: Optional[float] = None  # 0~100 점수
    profile_warning: Optional[str] = None  # 성향 불일치 경고 메시지
    
    # === Phase 21 통합: Market Buzz ===
    buzz_score: Optional[float] = None  # 0~100 Buzz 점수
    heat_level: Optional[HeatLevel] = None  # HOT/WARM/COLD
    volume_anomaly: bool = False  # 거래량 급증 여부
    
    @property
    def signal(self) -> str:
        """
        종합 매매 신호 판단
        
        RSI + MACD + 성향적합도를 종합하여 신호 생성
        """
        # RSI 기반 신호
        if self.rsi is not None:
            if self.rsi < 30:
                rsi_signal = "매수"
            elif self.rsi > 70:
                rsi_signal = "매도"
            else:
                rsi_signal = "중립"
        else:
            rsi_signal = "중립"
        
        # MACD 신호가 있으면 조합
        if self.macd_signal:
            if rsi_signal == self.macd_signal:
                return rsi_signal
            elif rsi_signal == "중립":
                return self.macd_signal
            elif self.macd_signal == "중립":
                return rsi_signal
            else:
                return "중립"  # 의견이 다르면 중립
        
        return rsi_signal
    
    @property
    def heat_emoji(self) -> str:
        """Heat Level 이모지 반환"""
        if self.heat_level == HeatLevel.HOT:
            return "🔥"
        elif self.heat_level == HeatLevel.WARM:
            return "🌤️"
        elif self.heat_level == HeatLevel.COLD:
            return "❄️"
        return ""
    
    @property
    def profile_fit_color(self) -> str:
        """성향 적합도에 따른 색상 코드 반환"""
        if self.profile_fit_score is None:
            return "#808080"  # 회색
        elif self.profile_fit_score >= 70:
            return "#4CAF50"  # 초록
        elif self.profile_fit_score >= 40:
            return "#FFC107"  # 노랑
        else:
            return "#F44336"  # 빨강


@dataclass
class PriceAlert:
    """
    가격 알림 설정
    
    특정 가격 도달 시 알림을 받기 위한 설정
    """
    id: str
    watchlist_item_id: str
    alert_type: str  # "target_price", "change_pct", "volume_spike"
    target_value: float
    is_active: bool = True
    triggered_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.now)
    
    def check_condition(self, current_price: float, change_pct: float, volume_ratio: float) -> bool:
        """알림 조건 충족 여부 확인"""
        if not self.is_active:
            return False
        
        if self.alert_type == "target_price":
            return current_price >= self.target_value
        elif self.alert_type == "change_pct":
            return abs(change_pct) >= self.target_value
        elif self.alert_type == "volume_spike":
            return volume_ratio >= self.target_value
        
        return False
