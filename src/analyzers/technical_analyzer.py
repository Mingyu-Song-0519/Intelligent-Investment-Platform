"""
기술적 분석 모듈 - RSI, MACD, 볼린저 밴드 등 주요 지표 계산
"""
import pandas as pd
import numpy as np
from typing import Optional, Tuple
import sys
from pathlib import Path

# 프로젝트 루트 경로 설정
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config import INDICATOR_PARAMS


class TechnicalAnalyzer:
    """기술적 지표 계산 클래스"""
    
    def __init__(self, df: pd.DataFrame, price_col: str = 'close'):
        """
        Args:
            df: OHLCV 데이터가 담긴 DataFrame
            price_col: 가격 컬럼명 (기본값: 'close')
        """
        self.df = df.copy()
        self.price_col = price_col
        self._validate_data()
    
    def _validate_data(self):
        """데이터 유효성 검증"""
        required_cols = ['open', 'high', 'low', 'close', 'volume']
        missing = [col for col in required_cols if col not in self.df.columns]
        if missing:
            raise ValueError(f"필수 컬럼 누락: {missing}")
    
    # =========================================================================
    # 이동평균선 (Moving Averages)
    # =========================================================================
    
    def sma(self, period: int) -> pd.Series:
        """
        단순 이동평균 (Simple Moving Average)
        
        Args:
            period: 이동평균 기간
            
        Returns:
            SMA 시리즈
        """
        return self.df[self.price_col].rolling(window=period).mean()
    
    def ema(self, period: int) -> pd.Series:
        """
        지수 이동평균 (Exponential Moving Average)
        
        Args:
            period: 이동평균 기간
            
        Returns:
            EMA 시리즈
        """
        return self.df[self.price_col].ewm(span=period, adjust=False).mean()
    
    def add_moving_averages(self) -> 'TechnicalAnalyzer':
        """모든 이동평균 지표를 DataFrame에 추가"""
        sma_periods = INDICATOR_PARAMS['SMA']['periods']
        ema_periods = INDICATOR_PARAMS['EMA']['periods']
        
        for period in sma_periods:
            self.df[f'sma_{period}'] = self.sma(period)
        
        for period in ema_periods:
            self.df[f'ema_{period}'] = self.ema(period)
        
        return self
    
    # =========================================================================
    # RSI (Relative Strength Index)
    # =========================================================================
    
    def rsi(self, period: int = None) -> pd.Series:
        """
        상대강도지수 (RSI) 계산
        
        RSI = 100 - (100 / (1 + RS))
        RS = 평균 상승폭 / 평균 하락폭
        
        Args:
            period: RSI 기간 (기본값: config 설정)
            
        Returns:
            RSI 시리즈 (0-100)
        """
        period = period or INDICATOR_PARAMS['RSI']['period']
        
        delta = self.df[self.price_col].diff()
        
        gain = delta.where(delta > 0, 0)
        loss = (-delta).where(delta < 0, 0)
        
        avg_gain = gain.rolling(window=period).mean()
        avg_loss = loss.rolling(window=period).mean()
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def add_rsi(self, period: int = None) -> 'TechnicalAnalyzer':
        """RSI를 DataFrame에 추가"""
        period = period or INDICATOR_PARAMS['RSI']['period']
        self.df['rsi'] = self.rsi(period)
        return self
    
    # =========================================================================
    # MACD (Moving Average Convergence Divergence)
    # =========================================================================
    
    def macd(
        self, 
        fast: int = None, 
        slow: int = None, 
        signal: int = None
    ) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        MACD 계산
        
        MACD Line = 12일 EMA - 26일 EMA
        Signal Line = MACD의 9일 EMA
        Histogram = MACD Line - Signal Line
        
        Args:
            fast: 단기 EMA 기간 (기본값: 12)
            slow: 장기 EMA 기간 (기본값: 26)
            signal: 시그널 라인 기간 (기본값: 9)
            
        Returns:
            (MACD Line, Signal Line, Histogram) 튜플
        """
        params = INDICATOR_PARAMS['MACD']
        fast = fast or params['fast']
        slow = slow or params['slow']
        signal = signal or params['signal']
        
        ema_fast = self.df[self.price_col].ewm(span=fast, adjust=False).mean()
        ema_slow = self.df[self.price_col].ewm(span=slow, adjust=False).mean()
        
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        histogram = macd_line - signal_line
        
        return macd_line, signal_line, histogram
    
    def add_macd(self) -> 'TechnicalAnalyzer':
        """MACD를 DataFrame에 추가"""
        macd_line, signal_line, histogram = self.macd()
        self.df['macd'] = macd_line
        self.df['macd_signal'] = signal_line
        self.df['macd_hist'] = histogram
        return self
    
    # =========================================================================
    # 볼린저 밴드 (Bollinger Bands)
    # =========================================================================
    
    def bollinger_bands(
        self, 
        period: int = None, 
        std_dev: float = None
    ) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """
        볼린저 밴드 계산
        
        Middle Band = 20일 SMA
        Upper Band = Middle Band + (2 * 표준편차)
        Lower Band = Middle Band - (2 * 표준편차)
        
        Args:
            period: 이동평균 기간 (기본값: 20)
            std_dev: 표준편차 배수 (기본값: 2)
            
        Returns:
            (Upper Band, Middle Band, Lower Band) 튜플
        """
        params = INDICATOR_PARAMS['BOLLINGER']
        period = period or params['period']
        std_dev = std_dev or params['std']
        
        middle = self.df[self.price_col].rolling(window=period).mean()
        std = self.df[self.price_col].rolling(window=period).std()
        
        upper = middle + (std * std_dev)
        lower = middle - (std * std_dev)
        
        return upper, middle, lower
    
    def add_bollinger_bands(self) -> 'TechnicalAnalyzer':
        """볼린저 밴드를 DataFrame에 추가"""
        upper, middle, lower = self.bollinger_bands()
        self.df['bb_upper'] = upper
        self.df['bb_middle'] = middle
        self.df['bb_lower'] = lower
        
        # %B 지표 (가격 위치)
        self.df['bb_percent'] = (
            (self.df[self.price_col] - lower) / (upper - lower)
        )
        
        return self
    
    # =========================================================================
    # 거래량 지표
    # =========================================================================
    
    def volume_sma(self, period: int = 20) -> pd.Series:
        """거래량 이동평균"""
        return self.df['volume'].rolling(window=period).mean()
    
    def add_volume_indicators(self) -> 'TechnicalAnalyzer':
        """거래량 지표를 DataFrame에 추가"""
        self.df['volume_sma_20'] = self.volume_sma(20)
        self.df['volume_ratio'] = self.df['volume'] / self.df['volume_sma_20']
        return self
    
    # =========================================================================
    # 변동성 지표
    # =========================================================================
    
    def atr(self, period: int = 14) -> pd.Series:
        """
        Average True Range (ATR) 계산
        
        True Range = max(고가-저가, |고가-전일종가|, |저가-전일종가|)
        ATR = TR의 이동평균
        """
        high = self.df['high']
        low = self.df['low']
        close = self.df['close']
        
        prev_close = close.shift(1)
        
        tr1 = high - low
        tr2 = (high - prev_close).abs()
        tr3 = (low - prev_close).abs()
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()
        
        return atr
    
    def add_atr(self, period: int = 14) -> 'TechnicalAnalyzer':
        """ATR을 DataFrame에 추가"""
        self.df['atr'] = self.atr(period)
        return self
    
    # =========================================================================
    # 통합 메서드
    # =========================================================================
    
    def add_all_indicators(self) -> 'TechnicalAnalyzer':
        """모든 지표를 한 번에 추가"""
        return (
            self.add_moving_averages()
            .add_rsi()
            .add_macd()
            .add_bollinger_bands()
            .add_volume_indicators()
            .add_atr()
        )
    
    def get_dataframe(self) -> pd.DataFrame:
        """분석이 추가된 DataFrame 반환"""
        return self.df
    
    def get_signals(self) -> pd.DataFrame:
        """매매 시그널 생성"""
        signals = pd.DataFrame(index=self.df.index)
        
        # RSI 시그널
        signals['rsi_oversold'] = self.df['rsi'] < 30
        signals['rsi_overbought'] = self.df['rsi'] > 70
        
        # MACD 시그널
        signals['macd_bullish'] = (
            (self.df['macd'] > self.df['macd_signal']) & 
            (self.df['macd'].shift(1) <= self.df['macd_signal'].shift(1))
        )
        signals['macd_bearish'] = (
            (self.df['macd'] < self.df['macd_signal']) & 
            (self.df['macd'].shift(1) >= self.df['macd_signal'].shift(1))
        )
        
        # 볼린저 밴드 시그널
        signals['bb_oversold'] = self.df[self.price_col] < self.df['bb_lower']
        signals['bb_overbought'] = self.df[self.price_col] > self.df['bb_upper']
        
        return signals


# 사용 예시
if __name__ == "__main__":
    # 샘플 데이터 생성 (실제로는 collector에서 가져옴)
    import yfinance as yf
    
    ticker = yf.Ticker("005930.KS")
    df = ticker.history(period="6mo")
    df.columns = [col.lower().replace(' ', '_') for col in df.columns]
    df = df.reset_index()
    
    # 기술적 분석 수행
    analyzer = TechnicalAnalyzer(df)
    analyzer.add_all_indicators()
    
    result = analyzer.get_dataframe()
    print("=== 기술적 지표 계산 결과 ===")
    print(result[['date', 'close', 'rsi', 'macd', 'bb_upper', 'bb_lower']].tail(10))
    
    # 시그널 확인
    signals = analyzer.get_signals()
    print("\n=== 매매 시그널 ===")
    print(signals.tail(10))
