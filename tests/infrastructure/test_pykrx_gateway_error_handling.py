"""
Phase 1 Tests: get_stock_fundamental() Error Handling
API 실패 시 에러 처리 검증
"""
import pytest
from unittest.mock import patch, MagicMock
from json.decoder import JSONDecodeError
from src.infrastructure.external.pykrx_gateway import PyKRXGateway


class TestGetStockFundamentalErrorHandling:
    """get_stock_fundamental() 에러 처리 테스트"""
    
    @pytest.fixture
    def gateway(self):
        return PyKRXGateway()
    
    def test_get_stock_fundamental_when_trading_day_fails(self, gateway):
        """_get_last_trading_day() 실패 시 None 딕셔너리 반환"""
        with patch.object(gateway, '_get_last_trading_day', side_effect=Exception("API down")):
            result = gateway.get_stock_fundamental("005930")
        
        # Should return dict with None values, not crash
        assert result is not None
        assert isinstance(result, dict)
        expected_keys = ['marketcap', 'per', 'pbr', 'dividend_yield', 'week52_high', 'week52_low']
        for key in expected_keys:
            assert key in result
            assert result[key] is None
    
    def test_get_stock_fundamental_when_pykrx_api_fails(self, gateway):
        """pykrx API JSONDecodeError 시 부분 데이터 반환"""
        with patch('pykrx.stock.get_market_cap_by_ticker', side_effect=JSONDecodeError("Expecting value", "", 0)):
            result = gateway.get_stock_fundamental("005930", date="20251220")
        
        # marketcap 없지만 결과는 딕셔너리
        assert isinstance(result, dict)
        assert result.get('marketcap') is None
    
    def test_get_stock_fundamental_when_all_apis_fail(self, gateway):
        """모든 API 실패 시 빈 딕셔너리 반환"""
        with patch('pykrx.stock.get_market_cap_by_ticker', side_effect=Exception("pykrx down")):
            with patch('yfinance.Ticker', side_effect=Exception("yfinance down")):
                result = gateway.get_stock_fundamental("005930", date="20251220")
        
        # Should return dict with None values, not crash
        assert isinstance(result, dict)
        assert all(v is None for v in result.values())
    
    def test_get_stock_fundamental_partial_data_ok(self, gateway):
        """부분 데이터만 있어도 반환 (crash 안 함)"""
        # Mock: pykrx 성공하지만 빈 데이터, yfinance 실패
        mock_df = MagicMock()
        mock_df.index = []  # 빈 인덱스
        
        with patch('pykrx.stock.get_market_cap_by_ticker', return_value=mock_df):
            with patch('yfinance.Ticker', side_effect=Exception("yfinance down")):
                result = gateway.get_stock_fundamental("005930", date="20251220")
        
        # Should have all keys, all None
        assert isinstance(result, dict)
        assert 'marketcap' in result
        assert 'per' in result
        # All should be None since both APIs "failed"
        assert result['marketcap'] is None
        assert result['per'] is None
    
    def test_get_stock_fundamental_returns_all_keys(self, gateway):
        """항상 모든 키가 존재하는 딕셔너리 반환"""
        # 완전 실패 시나리오
        with patch('pykrx.stock.get_market_cap_by_ticker', side_effect=Exception):
            result = gateway.get_stock_fundamental("999999", date="20251220")
        
        expected_keys = ['marketcap', 'per', 'pbr', 'dividend_yield', 'week52_high', 'week52_low']
        for key in expected_keys:
            assert key in result, f"Missing key: {key}"
