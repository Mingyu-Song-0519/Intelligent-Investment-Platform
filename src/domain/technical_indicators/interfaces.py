"""
Technical Indicators Service Interface
Domain Layer - Interface정의 (DIP)
"""
from abc import ABC, abstractmethod
from typing import Optional
import pandas as pd


class ITechnicalIndicatorsService(ABC):
    """기술적 지표 계산 서비스 인터페이스"""
    
    @abstractmethod
    def calculate_rsi_vectorized(
        self,
        ohlcv_data: pd.DataFrame,
        close_col: str = '종가',
        period: int = 14
    ) -> pd.Series:
        """
        벡터화된 RSI 계산
        
        Args:
            ohlcv_data: MultiIndex DataFrame (ticker, date)
            close_col:  종가 컬럼명
            period: RSI 기간 (기본 14일)
            
        Returns:
            Series with RSI values
        """
        pass
    
    @abstractmethod
    def calculate_ma_batch(
        self,
        ohlcv_data: pd.DataFrame,
        close_col: str = '종가',
        periods: list = [5, 20, 60, 120]
    ) -> pd.DataFrame:
        """
        이동평균선 배치 계산
        
        Args:
            ohlcv_data: MultiIndex DataFrame
            close_col: 종가 컬럼명
            periods: MA 기간 리스트
            
        Returns:
            DataFrame with MA columns
        """
        pass
    
    @abstractmethod
    def calculate_macd(
        self,
        ohlcv_data: pd.DataFrame,
        close_col: str = '종가',
        fast: int = 12,
        slow: int = 26,
        signal: int = 9
    ) -> pd.DataFrame:
        """
        MACD 계산
        
        Returns:
            DataFrame with MACD, Signal, Histogram columns
        """
        pass
