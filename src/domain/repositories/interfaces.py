"""
Repository 인터페이스 - Clean Architecture Domain Layer
의존성 역전 원칙(DIP) 적용: 도메인 레이어가 인터페이스를 정의하고,
인프라 레이어가 구현체를 제공
"""
from abc import ABC, abstractmethod
from typing import List, Optional, Dict
from datetime import datetime

from src.domain.entities.stock import StockEntity, PortfolioEntity, SignalEntity


class IStockRepository(ABC):
    """
    종목 데이터 Repository 인터페이스
    
    구현체 예시:
    - YFinanceStockRepository: yfinance API 사용
    - KISStockRepository: 한국투자증권 API 사용
    - MockStockRepository: 테스트용 Mock
    """
    
    @abstractmethod
    def get_stock_data(
        self, 
        ticker: str, 
        period: str = "1mo",
        interval: str = "1d"
    ) -> Optional[StockEntity]:
        """
        종목 데이터 조회
        
        Args:
            ticker: 종목 코드 (예: "AAPL", "005930.KS")
            period: 데이터 기간 ("1d", "1mo", "1y", "max")
            interval: 데이터 간격 ("1m", "1h", "1d")
            
        Returns:
            StockEntity 또는 None (조회 실패 시)
        """
        pass
    
    @abstractmethod
    def get_multiple_stocks(
        self, 
        tickers: List[str], 
        period: str = "1mo"
    ) -> Dict[str, StockEntity]:
        """
        여러 종목 데이터 일괄 조회
        
        Args:
            tickers: 종목 코드 리스트
            period: 데이터 기간
            
        Returns:
            {ticker: StockEntity} 딕셔너리
        """
        pass
    
    @abstractmethod
    def get_stock_info(self, ticker: str) -> Optional[Dict]:
        """
        종목 기본 정보 조회 (업종, 시가총액 등)
        
        Returns:
            {
                "name": 종목명,
                "sector": 섹터,
                "industry": 산업,
                "market_cap": 시가총액,
                ...
            }
        """
        pass


class IPortfolioRepository(ABC):
    """
    포트폴리오 Repository 인터페이스
    
    구현체 예시:
    - JSONPortfolioRepository: JSON 파일 저장
    - SQLitePortfolioRepository: SQLite DB 저장
    - SessionPortfolioRepository: Streamlit Session State
    """
    
    @abstractmethod
    def save(self, portfolio: PortfolioEntity) -> bool:
        """
        포트폴리오 저장
        
        Args:
            portfolio: 저장할 포트폴리오 엔티티
            
        Returns:
            성공 여부
        """
        pass
    
    @abstractmethod
    def load(self, portfolio_id: str) -> Optional[PortfolioEntity]:
        """
        포트폴리오 조회
        
        Args:
            portfolio_id: 포트폴리오 ID
            
        Returns:
            PortfolioEntity 또는 None
        """
        pass
    
    @abstractmethod
    def list_all(self) -> List[PortfolioEntity]:
        """
        모든 포트폴리오 목록 조회
        
        Returns:
            PortfolioEntity 리스트
        """
        pass
    
    @abstractmethod
    def delete(self, portfolio_id: str) -> bool:
        """
        포트폴리오 삭제
        
        Args:
            portfolio_id: 삭제할 포트폴리오 ID
            
        Returns:
            성공 여부
        """
        pass


class INewsRepository(ABC):
    """
    뉴스 데이터 Repository 인터페이스
    
    구현체 예시:
    - NaverNewsRepository: 네이버 뉴스 크롤링
    - GoogleNewsRepository: Google News RSS
    - YahooNewsRepository: Yahoo Finance News
    """
    
    @abstractmethod
    def get_news(
        self, 
        keyword: str, 
        max_results: int = 10,
        language: str = "ko"
    ) -> List[Dict]:
        """
        뉴스 검색
        
        Args:
            keyword: 검색 키워드
            max_results: 최대 결과 수
            language: 언어 코드 ("ko", "en")
            
        Returns:
            [{"title": ..., "content": ..., "url": ..., "date": ...}, ...]
        """
        pass
    
    @abstractmethod
    def get_stock_news(
        self, 
        ticker: str, 
        max_results: int = 10
    ) -> List[Dict]:
        """
        특정 종목 관련 뉴스 검색
        
        Args:
            ticker: 종목 코드
            max_results: 최대 결과 수
            
        Returns:
            뉴스 리스트
        """
        pass


class IIndicatorRepository(ABC):
    """
    기술적 지표 Repository 인터페이스
    
    구현체 예시:
    - TALibIndicatorRepository: TA-Lib 라이브러리 사용
    - CustomIndicatorRepository: 자체 구현 지표
    """
    
    @abstractmethod
    def calculate_indicators(
        self, 
        stock: StockEntity, 
        indicators: List[str]
    ) -> Dict[str, List[float]]:
        """
        기술적 지표 계산
        
        Args:
            stock: 종목 엔티티
            indicators: 계산할 지표 리스트 ("RSI", "MACD", "BB" 등)
            
        Returns:
            {"RSI": [70.5, 68.2, ...], "MACD": [...], ...}
        """
        pass
    
    @abstractmethod
    def get_signal(self, stock: StockEntity) -> SignalEntity:
        """
        종합 매매 신호 생성
        
        Args:
            stock: 종목 엔티티
            
        Returns:
            SignalEntity
        """
        pass
