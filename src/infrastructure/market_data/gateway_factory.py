"""
Gateway Factory
Clean Architecture: Infrastructure Layer

시장별 최적 게이트웨이 생성 팩토리
"""
import logging
from typing import List

from src.domain.market_data.interfaces import IStockDataGateway
from src.infrastructure.market_data.yahoo_gateway import YahooFinanceGateway
from src.infrastructure.market_data.pykrx_gateway import PyKRXGateway
from src.infrastructure.market_data.fallback_gateway import FallbackStockDataGateway

logger = logging.getLogger(__name__)


# @MX:ANCHOR: 게이트웨이 생성 단일 진입점 — KR/US 분기 로직이 집중됨. 새 데이터 소스 추가 시 여기를 수정
# @MX:REASON: [AUTO] market_data_service, fallback_gateway, 특성화 테스트 fan_in=5+
class GatewayFactory:
    """
    시장별 데이터 게이트웨이 팩토리

    각 시장에 최적화된 게이트웨이 우선순위로 생성합니다.
    """
    
    @staticmethod
    def create_gateways(market: str = "KR") -> List[IStockDataGateway]:
        """
        시장별 게이트웨이 리스트 생성 (우선순위 순)
        
        Args:
            market: "KR" (한국) 또는 "US" (미국)
            
        Returns:
            우선순위 순 게이트웨이 리스트
        """
        if market.upper() == "KR":
            return [
                PyKRXGateway(),       # 1순위: pykrx (한국 데이터 최적)
                YahooFinanceGateway() # 2순위: Yahoo Finance (보조)
            ]
        else:  # US 또는 기타
            return [
                YahooFinanceGateway() # 미국 주식은 Yahoo Finance 우선
            ]
    
    @staticmethod
    def create_fallback_gateway(market: str = "KR") -> FallbackStockDataGateway:
        """
        Fallback 게이트웨이 생성
        
        Args:
            market: "KR" 또는 "US"
            
        Returns:
            FallbackStockDataGateway 인스턴스
        """
        gateways = GatewayFactory.create_gateways(market)
        available = [g for g in gateways if g.is_available()]
        
        if not available:
            logger.warning(f"[GatewayFactory] No available gateways for {market}")
        else:
            logger.info(f"[GatewayFactory] Created fallback with: {[g.name for g in available]}")
        
        return FallbackStockDataGateway(gateways)
    
    @staticmethod
    def get_best_gateway(ticker: str, market: str = "KR") -> IStockDataGateway:
        """
        특정 티커에 가장 적합한 단일 게이트웨이 반환
        
        Args:
            ticker: 종목 코드
            market: 시장
            
        Returns:
            가장 적합한 게이트웨이
        """
        gateways = GatewayFactory.create_gateways(market)
        
        for gateway in gateways:
            if gateway.is_available() and gateway.supports_ticker(ticker):
                return gateway
        
        # 기본값: Yahoo Finance
        return YahooFinanceGateway()
