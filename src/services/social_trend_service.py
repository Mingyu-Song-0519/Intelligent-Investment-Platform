"""
Social Trend Analyzer - Phase 12
무료 API 기반 소셜 미디어 트렌드 분석

사용 API:
- Google Trends (pytrends) - 완전 무료
- RSS 피드 (뉴스 사이트)
- Pushshift (Reddit 아카이브 - 선택적)
"""
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)
from datetime import datetime, timedelta
import pandas as pd
from dataclasses import dataclass


@dataclass
class TrendData:
    """트렌드 데이터"""
    keyword: str
    current_interest: int  # 0-100
    avg_interest: float
    peak_interest: int
    trend_direction: str  # "UP", "DOWN", "STABLE"
    spike_detected: bool


class GoogleTrendsAnalyzer:
    """
    Google Trends 기반 종목 관심도 분석
    
    무료, API 키 불필요, 제한 없음
    """
    
    def __init__(self):
        """pytrends 초기화"""
        try:
            from pytrends.request import TrendReq
            # tz=-540 (UTC+9 Korea)
            self.pytrends = TrendReq(
                hl='ko-KR',
                tz=-540
            )
            self.available = True
        except ImportError:
            logger.warning("pytrends 설치 필요: pip install pytrends")
            self.available = False
    
    def get_trend(
        self,
        keyword: str,
        timeframe: str = "today 3-m",
        geo: str = ""
    ) -> Optional[TrendData]:
        """
        키워드 트렌드 조회
        
        Args:
            keyword: 검색 키워드 (예: "AAPL", "Tesla")
            timeframe: 기간 ("today 1-m", "today 3-m", "today 12-m")
            geo: 국가 코드 ("US", "KR", "" = 전세계)
        
        Returns:
            TrendData 또는 None
        """
        if not self.available:
            return None
        
        try:
            # Google Trends 조회
            self.pytrends.build_payload([keyword], timeframe=timeframe, geo=geo)
            df = self.pytrends.interest_over_time()
            
            if df.empty:
                return None
            
            # 통계 계산
            values = df[keyword].values
            current = int(values[-1])
            avg = float(values.mean())
            peak = int(values.max())
            
            # 추세 방향
            recent_avg = values[-7:].mean() if len(values) >= 7 else avg
            if recent_avg > avg * 1.2:
                direction = "UP"
            elif recent_avg < avg * 0.8:
                direction = "DOWN"
            else:
                direction = "STABLE"
            
            # 스파이크 감지 (최근값이 평균의 2배 이상)
            spike = current > avg * 2.0
            
            return TrendData(
                keyword=keyword,
                current_interest=current,
                avg_interest=round(avg, 2),
                peak_interest=peak,
                trend_direction=direction,
                spike_detected=spike
            )
            
        except Exception as e:
            logger.error(f"GoogleTrendsAnalyzer.get_trend: {e}")
            return None
    
    def get_interest_over_time(
        self,
        keyword: str,
        timeframe: str = "today 3-m",
        geo: str = ""
    ) -> pd.DataFrame:
        """
        관심도 시계열 데이터 조회 (차트용)
        
        Returns:
            DataFrame (index=date, columns=[keyword])
        """
        if not self.available:
            return pd.DataFrame()
        
        try:
            self.pytrends.build_payload([keyword], timeframe=timeframe, geo=geo)
            df = self.pytrends.interest_over_time()
            
            if not df.empty and 'isPartial' in df.columns:
                df = df.drop(columns=['isPartial'])
            
            return df
            
        except Exception as e:
            logger.error(f"GoogleTrendsAnalyzer.get_interest_over_time: {e}")
            return pd.DataFrame()
    
    def compare_trends(
        self,
        keywords: List[str],
        timeframe: str = "today 1-m"
    ) -> pd.DataFrame:
        """
        여러 키워드 비교
        
        Args:
            keywords: 키워드 리스트 (최대 5개)
            timeframe: 기간
        
        Returns:
            비교 DataFrame
        """
        if not self.available or not keywords:
            return pd.DataFrame()
        
        try:
            # 최대 5개만 비교 가능
            keywords = keywords[:5]
            
            self.pytrends.build_payload(keywords, timeframe=timeframe)
            df = self.pytrends.interest_over_time()
            
            if 'isPartial' in df.columns:
                df = df.drop(columns=['isPartial'])
            
            return df
            
        except Exception as e:
            logger.error(f"GoogleTrendsAnalyzer.compare_trends: {e}")
            return pd.DataFrame()
    
    def get_related_queries(self, keyword: str) -> Dict:
        """
        연관 검색어 조회
        
        Returns:
            {
                "top": DataFrame (상위 연관 검색어),
                "rising": DataFrame (급상승 검색어)
            }
        """
        if not self.available:
            return {"top": pd.DataFrame(), "rising": pd.DataFrame()}
        
        try:
            self.pytrends.build_payload([keyword])
            related = self.pytrends.related_queries()
            
            return related.get(keyword, {"top": pd.DataFrame(), "rising": pd.DataFrame()})
            
        except Exception as e:
            logger.error(f"GoogleTrendsAnalyzer.get_related_queries: {e}")
            return {"top": pd.DataFrame(), "rising": pd.DataFrame()}


class SocialTrendAnalyzer:
    """
    소셜 트렌드 종합 분석
    
    Clean Architecture 적용
    """
    
    def __init__(self):
        """분석기 초기화"""
        self.google_trends = GoogleTrendsAnalyzer()
    
    def analyze_stock_buzz(
        self,
        ticker: str,
        company_name: str,
        timeframe: str = "today 3-m"
    ) -> Dict:
        """
        종목 관심도 분석
        
        Args:
            ticker: 종목 코드 (예: "AAPL")
            company_name: 회사명 (예: "Apple")
            timeframe: 분석 기간
        
        Returns:
            {
                "ticker_trend": TrendData,
                "name_trend": TrendData,
                "alert_level": "HIGH" | "MEDIUM" | "LOW",
                "description": str
            }
        """
        # 티커와 회사명 모두 조회
        ticker_trend = self.google_trends.get_trend(ticker, timeframe)
        name_trend = self.google_trends.get_trend(company_name, timeframe)
        
        # 더 높은 관심도 사용
        main_trend = ticker_trend
        if name_trend and (not ticker_trend or name_trend.current_interest > ticker_trend.current_interest):
            main_trend = name_trend
        
        if not main_trend:
            return {
                "ticker_trend": None,
                "name_trend": None,
                "alert_level": "LOW",
                "description": "트렌드 데이터 없음"
            }
        
        # 알림 수준 결정
        if main_trend.spike_detected:
            alert_level = "HIGH"
            description = f"⚠️ 급증 감지! 평균 대비 {main_trend.current_interest / main_trend.avg_interest:.1f}배"
        elif main_trend.trend_direction == "UP":
            alert_level = "MEDIUM"
            description = f"📈 관심도 상승 중 (현재: {main_trend.current_interest})"
        else:
            alert_level = "LOW"
            description = f"평온 (현재: {main_trend.current_interest})"
        
        return {
            "ticker_trend": ticker_trend,
            "name_trend": name_trend,
            "alert_level": alert_level,
            "description": description
        }
    
    def detect_meme_stocks(
        self,
        tickers: List[str],
        threshold: float = 2.0
    ) -> List[Dict]:
        """
        밈주식 감지 (급증 키워드)
        
        Args:
            tickers: 감시할 종목 리스트
            threshold: 스파이크 임계값 (평균 대비 배수)
        
        Returns:
            [{ticker: "GME", interest: 95, spike: True}, ...]
        """
        meme_candidates = []
        
        for ticker in tickers:
            trend = self.google_trends.get_trend(ticker, timeframe="today 1-m")
            
            if trend and trend.spike_detected:
                meme_candidates.append({
                    "ticker": ticker,
                    "interest": trend.current_interest,
                    "spike": True,
                    "avg": trend.avg_interest
                })
        
        # 관심도 높은 순 정렬
        meme_candidates.sort(key=lambda x: x["interest"], reverse=True)
        
        return meme_candidates
    
    def get_sector_trends(
        self,
        sector_keywords: Dict[str, List[str]],
        timeframe: str = "today 3-m"
    ) -> Dict:
        """
        섹터별 트렌드 분석
        
        Args:
            sector_keywords: {"Tech": ["AI", "Cloud"], "Energy": ["Oil", "EV"]}
            timeframe: 분석 기간
        
        Returns:
            섹터별 종합 트렌드
        """
        sector_trends = {}
        
        for sector, keywords in sector_keywords.items():
            all_values = []
            
            for keyword in keywords:
                trend = self.google_trends.get_trend(keyword, timeframe)
                if trend:
                    all_values.append(trend.current_interest)
            
            if all_values:
                sector_trends[sector] = {
                    "avg_interest": round(sum(all_values) / len(all_values), 2),
                    "max_interest": max(all_values),
                    "keywords_count": len(all_values)
                }
        
        return sector_trends


class TrendCache:
    """
    트렌드 데이터 캐싱 (Google Trends API 호출 제한 대비)
    """
    
    def __init__(self, ttl_minutes: int = 60):
        """
        Args:
            ttl_minutes: 캐시 유효 시간 (분)
        """
        self.cache: Dict[str, tuple] = {}  # {key: (data, timestamp)}
        self.ttl = timedelta(minutes=ttl_minutes)
    
    def get(self, key: str) -> Optional[TrendData]:
        """캐시 조회"""
        if key in self.cache:
            data, timestamp = self.cache[key]
            if datetime.now() - timestamp < self.ttl:
                return data
            else:
                del self.cache[key]
        return None
    
    def set(self, key: str, data: TrendData):
        """캐시 저장"""
        self.cache[key] = (data, datetime.now())
    
    def clear(self):
        """캐시 초기화"""
        self.cache.clear()
