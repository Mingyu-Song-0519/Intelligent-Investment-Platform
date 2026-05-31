"""
Market Data Domain Interfaces
Clean Architecture: Domain Layer

데이터 소스에 대한 추상화 인터페이스 정의 (DIP 준수)
"""
from abc import ABC, abstractmethod
from typing import Optional, List
from dataclasses import dataclass, field
from datetime import datetime
import pandas as pd


@dataclass
class OHLCV:
    """
    OHLCV 데이터 엔티티
    
    Attributes:
        ticker: 종목 코드
        data: OHLCV DataFrame (columns: open, high, low, close, volume)
        source: 데이터 출처 (yahoo, naver, pykrx 등)
        fetched_at: 데이터 수집 시각
    """
    ticker: str
    data: pd.DataFrame
    source: str = "unknown"
    fetched_at: datetime = field(default_factory=datetime.now)
    
    @classmethod
    def from_dataframe(cls, ticker: str, df: pd.DataFrame, source: str = "unknown") -> 'OHLCV':
        """DataFrame에서 OHLCV 생성"""
        # 컬럼명 정규화
        df = df.copy()
        df.columns = [c.lower() for c in df.columns]
        
        required_cols = ['open', 'high', 'low', 'close', 'volume']
        for col in required_cols:
            if col not in df.columns:
                # 대체 컬럼명 시도
                alt_names = {
                    'open': ['시가', 'Open'],
                    'high': ['고가', 'High'],
                    'low': ['저가', 'Low'],
                    'close': ['종가', 'Close', 'adj close'],
                    'volume': ['거래량', 'Volume']
                }
                for alt in alt_names.get(col, []):
                    if alt.lower() in df.columns:
                        df = df.rename(columns={alt.lower(): col})
                        break
        
        return cls(ticker=ticker, data=df, source=source)
    
    def to_dataframe(self) -> pd.DataFrame:
        """DataFrame으로 변환"""
        return self.data.copy()
    
    def is_valid(self) -> bool:
        """데이터 유효성 검증"""
        if self.data is None or self.data.empty:
            return False
        required_cols = ['open', 'high', 'low', 'close', 'volume']
        return all(col in self.data.columns for col in required_cols)
    
    def __len__(self) -> int:
        return len(self.data) if self.data is not None else 0


# @MX:ANCHOR: 헥사고날 아키텍처 핵심 포트 — 모든 데이터 소스가 이 인터페이스를 구현
# @MX:REASON: [AUTO] Yahoo, PyKRX, KIS 게이트웨이 3개 구현체 + FallbackGateway 의존. fan_in=4+
class IStockDataGateway(ABC):
    """
    주식 데이터 게이트웨이 인터페이스 (DIP)

    모든 데이터 소스 구현체는 이 인터페이스를 구현해야 합니다.
    Application Layer는 이 인터페이스에만 의존합니다.
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """게이트웨이 이름"""
        pass
    
    @abstractmethod
    def fetch_ohlcv(
        self,
        ticker: str,
        start: Optional[str] = None,
        end: Optional[str] = None,
        period: str = "1y"
    ) -> Optional[pd.DataFrame]:
        """
        OHLCV 데이터 조회
        
        Args:
            ticker: 종목 코드 (예: '005930', 'AAPL')
            start: 시작일 (YYYY-MM-DD)
            end: 종료일 (YYYY-MM-DD)
            period: 조회 기간 (start/end가 없을 때 사용)
            
        Returns:
            OHLCV DataFrame 또는 None (실패 시)
        """
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """
        데이터 소스 사용 가능 여부 확인
        
        Returns:
            True if 사용 가능, False otherwise
        """
        pass
    
    def supports_ticker(self, ticker: str) -> bool:
        """
        해당 게이트웨이가 특정 티커를 지원하는지 확인
        
        Args:
            ticker: 종목 코드
            
        Returns:
            True if 지원, False otherwise
        """
        return True  # 기본값: 모든 티커 지원


# @MX:ANCHOR: 캐시 레이어 포트 — SQLiteMarketDataCache가 유일 구현체. 교체 시 이 인터페이스 유지
# @MX:REASON: [AUTO] market_data_service, fallback_gateway 등 다수 호출. fan_in=3+
class IMarketDataCache(ABC):
    """
    시장 데이터 캐시 인터페이스
    """
    
    @abstractmethod
    def get(self, ticker: str, start: str, end: str) -> Optional[OHLCV]:
        """캐시에서 데이터 조회"""
        pass
    
    @abstractmethod
    def save(self, ohlcv: OHLCV) -> bool:
        """캐시에 데이터 저장"""
        pass
    
    @abstractmethod
    def invalidate(self, ticker: str) -> bool:
        """캐시 무효화"""
        pass


class DataUnavailableError(Exception):
    """데이터를 사용할 수 없을 때 발생하는 예외"""
    pass


class DataNotFoundError(Exception):
    """요청한 데이터가 존재하지 않을 때 발생하는 예외"""
    pass
