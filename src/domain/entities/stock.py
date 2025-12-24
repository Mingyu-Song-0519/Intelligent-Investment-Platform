"""
주식 엔티티 - Clean Architecture Domain Layer
종목의 핵심 속성과 비즈니스 로직을 캡슐화
"""
from dataclasses import dataclass, field
from typing import List, Optional, Dict
from datetime import datetime
import pandas as pd


@dataclass
class PriceData:
    """가격 데이터 Value Object"""
    open: float
    high: float
    low: float
    close: float
    volume: int
    date: datetime
    
    @property
    def typical_price(self) -> float:
        """전형가 = (High + Low + Close) / 3"""
        return (self.high + self.low + self.close) / 3
    
    @property
    def is_bullish(self) -> bool:
        """양봉 여부"""
        return self.close > self.open


@dataclass 
class StockEntity:
    """주식 종목 엔티티"""
    ticker: str
    name: str
    market: str  # "KR" or "US"
    price_history: List[PriceData] = field(default_factory=list)
    
    # 메타데이터
    sector: Optional[str] = None
    industry: Optional[str] = None
    market_cap: Optional[float] = None
    
    @classmethod
    def from_dataframe(cls, ticker: str, df: pd.DataFrame, name: str = "", market: str = "US") -> 'StockEntity':
        """
        DataFrame에서 StockEntity 생성
        
        Args:
            ticker: 종목 코드
            df: OHLCV DataFrame (columns: Open, High, Low, Close, Volume)
            name: 종목 이름
            market: 시장 코드
        """
        price_history = []
        
        for idx, row in df.iterrows():
            price = PriceData(
                open=row.get('Open', row.get('open', 0)),
                high=row.get('High', row.get('high', 0)),
                low=row.get('Low', row.get('low', 0)),
                close=row.get('Close', row.get('close', 0)),
                volume=int(row.get('Volume', row.get('volume', 0))),
                date=idx if isinstance(idx, datetime) else datetime.now()
            )
            price_history.append(price)
        
        return cls(
            ticker=ticker,
            name=name or ticker,
            market=market,
            price_history=price_history
        )
    
    def to_dataframe(self) -> pd.DataFrame:
        """StockEntity를 DataFrame으로 변환"""
        data = []
        for p in self.price_history:
            data.append({
                'date': p.date,
                'open': p.open,
                'high': p.high,
                'low': p.low,
                'close': p.close,
                'volume': p.volume
            })
        
        df = pd.DataFrame(data)
        if not df.empty:
            df.set_index('date', inplace=True)
        return df
    
    @property
    def latest_price(self) -> Optional[float]:
        """최신 종가"""
        if self.price_history:
            return self.price_history[-1].close
        return None
    
    @property
    def price_change_pct(self) -> Optional[float]:
        """전일 대비 변동률"""
        if len(self.price_history) >= 2:
            prev = self.price_history[-2].close
            curr = self.price_history[-1].close
            return (curr - prev) / prev * 100 if prev != 0 else 0
        return None
    
    # ===== 비즈니스 로직 추가 (Phase 10-1) =====
    
    def get_price_range(self, days: int = 5) -> tuple[float, float]:
        """
        최근 N일 가격 범위
        
        Args:
            days: 조회 기간 (일)
            
        Returns:
            (최저가, 최고가)
        """
        if len(self.price_history) < days:
            days = len(self.price_history)
        
        recent_prices = self.price_history[-days:]
        if not recent_prices:
            return (0.0, 0.0)
        
        low = min(p.low for p in recent_prices)
        high = max(p.high for p in recent_prices)
        
        return (low, high)
    
    def calculate_return(self, days: int = 30) -> Optional[float]:
        """
        N일 수익률 계산
        
        Args:
            days: 조회 기간 (일)
            
        Returns:
            수익률 (%)
        """
        if len(self.price_history) <= days:
            return None
        
        start_price = self.price_history[-days].close
        end_price = self.price_history[-1].close
        
        if start_price == 0:
            return None
        
        return (end_price - start_price) / start_price * 100
    
    def calculate_volatility(self, days: int = 20) -> Optional[float]:
        """
        과거 변동성 계산 (일간 수익률 표준편차)
        
        Args:
            days: 조회 기간 (일)
            
        Returns:
            연율화 변동성 (%)
        """
        if len(self.price_history) < days + 1:
            return None
        
        # 일간 수익률 계산
        returns = []
        for i in range(-days, 0):
            curr = self.price_history[i].close
            prev = self.price_history[i-1].close
            if prev != 0:
                daily_return = (curr - prev) / prev
                returns.append(daily_return)
        
        if not returns:
            return None
        
        # 표준편차 계산
        import statistics
        std = statistics.stdev(returns)
        
        # 연율화 (252 거래일)
        annual_vol = std * (252 ** 0.5) * 100
        
        return annual_vol
    
    def is_trending_up(self, short_period: int = 5, long_period: int = 20) -> bool:
        """
        상승 추세 여부 (단기 평균 > 장기 평균)
        
        Args:
            short_period: 단기 이동평균 기간
            long_period: 장기 이동평균 기간
        """
        if len(self.price_history) < long_period:
            return False
        
        # 단기 평균
        short_prices = [p.close for p in self.price_history[-short_period:]]
        short_ma = sum(short_prices) / len(short_prices)
        
        # 장기 평균
        long_prices = [p.close for p in self.price_history[-long_period:]]
        long_ma = sum(long_prices) / len(long_prices)
        
        return short_ma > long_ma
    
    def get_max_drawdown(self) -> float:
        """
        MDD (Maximum Drawdown) 계산
        
        Returns:
            MDD (%)
        """
        if len(self.price_history) < 2:
            return 0.0
        
        peak = self.price_history[0].close
        max_dd = 0.0
        
        for price_data in self.price_history:
            # 신고점 갱신
            if price_data.close > peak:
                peak = price_data.close
            
            # 낙폭 계산
            drawdown = (peak - price_data.close) / peak * 100 if peak != 0 else 0
            
            # 최대 낙폭 갱신
            if drawdown > max_dd:
                max_dd = drawdown
        
        return max_dd


@dataclass
class PortfolioEntity:
    """포트폴리오 엔티티"""
    portfolio_id: str
    name: str
    holdings: Dict[str, float] = field(default_factory=dict)  # ticker -> 비중
    cash: float = 0.0
    
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def add_holding(self, ticker: str, weight: float):
        """종목 추가/업데이트"""
        self.holdings[ticker] = weight
        self.updated_at = datetime.now()
    
    def remove_holding(self, ticker: str):
        """종목 제거"""
        if ticker in self.holdings:
            del self.holdings[ticker]
            self.updated_at = datetime.now()
    
    @property
    def total_weight(self) -> float:
        """전체 비중 합계"""
        return sum(self.holdings.values())
    
    def normalize_weights(self):
        """비중 정규화 (합계 = 1)"""
        total = self.total_weight
        if total > 0:
            self.holdings = {k: v / total for k, v in self.holdings.items()}
            self.updated_at = datetime.now()


@dataclass
class SignalEntity:
    """매매 신호 엔티티"""
    
    class SignalType:
        BUY = "BUY"
        SELL = "SELL"
        HOLD = "HOLD"
        STRONG_BUY = "STRONG_BUY"
        STRONG_SELL = "STRONG_SELL"
    
    ticker: str
    signal_type: str  # SignalType
    confidence: float  # 0.0 ~ 1.0
    reason: str = ""
    
    # 가격 정보
    target_price: Optional[float] = None
    stop_loss: Optional[float] = None
    
    # 메타데이터
    generated_at: datetime = field(default_factory=datetime.now)
    source: str = ""  # "AI", "TECHNICAL", "FUNDAMENTAL"
    
    @property
    def is_bullish(self) -> bool:
        """강세 신호 여부"""
        return self.signal_type in [self.SignalType.BUY, self.SignalType.STRONG_BUY]
    
    @property
    def is_bearish(self) -> bool:
        """약세 신호 여부"""
        return self.signal_type in [self.SignalType.SELL, self.SignalType.STRONG_SELL]
    
    def to_emoji(self) -> str:
        """신호를 이모지로 변환"""
        emoji_map = {
            self.SignalType.STRONG_BUY: "🟢🟢",
            self.SignalType.BUY: "🟢",
            self.SignalType.HOLD: "🟡",
            self.SignalType.SELL: "🔴",
            self.SignalType.STRONG_SELL: "🔴🔴"
        }
        return emoji_map.get(self.signal_type, "⚪")
