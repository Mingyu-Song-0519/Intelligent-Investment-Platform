"""
Phase 11 멀티팩터 분석 검증 스크립트
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

results = {"passed": [], "failed": []}


def log_pass(test_name: str, msg: str = ""):
    results["passed"].append(test_name)
    print(f"✅ PASS: {test_name} {msg}")


def log_fail(test_name: str, error: str):
    results["failed"].append((test_name, error))
    print(f"❌ FAIL: {test_name} - {error}")


def test_factor_analyzer():
    """FactorAnalyzer 테스트"""
    print("\n" + "="*60)
    print("🏆 1. FactorAnalyzer 테스트")
    print("="*60)
    
    try:
        from src.analyzers.factor_analyzer import FactorAnalyzer, FactorScores
        from src.infrastructure.repositories.stock_repository import YFinanceStockRepository
        
        repo = YFinanceStockRepository()
        analyzer = FactorAnalyzer(market="US")
        
        log_pass("FactorAnalyzer 생성")
        
        # AAPL 분석
        stock = repo.get_stock_data("AAPL", period="1y")
        stock_info = repo.get_stock_info("AAPL")
        
        if stock and stock_info:
            scores = analyzer.analyze(stock, stock_info)
            
            log_pass("analyze", f"(종합 점수: {scores.composite:.2f})")
            
            # 개별 팩터
            log_pass("momentum_score", f"({scores.momentum:.2f})")
            log_pass("value_score", f"({scores.value:.2f})")
            log_pass("quality_score", f"({scores.quality:.2f})")
            log_pass("size_score", f"({scores.size:.2f})")
            log_pass("volatility_score", f"({scores.volatility:.2f})")
        else:
            log_fail("analyze", "AAPL 데이터 없음")
        
    except Exception as e:
        log_fail("FactorAnalyzer", str(e))


def test_factor_screener():
    """FactorScreener 테스트"""
    print("\n" + "="*60)
    print("📊 2. FactorScreener 테스트")
    print("="*60)
    
    try:
        from src.analyzers.factor_analyzer import FactorScreener
        from src.infrastructure.repositories.stock_repository import YFinanceStockRepository
        
        repo = YFinanceStockRepository()
        screener = FactorScreener(stock_repo=repo, market="US")
        
        log_pass("FactorScreener 생성 (DI 적용)")
        
        # TOP 5 종목 스크리닝
        tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]
        top_stocks = screener.screen_top_stocks(tickers, top_n=3, sort_by="composite")
        
        if top_stocks:
            log_pass("screen_top_stocks", f"({len(top_stocks)}개 선정)")
            
            print(f"\n{'='*60}")
            print("  🥇 팩터 스코어 TOP 3")
            print(f"{'='*60}")
            for i, scores in enumerate(top_stocks, 1):
                print(f"  {i}. {scores.ticker}: {scores.composite:.1f}점")
                print(f"     모멘텀: {scores.momentum:.1f} | 가치: {scores.value:.1f} | 품질: {scores.quality:.1f}")
            print(f"{'='*60}\n")
        else:
            log_fail("screen_top_stocks", "결과 없음")
        
        # 팩터 분포
        distribution = screener.get_factor_distribution(tickers)
        if distribution:
            log_pass("get_factor_distribution", f"({len(distribution)}개 팩터)")
        
    except Exception as e:
        log_fail("FactorScreener", str(e))


def test_custom_weights():
    """커스텀 가중치 테스트"""
    print("\n" + "="*60)
    print("⚖️ 3. 커스텀 가중치 테스트")
    print("="*60)
    
    try:
        from src.analyzers.factor_analyzer import FactorAnalyzer
        
        analyzer = FactorAnalyzer()
        
        # 가중치 변경 (모멘텀 중심)
        analyzer.set_custom_weights({
            "momentum": 0.4,
            "value": 0.15,
            "quality": 0.15,
            "size": 0.15,
            "volatility": 0.15
        })
        
        log_pass("set_custom_weights", "(모멘텀 40%)")
        
        # 잘못된 가중치 (합계 != 1.0)
        try:
            analyzer.set_custom_weights({
                "momentum": 0.5,
                "value": 0.3,
                "quality": 0.1,
                "size": 0.1,
                "volatility": 0.1
            })
            log_fail("가중치 검증", "잘못된 가중치를 허용함")
        except ValueError:
            log_pass("가중치 검증", "(합계 1.0 체크 정상)")
        
    except Exception as e:
        log_fail("커스텀 가중치", str(e))


def print_summary():
    """결과 요약"""
    print("\n" + "="*60)
    print("📋 Phase 11 테스트 결과")
    print("="*60)
    
    total = len(results["passed"]) + len(results["failed"])
    pass_rate = len(results["passed"]) / total * 100 if total > 0 else 0
    
    print(f"\n✅ 통과: {len(results['passed'])}개")
    print(f"❌ 실패: {len(results['failed'])}개")
    print(f"📊 통과율: {pass_rate:.1f}%")
    
    if results["failed"]:
        print("\n❌ 실패한 테스트:")
        for test, error in results["failed"]:
            print(f"  - {test}: {error[:50]}...")
    
    print("\n" + "="*60)
    if len(results["failed"]) == 0:
        print("🎉 Phase 11 멀티팩터 분석 검증 완료!")
        print("   - FactorAnalyzer (Fama-French 5팩터 + 저변동성) ✅")
        print("   - FactorScreener (Clean Architecture DI) ✅")
        print("   - 커스텀 가중치 시스템 ✅")
    else:
        print("⚠️ 일부 테스트 실패. 위 오류를 확인해주세요.")
    print("="*60)


if __name__ == "__main__":
    print("="*60)
    print("🏆 Phase 11: 멀티팩터 분석 검증")
    print("="*60)
    
    test_factor_analyzer()
    test_factor_screener()
    test_custom_weights()
    
    print_summary()
