"""
SQLite 기반 프로필 저장소 구현
Clean Architecture: Infrastructure Layer - Adapter
"""
import sqlite3
import json
from pathlib import Path
from datetime import datetime
from typing import List, Optional

from src.domain.repositories.profile_interfaces import IProfileRepository
from src.domain.investment_profile.entities.investor_profile import InvestorProfile
from src.domain.investment_profile.value_objects.risk_tolerance import RiskTolerance


class SQLiteProfileRepository(IProfileRepository):
    """
    SQLite 기반 프로필 Repository 구현
    
    멀티 유저 환경을 지원하며, 데이터 영속성을 제공합니다.
    """
    
    def __init__(self, db_path: str = "data/profiles.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _init_db(self) -> None:
        """데이터베이스 초기화"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS investor_profiles (
                user_id TEXT PRIMARY KEY,
                risk_tolerance INTEGER NOT NULL,
                investment_horizon TEXT NOT NULL,
                preferred_sectors TEXT,
                style_scores TEXT,
                created_at TEXT NOT NULL,
                last_updated TEXT NOT NULL
            )
        """)
        
        conn.commit()
        conn.close()
    
    def save(self, profile: InvestorProfile) -> bool:
        """프로필 저장 (INSERT OR REPLACE)"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO investor_profiles
                (user_id, risk_tolerance, investment_horizon, 
                 preferred_sectors, style_scores, created_at, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                profile.user_id,
                profile.risk_tolerance.value,
                profile.investment_horizon,
                json.dumps(profile.preferred_sectors, ensure_ascii=False),
                json.dumps(profile.style_scores, ensure_ascii=False),
                profile.created_at.isoformat(),
                profile.last_updated.isoformat()
            ))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"[ERROR] 프로필 저장 실패: {e}")
            return False
    
    def load(self, user_id: str) -> Optional[InvestorProfile]:
        """프로필 조회"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute(
                "SELECT * FROM investor_profiles WHERE user_id = ?",
                (user_id,)
            )
            row = cursor.fetchone()
            conn.close()
            
            if not row:
                return None
            
            return InvestorProfile(
                user_id=row[0],
                risk_tolerance=RiskTolerance(row[1]),
                investment_horizon=row[2],
                preferred_sectors=json.loads(row[3]) if row[3] else [],
                style_scores=json.loads(row[4]) if row[4] else {},
                created_at=datetime.fromisoformat(row[5]),
                last_updated=datetime.fromisoformat(row[6])
            )
        except Exception as e:
            print(f"[ERROR] 프로필 로드 실패: {e}")
            return None
    
    def delete(self, user_id: str) -> bool:
        """프로필 삭제"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute(
                "DELETE FROM investor_profiles WHERE user_id = ?",
                (user_id,)
            )
            
            conn.commit()
            affected = cursor.rowcount
            conn.close()
            
            return affected > 0
        except Exception as e:
            print(f"[ERROR] 프로필 삭제 실패: {e}")
            return False
    
    def exists(self, user_id: str) -> bool:
        """프로필 존재 여부 확인"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute(
                "SELECT 1 FROM investor_profiles WHERE user_id = ?",
                (user_id,)
            )
            result = cursor.fetchone()
            conn.close()
            
            return result is not None
        except Exception as e:
            print(f"[ERROR] 프로필 존재 확인 실패: {e}")
            return False
    
    def list_all_users(self) -> List[str]:
        """모든 사용자 ID 목록 반환"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT user_id FROM investor_profiles")
            rows = cursor.fetchall()
            conn.close()
            
            return [row[0] for row in rows]
        except Exception as e:
            print(f"[ERROR] 사용자 목록 조회 실패: {e}")
            return []
