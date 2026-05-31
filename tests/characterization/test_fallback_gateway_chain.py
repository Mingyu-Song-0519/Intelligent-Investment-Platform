"""
Characterization tests for FallbackStockDataGateway — fallback chain behavior.

Captures:
- Sequential gateway iteration (first available + supporting wins)
- DataUnavailableError raised (not None returned) when all gateways fail
- Empty DataFrame treated the same as None (skip to next)
- Last-successful-gateway tracking
- Availability aggregation
"""
import pytest
import pandas as pd
from unittest.mock import MagicMock

from src.infrastructure.market_data.fallback_gateway import FallbackStockDataGateway
from src.domain.market_data.interfaces import DataUnavailableError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_gateway(
    name: str,
    available: bool = True,
    supports: bool = True,
    ohlcv: object = None,
    raises: Exception = None,
) -> MagicMock:
    g = MagicMock()
    g.name = name
    g.is_available.return_value = available
    g.supports_ticker.return_value = supports
    if raises:
        g.fetch_ohlcv.side_effect = raises
    else:
        g.fetch_ohlcv.return_value = ohlcv
    return g


def _make_ohlcv_df(n: int = 3) -> pd.DataFrame:
    dates = pd.date_range("2024-01-01", periods=n, freq="D")
    return pd.DataFrame(
        {"Open": [100.0]*n, "High": [105.0]*n, "Low": [98.0]*n, "Close": [102.0]*n, "Volume": [1_000_000]*n},
        index=dates,
    )


# ---------------------------------------------------------------------------
# fetch_ohlcv — fallback ordering
# ---------------------------------------------------------------------------

class TestFallbackOhlcv:

    def test_returns_data_from_first_successful_gateway(self):
        df = _make_ohlcv_df()
        g1 = _make_gateway("pykrx", ohlcv=df)
        g2 = _make_gateway("yahoo", ohlcv=_make_ohlcv_df(2))
        fallback = FallbackStockDataGateway([g1, g2])
        result = fallback.fetch_ohlcv("005930")
        assert result is df  # g1 승리
        g2.fetch_ohlcv.assert_not_called()

    def test_falls_back_to_second_when_first_raises(self):
        df = _make_ohlcv_df()
        g1 = _make_gateway("pykrx", raises=ConnectionError("timeout"))
        g2 = _make_gateway("yahoo", ohlcv=df)
        fallback = FallbackStockDataGateway([g1, g2])
        result = fallback.fetch_ohlcv("005930")
        assert result is df

    def test_falls_back_when_first_returns_empty_df(self):
        """빈 DataFrame은 None과 동일하게 처리 → 다음 게이트웨이 시도."""
        df = _make_ohlcv_df()
        g1 = _make_gateway("pykrx", ohlcv=pd.DataFrame())
        g2 = _make_gateway("yahoo", ohlcv=df)
        fallback = FallbackStockDataGateway([g1, g2])
        result = fallback.fetch_ohlcv("005930")
        assert result is df

    def test_skips_unavailable_gateway(self):
        df = _make_ohlcv_df()
        g1 = _make_gateway("pykrx", available=False, ohlcv=df)
        g2 = _make_gateway("yahoo", ohlcv=df)
        fallback = FallbackStockDataGateway([g1, g2])
        fallback.fetch_ohlcv("005930")
        g1.fetch_ohlcv.assert_not_called()
        g2.fetch_ohlcv.assert_called_once()

    def test_skips_non_supporting_gateway(self):
        df = _make_ohlcv_df()
        g1 = _make_gateway("pykrx", supports=False, ohlcv=df)
        g2 = _make_gateway("yahoo", ohlcv=df)
        fallback = FallbackStockDataGateway([g1, g2])
        fallback.fetch_ohlcv("AAPL")
        g1.fetch_ohlcv.assert_not_called()
        g2.fetch_ohlcv.assert_called_once()

    def test_raises_data_unavailable_when_all_gateways_fail(self):
        """None 반환이 아닌 DataUnavailableError 발생 — 이 계약을 보존한다."""
        g1 = _make_gateway("pykrx", raises=RuntimeError("fail"))
        g2 = _make_gateway("yahoo", raises=RuntimeError("fail"))
        fallback = FallbackStockDataGateway([g1, g2])
        with pytest.raises(DataUnavailableError):
            fallback.fetch_ohlcv("005930")

    def test_raises_data_unavailable_when_no_gateways_available(self):
        g1 = _make_gateway("pykrx", available=False)
        fallback = FallbackStockDataGateway([g1])
        with pytest.raises(DataUnavailableError):
            fallback.fetch_ohlcv("005930")


# ---------------------------------------------------------------------------
# last_successful_gateway tracking
# ---------------------------------------------------------------------------

class TestLastSuccessfulGateway:

    def test_initially_none(self):
        fallback = FallbackStockDataGateway([_make_gateway("g1", ohlcv=_make_ohlcv_df())])
        assert fallback.get_last_successful_gateway() is None

    def test_set_after_successful_fetch(self):
        g = _make_gateway("pykrx", ohlcv=_make_ohlcv_df())
        fallback = FallbackStockDataGateway([g])
        fallback.fetch_ohlcv("005930")
        assert fallback.get_last_successful_gateway() == "pykrx"

    def test_reflects_fallback_gateway_name(self):
        g1 = _make_gateway("pykrx", raises=RuntimeError())
        g2 = _make_gateway("yahoo", ohlcv=_make_ohlcv_df())
        fallback = FallbackStockDataGateway([g1, g2])
        fallback.fetch_ohlcv("005930")
        assert fallback.get_last_successful_gateway() == "yahoo"


# ---------------------------------------------------------------------------
# is_available / get_available_gateways
# ---------------------------------------------------------------------------

class TestFallbackAvailability:

    def test_is_available_true_when_any_gateway_available(self):
        g1 = _make_gateway("g1", available=False)
        g2 = _make_gateway("g2", available=True)
        fallback = FallbackStockDataGateway([g1, g2])
        assert fallback.is_available() is True

    def test_is_available_false_when_all_unavailable(self):
        g1 = _make_gateway("g1", available=False)
        g2 = _make_gateway("g2", available=False)
        fallback = FallbackStockDataGateway([g1, g2])
        assert fallback.is_available() is False

    def test_get_available_gateways_returns_names_of_available(self):
        g1 = _make_gateway("pykrx", available=True)
        g2 = _make_gateway("yahoo", available=False)
        fallback = FallbackStockDataGateway([g1, g2])
        names = fallback.get_available_gateways()
        assert "pykrx" in names
        assert "yahoo" not in names

    def test_fallback_name_property(self):
        fallback = FallbackStockDataGateway([])
        assert fallback.name == "fallback"
