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
    
    @abstractmethod
    def save_stock_data(self, stock: StockEntity) -> bool:
        """
        종목 데이터를 영속 저장소에 저장
        
        Args:
            stock: 저장할 StockEntity
            
        Returns:
            성공 여부
        """
        pass
    
    @abstractmethod
    def load_stock_data(
        self, 
        ticker: str, 
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Optional[StockEntity]:
        """
        영속 저장소에서 종목 데이터 로드
        
        Args:
            ticker: 종목 코드
            start_date: 시작일 (None이면 전체)
            end_date: 종료일 (None이면 오늘)
            
        Returns:
            StockEntity 또는 None
        """
        pass


class IKISRepository(ABC):
    """
    한국투자증권 API Repository 인터페이스
    
    한국 주식 시장 전용 기능 (실시간 시세, 주문)
    
    구현체 예시:
    - KISRepository: 한국투자증권 OpenAPI 사용
    - MockKISRepository: 테스트용 Mock
    """
    
    @abstractmethod
    def authenticate(self, app_key: str, app_secret: str) -> Optional[str]:
        """
        OAuth 토큰 발급
        
        Args:
            app_key: 앱 키
            app_secret: 앱 시크릿
            
        Returns:
            Access Token 또는 None (실패 시)
        """
        pass
    
    @abstractmethod
    def get_realtime_price(self, ticker: str) -> Optional[Dict]:
        """
        실시간 시세 조회 (한국 종목 전용)
        
        Args:
            ticker: 종목 코드 (예: "005930")
            
        Returns:
            {
                "price": 현재가,
                "change": 전일대비,
                "change_rate": 등락률,
                "volume": 거래량,
                "high": 고가,
                "low": 저가,
                "open": 시가,
                "timestamp": 시간
            }
        """
        pass
    
    @abstractmethod
    def get_orderbook(self, ticker: str) -> Optional[Dict]:
        """
        호가 정보 조회
        
        Args:
            ticker: 종목 코드
            
        Returns:
            {
                "ask": [(가격, 잔량), ...],  # 매도호가
                "bid": [(가격, 잔량), ...],  # 매수호가
                "timestamp": 시간
            }
        """
        pass
    
    @abstractmethod
    def create_order(
        self, 
        ticker: str, 
        side: str,  # "BUY" or "SELL"
        quantity: int, 
        price: Optional[float] = None,  # None이면 시장가
        order_type: str = "LIMIT"  # "LIMIT", "MARKET"
    ) -> Optional[Dict]:
        """
        주문 생성
        
        Args:
            ticker: 종목 코드
            side: 매수/매도 ("BUY", "SELL")
            quantity: 수량
            price: 가격 (시장가 주문 시 None)
            order_type: 주문 유형 ("LIMIT", "MARKET")
            
        Returns:
            {
                "order_id": 주문번호,
                "status": 상태,
                ...
            } 또는 None (실패 시)
        """
        pass
    
    @abstractmethod
    def get_balance(self) -> Optional[Dict]:
        """
        계좌 잔고 조회
        
        Returns:
            {
                "total_balance": 총 평가금액,
                "cash": 예수금,
                "holdings": [
                    {"ticker": ..., "quantity": ..., "avg_price": ...},
                    ...
                ]
            }
        """
        pass
    
    @abstractmethod
    def is_authenticated(self) -> bool:
        """
        인증 상태 확인
        
        Returns:
            인증 여부
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

