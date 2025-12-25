"""
Watchlist Repository 인터페이스
의존성 역전 원칙(DIP)을 위한 추상 인터페이스 정의
"""
from abc import ABC, abstractmethod
from typing import List, Optional
from ..entities import WatchlistItem


class IWatchlistRepository(ABC):
    """
    관심 종목 저장소 인터페이스
    
    Clean Architecture의 의존성 역전 원칙을 위해
    인프라 계층 구현체가 이 인터페이스를 구현
    """
    
    @abstractmethod
    def add_item(
        self,
        user_id: str,
        ticker: str,
        stock_name: str,
        market: str,
        notes: Optional[str] = None
    ) -> WatchlistItem:
        """
        관심 종목 추가
        
        Args:
            user_id: 사용자 ID
            ticker: 종목 코드
            stock_name: 종목명
            market: 시장 구분 ("KR" or "US")
            notes: 메모 (선택)
            
        Returns:
            생성된 WatchlistItem
            
        Raises:
            ValueError: 이미 존재하는 종목인 경우
        """
        pass
    
    @abstractmethod
    def remove_item(self, user_id: str, ticker: str) -> bool:
        """
        관심 종목 삭제
        
        Args:
            user_id: 사용자 ID
            ticker: 종목 코드
            
        Returns:
            삭제 성공 여부
        """
        pass
    
    @abstractmethod
    def get_all(self, user_id: str) -> List[WatchlistItem]:
        """
        사용자의 모든 관심 종목 조회
        
        Args:
            user_id: 사용자 ID
            
        Returns:
            관심 종목 리스트 (추가일 기준 정렬)
        """
        pass
    
    @abstractmethod
    def get_by_market(self, user_id: str, market: str) -> List[WatchlistItem]:
        """
        시장별 관심 종목 조회
        
        Args:
            user_id: 사용자 ID
            market: 시장 구분 ("KR" or "US")
            
        Returns:
            해당 시장의 관심 종목 리스트
        """
        pass
    
    @abstractmethod
    def exists(self, user_id: str, ticker: str) -> bool:
        """
        관심 종목 존재 여부 확인
        
        Args:
            user_id: 사용자 ID
            ticker: 종목 코드
            
        Returns:
            존재 여부
        """
        pass
    
    @abstractmethod
    def get_item(self, user_id: str, ticker: str) -> Optional[WatchlistItem]:
        """
        특정 관심 종목 조회
        
        Args:
            user_id: 사용자 ID
            ticker: 종목 코드
            
        Returns:
            WatchlistItem 또는 None
        """
        pass
    
    @abstractmethod
    def update_notes(self, user_id: str, ticker: str, notes: str) -> bool:
        """
        메모 업데이트
        
        Args:
            user_id: 사용자 ID
            ticker: 종목 코드
            notes: 새 메모 내용
            
        Returns:
            업데이트 성공 여부
        """
        pass
    
    @abstractmethod
    def count(self, user_id: str) -> int:
        """
        관심 종목 개수 조회
        
        Args:
            user_id: 사용자 ID
            
        Returns:
            관심 종목 개수
        """
        pass
