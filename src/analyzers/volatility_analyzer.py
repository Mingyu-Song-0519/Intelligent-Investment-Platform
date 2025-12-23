"""
변동성 분석 모듈 - VIX 데이터 수집 및 변동성 구간 판단
2024-2025 트렌드: 시장 스트레스/보험료(VIX)를 통한 리스크 온/오프 판단
"""
import yfinance as yf
import pandas as pd
import numpy as np
from typing import Tuple, Optional
from datetime import datetime, timedelta


class VolatilityAnalyzer:
    """변동성 분석 클래스"""
    
    def __init__(self):
        """초기화"""
        self.vix_ticker = "^VIX"
        self._vix_cache = None
        self._cache_timestamp = None
        self._cache_ttl = 300  # 5분 캐싱
    
    def get_vix_data(self, period: str = "1y") -> pd.DataFrame:
        """
        VIX 데이터 수집
        
        VIX는 S&P 500 옵션의 내재변동성으로,
        "시장 공포 지수"로 불립니다.
        
        Args:
            period: 데이터 수집 기간 (기본값: 1년)
            
        Returns:
            VIX 데이터 DataFrame
        """
        now = datetime.now()
        
        # 캐시 유효성 확인
        if (self._vix_cache is not None and 
            self._cache_timestamp is not None and
            (now - self._cache_timestamp).seconds < self._cache_ttl):
            return self._vix_cache
        
        try:
            ticker = yf.Ticker(self.vix_ticker)
            df = ticker.history(period=period)
            df = df.reset_index()
            df.columns = [col.lower().replace(' ', '_') for col in df.columns]
            
            # 캐시 저장
            self._vix_cache = df
            self._cache_timestamp = now
            
            return df
        except Exception as e:
            print(f"VIX 데이터 수집 오류: {e}")
            return pd.DataFrame()
    
    def get_current_vix(self) -> Optional[float]:
        """현재 VIX 값 반환"""
        df = self.get_vix_data(period="5d")
        if not df.empty:
            return df['close'].iloc[-1]
        return None
    
    def get_vix_percentile(self, days: int = 252) -> Optional[float]:
        """
        VIX 백분위수 계산 (과거 N일 대비)
        
        Args:
            days: 비교 기간 (기본값: 252 = 1년 거래일)
            
        Returns:
            현재 VIX의 백분위수 (0-100)
        """
        df = self.get_vix_data(period="2y")
        if df.empty or len(df) < days:
            return None
        
        recent_vix = df['close'].tail(days)
        current_vix = df['close'].iloc[-1]
        percentile = (recent_vix < current_vix).sum() / len(recent_vix) * 100
        
        return percentile
    
    def volatility_regime(self) -> Tuple[str, str]:
        """
        현재 변동성 구간 판단
        
        Returns:
            (구간명, 색상 이모지) 튜플
            - 저변동성 (VIX < 15): 🟢
            - 중변동성 (15 <= VIX < 25): 🟡
            - 고변동성 (VIX >= 25): 🔴
            - 극고변동성 (VIX >= 35): 🟣
        """
        vix = self.get_current_vix()
        
        if vix is None:
            return ("데이터 없음", "⚪")
        
        if vix < 15:
            return ("저변동성 (안정)", "🟢")
        elif vix < 25:
            return ("중변동성 (경계)", "🟡")
        elif vix < 35:
            return ("고변동성 (위험)", "🔴")
        else:
            return ("극고변동성 (공포)", "🟣")
    
    def bollinger_bandwidth(self, df: pd.DataFrame, period: int = 20) -> pd.Series:
        """
        볼린저 밴드 폭 계산 (변동성 측정)
        
        Bandwidth = (Upper Band - Lower Band) / Middle Band
        
        Args:
            df: OHLCV DataFrame
            period: 이동평균 기간
            
        Returns:
            Bandwidth 시리즈
        """
        middle = df['close'].rolling(window=period).mean()
        std = df['close'].rolling(window=period).std()
        upper = middle + (2 * std)
        lower = middle - (2 * std)
        
        bandwidth = (upper - lower) / middle
        return bandwidth
    
    def historical_volatility(self, df: pd.DataFrame, period: int = 20) -> pd.Series:
        """
        과거 변동성 계산 (일별 수익률의 표준편차 * sqrt(252))
        
        Args:
            df: OHLCV DataFrame
            period: 계산 기간
            
        Returns:
            연율화 변동성 시리즈
        """
        returns = df['close'].pct_change()
        volatility = returns.rolling(window=period).std() * np.sqrt(252) * 100
        return volatility


if __name__ == "__main__":
    # 테스트
    analyzer = VolatilityAnalyzer()
    
    # VIX 데이터 수집
    vix_data = analyzer.get_vix_data()
    print(f"VIX 데이터: {len(vix_data)}개")
    
    # 현재 VIX
    current_vix = analyzer.get_current_vix()
    print(f"현재 VIX: {current_vix:.2f}")
    
    # VIX 백분위수
    percentile = analyzer.get_vix_percentile()
    print(f"VIX 백분위수 (1년): {percentile:.1f}%")
    
    # 변동성 구간
    regime, color = analyzer.volatility_regime()
    print(f"현재 변동성 구간: {color} {regime}")
