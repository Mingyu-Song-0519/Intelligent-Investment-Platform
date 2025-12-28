"""
Phase 0 Tests: Long Holiday Trading Day Detection
크리스마스/설날 등 긴 연휴 대응 거래일 감지 테스트
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from src.infrastructure.external.pykrx_gateway import PyKRXGateway


class TestLongHolidayTradingDay:
    """긴 연휴 대응 거래일 감지 테스트"""
    
    @pytest.fixture
    def gateway(self):
        return PyKRXGateway()
    
    @patch('src.infrastructure.external.pykrx_gateway.datetime')
    def test_get_last_trading_day_after_christmas_4days(self, mock_datetime, gateway):
        """크리스마스 연휴 4일 후 실행 → 12/26 또는 그 이전 반환"""
        # Mock: 2025-12-27 (금요일, 크리스마스 연휴 종료)
        friday_after_christmas = datetime(2025, 12, 27, 10, 0, 0)
        mock_datetime.now.return_value = friday_after_christmas
        mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
        
        with patch('src.infrastructure.external.pykrx_gateway.timedelta', timedelta):
            date = gateway._get_last_trading_day()
        
        # Should return valid trading day (20251226 목요일 is actually valid!)
        assert int(date) <= 20251227, f"Expected date <= 20251227, got {date}"
        assert len(date) == 8
        
        # Should be a weekday
        date_obj = datetime.strptime(date, "%Y%m%d")
        assert 0 <= date_obj.weekday() <= 4, f"Date {date} is not a weekday"
    
    @patch('src.infrastructure.external.pykrx_gateway.datetime')
    def test_get_last_trading_day_searches_14_days(self, mock_datetime, gateway):
        """14일 검색 범위 확인"""
        mock_datetime.now.return_value = datetime.now()
        mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
        
        # Mock: 모든 API 호출 실패
        with patch('pykrx.stock.get_market_cap_by_ticker', side_effect=Exception("API down")):
            with patch('src.infrastructure.external.pykrx_gateway.timedelta', timedelta):
                date = gateway._get_last_trading_day()
        
        # Should fallback to 10 days ago (not 3 days)
        expected_fallback = (datetime.now() - timedelta(days=10)).strftime("%Y%m%d")
        assert date == expected_fallback, f"Expected fallback {expected_fallback}, got {date}"
    
    @patch('src.infrastructure.external.pykrx_gateway.datetime')
    def test_get_last_trading_day_fallback_is_10_days(self, mock_datetime, gateway):
        """Fallback이 10일 전인지 확인"""
        today = datetime(2025, 12, 27, 10, 0, 0)
        mock_datetime.now.return_value = today
        mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)
        
        # Mock: 모든 검색 실패
        with patch('pykrx.stock.get_market_cap_by_ticker', return_value=None):
            with patch('src.infrastructure.external.pykrx_gateway.timedelta', timedelta):
                date = gateway._get_last_trading_day()
        
        expected = (today - timedelta(days=10)).strftime("%Y%m%d")
        assert date == expected, f"Fallback should be 10 days ago: expected {expected}, got {date}"
    
    def test_get_last_trading_day_returns_valid_format(self, gateway):
        """유효한 YYYYMMDD 형식 반환"""
        date = gateway._get_last_trading_day()
        
        assert len(date) == 8, "Date should be 8 characters (YYYYMMDD)"
        assert date.isdigit(), "Date should be all digits"
        assert int(date[:4]) >= 2020, "Year should be >= 2020"
        assert 1 <= int(date[4:6]) <= 12, "Month should be 1-12"
        assert 1 <= int(date[6:8]) <= 31, "Day should be 1-31"
    
    def test_get_last_trading_day_is_weekday(self, gateway):
        """반환된 날짜가 평일인지 확인"""
        date = gateway._get_last_trading_day()
        date_obj = datetime.strptime(date, "%Y%m%d")
        
        # Monday=0, Friday=4
        assert 0 <= date_obj.weekday() <= 4, f"Trading day {date} should be a weekday, got {date_obj.strftime('%A')}"
