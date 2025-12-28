"""
Phase 0 Tests: Trading Day Detection
주말/공휴일 거래일 감지 테스트
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from src.infrastructure.external.pykrx_gateway import PyKRXGateway


class TestGetLastTradingDay:
    """_get_last_trading_day() 메서드 테스트"""
    
    @pytest.fixture
    def gateway(self):
        """PyKRXGateway fixture"""
        return PyKRXGateway()
    
    def test_get_last_trading_day_returns_valid_format(self, gateway):
        """_get_last_trading_day() 유효한 YYYYMMDD 형식 반환"""
        date = gateway._get_last_trading_day()
        
        assert len(date) == 8
        assert date.isdigit()
        assert int(date[:4]) >= 2020  # 2020년 이후
        assert 1 <= int(date[4:6]) <= 12  # 월: 1-12
        assert 1 <= int(date[6:8]) <= 31  # 일: 1-31
    
    @patch('src.infrastructure.external.pykrx_gateway.datetime')
    def test_get_last_trading_day_on_saturday_returns_friday(self, mock_datetime, gateway):
        """토요일에 실행 시 금요일 반환"""
        # Mock: 2025-12-27 (토요일)
        saturday = datetime(2025, 12, 27, 10, 0, 0)
        mock_datetime.now.return_value = saturday
        mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
        
        # Patch timedelta to use real datetime
        with patch('src.infrastructure.external.pykrx_gateway.timedelta', timedelta):
            date = gateway._get_last_trading_day()
        
        # Should return Friday (2025-12-26) or earlier
        expected = "20251226"  # 금요일
        assert date == expected or int(date) < int(expected)
    
    @patch('src.infrastructure.external.pykrx_gateway.datetime')
    def test_get_last_trading_day_on_sunday_returns_friday(self, mock_datetime, gateway):
        """일요일에 실행 시 금요일 반환"""
        # Mock: 2025-12-28 (일요일)
        sunday = datetime(2025, 12, 28, 10, 0, 0)
        mock_datetime.now.return_value = sunday
        mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
        
        with patch('src.infrastructure.external.pykrx_gateway.timedelta', timedelta):
            date = gateway._get_last_trading_day()
        
        # Should return Friday (2025-12-26) or earlier
        expected = "20251226"
        assert date == expected or int(date) < int(expected)
    
    def test_get_last_trading_day_skips_weekends(self, gateway):
        """주말을 건너뛰고 평일만 선택"""
        date = gateway._get_last_trading_day()
        date_obj = datetime.strptime(date, "%Y%m%d")
        
        # Should be Monday(0) to Friday(4)
        assert 0 <= date_obj.weekday() <= 4
    
    def test_get_last_trading_day_within_7_days(self, gateway):
        """최대 7일 이내의 거래일 반환"""
        date = gateway._get_last_trading_day()
        date_obj = datetime.strptime(date, "%Y%m%d")
        today = datetime.now()
        
        days_diff = (today - date_obj).days
        assert 0 <= days_diff <= 7


class TestGetMarketSnapshotWithTradingDay:
    """get_market_snapshot() 거래일 통합 테스트"""
    
    @pytest.fixture
    def gateway(self):
        return PyKRXGateway()
    
    def test_get_market_snapshot_uses_trading_day_by_default(self, gateway):
        """date=None일 때 _get_last_trading_day() 사용"""
        if not gateway.is_available():
            pytest.skip("pykrx not available")
        
        snapshot = gateway.get_market_snapshot(date=None, market="KOSPI")
        
        # Should return valid data
        assert not snapshot.empty
        assert '시가총액' in snapshot.columns
        assert snapshot['시가총액'].sum() > 0  # Not all zeros
    
    @patch('src.infrastructure.external.pykrx_gateway.datetime')
    def test_get_market_snapshot_on_weekend_returns_valid_data(self, mock_datetime, gateway):
        """주말에 스냅샷 조회 → 유효한 데이터 반환"""
        if not gateway.is_available():
            pytest.skip("pykrx not available")
        
        # Mock weekend
        saturday = datetime(2025, 12, 27, 10, 0, 0)
        mock_datetime.now.return_value = saturday
        mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
        
        with patch('src.infrastructure.external.pykrx_gateway.timedelta', timedelta):
            snapshot = gateway.get_market_snapshot(date=None, market="KOSPI")
        
        # Should still return valid data
        assert not snapshot.empty
        assert snapshot['시가총액'].sum() > 0
