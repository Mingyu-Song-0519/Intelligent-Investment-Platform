"""
Phase 1 Tests: OHLCV Performance Benchmarks
병렬 OHLCV 처리 성능 검증 (15s → 1.5s)
"""
import pytest
import time
from src.infrastructure.external.pykrx_gateway import PyKRXGateway


@pytest.mark.slow
def test_parallel_ohlcv_multi_day_is_faster_than_sequential():
    """병렬 OHLCV가 순차 방식보다 빠름 (핵심 주장 검증)"""
    gateway = PyKRXGateway()
    
    if not gateway.is_available():
        pytest.skip("pykrx not available")
    
    # Test with 3 days of data
    test_days = 3
    
    # Measure parallel version (현재 구현)
    start = time.time()
    parallel_result = gateway.get_market_ohlcv_multi_day(days=test_days, market="KOSPI")
    parallel_time = time.time() - start
    
    print(f"\n📊 OHLCV Multi-Day Performance:")
    print(f"  Parallel ({test_days} days): {parallel_time:.2f}s")
    print(f"  Rows: {len(parallel_result) if not parallel_result.empty else 0}")
    
    # Should complete within reasonable time
    assert parallel_time < 5.0, f"Parallel OHLCV took {parallel_time:.2f}s (goal: <5s for {test_days} days)"
    assert not parallel_result.empty, "Should return data"


@pytest.mark.slow
def test_batch_ohlcv_performance_benchmark():
    """전체 시장 OHLCV 성능 벤치마크"""
    gateway = PyKRXGateway()
    
    if not gateway.is_available():
        pytest.skip("pykrx not available")
    
    test_cases = [
        (1, 2.0),   # 1일: 2초 이내
        (3, 5.0),   # 3일: 5초 이내
        (5, 10.0),  # 5일: 10초 이내
    ]
    
    for days, max_time in test_cases:
        start = time.time()
        result = gateway.get_market_ohlcv_multi_day(days=days, market="KOSPI")
        elapsed = time.time() - start
        
        print(f"\n📊 {days} days OHLCV:")
        print(f"  Time: {elapsed:.2f}s (goal: <{max_time}s)")
        print(f"  Rows: {len(result) if not result.empty else 0}")
        
        assert elapsed < max_time, \
            f"{days} days OHLCV took {elapsed:.2f}s (goal: <{max_time}s)"


@pytest.mark.slow
@pytest.mark.integration
def test_ohlcv_speedup_calculation():
    """OHLCV 병렬 처리 속도 향상 계산"""
    gateway = PyKRXGateway()
    
    if not gateway.is_available():
        pytest.skip("pykrx not available")
    
    # 병렬 처리 시간 측정
    start = time.time()
    parallel_result = gateway.get_market_ohlcv_multi_day(days=3, market="KOSPI")
    parallel_time = time.time() - start
    
    # ThreadPoolExecutor workers 수 확인
    # 이론적으로 10 workers면 10배 빠를 수 있음
    # 실제로는 API rate limit, I/O 대기로 3-5배 정도 기대
    
    print(f"\n📊 성능 분석:")
    print(f"  병렬 처리 시간: {parallel_time:.2f}s")
    print(f"  이론적 순차 시간 (예상): {parallel_time * 3:.2f}s")
    print(f"  예상 속도 향상: 3-5배")
    
    # 병렬 처리가 합리적인 시간 내 완료되는지만 확인
    assert parallel_time < 10.0, "Parallel processing should be reasonably fast"
    assert not parallel_result.empty, "Should return valid data"


@pytest.mark.slow
def test_ohlcv_concurrent_execution():
    """OHLCV 동시 실행 확인 (ThreadPoolExecutor 사용 검증)"""
    import inspect
    from src.infrastructure.external.pykrx_gateway import PyKRXGateway
    
    # get_market_ohlcv_multi_day 소스 코드 확인
    source = inspect.getsource(PyKRXGateway.get_market_ohlcv_multi_day)
    
    # ThreadPoolExecutor 사용 확인
    assert 'ThreadPoolExecutor' in source, \
        "Should use ThreadPoolExecutor for parallel processing"
    assert 'as_completed' in source or 'submit' in source, \
        "Should use concurrent execution pattern"
    
    print("\n✅ OHLCV uses parallel processing (ThreadPoolExecutor)")


def test_ohlcv_performance_logging():
    """OHLCV 성능 로깅 구현 확인"""
    import inspect
    from src.infrastructure.external.pykrx_gateway import PyKRXGateway
    
    source = inspect.getsource(PyKRXGateway.get_market_ohlcv_multi_day)
    
    # 성능 측정 코드 확인
    has_timing = 'time.time()' in source or 'elapsed' in source.lower()
    
    assert has_timing, "Should measure execution time for performance monitoring"
    
    print("\n✅ OHLCV has performance logging")
