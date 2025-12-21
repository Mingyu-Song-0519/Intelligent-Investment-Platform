"""
데이터 수집 모듈 - Yahoo Finance API를 통한 주식 데이터 수집
"""
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, Dict, List
import sqlite3
import sys
from pathlib import Path

# 프로젝트 루트 경로 설정
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config import DATABASE_PATH, DEFAULT_PERIOD, DEFAULT_INTERVAL, DATA_DIR


class StockDataCollector:
    """Yahoo Finance를 통한 주식 데이터 수집 클래스"""
    
    def __init__(self, db_path: Optional[Path] = None):
        """
        Args:
            db_path: SQLite 데이터베이스 경로 (기본값: config의 DATABASE_PATH)
        """
        self.db_path = db_path or DATABASE_PATH
        self._init_database()
    
    def _init_database(self):
        """데이터베이스 및 테이블 초기화"""
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
    
    def fetch_stock_data(
        self, 
        ticker: str, 
        period: str = DEFAULT_PERIOD,
        interval: str = DEFAULT_INTERVAL,
        start: Optional[str] = None,
        end: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Yahoo Finance에서 주식 데이터를 가져옵니다.
        
        Args:
            ticker: 종목 코드 (예: '005930.KS' 삼성전자)
            period: 조회 기간 ('1d', '5d', '1mo', '3mo', '6mo', '1y', '2y', '5y', '10y', 'ytd', 'max')
            interval: 데이터 간격 ('1m', '2m', '5m', '15m', '30m', '60m', '90m', '1h', '1d', '5d', '1wk', '1mo', '3mo')
            start: 시작 날짜 (YYYY-MM-DD)
            end: 종료 날짜 (YYYY-MM-DD)
            
        Returns:
            OHLCV 데이터가 담긴 DataFrame
        """
        try:
            stock = yf.Ticker(ticker)
            
            if start and end:
                df = stock.history(start=start, end=end, interval=interval)
            else:
                df = stock.history(period=period, interval=interval)
            
            if df.empty:
                print(f"[WARNING] {ticker}: 데이터를 가져올 수 없습니다.")
                return pd.DataFrame()
            
            # 컬럼명 정규화
            df = df.reset_index()
            df.columns = [col.lower().replace(' ', '_') for col in df.columns]
            
            # 필요한 컬럼만 선택
            required_cols = ['date', 'open', 'high', 'low', 'close', 'volume']
            if 'adj_close' in df.columns or 'adj close' in df.columns:
                adj_col = 'adj_close' if 'adj_close' in df.columns else 'adj close'
                df = df.rename(columns={adj_col: 'adj_close'})
                required_cols.append('adj_close')
            
            # date 컬럼 처리
            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date']).dt.date
            
            df['ticker'] = ticker
            
            print(f"[INFO] {ticker}: {len(df)}개 데이터 수집 완료")
            return df
            
        except Exception as e:
            print(f"[ERROR] {ticker}: 데이터 수집 실패 - {str(e)}")
            return pd.DataFrame()
    
    def save_to_database(self, df: pd.DataFrame, ticker: str) -> int:
        """
        수집된 데이터를 SQLite에 저장합니다.
        
        Args:
            df: 저장할 DataFrame
            ticker: 종목 코드
            
        Returns:
            저장된 행 수
        """
        if df.empty:
            return 0
        
        saved_count = 0
        with sqlite3.connect(self.db_path) as conn:
            for _, row in df.iterrows():
                try:
                    conn.execute("""
                        INSERT OR REPLACE INTO stock_prices 
                        (ticker, date, open, high, low, close, adj_close, volume)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        ticker,
                        str(row.get('date', '')),
                        row.get('open'),
                        row.get('high'),
                        row.get('low'),
                        row.get('close'),
                        row.get('adj_close'),
                        row.get('volume')
                    ))
                    saved_count += 1
                except Exception as e:
                    print(f"[ERROR] 데이터 저장 실패: {e}")
            
            conn.commit()
        
        print(f"[INFO] {ticker}: {saved_count}개 데이터 DB 저장 완료")
        return saved_count
    
    def fetch_and_save(
        self, 
        ticker: str, 
        period: str = DEFAULT_PERIOD,
        **kwargs
    ) -> pd.DataFrame:
        """
        데이터를 수집하고 DB에 저장하는 통합 메서드
        
        Args:
            ticker: 종목 코드
            period: 조회 기간
            **kwargs: fetch_stock_data에 전달할 추가 인자
            
        Returns:
            수집된 DataFrame
        """
        df = self.fetch_stock_data(ticker, period, **kwargs)
        if not df.empty:
            self.save_to_database(df, ticker)
        return df
    
    def get_stock_data(
        self, 
        ticker: str, 
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        DB에서 주식 데이터를 조회합니다.
        
        Args:
            ticker: 종목 코드
            start_date: 시작 날짜 (YYYY-MM-DD)
            end_date: 종료 날짜 (YYYY-MM-DD)
            
        Returns:
            조회된 DataFrame
        """
        query = "SELECT * FROM stock_prices WHERE ticker = ?"
        params = [ticker]
        
        if start_date:
            query += " AND date >= ?"
            params.append(start_date)
        
        if end_date:
            query += " AND date <= ?"
            params.append(end_date)
        
        query += " ORDER BY date"
        
        with sqlite3.connect(self.db_path) as conn:
            df = pd.read_sql_query(query, conn, params=params)
        
        if not df.empty:
            df['date'] = pd.to_datetime(df['date'])
        
        return df
    
    def get_stock_info(self, ticker: str) -> Dict:
        """종목의 기본 정보를 가져옵니다."""
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            return {
                'ticker': ticker,
                'name': info.get('longName', info.get('shortName', '')),
                'sector': info.get('sector', ''),
                'industry': info.get('industry', ''),
                'market_cap': info.get('marketCap', 0),
            }
        except Exception as e:
            print(f"[ERROR] 종목 정보 조회 실패: {e}")
            return {}


# 사용 예시
if __name__ == "__main__":
    collector = StockDataCollector()
    
    # 삼성전자 데이터 수집 테스트
    df = collector.fetch_and_save("005930.KS", period="6mo")
    print(f"\n수집된 데이터:\n{df.head()}")
    
    # DB에서 조회 테스트
    loaded_df = collector.get_stock_data("005930.KS")
    print(f"\nDB 조회 데이터:\n{loaded_df.tail()}")
