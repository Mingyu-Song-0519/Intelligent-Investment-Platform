"""
AI Report Domain Entities
투자 분석 리포트 관련 도메인 엔티티
Clean Architecture: Domain Layer
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List
from enum import Enum


class SignalType(Enum):
    """매매 신호 유형"""
    STRONG_BUY = "강력 매수"
    BUY = "매수"
    HOLD = "보유"
    SELL = "매도"
    STRONG_SELL = "강력 매도"
    
    @classmethod
    def from_string(cls, value: str) -> "SignalType":
        """문자열에서 SignalType 파싱"""
        value_upper = value.upper().strip()
        
        mapping = {
            "STRONG_BUY": cls.STRONG_BUY,
            "강력 매수": cls.STRONG_BUY,
            "강력매수": cls.STRONG_BUY,
            "BUY": cls.BUY,
            "매수": cls.BUY,
            "HOLD": cls.HOLD,
            "보유": cls.HOLD,
            "중립": cls.HOLD,
            "SELL": cls.SELL,
            "매도": cls.SELL,
            "STRONG_SELL": cls.STRONG_SELL,
            "강력 매도": cls.STRONG_SELL,
            "강력매도": cls.STRONG_SELL
        }
        
        return mapping.get(value_upper, cls.HOLD)


@dataclass
class InvestmentReport:
    """
    AI 투자 분석 리포트
    
    Gemini API로 생성된 종목 분석 결과를 담는 엔티티
    """
    ticker: str
    stock_name: str
    signal: SignalType
    confidence_score: float  # 0-100
    summary: str  # AI 분석 요약 (3-5줄)
    reasoning: str  # 상세 논리
    generated_at: datetime = field(default_factory=datetime.now)
    
    # 분석에 사용된 데이터 출처
    data_sources: List[str] = field(default_factory=list)
    
    # 사용자 프로필 기반 개인화 정보
    profile_adjusted: bool = False
    profile_warning: Optional[str] = None
    
    @property
    def is_actionable(self) -> bool:
        """실행 가능한 신호인지 (신뢰도 80% 이상)"""
        return self.confidence_score >= 80
    
    @property
    def signal_emoji(self) -> str:
        """신호에 따른 이모지"""
        emoji_map = {
            SignalType.STRONG_BUY: "🚀",
            SignalType.BUY: "📈",
            SignalType.HOLD: "➡️",
            SignalType.SELL: "📉",
            SignalType.STRONG_SELL: "🔻"
        }
        return emoji_map.get(self.signal, "➡️")
    
    @property
    def signal_color(self) -> str:
        """신호에 따른 색상 코드"""
        color_map = {
            SignalType.STRONG_BUY: "#00C853",
            SignalType.BUY: "#4CAF50",
            SignalType.HOLD: "#9E9E9E",
            SignalType.SELL: "#FF9800",
            SignalType.STRONG_SELL: "#F44336"
        }
        return color_map.get(self.signal, "#9E9E9E")
    
    def to_dict(self) -> dict:
        """딕셔너리로 변환 (직렬화용)"""
        return {
            "ticker": self.ticker,
            "stock_name": self.stock_name,
            "signal": self.signal.value,
            "confidence_score": self.confidence_score,
            "summary": self.summary,
            "reasoning": self.reasoning,
            "generated_at": self.generated_at.isoformat(),
            "data_sources": self.data_sources,
            "profile_adjusted": self.profile_adjusted,
            "profile_warning": self.profile_warning
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "InvestmentReport":
        """딕셔너리에서 생성"""
        return cls(
            ticker=data["ticker"],
            stock_name=data["stock_name"],
            signal=SignalType.from_string(data["signal"]),
            confidence_score=data["confidence_score"],
            summary=data["summary"],
            reasoning=data["reasoning"],
            generated_at=datetime.fromisoformat(data["generated_at"]),
            data_sources=data.get("data_sources", []),
            profile_adjusted=data.get("profile_adjusted", False),
            profile_warning=data.get("profile_warning")
        )
