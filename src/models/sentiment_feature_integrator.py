"""
감성 분석 피처 통합 모듈
뉴스 감성 점수를 AI 예측 모델의 입력 피처로 변환
2024-2025 트렌드: 기술적 분석 + 감성 분석 결합으로 예측 정확도 향상
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.collectors.news_collector import NewsCollector
from src.analyzers.sentiment_analyzer import SentimentAnalyzer


class SentimentFeatureIntegrator:
    """감성 분석 결과를 AI 모델 피처로 통합하는 클래스"""
    
    def __init__(self, ticker: str, stock_name: str = None, market: str = "KR"):
        """
        Args:
            ticker: 종목 코드 (예: "005930.KS" 또는 "AAPL")
            stock_name: 종목 이름 (예: "삼성전자")
            market: 시장 코드 ("KR" 또는 "US")
        """
        self.ticker = ticker
        self.stock_name = stock_name or ticker.split('.')[0]
        self.market = market
        self.news_collector = NewsCollector()
        self.sentiment_analyzer = SentimentAnalyzer()
    
    def get_sentiment_features(self, lookback_days: int = 7) -> Dict:
        """
        최근 N일간 뉴스 감성 분석 피처 생성
        
        Args:
            lookback_days: 뉴스 수집 기간 (일)
            
        Returns:
            {
                "sentiment_score": 평균 감성 점수 (-1 ~ 1),
                "sentiment_std": 감성 표준편차 (일관성),
                "positive_ratio": 긍정 뉴스 비율,
                "negative_ratio": 부정 뉴스 비율,
                "news_volume": 뉴스 수 (관심도),
                "sentiment_trend": 감성 추세 (최근 vs 과거)
            }
        """
        try:
            # 뉴스 수집
            if self.market == "US":
                articles = self._collect_us_news()
            else:
                articles = self._collect_kr_news()
            
            if not articles:
                return self._get_neutral_features()
            
            # 감성 분석
            sentiments = []
            for article in articles:
                text = article.get('title', '') + ' ' + article.get('content', '')
                
                if self.market == "US":
                    score = self.sentiment_analyzer.analyze_text_en(text)
                else:
                    score = self.sentiment_analyzer.analyze_text(text)
                
                if isinstance(score, (tuple, list)):
                    score = score[0] if score else 0
                
                sentiments.append(score)
            
            sentiments = np.array(sentiments)
            
            # 피처 계산
            avg_sentiment = np.mean(sentiments)
            std_sentiment = np.std(sentiments)
            positive_ratio = np.mean(sentiments > 0.1)
            negative_ratio = np.mean(sentiments < -0.1)
            news_volume = len(sentiments)
            
            # 감성 추세 (최근 50% vs 과거 50%)
            if len(sentiments) >= 4:
                mid = len(sentiments) // 2
                recent = np.mean(sentiments[:mid])
                past = np.mean(sentiments[mid:])
                trend = recent - past
            else:
                trend = 0
            
            return {
                "sentiment_score": float(avg_sentiment),
                "sentiment_std": float(std_sentiment),
                "positive_ratio": float(positive_ratio),
                "negative_ratio": float(negative_ratio),
                "news_volume": int(news_volume),
                "sentiment_trend": float(trend)
            }
            
        except Exception as e:
            print(f"[WARNING] 감성 피처 생성 오류: {e}")
            return self._get_neutral_features()
    
    def _collect_kr_news(self) -> List[Dict]:
        """한국 시장 뉴스 수집"""
        articles = []
        
        # 네이버 금융
        try:
            naver = self.news_collector.fetch_naver_finance_news(
                self.stock_name,
                max_pages=2
            )
            articles.extend(naver)
        except Exception:
            pass
        
        # 구글 뉴스
        try:
            google = self.news_collector.fetch_google_news_rss(
                self.stock_name,
                max_results=15
            )
            articles.extend(google)
        except Exception:
            pass
        
        return articles
    
    def _collect_us_news(self) -> List[Dict]:
        """미국 시장 뉴스 수집"""
        articles = []
        
        # Yahoo Finance RSS
        try:
            yahoo = self.news_collector.fetch_yahoo_finance_news_rss(
                self.ticker.replace('.KS', ''),
                max_results=15
            )
            articles.extend(yahoo)
        except Exception:
            pass
        
        # Google News EN
        try:
            google_en = self.news_collector.fetch_google_news_en_rss(
                self.stock_name,
                max_results=15
            )
            articles.extend(google_en)
        except Exception:
            pass
        
        return articles
    
    def _get_neutral_features(self) -> Dict:
        """뉴스가 없을 때 중립 피처 반환"""
        return {
            "sentiment_score": 0.0,
            "sentiment_std": 0.0,
            "positive_ratio": 0.5,
            "negative_ratio": 0.5,
            "news_volume": 0,
            "sentiment_trend": 0.0
        }
    
    def add_sentiment_to_dataframe(
        self, 
        df: pd.DataFrame, 
        sentiment_features: Optional[Dict] = None
    ) -> pd.DataFrame:
        """
        DataFrame에 감성 피처 컬럼 추가
        
        Args:
            df: 기술적 지표가 포함된 OHLCV DataFrame
            sentiment_features: 미리 계산된 감성 피처 (없으면 자동 계산)
            
        Returns:
            감성 피처가 추가된 DataFrame
        """
        if sentiment_features is None:
            sentiment_features = self.get_sentiment_features()
        
        df = df.copy()
        
        # 감성 피처를 모든 행에 동일하게 추가 (최근 뉴스 기반)
        df['sentiment_score'] = sentiment_features['sentiment_score']
        df['sentiment_std'] = sentiment_features['sentiment_std']
        df['positive_ratio'] = sentiment_features['positive_ratio']
        df['negative_ratio'] = sentiment_features['negative_ratio']
        df['news_volume'] = sentiment_features['news_volume']
        df['sentiment_trend'] = sentiment_features['sentiment_trend']
        
        return df
    
    @staticmethod
    def get_sentiment_feature_columns() -> List[str]:
        """감성 피처 컬럼 이름 리스트 반환"""
        return [
            'sentiment_score',
            'sentiment_std',
            'positive_ratio',
            'negative_ratio',
            'news_volume',
            'sentiment_trend'
        ]


def create_enhanced_features(
    df: pd.DataFrame,
    ticker: str,
    stock_name: str = None,
    market: str = "KR",
    include_sentiment: bool = True
) -> Tuple[pd.DataFrame, List[str]]:
    """
    기술적 지표 + 감성 분석 통합 피처 생성
    
    Args:
        df: 기본 OHLCV DataFrame (기술적 지표 포함)
        ticker: 종목 코드
        stock_name: 종목 이름
        market: 시장 코드
        include_sentiment: 감성 피처 포함 여부
        
    Returns:
        (향상된 DataFrame, 피처 컬럼 리스트)
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
    
    # 새 지표 추가 (Phase 9-0)
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
