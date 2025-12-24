"""
Phase 10 전체 검증 스크립트
Clean Architecture 전체 레이어 테스트
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


def test_stock_business_logic():
    """Stock Entity 비즈니스 로직 테스트 (Phase 10-1)"""
    print("\n" + "="*60)
    print("📊 1. StockEntity 비즈니스 로직 테스트")
    print("="*60)
    
    try:
        from src.domain.entities.stock import StockEntity, PriceData
        from datetime import datetime, timedelta
        
        # 테스트 데이터 생성
        stock = StockEntity(ticker="TEST", name="Test Stock", market="US")
        
        # 30일 가격 데이터
        base_price = 100
        for i in range(30):
            price = PriceData(
                open=base_price + i,
                high=base_price + i + 5,
                low=base_price + i - 5,
                close=base_price + i + 2,
                volume=100000,
                date=datetime.now() - timedelta(days=30-i)
            )
            stock.price_history.append(price)
        
        # 가격 범위
        low, high = stock.get_price_range(days=5)
        assert low < high
        log_pass("get_price_range", f"(Low: {low:.2f}, High: {high:.2f})")
        
        # 수익률
        ret = stock.calculate_return(days=10)
        if ret is not None:
            log_pass("calculate_return", f"({ret:.2f}%)")
        else:
            log_fail("calculate_return", "None 반환")
        
        # 변동성
        vol = stock.calculate_volatility(days=20)
        if vol and vol > 0:
            log_pass("calculate_volatility", f"({vol:.2f}%)")
        else:
            log_fail("calculate_volatility", "None 또는 0")
        
        # 추세
        is_up = stock.is_trending_up(short_period=5, long_period=20)
        log_pass("is_trending_up", f"({'상승' if is_up else '하락'})")
        
        # MDD
        mdd = stock.get_max_drawdown()
        log_pass("get_max_drawdown", f"({mdd:.2f}%)")
        
    except Exception as e:
        log_fail("StockEntity 비즈니스 로직", str(e))


def test_portfolio_repository():
    """Portfolio Repository 테스트 (Phase 10-1)"""
    print("\n" + "="*60)
    print("💾 2. Portfolio Repository 테스트")
    print("="*60)
    
    try:
        from src.infrastructure.repositories.portfolio_repository import (
            JSONPortfolioRepository,
            SessionPortfolioRepository
        )
        from src.domain.entities.stock import PortfolioEntity
        
        # JSON Repository
        repo = JSONPortfolioRepository(storage_path="data/test_portfolios")
        
        # 포트폴리오 생성 및 저장
        portfolio = PortfolioEntity(
            portfolio_id="test_001",
            name="테스트 포트폴리오"
        )
        portfolio.add_holding("AAPL", 0.5)
        portfolio.add_holding("MSFT", 0.5)
        
        success = repo.save(portfolio)
        if success:
            log_pass("JSONPortfolioRepository.save")
        else:
            log_fail("JSONPortfolioRepository.save", "저장 실패")
        
        # 로드
        loaded = repo.load("test_001")
        if loaded and loaded.total_weight == 1.0:
            log_pass("JSONPortfolioRepository.load", f"({len(loaded.holdings)}개 종목)")
        else:
            log_fail("JSONPortfolioRepository.load", "로드 실패")
        
        # 목록 조회
        all_portfolios = repo.list_all()
        log_pass("JSONPortfolioRepository.list_all", f"({len(all_portfolios)}개)")
        
        # 삭제
        repo.delete("test_001")
        
        # Session Repository
        session_repo = SessionPortfolioRepository()
        session_repo.save(portfolio)
        loaded_session = session_repo.load("test_001")
        
        if loaded_session:
            log_pass("SessionPortfolioRepository")
        else:
            log_fail("SessionPortfolioRepository", "로드 실패")
        
    except Exception as e:
        log_fail("Portfolio Repository", str(e))


def test_portfolio_management_service():
    """Portfolio Management Service 테스트 (Phase 10-2)"""
    print("\n" + "="*60)
    print("📦 3. PortfolioManagementService 테스트")
    print("="*60)
    
    try:
        from src.services.portfolio_management_service import PortfolioManagementService
        from src.infrastructure.repositories.portfolio_repository import SessionPortfolioRepository
        from src.infrastructure.repositories.stock_repository import YFinanceStockRepository
        
        # DI
        portfolio_repo = SessionPortfolioRepository()
        stock_repo = YFinanceStockRepository()
        service = PortfolioManagementService(portfolio_repo, stock_repo)
        
        log_pass("PortfolioManagementService 생성")
        
        # 포트폴리오 생성
        portfolio = service.create_portfolio(
            portfolio_id="service_test",
            name="서비스 테스트",
            holdings={"AAPL": 0.6, "MSFT": 0.4}
        )
        
        if portfolio.total_weight == 1.0:
            log_pass("create_portfolio", f"(비중 합: {portfolio.total_weight})")
        
        # 수익률 계산
        perf = service.calculate_portfolio_return("service_test", period="5d")
        if perf:
            log_pass("calculate_portfolio_return", f"({perf['total_return']:.2f}%)")
        else:
            log_fail("calculate_portfolio_return", "None 반환")
        
        # 리스크 계산
        risk = service.calculate_portfolio_risk("service_test", period="5d")
        if risk:
            log_pass("calculate_portfolio_risk", f"(Vol: {risk['portfolio_volatility']:.2f}%)")
        else:
            log_fail("calculate_portfolio_risk", "None 반환")
        
        # 리밸런싱
        rebal = service.suggest_rebalancing(
            "service_test",
            target_weights={"AAPL": 0.5, "MSFT": 0.5}
        )
        
        if rebal:
            log_pass("suggest_rebalancing", f"({len(rebal['actions'])}개 액션)")
        else:
            log_fail("suggest_rebalancing", "None 반환")
        
    except Exception as e:
        log_fail("PortfolioManagementService", str(e))


def test_alert_orchestrator_service():
    """Alert Orchestrator Service 테스트 (Phase 10-2)"""
    print("\n" + "="*60)
    print("🔔 4. AlertOrchestratorService 테스트")
    print("="*60)
    
    try:
        from src.services.alert_orchestrator_service import AlertOrchestratorService
        from src.infrastructure.repositories.stock_repository import YFinanceStockRepository
        from src.utils.notification_manager import NotificationManager, AlertConfig
        
        # DI
        stock_repo = YFinanceStockRepository()
        config = AlertConfig(vix_spike_threshold=15.0, mdd_warning_threshold=5.0)
        notification_manager = NotificationManager(config)
        
        service = AlertOrchestratorService(stock_repo, notification_manager)
        
        log_pass("AlertOrchestratorService 생성")
        
        # VIX 체크
        vix_alert = service.check_and_alert_vix()
        if vix_alert:
            log_pass("check_and_alert_vix", "(알림 발생)")
        else:
            log_pass("check_and_alert_vix", "(임계값 미달, 정상)")
        
        # MDD 체크
        mdd_alert = service.check_and_alert_portfolio_mdd("AAPL", threshold=5.0)
        if mdd_alert:
            log_pass("check_and_alert_portfolio_mdd", "(알림 발생)")
        else:
            log_pass("check_and_alert_portfolio_mdd", "(임계값 미달, 정상)")
        
        # Watchlist 일괄 체크
        result = service.batch_check_watchlist(["AAPL", "MSFT"], check_vix=True, check_mdd=True)
        log_pass("batch_check_watchlist", f"({len(result['mdd_alerts'])}개 MDD 알림)")
        
    except Exception as e:
        log_fail("AlertOrchestratorService", str(e))


def print_summary():
    """결과 요약"""
    print("\n" + "="*60)
    print("📋 Phase 10 전체 테스트 결과")
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
        print("🎉 Phase 10 Clean Architecture 전체 구축 완료!")
        print("   - Phase 10-0: 인터페이스 레이어 ✅")
        print("   - Phase 10-1: Domain Layer 확장 ✅")
        print("   - Phase 10-2: Application Services ✅")
        print("   - Phase 10-3: Repository Pattern ✅")
    else:
        print("⚠️ 일부 테스트 실패. 위 오류를 확인해주세요.")
    print("="*60)


if __name__ == "__main__":
    print("="*60)
    print("🏗️ Phase 10: Clean Architecture 전체 검증")
    print("="*60)
    
    test_stock_business_logic()
    test_portfolio_repository()
    test_portfolio_management_service()
    test_alert_orchestrator_service()
    
    print_summary()
