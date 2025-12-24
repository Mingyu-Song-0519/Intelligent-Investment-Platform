"""
YFinance Stock Repository - Infrastructure Layer
IStockRepository 인터페이스의 yfinance 구현체
"""
import yfinance as yf
import pandas as pd
from typing import List, Optional, Dict
from datetime import datetime

from src.domain.repositories.interfaces import IStockRepository
from src.domain.entities.stock import StockEntity


class YFinanceStockRepository(IStockRepository):
    """
    yfinance API를 이용한 종목 데이터 Repository 구현체
    
    사용 예:
        repo = YFinanceStockRepository()
        stock = repo.get_stock_data("AAPL", period="1mo")
    """
    
    def __init__(self, cache_ttl: int = 300):
        """
        Args:
            cache_ttl: 캐시 유효 시간 (초)
        """
        self._cache: Dict[str, tuple] = {}  # {key: (data, timestamp)}
        self._cache_ttl = cache_ttl
    
    def get_stock_data(
        self, 
        ticker: str, 
        period: str = "1mo",
        interval: str = "1d"
    ) -> Optional[StockEntity]:
        """종목 데이터 조회"""
        
        cache_key = f"{ticker}_{period}_{interval}"
        
        # 캐시 확인
        if cache_key in self._cache:
            data, timestamp = self._cache[cache_key]
            if (datetime.now() - timestamp).seconds < self._cache_ttl:
                return data
        
        try:
            ticker_obj = yf.Ticker(ticker)
            df = ticker_obj.history(period=period, interval=interval)
            
            if df.empty:
                return None
            
            # 종목 정보 조회
            info = ticker_obj.info
            name = info.get("shortName") or info.get("longName") or ticker
            market = "US" if not ticker.endswith(".KS") else "KR"
            
            stock = StockEntity.from_dataframe(
                ticker=ticker,
                df=df,
                name=name,
                market=market
            )
            
            # 추가 정보 설정
            stock.sector = info.get("sector")
            stock.industry = info.get("industry")
            stock.market_cap = info.get("marketCap")
            
            # 캐시 저장
            self._cache[cache_key] = (stock, datetime.now())
            
            return stock
            
        except Exception as e:
            print(f"[ERROR] YFinanceStockRepository.get_stock_data: {e}")
            return None
    
    def get_multiple_stocks(
        self, 
        tickers: List[str], 
        period: str = "1mo"
    ) -> Dict[str, StockEntity]:
        """여러 종목 데이터 일괄 조회"""
        
        result = {}
        
        for ticker in tickers:
            stock = self.get_stock_data(ticker, period)
            if stock:
                result[ticker] = stock
        
        return result
    
    def get_stock_info(self, ticker: str) -> Optional[Dict]:
        """종목 기본 정보 조회"""
        
        try:
            ticker_obj = yf.Ticker(ticker)
            info = ticker_obj.info
            
            return {
                "name": info.get("shortName") or info.get("longName"),
                "sector": info.get("sector"),
                "industry": info.get("industry"),
                "market_cap": info.get("marketCap"),
                "pe_ratio": info.get("trailingPE"),
                "pb_ratio": info.get("priceToBook"),
                "dividend_yield": info.get("dividendYield"),
                "roe": info.get("returnOnEquity"),
                "country": info.get("country"),
                "currency": info.get("currency"),
                "website": info.get("website"),
                "description": info.get("longBusinessSummary")
            }
            
        except Exception as e:
            print(f"[ERROR] YFinanceStockRepository.get_stock_info: {e}")
            return None
    
    def clear_cache(self):
        """캐시 초기화"""
        self._cache.clear()


class KISStockRepository(IStockRepository):
    """
    한국투자증권 API를 이용한 종목 데이터 Repository 구현체
    (향후 구현 예정)
    """
    
    def __init__(self, app_key: str = "", app_secret: str = ""):
        self.app_key = app_key
        self.app_secret = app_secret
    
    def get_stock_data(
        self, 
        ticker: str, 
        period: str = "1mo",
        interval: str = "1d"
    ) -> Optional[StockEntity]:
        """한국투자증권 API로 종목 데이터 조회"""
        # TODO: KIS API 연동 구현
        raise NotImplementedError("KIS API 연동 구현 예정")
    
    def get_multiple_stocks(
        self, 
        tickers: List[str], 
        period: str = "1mo"
    ) -> Dict[str, StockEntity]:
        raise NotImplementedError("KIS API 연동 구현 예정")
    
    def get_stock_info(self, ticker: str) -> Optional[Dict]:
        raise NotImplementedError("KIS API 연동 구현 예정")
