"""
[DEPRECATED] 감성 분석 피처 통합 모듈

⚠️ 이 모듈은 더 이상 권장되지 않습니다.
대신 src.services.sentiment_analysis_service.SentimentAnalysisService를 사용하세요.

하위 호환성을 위해 유지되며, 내부적으로 새 Service Layer를 호출합니다.
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
import warnings
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 새 Service Layer import
from src.services.sentiment_analysis_service import SentimentAnalysisService
from src.collectors.news_collector import NewsCollector
from src.analyzers.sentiment_analyzer import SentimentAnalyzer


class SentimentFeatureIntegrator:
    """
    [DEPRECATED] 감성 분석 결과를 AI 모델 피처로 통합하는 클래스
    
    ⚠️ 이 클래스는 더 이상 권장되지 않습니다.
    내부적으로 SentimentAnalysisService를 호출하는 Wrapper입니다.
    """
    
    def __init__(self, ticker: str, stock_name: str = None, market: str = "KR"):
        """
        Args:
            ticker: 종목 코드
            stock_name: 종목 이름
            market: 시장 코드 ("KR" 또는 "US")
        """
        warnings.warn(
            "SentimentFeatureIntegrator is deprecated. "
            "Use SentimentAnalysisService instead.",
            DeprecationWarning,
            stacklevel=2
        )
        
        self.ticker = ticker
        self.stock_name = stock_name
        self.market = market
        
        # 새 Service Layer 초기화
        self._service = SentimentAnalysisService(
            news_collector=NewsCollector(),
            sentiment_analyzer=SentimentAnalyzer()
        )
    
    def get_sentiment_features(self, lookback_days: int = 7) -> Dict:
        """
        최근 N일간 뉴스 감성 분석 피처 생성
        
        [DEPRECATED] SentimentAnalysisService.get_sentiment_features() 사용 권장
        """
        return self._service.get_sentiment_features(
            ticker=self.ticker,
            stock_name=self.stock_name,
            market=self.market,
            lookback_days=lookback_days
        )
    
    def add_sentiment_to_dataframe(
        self,
        df: pd.DataFrame,
        sentiment_features: Optional[Dict] = None
    ) -> pd.DataFrame:
        """
        DataFrame에 감성 피처 추가
        
        [DEPRECATED] SentimentAnalysisService.add_sentiment_to_dataframe() 사용 권장
        """
        return self._service.add_sentiment_to_dataframe(
            df=df,
            ticker=self.ticker,
            stock_name=self.stock_name,
            market=self.market,
            sentiment_features=sentiment_features
        )
    
    @staticmethod
    def get_sentiment_feature_columns() -> List[str]:
        """
        감성 피처 컬럼 이름 리스트 반환
        
        [DEPRECATED] SentimentAnalysisService.get_sentiment_feature_columns() 사용 권장
        """
        return SentimentAnalysisService.get_sentiment_feature_columns()


def create_enhanced_features(
    df: pd.DataFrame,
    ticker: str,
    stock_name: str = None,
    market: str = "KR",
    include_sentiment: bool = True
) -> Tuple[pd.DataFrame, List[str]]:
    """
    [DEPRECATED] 기술적 지표 + 감성 분석 통합 피처 생성
    
    하위 호환성을 위한 Wrapper 함수입니다.
    """
    # 기본 기술적 지표 컬럼
    base_features = [
        'close', 'volume', 'rsi', 'macd', 'macd_signal', 'macd_hist',
        'bb_upper', 'bb_lower', 'bb_percent', 'atr',
        'sma_5', 'sma_20', 'sma_60',
        'volume_sma_20', 'volume_ratio'
    ]
    
    # 존재하는 컬럼만 선택
    available_features = [col for col in base_features if col in df.columns]
    
    # 새 지표 추가
    if 'vwap' in df.columns:
        available_features.append('vwap')
    if 'obv' in df.columns:
        available_features.append('obv')
    if 'adx' in df.columns:
        available_features.append('adx')
    
    # 감성 피처 추가
    if include_sentiment:
        print(f"[INFO] 감성 분석 피처 수집 중... ({stock_name or ticker})")
        integrator = SentimentFeatureIntegrator(ticker, stock_name, market)
        sentiment_features = integrator.get_sentiment_features()
        
        df = integrator.add_sentiment_to_dataframe(df, sentiment_features)
        available_features.extend(SentimentFeatureIntegrator.get_sentiment_feature_columns())
        
        print(f"[SUCCESS] 감성 피처 추가 완료 - 점수: {sentiment_features['sentiment_score']:.3f}")
    
    return df, available_features


if __name__ == "__main__":
    # 테스트
    print("=== 감성 피처 통합 테스트 ===")
    
    integrator = SentimentFeatureIntegrator("005930.KS", "삼성전자", "KR")
    features = integrator.get_sentiment_features()
    
    print(f"\n[삼성전자 감성 피처]")
    for key, value in features.items():
        print(f"  {key}: {value}")
