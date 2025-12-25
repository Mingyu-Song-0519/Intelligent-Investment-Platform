"""
YFinance Stock Repository - Infrastructure Layer
IStockRepository 인터페이스의 yfinance 구현체
"""
import yfinance as yf
import pandas as pd
import sqlite3
from typing import List, Optional, Dict
from datetime import datetime
from pathlib import Path

from src.domain.repositories.interfaces import IStockRepository
from src.domain.entities.stock import StockEntity


class YFinanceStockRepository(IStockRepository):
    """
    yfinance API를 이용한 종목 데이터 Repository 구현체
    
    Features:
    - 메모리 캐싱 (TTL 기반)
    - SQLite 영속 저장 (선택적)
    - yfinance API 조회
    
    사용 예:
        repo = YFinanceStockRepository(db_path="stocks.db")
        stock = repo.get_stock_data("AAPL", period="1mo")
        repo.save_stock_data(stock)  # DB에 저장
    """
    
    def __init__(self, cache_ttl: int = 300, db_path: Optional[str] = None):
        """
        Args:
            cache_ttl: 캐시 유효 시간 (초)
            db_path: SQLite 데이터베이스 경로 (None이면 DB 사용 안 함)
        """
        self._cache: Dict[str, tuple] = {}  # {key: (data, timestamp)}
        self._cache_ttl = cache_ttl
        self.db_path = db_path
        
        # DB 경로가 지정되면 초기화
        if self.db_path:
            self._init_database()

    
    def _init_database(self):
        """SQLite 데이터베이스 및 테이블 초기화"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # OHLCV 데이터 테이블
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS stock_prices (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticker TEXT NOT NULL,
                    date DATE NOT NULL,
                    open REAL,
                    high REAL,
                    low REAL,
                    close REAL,
                    adj_close REAL,
                    volume INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(ticker, date)
                )
            """)
            
            # 종목 정보 테이블
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS stock_info (
                    ticker TEXT PRIMARY KEY,
                    name TEXT,
                    sector TEXT,
                    industry TEXT,
                    market_cap REAL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 인덱스 생성
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_ticker_date 
                ON stock_prices(ticker, date)
            """)
            
            conn.commit()
    
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
    
    def save_stock_data(self, stock: StockEntity) -> bool:
        """
        종목 데이터를 영속 저장소에 저장
        
        - db_path가 설정되어 있으면 SQLite에 저장
        - 그렇지 않으면 메모리 캐시에만 저장
        """
        try:
            # 메모리 캐시 저장
            cache_key = f"{stock.ticker}_saved"
            self._cache[cache_key] = (stock, datetime.now())
            
            # DB 저장 (db_path가 있을 때만)
            if self.db_path:
                return self._save_to_database(stock)
            
            return True
            
        except Exception as e:
            print(f"[ERROR] YFinanceStockRepository.save_stock_data: {e}")
            return False
    
    def _save_to_database(self, stock: StockEntity) -> bool:
        """StockEntity를 SQLite DB에 저장"""
        if not self.db_path or stock.price_data is None:
            return False
        
        saved_count = 0
        with sqlite3.connect(self.db_path) as conn:
            # OHLCV 데이터 저장
            for date, price in stock.price_data.items():
                try:
                    conn.execute("""
                        INSERT OR REPLACE INTO stock_prices 
                        (ticker, date, open, high, low, close, adj_close, volume)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        stock.ticker,
                        date.strftime("%Y-%m-%d") if isinstance(date, datetime) else str(date),
                        price.open,
                        price.high,
                        price.low,
                        price.close,
                        price.close,  # adj_close는 close와 동일하게 처리
                        price.volume
                    ))
                    saved_count += 1
                except Exception as e:
                    print(f"[ERROR] DB 저장 실패 ({date}): {e}")
            
            # 종목 정보 저장
            try:
                conn.execute("""
                    INSERT OR REPLACE INTO stock_info
                    (ticker, name, sector, industry, market_cap)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    stock.ticker,
                    stock.name,
                    stock.sector,
                    stock.industry,
                    stock.market_cap
                ))
            except Exception as e:
                print(f"[ERROR] 종목 정보 저장 실패: {e}")
            
            conn.commit()
        
        print(f"[INFO] {stock.ticker}: {saved_count}개 데이터 DB 저장 완료")
        return saved_count > 0
    
    def load_stock_data(
        self, 
        ticker: str, 
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Optional[StockEntity]:
        """
        영속 저장소에서 종목 데이터 로드
        
        우선순위:
        1. 메모리 캐시
        2. SQLite DB (db_path가 있을 때)
        3. yfinance API
        """
        try:
            # 1. 캐시 확인
            cache_key = f"{ticker}_saved"
            if cache_key in self._cache:
                data, timestamp = self._cache[cache_key]
                if (datetime.now() - timestamp).seconds < self._cache_ttl:
                    return data
            
            # 2. DB에서 로드 (db_path가 있을 때)
            if self.db_path:
                db_stock = self._load_from_database(ticker, start_date, end_date)
                if db_stock:
                    return db_stock
            
            # 3. API에서 로드
            if start_date or end_date:
                ticker_obj = yf.Ticker(ticker)
                df = ticker_obj.history(
                    start=start_date.strftime("%Y-%m-%d") if start_date else None,
                    end=end_date.strftime("%Y-%m-%d") if end_date else None
                )
                
                if df.empty:
                    return None
                
                info = ticker_obj.info
                name = info.get("shortName") or info.get("longName") or ticker
                market = "US" if not ticker.endswith(".KS") else "KR"
                
                return StockEntity.from_dataframe(
                    ticker=ticker,
                    df=df,
                    name=name,
                    market=market
                )
            
            # 기본: get_stock_data 사용
            return self.get_stock_data(ticker)
            
        except Exception as e:
            print(f"[ERROR] YFinanceStockRepository.load_stock_data: {e}")
            return None
    
    def _load_from_database(
        self, 
        ticker: str, 
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Optional[StockEntity]:
        """SQLite DB에서 종목 데이터 로드"""
        if not self.db_path:
            return None
        
        try:
            query = "SELECT * FROM stock_prices WHERE ticker = ?"
            params = [ticker]
            
            if start_date:
                query += " AND date >= ?"
                params.append(start_date.strftime("%Y-%m-%d"))
            
            if end_date:
                query += " AND date <= ?"
                params.append(end_date.strftime("%Y-%m-%d"))
            
            query += " ORDER BY date"
            
            with sqlite3.connect(self.db_path) as conn:
                df = pd.read_sql_query(query, conn, params=params)
            
            if df.empty:
                return None
            
            # DataFrame 컬럼 정규화
            df['date'] = pd.to_datetime(df['date'])
            df = df.rename(columns={'adj_close': 'Adj Close'})
            df = df.set_index('date')
            
            # 종목 정보 조회
            with sqlite3.connect(self.db_path) as conn:
                info_query = "SELECT * FROM stock_info WHERE ticker = ?"
                info_df = pd.read_sql_query(info_query, conn, params=[ticker])
            
            name = info_df['name'].iloc[0] if not info_df.empty else ticker
            market = "US" if not ticker.endswith(".KS") else "KR"
            
            stock = StockEntity.from_dataframe(
                ticker=ticker,
                df=df,
                name=name,
                market=market
            )
            
            # 추가 정보 설정
            if not info_df.empty:
                stock.sector = info_df['sector'].iloc[0]
                stock.industry = info_df['industry'].iloc[0]
                stock.market_cap = info_df['market_cap'].iloc[0]
            
            return stock
            
        except Exception as e:
            print(f"[ERROR] DB 로드 실패: {e}")
            return None


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
    
    def save_stock_data(self, stock: StockEntity) -> bool:
        raise NotImplementedError("KIS API 연동 구현 예정")
    
    def load_stock_data(
        self, 
        ticker: str, 
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Optional[StockEntity]:
        raise NotImplementedError("KIS API 연동 구현 예정")
