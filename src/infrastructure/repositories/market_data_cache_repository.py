"""
Market Data Cache Repository
Clean Architecture: Infrastructure Layer

SQLite 기반 시장 데이터 캐시
"""
import io
import logging
import sqlite3
from pathlib import Path
from typing import Optional
from datetime import datetime, timedelta

import pandas as pd

from src.domain.market_data.interfaces import OHLCV, IMarketDataCache

logger = logging.getLogger(__name__)


class SQLiteMarketDataCache(IMarketDataCache):
    """
    SQLite 기반 시장 데이터 캐시
    
    TTL(Time To Live) 기반 캐시 관리
    """
    
    DEFAULT_TTL_HOURS = 24  # 기본 1일 유효
    
    def __init__(self, db_path: Optional[Path] = None, ttl_hours: int = DEFAULT_TTL_HOURS):
        """
        Args:
            db_path: 데이터베이스 경로 (None이면 기본 경로)
            ttl_hours: 캐시 유효 시간 (시간)
        """
        if db_path is None:
            db_path = Path(__file__).parent.parent.parent / "data" / "market_cache.db"
        
        self.db_path = Path(db_path)
        self.ttl_hours = ttl_hours
        
        # 디렉토리 생성
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 테이블 초기화
        self._init_database()
        
        logger.info(f"[MarketDataCache] Initialized at {self.db_path}")
    
    def get(self, ticker: str, start: str, end: str) -> Optional[OHLCV]:
        """캐시에서 데이터 조회"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT data, source, cached_at
                    FROM ohlcv_cache
                    WHERE ticker = ? AND start_date = ? AND end_date = ?
                """, (ticker, start, end))
                
                row = cursor.fetchone()
                if not row:
                    return None
                
                data_blob, source, cached_at_str = row
                
                # TTL 확인
                cached_at = datetime.fromisoformat(cached_at_str)
                if datetime.now() - cached_at > timedelta(hours=self.ttl_hours):
                    logger.debug(f"[MarketDataCache] Expired: {ticker}")
                    self.invalidate(ticker)
                    return None
                
                # Parquet 역직렬화 (H1: pickle RCE 방지)
                df = pd.read_parquet(io.BytesIO(bytes(data_blob)))
                
                return OHLCV(
                    ticker=ticker,
                    data=df,
                    source=source,
                    fetched_at=cached_at
                )
                
        except Exception as e:
            logger.warning(f"[MarketDataCache] Get failed for {ticker}: {e}")
            return None
    
    def save(self, ohlcv: OHLCV) -> bool:
        """캐시에 데이터 저장"""
        if not ohlcv.is_valid():
            return False
        
        try:
            # 날짜 범위 추출
            df = ohlcv.data
            start = df.index.min().strftime('%Y-%m-%d')
            end = df.index.max().strftime('%Y-%m-%d')
            
            # Parquet 직렬화 (H1: pickle RCE 방지)
            buf = io.BytesIO()
            df.to_parquet(buf, index=True)
            data_blob = buf.getvalue()
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO ohlcv_cache
                    (ticker, start_date, end_date, data, source, cached_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    ohlcv.ticker,
                    start,
                    end,
                    data_blob,
                    ohlcv.source,
                    datetime.now().isoformat()
                ))
                conn.commit()
            
            logger.debug(f"[MarketDataCache] Saved: {ohlcv.ticker}")
            return True
            
        except Exception as e:
            logger.warning(f"[MarketDataCache] Save failed: {e}")
            return False
    
    def invalidate(self, ticker: str) -> bool:
        """캐시 무효화"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM ohlcv_cache WHERE ticker = ?", (ticker,))
                conn.commit()
            
            logger.debug(f"[MarketDataCache] Invalidated: {ticker}")
            return True
            
        except Exception as e:
            logger.warning(f"[MarketDataCache] Invalidate failed: {e}")
            return False
    
    def cleanup_expired(self) -> int:
        """만료된 캐시 정리"""
        try:
            cutoff = (datetime.now() - timedelta(hours=self.ttl_hours)).isoformat()
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM ohlcv_cache WHERE cached_at < ?", (cutoff,))
                deleted = cursor.rowcount
                conn.commit()
            
            if deleted > 0:
                logger.info(f"[MarketDataCache] Cleaned up {deleted} expired entries")
            
            return deleted
            
        except Exception as e:
            logger.warning(f"[MarketDataCache] Cleanup failed: {e}")
            return 0
    
    def get_stats(self) -> dict:
        """캐시 통계"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*), SUM(LENGTH(data)) FROM ohlcv_cache")
                count, size = cursor.fetchone()
                
            return {
                'entries': count or 0,
                'size_bytes': size or 0,
                'ttl_hours': self.ttl_hours
            }
        except Exception:
            return {'entries': 0, 'size_bytes': 0, 'ttl_hours': self.ttl_hours}
    
    def _init_database(self):
        """데이터베이스 초기화"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ohlcv_cache (
                    ticker TEXT NOT NULL,
                    start_date TEXT NOT NULL,
                    end_date TEXT NOT NULL,
                    data BLOB NOT NULL,
                    source TEXT,
                    cached_at TEXT NOT NULL,
                    PRIMARY KEY (ticker, start_date, end_date)
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_cached_at ON ohlcv_cache(cached_at)")
            conn.commit()
