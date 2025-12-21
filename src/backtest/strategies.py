"""
매매 전략 모듈 - RSI, MACD, 이동평균 등 다양한 매매 전략 구현
"""
import pandas as pd
import numpy as np
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from pathlib import Path
import sys

# 프로젝트 루트 경로 설정
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class BaseStrategy(ABC):
    """매매 전략 기본 클래스"""
    
    def __init__(self, name: str = "BaseStrategy"):
        self.name = name
    
    @abstractmethod
    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        """
        매매 시그널 생성
        
        Args:
            df: OHLCV + 지표가 포함된 DataFrame
            
        Returns:
            시그널 시리즈 (1: 매수, -1: 매도, 0: 홀드)
        """
        pass
    
    def get_position(self, df: pd.DataFrame) -> pd.Series:
        """
        포지션 계산 (시그널 누적)
        
        Returns:
            포지션 시리즈 (1: 롱, 0: 현금)
        """
        signals = self.generate_signals(df)
        position = pd.Series(0, index=df.index)
        
        current_position = 0
        for i in range(len(signals)):
            if signals.iloc[i] == 1:  # 매수 시그널
                current_position = 1
            elif signals.iloc[i] == -1:  # 매도 시그널
                current_position = 0
            position.iloc[i] = current_position
        
        return position


class RSIStrategy(BaseStrategy):
    """RSI 기반 매매 전략"""
    
    def __init__(self, oversold: int = 30, overbought: int = 70):
        """
        Args:
            oversold: 과매도 임계값 (매수 시그널)
            overbought: 과매수 임계값 (매도 시그널)
        """
        super().__init__(name="RSI Strategy")
        self.oversold = oversold
        self.overbought = overbought
    
    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        """RSI 기반 시그널 생성"""
        if 'rsi' not in df.columns:
            raise ValueError("RSI 컬럼이 필요합니다. TechnicalAnalyzer로 추가하세요.")
        
        signals = pd.Series(0, index=df.index)
        
        # RSI가 과매도 구간에서 벗어날 때 매수
        signals[(df['rsi'].shift(1) < self.oversold) & (df['rsi'] >= self.oversold)] = 1
        
        # RSI가 과매수 구간에 진입할 때 매도
        signals[(df['rsi'].shift(1) < self.overbought) & (df['rsi'] >= self.overbought)] = -1
        
        return signals


class MACDStrategy(BaseStrategy):
    """MACD 기반 매매 전략"""
    
    def __init__(self):
        super().__init__(name="MACD Strategy")
    
    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        """MACD 골든크로스/데드크로스 시그널"""
        if 'macd' not in df.columns or 'macd_signal' not in df.columns:
            raise ValueError("MACD, MACD_SIGNAL 컬럼이 필요합니다.")
        
        signals = pd.Series(0, index=df.index)
        
        # 골든크로스 (MACD가 시그널을 상향 돌파)
        signals[(df['macd'].shift(1) <= df['macd_signal'].shift(1)) & 
                (df['macd'] > df['macd_signal'])] = 1
        
        # 데드크로스 (MACD가 시그널을 하향 돌파)
        signals[(df['macd'].shift(1) >= df['macd_signal'].shift(1)) & 
                (df['macd'] < df['macd_signal'])] = -1
        
        return signals


class MovingAverageStrategy(BaseStrategy):
    """이동평균선 교차 전략"""
    
    def __init__(self, short_period: int = 20, long_period: int = 60):
        """
        Args:
            short_period: 단기 이동평균 기간
            long_period: 장기 이동평균 기간
        """
        super().__init__(name=f"MA({short_period}/{long_period}) Strategy")
        self.short_period = short_period
        self.long_period = long_period
    
    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        """이동평균선 교차 시그널"""
        short_ma_col = f'sma_{self.short_period}'
        long_ma_col = f'sma_{self.long_period}'
        
        # 컬럼이 없으면 직접 계산
        if short_ma_col not in df.columns:
            short_ma = df['close'].rolling(window=self.short_period).mean()
        else:
            short_ma = df[short_ma_col]
        
        if long_ma_col not in df.columns:
            long_ma = df['close'].rolling(window=self.long_period).mean()
        else:
            long_ma = df[long_ma_col]
        
        signals = pd.Series(0, index=df.index)
        
        # 골든크로스 (단기선이 장기선 상향 돌파)
        signals[(short_ma.shift(1) <= long_ma.shift(1)) & 
                (short_ma > long_ma)] = 1
        
        # 데드크로스 (단기선이 장기선 하향 돌파)
        signals[(short_ma.shift(1) >= long_ma.shift(1)) & 
                (short_ma < long_ma)] = -1
        
        return signals


class BollingerBandStrategy(BaseStrategy):
    """볼린저 밴드 전략"""
    
    def __init__(self):
        super().__init__(name="Bollinger Band Strategy")
    
    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        """볼린저 밴드 터치 시그널"""
        if 'bb_lower' not in df.columns or 'bb_upper' not in df.columns:
            raise ValueError("볼린저 밴드 컬럼이 필요합니다.")
        
        signals = pd.Series(0, index=df.index)
        
        # 하단 밴드 터치 후 반등 시 매수
        signals[(df['close'].shift(1) < df['bb_lower'].shift(1)) & 
                (df['close'] >= df['bb_lower'])] = 1
        
        # 상단 밴드 터치 시 매도
        signals[(df['close'].shift(1) < df['bb_upper'].shift(1)) & 
                (df['close'] >= df['bb_upper'])] = -1
        
        return signals


class CombinedStrategy(BaseStrategy):
    """여러 지표를 결합한 복합 전략"""
    
    def __init__(
        self, 
        use_rsi: bool = True,
        use_macd: bool = True,
        use_bb: bool = False,
        min_signals: int = 2
    ):
        """
        Args:
            use_rsi: RSI 시그널 사용 여부
            use_macd: MACD 시그널 사용 여부
            use_bb: 볼린저 밴드 시그널 사용 여부
            min_signals: 최소 동의 시그널 수
        """
        super().__init__(name="Combined Strategy")
        self.use_rsi = use_rsi
        self.use_macd = use_macd
        self.use_bb = use_bb
        self.min_signals = min_signals
        
        self.strategies = []
        if use_rsi:
            self.strategies.append(RSIStrategy())
        if use_macd:
            self.strategies.append(MACDStrategy())
        if use_bb:
            self.strategies.append(BollingerBandStrategy())
    
    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        """복합 시그널 생성 (투표 방식)"""
        if not self.strategies:
            return pd.Series(0, index=df.index)
        
        all_signals = pd.DataFrame(index=df.index)
        
        for i, strategy in enumerate(self.strategies):
            try:
                all_signals[f'signal_{i}'] = strategy.generate_signals(df)
            except ValueError:
                all_signals[f'signal_{i}'] = 0
        
        # 매수/매도 투표 집계
        buy_votes = (all_signals == 1).sum(axis=1)
        sell_votes = (all_signals == -1).sum(axis=1)
        
        signals = pd.Series(0, index=df.index)
        signals[buy_votes >= self.min_signals] = 1
        signals[sell_votes >= self.min_signals] = -1
        
        return signals


class CustomStrategy(BaseStrategy):
    """사용자 정의 전략"""
    
    def __init__(self, signal_func):
        """
        Args:
            signal_func: 시그널 생성 함수 (DataFrame -> Series)
        """
        super().__init__(name="Custom Strategy")
        self.signal_func = signal_func
    
    def generate_signals(self, df: pd.DataFrame) -> pd.Series:
        return self.signal_func(df)


# 사용 예시
if __name__ == "__main__":
    import yfinance as yf
    from src.analyzers.technical_analyzer import TechnicalAnalyzer
    
    print("=== 매매 전략 테스트 ===\n")
    
    # 데이터 준비
    ticker = yf.Ticker("005930.KS")
    df = ticker.history(period="1y")
    df.columns = [col.lower().replace(' ', '_') for col in df.columns]
    df = df.reset_index()
    
    # 기술적 지표 추가
    analyzer = TechnicalAnalyzer(df)
    analyzer.add_all_indicators()
    df = analyzer.get_dataframe()
    
    # RSI 전략 테스트
    rsi_strategy = RSIStrategy(oversold=30, overbought=70)
    rsi_signals = rsi_strategy.generate_signals(df)
    print(f"RSI 전략 - 매수 시그널: {(rsi_signals == 1).sum()}개")
    print(f"RSI 전략 - 매도 시그널: {(rsi_signals == -1).sum()}개")
    
    # MACD 전략 테스트
    macd_strategy = MACDStrategy()
    macd_signals = macd_strategy.generate_signals(df)
    print(f"\nMACD 전략 - 매수 시그널: {(macd_signals == 1).sum()}개")
    print(f"MACD 전략 - 매도 시그널: {(macd_signals == -1).sum()}개")
    
    # 복합 전략 테스트
    combined_strategy = CombinedStrategy(use_rsi=True, use_macd=True, min_signals=2)
    combined_signals = combined_strategy.generate_signals(df)
    print(f"\n복합 전략 - 매수 시그널: {(combined_signals == 1).sum()}개")
    print(f"복합 전략 - 매도 시그널: {(combined_signals == -1).sum()}개")
