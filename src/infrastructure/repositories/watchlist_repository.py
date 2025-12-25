"""
SQLite 기반 Watchlist Repository 구현
인프라 계층: 도메인 인터페이스의 실제 구현체
"""
import sqlite3
import uuid
import logging
from datetime import datetime
from typing import List, Optional
from pathlib import Path

from src.domain.watchlist import WatchlistItem, IWatchlistRepository

logger = logging.getLogger(__name__)


class SQLiteWatchlistRepository(IWatchlistRepository):
    """
    SQLite 기반 관심 종목 저장소
    
    특징:
    - 경량 파일 기반 DB
    - 자동 테이블 생성
    - 메모리 캐싱 지원
    """
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Args:
            db_path: DB 파일 경로 (None이면 기본 경로 사용)
        """
        if db_path is None:
            # 기본 경로: D:\Stock\data\watchlist.db
            # __file__ = src/infrastructure/repositories/watchlist_repository.py
            # parent 4번: infrastructure -> src -> Stock
            self.db_path = Path(__file__).parent.parent.parent.parent / "data" / "watchlist.db"
        else:
            self.db_path = Path(db_path)
        
        # 디렉토리 생성
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 메모리 캐시
        self._cache: dict = {}  # {user_id: (items, timestamp)}
        self._cache_ttl = 60  # 1분
        
        # 테이블 초기화
        self._init_db()
    
    def _get_connection(self) -> sqlite3.Connection:
        """DB 연결 획득"""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn
    
    def _init_db(self):
        """테이블 초기화"""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS watchlist (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    ticker TEXT NOT NULL,
                    stock_name TEXT NOT NULL,
                    market TEXT NOT NULL DEFAULT 'KR',
                    notes TEXT,
                    added_at TEXT NOT NULL,
                    UNIQUE(user_id, ticker)
                )
            """)
            
            # 인덱스 생성
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_watchlist_user_id 
                ON watchlist(user_id)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_watchlist_market 
                ON watchlist(user_id, market)
            """)
            
            conn.commit()
            logger.info(f"[Watchlist DB] Initialized at {self.db_path}")
        finally:
            conn.close()
    
    def _invalidate_cache(self, user_id: str):
        """캐시 무효화"""
        if user_id in self._cache:
            del self._cache[user_id]
    
    def _row_to_item(self, row: sqlite3.Row) -> WatchlistItem:
        """DB Row를 WatchlistItem으로 변환"""
        return WatchlistItem(
            id=row['id'],
            user_id=row['user_id'],
            ticker=row['ticker'],
            stock_name=row['stock_name'],
            market=row['market'],
            added_at=datetime.fromisoformat(row['added_at']),
            notes=row['notes']
        )
    
    def add_item(
        self,
        user_id: str,
        ticker: str,
        stock_name: str,
        market: str,
        notes: Optional[str] = None
    ) -> WatchlistItem:
        """관심 종목 추가"""
        # 중복 체크
        if self.exists(user_id, ticker):
            raise ValueError(f"{stock_name}({ticker})은(는) 이미 관심 종목에 있습니다.")
        
        item_id = str(uuid.uuid4())
        added_at = datetime.now()
        
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO watchlist (id, user_id, ticker, stock_name, market, notes, added_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (item_id, user_id, ticker, stock_name, market, notes, added_at.isoformat()))
            conn.commit()
            
            self._invalidate_cache(user_id)
            
            logger.info(f"[Watchlist] Added: {user_id} -> {ticker} ({market})")
            
            return WatchlistItem(
                id=item_id,
                user_id=user_id,
                ticker=ticker,
                stock_name=stock_name,
                market=market,
                added_at=added_at,
                notes=notes
            )
        finally:
            conn.close()
    
    def remove_item(self, user_id: str, ticker: str) -> bool:
        """관심 종목 삭제"""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM watchlist 
                WHERE user_id = ? AND ticker = ?
            """, (user_id, ticker))
            conn.commit()
            
            deleted = cursor.rowcount > 0
            if deleted:
                self._invalidate_cache(user_id)
                logger.info(f"[Watchlist] Removed: {user_id} -> {ticker}")
            
            return deleted
        finally:
            conn.close()
    
    def get_all(self, user_id: str) -> List[WatchlistItem]:
        """사용자의 모든 관심 종목 조회"""
        # 캐시 확인
        if user_id in self._cache:
            items, cached_at = self._cache[user_id]
            if (datetime.now() - cached_at).seconds < self._cache_ttl:
                return items
        
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM watchlist 
                WHERE user_id = ?
                ORDER BY added_at DESC
            """, (user_id,))
            
            rows = cursor.fetchall()
            items = [self._row_to_item(row) for row in rows]
            
            # 캐시 저장
            self._cache[user_id] = (items, datetime.now())
            
            return items
        finally:
            conn.close()
    
    def get_by_market(self, user_id: str, market: str) -> List[WatchlistItem]:
        """시장별 관심 종목 조회"""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM watchlist 
                WHERE user_id = ? AND market = ?
                ORDER BY added_at DESC
            """, (user_id, market))
            
            rows = cursor.fetchall()
            return [self._row_to_item(row) for row in rows]
        finally:
            conn.close()
    
    def exists(self, user_id: str, ticker: str) -> bool:
        """관심 종목 존재 여부 확인"""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 1 FROM watchlist 
                WHERE user_id = ? AND ticker = ?
            """, (user_id, ticker))
            
            return cursor.fetchone() is not None
        finally:
            conn.close()
    
    def get_item(self, user_id: str, ticker: str) -> Optional[WatchlistItem]:
        """특정 관심 종목 조회"""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM watchlist 
                WHERE user_id = ? AND ticker = ?
            """, (user_id, ticker))
            
            row = cursor.fetchone()
            return self._row_to_item(row) if row else None
        finally:
            conn.close()
    
    def update_notes(self, user_id: str, ticker: str, notes: str) -> bool:
        """메모 업데이트"""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE watchlist 
                SET notes = ?
                WHERE user_id = ? AND ticker = ?
            """, (notes, user_id, ticker))
            conn.commit()
            
            updated = cursor.rowcount > 0
            if updated:
                self._invalidate_cache(user_id)
            
            return updated
        finally:
            conn.close()
    
    def count(self, user_id: str) -> int:
        """관심 종목 개수 조회"""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) FROM watchlist 
                WHERE user_id = ?
            """, (user_id,))
            
            return cursor.fetchone()[0]
        finally:
            conn.close()
