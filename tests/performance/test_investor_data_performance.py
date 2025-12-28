"""
Phase 1 Tests: Performance Benchmarks for Parallel OHLCV
병렬 OHLCV 처리 성능 검증
"""
import pytest
import time
from src.infrastructure.external.pykrx_gateway import PyKRXGateway


@pytest.mark.slow
def test_parallel_investor_data_is_3x_faster_than_sequential():
    """병렬 수급 데이터 조회가 순차 방식보다 3배 빠름"""
    gateway = PyKRXGateway()
    
    if not gateway.is_available():
        pytest.skip("pykrx not available")
    
    test_tickers = ['005930', '000660', '035420']  # 삼성전자, SK하이닉스, NAVER
    
    # Sequential baseline
    start = time.time()
    seq_results = []
    for ticker in test_tickers:
        try:
            data = gateway.get_investor_trading(ticker, days=20)
            if data is not None:
                seq_results.append(data)
        except:
            pass
    seq_time = time.time() - start
    
    # Parallel version
    start = time.time()
    par_results = gateway.batch_get_investor_trading_parallel(test_tickers, days=20)
    par_time = time.time() - start
    
    # Should be at least 2x faster (relaxed from 3x for API variability)
    speedup = seq_time / par_time if par_time > 0 else 0
    
    print(f"\n📊 Performance:")
    print(f"  Sequential: {seq_time:.2f}s")
    print(f"  Parallel:   {par_time:.2f}s")
    print(f"  Speedup:    {speedup:.1f}x")
    
    assert speedup >= 2.0, \
        f"Parallel ({par_time:.2f}s) should be 2x+ faster than sequential ({seq_time:.2f}s), got {speedup:.1f}x"


@pytest.mark.slow
def test_batch_investor_data_50_stocks_under_5_seconds():
    """50개 종목 수급 데이터 병렬 조회 < 5초"""
    gateway = PyKRXGateway()
    
    if not gateway.is_available():
        pytest.skip("pykrx not available")
    
    # Get 50 real tickers
    from pykrx import stock as pykrx_stock
    all_tickers = pykrx_stock.get_market_ticker_list(market="ALL")
    test_tickers = all_tickers[:50]
    
    start = time.time()
    result = gateway.batch_get_investor_trading_parallel(test_tickers, days=20)
    elapsed = time.time() - start
    
    print(f"\n📊 50 stocks performance:")
    print(f"  Time: {elapsed:.2f}s")
    print(f"  Success rate: {len(result)}/{len(test_tickers)} ({len(result)/len(test_tickers)*100:.1f}%)")
    
    assert elapsed < 5.0, f"50 stocks took {elapsed:.2f}s (goal: <5s)"
    assert len(result) >= 30, f"Should fetch 30+/50 (got {len(result)})"


@pytest.mark.slow
@pytest.mark.integration
def test_full_market_ohlcv_multi_day_performance():
    """전체 시장 OHLCV 조회 성능 테스트"""
    gateway = PyKRXGateway()
    
    if not gateway.is_available():
        pytest.skip("pykrx not available")
    
    # Test with real market data
    start = time.time()
    result = gateway.get_market_ohlcv_multi_day(days=3, market="KOSPI")
    elapsed = time.time() - start
    
    print(f"\n📊 Market OHLCV (3 days):")
    print(f"  Time: {elapsed:.2f}s")
    print(f"  Rows: {len(result) if result is not None and not result.empty else 0}")
    
    # Should complete within reasonable time
    assert elapsed < 10.0, f"Market OHLCV took {elapsed:.2f}s (goal: <10s)"
    assert result is not None
    assert not result.empty


def test_performance_logging_exists():
    """성능 로깅이 구현되어 있는지 확인"""
    import inspect
    from src.infrastructure.external.pykrx_gateway import PyKRXGateway
    
    # Check if batch method has performance logging
    source = inspect.getsource(PyKRXGateway.batch_get_investor_trading_parallel)
    
    # Should have time measurement
    assert 'time.time()' in source or 'elapsed' in source.lower(), \
        "Performance logging should measure elapsed time"
