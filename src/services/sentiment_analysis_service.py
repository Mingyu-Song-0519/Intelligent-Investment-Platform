"""
Sentiment Analysis Service - Application Layer

Clean Architecture:
- 감성 분석 유즈케이스 오케스트레이션
- NewsCollector, SentimentAnalyzer에 대한 의존성 주입
- 비즈니스 로직 캡슐화
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from src.collectors.news_collector import NewsCollector
from src.analyzers.sentiment_analyzer import SentimentAnalyzer


class SentimentAnalysisService:
    """
    감성 분석 서비스
    
    책임:
    - 뉴스 수집 및 감성 분석 오케스트레이션
    - 감성 피처 생성 및 추출
    - DataFrame 통합
    """
    
    def __init__(
        self,
        news_collector: Optional[NewsCollector] = None,
        sentiment_analyzer: Optional[SentimentAnalyzer] = None
    ):
        """
        Args:
            news_collector: 뉴스 수집기 (DI)
            sentiment_analyzer: 감성 분석기 (DI)
        """
        self.news_collector = news_collector or NewsCollector()
        self.sentiment_analyzer = sentiment_analyzer or SentimentAnalyzer()
    
    def get_sentiment_features(
        self,
        ticker: str,
        stock_name: Optional[str] = None,
        market: str = "KR",
        lookback_days: int = 7
    ) -> Dict[str, float]:
        """
        뉴스 감성 분석 피처 생성
        
        Args:
            ticker: 종목 코드 (예: "005930.KS", "AAPL")
            stock_name: 종목 이름 (예: "삼성전자")
            market: 시장 코드 ("KR" 또는 "US")
            lookback_days: 뉴스 수집 기간 (일)
        
        Returns:
            {
                'sentiment_score': 평균 감성 점수 (-1 ~ 1),
                'sentiment_std': 감성 표준편차,
                'positive_ratio': 긍정 뉴스 비율,
                'negative_ratio': 부정 뉴스 비율,
                'news_volume': 뉴스 수,
                'sentiment_trend': 감성 추세
            }
        """
        try:
            # 1. 뉴스 수집
            if market == "US":
                articles = self._collect_us_news(ticker)
            else:
                articles = self._collect_kr_news(ticker, stock_name or ticker)
            
            if not articles:
                return self._get_neutral_features()
            
            # 2. 감성 분석
            sentiments = self._analyze_sentiments(articles, market)
            
            # 3. 피처 추출
            return self._extract_features(sentiments)
            
        except Exception as e:
            print(f"[WARNING] 감성 피처 생성 오류: {e}")
            return self._get_neutral_features()
    
    def add_sentiment_to_dataframe(
        self,
        df: pd.DataFrame,
        ticker: str,
        stock_name: Optional[str] = None,
        market: str = "KR",
        sentiment_features: Optional[Dict] = None
    ) -> pd.DataFrame:
        """
        DataFrame에 감성 피처 추가
        
        Args:
            df: 기술적 지표가 포함된 DataFrame
            ticker: 종목 코드
            stock_name: 종목 이름
            market: 시장 코드
            sentiment_features: 미리 계산된 감성 피처 (없으면 자동 계산)
        
        Returns:
            감성 피처가 추가된 DataFrame
        """
        if sentiment_features is None:
            sentiment_features = self.get_sentiment_features(ticker, stock_name, market)
        
        # 모든 행에 동일한 감성 피처 추가
        for key, value in sentiment_features.items():
            df[key] = value
        
        return df
    
    def _collect_kr_news(self, ticker: str, stock_name: str) -> List[Dict]:
        """한국 시장 뉴스 수집"""
        articles = []
        
        try:
            # 네이버 금융 (ticker 코드 사용)
            clean_ticker = ticker.split('.')[0]  # 005930.KS → 005930
            naver_articles = self.news_collector.fetch_naver_finance_news(
                ticker=clean_ticker,
                max_pages=2
            )
            articles.extend(naver_articles)
            
            # 구글 뉴스 (종목 이름 사용)
            google_articles = self.news_collector.fetch_google_news_rss(
                query=stock_name or ticker,
                max_items=15
            )
            articles.extend(google_articles)
            
            print(f"[INFO] 네이버 금융 {len(naver_articles)}개 + 구글 {len(google_articles)}개 = 총 {len(articles)}개 뉴스 수집 완료")
        except Exception as e:
            print(f"[ERROR] 한국 뉴스 수집 실패: {e}")
        
        return articles
    
    def _collect_us_news(self, ticker: str) -> List[Dict]:
        """미국 시장 뉴스 수집"""
        try:
            # Yahoo Finance 뉴스
            articles = self.news_collector.fetch_yahoo_news(ticker, max_results=20)
            print(f"[INFO] Yahoo Finance에서 {len(articles)}개 뉴스 수집 완료")
            return articles
        except Exception as e:
            print(f"[ERROR] Yahoo Finance 뉴스 수집 실패: {e}")
            return []
    
    def _analyze_sentiments(self, articles: List[Dict], market: str) -> np.ndarray:
        """뉴스 리스트 감성 분석"""
        sentiments = []
        
        for article in articles:
            text = article.get('title', '') + ' ' + article.get('content', '')
            
            if market == "US":
                score = self.sentiment_analyzer.analyze_text_en(text)
            else:
                score = self.sentiment_analyzer.analyze_text(text)
            
            # 튜플/리스트인 경우 첫 번째 값 추출
            if isinstance(score, (tuple, list)):
                score = score[0] if score else 0
            
            sentiments.append(score)
        
        return np.array(sentiments)
    
    def _extract_features(self, sentiments: np.ndarray) -> Dict[str, float]:
        """감성 점수 배열에서 피처 추출"""
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
            'sentiment_score': float(avg_sentiment),
            'sentiment_std': float(std_sentiment),
            'positive_ratio': float(positive_ratio),
            'negative_ratio': float(negative_ratio),
            'news_volume': int(news_volume),
            'sentiment_trend': float(trend)
        }
    
    def _get_neutral_features(self) -> Dict[str, float]:
        """뉴스가 없을 때 중립 피처 반환"""
        return {
            'sentiment_score': 0.0,
            'sentiment_std': 0.0,
            'positive_ratio': 0.0,
            'negative_ratio': 0.0,
            'news_volume': 0,
            'sentiment_trend': 0.0
        }
    
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
