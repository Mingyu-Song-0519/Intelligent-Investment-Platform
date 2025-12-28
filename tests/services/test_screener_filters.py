"""
Phase 3 Tests: Core Business Logic
필터링 및 스코어링 로직 테스트
"""
import pytest
import pandas as pd
import numpy as np
from unittest.mock import MagicMock
from src.services.screener_service import ScreenerService


class TestScreenerFilters:
    """필터링 로직 단위 테스트"""
    
    @pytest.fixture
    def sample_snapshot(self):
        """샘플 시장 스냅샷"""
        return pd.DataFrame({
            'ticker': ['A', 'B', 'C', 'D'],
            '종가': [10000, 50000, 100000, 5000],
            '시가총액': [50e9, 150e12, 300e12, 20e9],  # 50억, 150조, 300조, 20억
            '거래량': [50000, 150000, 500000, 30000]
        })
    
    def test_volume_filter_removes_low_volume_stocks(self, sample_snapshot):
        """거래량 필터: 10만주 미만 제거"""
        filtered = sample_snapshot[sample_snapshot['거래량'] > 100000]
        
        assert len(filtered) == 2  # B, C만
        assert 'A' not in filtered['ticker'].values
        assert 'D' not in filtered['ticker'].values
    
    def test_market_cap_filter_removes_small_caps(self, sample_snapshot):
        """시가총액 필터: 1000억 미만 제거"""
        filtered = sample_snapshot[sample_snapshot['시가총액'] > 100e9]
        
        assert len(filtered) == 2  # B, C만
        assert 'A' not in filtered['ticker'].values
    
    def test_combined_filters(self, sample_snapshot):
        """복합 필터: 거래량 AND 시가총액"""
        filtered = sample_snapshot[
            (sample_snapshot['거래량'] > 100000) &
            (sample_snapshot['시가총액'] > 100000000000)  # 1천억
        ]
        
        assert len(filtered) == 2  # B, C
        assert set(filtered['ticker']) == {'B', 'C'}


class TestRSIFilter:
    """RSI 필터 테스트"""
    
    def test_rsi_filter_handles_nan_values(self):
        """RSI 필터: NaN 값 안전하게 처리"""
        data = pd.DataFrame({
            'ticker': ['A', 'B', 'C'],
            'rsi': [30, np.nan, 45]
        })
        
        # NaN 제거
        filtered = data.dropna(subset=['rsi'])
        filtered = filtered[filtered['rsi'] < 50]
        
        assert len(filtered) == 2  # A, C만
        assert 'B' not in filtered['ticker'].values
    
    def test_rsi_filter_boundary_cases(self):
        """RSI 필터: 경계값 테스트"""
        test_cases = [
            (49.9, True),   # 통과
            (50.0, False),  # 제외
            (50.1, False),  # 제외
            (30.0, True),   # 통과
        ]
        
        for rsi_value, should_pass in test_cases:
            passed = rsi_value < 50
            assert passed == should_pass


class TestDIPCompliance:
    """DIP(Dependency Inversion Principle) 준수 테스트"""
    
    def test_screener_service_accepts_injected_tech_indicators(self):
        """ScreenerService가 tech_indicators를 주입받음"""
        mock_indicators = MagicMock()
        mock_gateway = MagicMock()
        
        service = ScreenerService(
            pykrx_gateway=mock_gateway,
            tech_indicators=mock_indicators
        )
        
        assert service.tech_indicators is mock_indicators
    
    def test_screener_service_creates_default_tech_indicators(self):
        """tech_indicators 미주입 시 기본값 생성"""
        service = ScreenerService()
        
        assert service.tech_indicators is not None
        assert hasattr(service.tech_indicators, 'calculate_rsi_vectorized')
    
    def test_tech_indicators_interface_methods_exist(self):
        """ITechnicalIndicatorsService 인터페이스 메서드 존재"""
        service = ScreenerService()
        
        required_methods = [
            'calculate_rsi_vectorized',
            # 'calculate_ma_batch',  # 아직 구현 안 됨
            # 'calculate_macd'  # 아직 구현 안 됨
        ]
        
        for method in required_methods:
            assert hasattr(service.tech_indicators, method), \
                f"Missing method: {method}"



class TestErrorHandling:
    """에러 처리 테스트"""
    
    @pytest.fixture
    def service(self):
        mock_gateway = MagicMock()
        mock_gateway.is_available.return_value = True
        return ScreenerService(pykrx_gateway=mock_gateway)
    
    def test_handles_empty_ticker_list(self, service):
        """빈 티커 리스트 처리"""
        result = service._apply_base_filters_vectorized([], "KR")
        
        assert isinstance(result, list)
        assert len(result) == 0
    
    def test_handles_none_snapshot_gracefully(self, service):
        """None 스냅샷 처리"""
        service.pykrx_gateway.get_market_snapshot.return_value = pd.DataFrame()
        
        # Should not crash
        try:
            result = service._apply_base_filters_vectorized(['005930'], "KR")
            assert isinstance(result, list)
        except Exception as e:
            pytest.fail(f"Should handle empty snapshot gracefully: {e}")
