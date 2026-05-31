"""
Characterization tests for LegacyCollectorAdapter — Strangler Fig seam.

These tests capture the CURRENT behavior of the transition seam so that
future refactoring does not silently break it. They are not correctness
tests; they are behavioral snapshots.

Key behaviors captured:
- Exception swallowing (print + return None/False/{})
- Market detection: `.KS` suffix → "KR", everything else → "US"
- Delegation to StockDataCollector and NewsCollector (lazy imports)
"""
import pytest
import pandas as pd
from unittest.mock import patch, MagicMock

from src.infrastructure.adapters.legacy_adapter import (
    LegacyCollectorAdapter,
    LegacyNewsAdapter,
)
from src.domain.entities.stock import StockEntity


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_ohlcv_df(n: int = 3) -> pd.DataFrame:
    dates = pd.date_range("2024-01-01", periods=n, freq="D")
    return pd.DataFrame(
        {
            "Open": [100.0] * n,
            "High": [105.0] * n,
            "Low": [98.0] * n,
            "Close": [102.0] * n,
            "Volume": [1_000_000] * n,
        },
        index=dates,
    )


# ---------------------------------------------------------------------------
# LegacyCollectorAdapter — get_stock_data
# ---------------------------------------------------------------------------

class TestLegacyCollectorAdapterGetStockData:

    @patch("src.collectors.stock_collector.StockDataCollector")
    def test_returns_none_when_collector_returns_none(self, MockCollector):
        MockCollector.return_value.fetch_stock_data.return_value = None
        adapter = LegacyCollectorAdapter()
        assert adapter.get_stock_data("AAPL") is None

    @patch("src.collectors.stock_collector.StockDataCollector")
    def test_returns_none_when_collector_returns_empty_df(self, MockCollector):
        MockCollector.return_value.fetch_stock_data.return_value = pd.DataFrame()
        adapter = LegacyCollectorAdapter()
        assert adapter.get_stock_data("AAPL") is None

    @patch("src.collectors.stock_collector.StockDataCollector")
    def test_returns_stock_entity_for_valid_dataframe(self, MockCollector):
        MockCollector.return_value.fetch_stock_data.return_value = _make_ohlcv_df()
        adapter = LegacyCollectorAdapter()
        result = adapter.get_stock_data("AAPL")
        assert isinstance(result, StockEntity)
        assert result.ticker == "AAPL"

    @patch("src.collectors.stock_collector.StockDataCollector")
    def test_swallows_exception_and_returns_none(self, MockCollector):
        """예외 발생 시 None 반환 (silent swallow — PRESERVE this behavior)."""
        MockCollector.return_value.fetch_stock_data.side_effect = RuntimeError("network error")
        adapter = LegacyCollectorAdapter()
        assert adapter.get_stock_data("AAPL") is None

    @patch("src.collectors.stock_collector.StockDataCollector")
    def test_ks_suffix_maps_to_kr_market(self, MockCollector):
        MockCollector.return_value.fetch_stock_data.return_value = _make_ohlcv_df()
        adapter = LegacyCollectorAdapter()
        result = adapter.get_stock_data("005930.KS")
        assert result is not None
        assert result.market == "KR"

    @patch("src.collectors.stock_collector.StockDataCollector")
    def test_no_ks_suffix_maps_to_us_market(self, MockCollector):
        MockCollector.return_value.fetch_stock_data.return_value = _make_ohlcv_df()
        adapter = LegacyCollectorAdapter()
        result = adapter.get_stock_data("AAPL")
        assert result is not None
        assert result.market == "US"

    @patch("src.collectors.stock_collector.StockDataCollector")
    def test_ticker_name_derived_from_ticker_prefix(self, MockCollector):
        """name은 ticker에서 '.' 앞부분으로 파생된다 (005930.KS → 005930)."""
        MockCollector.return_value.fetch_stock_data.return_value = _make_ohlcv_df()
        adapter = LegacyCollectorAdapter()
        result = adapter.get_stock_data("005930.KS")
        assert result is not None
        assert result.name == "005930"


# ---------------------------------------------------------------------------
# LegacyCollectorAdapter — get_multiple_stocks
# ---------------------------------------------------------------------------

class TestLegacyCollectorAdapterGetMultipleStocks:

    @patch("src.collectors.stock_collector.StockDataCollector")
    def test_returns_only_successful_tickers(self, MockCollector):
        MockCollector.return_value.fetch_stock_data.side_effect = [
            _make_ohlcv_df(),
            None,
        ]
        adapter = LegacyCollectorAdapter()
        result = adapter.get_multiple_stocks(["AAPL", "FAIL"])
        assert "AAPL" in result
        assert "FAIL" not in result

    @patch("src.collectors.stock_collector.StockDataCollector")
    def test_returns_empty_dict_when_all_fail(self, MockCollector):
        MockCollector.return_value.fetch_stock_data.return_value = None
        adapter = LegacyCollectorAdapter()
        assert adapter.get_multiple_stocks(["A", "B"]) == {}


# ---------------------------------------------------------------------------
# LegacyCollectorAdapter — save_stock_data
# ---------------------------------------------------------------------------

class TestLegacyCollectorAdapterSaveStockData:

    @patch("src.collectors.stock_collector.StockDataCollector")
    def test_returns_true_when_rows_saved(self, MockCollector):
        MockCollector.return_value.save_to_database.return_value = 5
        stock = StockEntity.from_dataframe("AAPL", _make_ohlcv_df())
        adapter = LegacyCollectorAdapter()
        assert adapter.save_stock_data(stock) is True

    @patch("src.collectors.stock_collector.StockDataCollector")
    def test_returns_false_when_zero_rows_saved(self, MockCollector):
        MockCollector.return_value.save_to_database.return_value = 0
        stock = StockEntity.from_dataframe("AAPL", _make_ohlcv_df())
        adapter = LegacyCollectorAdapter()
        assert adapter.save_stock_data(stock) is False

    @patch("src.collectors.stock_collector.StockDataCollector")
    def test_swallows_exception_and_returns_false(self, MockCollector):
        MockCollector.return_value.save_to_database.side_effect = Exception("db error")
        stock = StockEntity.from_dataframe("AAPL", _make_ohlcv_df())
        adapter = LegacyCollectorAdapter()
        assert adapter.save_stock_data(stock) is False


# ---------------------------------------------------------------------------
# LegacyNewsAdapter
# ---------------------------------------------------------------------------

class TestLegacyNewsAdapterGetNews:

    @patch("src.collectors.news_collector.NewsCollector")
    def test_delegates_ko_to_naver_news(self, MockCollector):
        MockCollector.return_value.fetch_naver_finance_news.return_value = [
            {"title": "뉴스1"}, {"title": "뉴스2"}
        ]
        adapter = LegacyNewsAdapter()
        result = adapter.get_news("삼성전자", max_results=10, language="ko")
        MockCollector.return_value.fetch_naver_finance_news.assert_called_once()
        assert len(result) <= 10

    @patch("src.collectors.news_collector.NewsCollector")
    def test_swallows_exception_and_returns_empty_list(self, MockCollector):
        MockCollector.return_value.fetch_naver_finance_news.side_effect = Exception("err")
        adapter = LegacyNewsAdapter()
        assert adapter.get_news("삼성전자", language="ko") == []

    @patch("src.collectors.news_collector.NewsCollector")
    def test_get_stock_news_strips_ks_suffix(self, MockCollector):
        MockCollector.return_value.fetch_naver_finance_news.return_value = []
        adapter = LegacyNewsAdapter()
        adapter.get_stock_news("005930.KS", max_results=5)
        keyword = MockCollector.return_value.fetch_naver_finance_news.call_args[0][0]
        assert ".KS" not in keyword

    @patch("src.collectors.news_collector.NewsCollector")
    def test_get_stock_news_strips_kq_suffix(self, MockCollector):
        MockCollector.return_value.fetch_naver_finance_news.return_value = []
        adapter = LegacyNewsAdapter()
        adapter.get_stock_news("293490.KQ", max_results=5)
        keyword = MockCollector.return_value.fetch_naver_finance_news.call_args[0][0]
        assert ".KQ" not in keyword
