"""
Characterization tests for GatewayFactory — gateway creation behavior.

Captures:
- KR market → [PyKRXGateway, YahooFinanceGateway] order
- US market  → [YahooFinanceGateway] only
- create_fallback_gateway returns FallbackStockDataGateway instance
- get_best_gateway falls back to YahooFinanceGateway when no gateway available
"""
import pytest
from unittest.mock import patch, MagicMock

from src.infrastructure.market_data.gateway_factory import GatewayFactory
from src.infrastructure.market_data.fallback_gateway import FallbackStockDataGateway
from src.infrastructure.market_data.yahoo_gateway import YahooFinanceGateway
from src.infrastructure.market_data.pykrx_gateway import PyKRXGateway


class TestGatewayFactoryCreateGateways:

    def test_kr_market_returns_two_gateways(self):
        gateways = GatewayFactory.create_gateways("KR")
        assert len(gateways) == 2

    def test_kr_market_first_gateway_is_pykrx(self):
        gateways = GatewayFactory.create_gateways("KR")
        assert isinstance(gateways[0], PyKRXGateway)

    def test_kr_market_second_gateway_is_yahoo(self):
        gateways = GatewayFactory.create_gateways("KR")
        assert isinstance(gateways[1], YahooFinanceGateway)

    def test_us_market_returns_one_gateway(self):
        gateways = GatewayFactory.create_gateways("US")
        assert len(gateways) == 1

    def test_us_market_gateway_is_yahoo(self):
        gateways = GatewayFactory.create_gateways("US")
        assert isinstance(gateways[0], YahooFinanceGateway)

    def test_unknown_market_returns_yahoo_only(self):
        """알 수 없는 시장 코드는 US 브랜치(Yahoo only)로 처리."""
        gateways = GatewayFactory.create_gateways("JP")
        assert len(gateways) == 1
        assert isinstance(gateways[0], YahooFinanceGateway)

    def test_case_insensitive_kr(self):
        gateways_lower = GatewayFactory.create_gateways("kr")
        gateways_upper = GatewayFactory.create_gateways("KR")
        assert len(gateways_lower) == len(gateways_upper) == 2


class TestGatewayFactoryCreateFallback:

    def test_returns_fallback_gateway_instance(self):
        fallback = GatewayFactory.create_fallback_gateway("KR")
        assert isinstance(fallback, FallbackStockDataGateway)

    def test_fallback_contains_gateways(self):
        fallback = GatewayFactory.create_fallback_gateway("KR")
        assert len(fallback.gateways) == 2

    def test_fallback_us_contains_one_gateway(self):
        fallback = GatewayFactory.create_fallback_gateway("US")
        assert len(fallback.gateways) == 1


class TestGatewayFactoryGetBestGateway:

    def test_returns_yahoo_when_no_gateway_available(self):
        """모든 게이트웨이 불가 시 Yahoo Finance 반환 (기본값 계약)."""
        with patch.object(PyKRXGateway, "is_available", return_value=False), \
             patch.object(YahooFinanceGateway, "is_available", return_value=False):
            gateway = GatewayFactory.get_best_gateway("005930", "KR")
        assert isinstance(gateway, YahooFinanceGateway)

    def test_returns_first_available_supporting_gateway(self):
        """사용 가능+지원 조건을 만족하는 첫 번째 게이트웨이 반환."""
        with patch.object(PyKRXGateway, "is_available", return_value=True), \
             patch.object(PyKRXGateway, "supports_ticker", return_value=True):
            gateway = GatewayFactory.get_best_gateway("005930", "KR")
        assert isinstance(gateway, PyKRXGateway)
