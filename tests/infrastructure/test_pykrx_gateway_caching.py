"""
Phase 2 Tests: 거래일 캐싱 검증
1시간 TTL 메모리 캐시로 API 호출 최소화
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from src.infrastructure.external.pykrx_gateway import PyKRXGateway


class TestTradingDayCaching:
    """거래일 캐싱 테스트"""
    
    @pytest.fixture
    def gateway(self):
        # 캐시 초기화
        gateway = PyKRXGateway()
        gateway._trading_day_cache = None
        gateway._cache_timestamp = None
        return gateway
    
    def test_first_call_hits_api_and_caches(self, gateway):
        """첫 호출 시 API 호출하고 캐시 저장"""
        with patch('pykrx.stock.get_market_cap_by_ticker') as mock_api:
            mock_df = MagicMock()
            mock_df.empty = False
            mock_df.index = ['005930']
            mock_df.loc.__getitem__.return_value = {'시가총액': 350000000000000}
            mock_api.return_value = mock_df
            
            date1 = gateway._get_last_trading_day()
            first_call_count = mock_api.call_count
            
            date2 = gateway._get_last_trading_day()  # 즉시 재호출
            second_call_count = mock_api.call_count
            
            # Should cache: API called only for first call
            assert date1 == date2
            assert gateway._trading_day_cache is not None
            assert gateway._cache_timestamp is not None
            
            # Second call should NOT increase API count (cached)
            assert second_call_count == first_call_count, f"Cache should prevent redundant API calls: {first_call_count} -> {second_call_count}"
    
    def test_cache_expires_after_1_hour(self, gateway):
        """캐시가 1시간 후 만료됨"""
        with patch('pykrx.stock.get_market_cap_by_ticker') as mock_api:
            mock_df = MagicMock()
            mock_df.empty = False
            mock_df.index = ['005930']
            mock_df.loc.__getitem__.return_value = {'시가총액': 350000000000000}
            mock_api.return_value = mock_df
            
            # 첫 호출
            date1 = gateway._get_last_trading_day()
            initial_call_count = mock_api.call_count
            
            # 캐시 타임스탬프를 2시간 전으로 조작 (캐시 만료)
            gateway._cache_timestamp = datetime.now() - timedelta(hours=2)
            
            # 재호출 → 캐시 만료 → API 재호출
            date2 = gateway._get_last_trading_day()
            
            # API should be called again after TTL expiry
            assert mock_api.call_count > initial_call_count, "API should be called again after cache expiry"
    
    def test_cache_invalidation(self, gateway):
        """캐시 수동 무효화"""
        # 캐시 설정
        gateway._trading_day_cache = "20251220"
        gateway._cache_timestamp = datetime.now()
        
        assert gateway._trading_day_cache is not None
        
        # 무효화
        gateway.invalidate_trading_day_cache()
        
        assert gateway._trading_day_cache is None
        assert gateway._cache_timestamp is None
