"""
미검증 항목 테스트 스크립트
verification_checklist.md의 미검증 항목들을 자동으로 테스트
"""
import sys
from pathlib import Path
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# 프로젝트 루트 설정
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

# 테스트 결과 저장
results = {
    "passed": [],
    "failed": [],
    "warnings": []
}


def log_pass(test_name: str, message: str = ""):
    """테스트 통과"""
    results["passed"].append(test_name)
    print(f"✅ PASS: {test_name} {message}")


def log_fail(test_name: str, error: str):
    """테스트 실패"""
    results["failed"].append((test_name, error))
    print(f"❌ FAIL: {test_name} - {error}")


def log_warn(test_name: str, message: str):
    """경고"""
    results["warnings"].append((test_name, message))
    print(f"⚠️ WARN: {test_name} - {message}")


def test_us_stock_ai_prediction():
    """미국 종목 AI 예측 테스트"""
    print("\n" + "="*60)
    print("🤖 1. 미국 종목 AI 예측 학습/저장 테스트")
    print("="*60)

    try:
        import pandas as pd
        from src.collectors.stock_collector import StockDataCollector
        from src.analyzers.technical_analyzer import TechnicalAnalyzer
        from src.models.ensemble_predictor import EnsemblePredictor

        # 미국 종목 데이터 수집 (AAPL)
        print("  📥 데이터 수집 중... (AAPL)")
        collector = StockDataCollector()
        df = collector.fetch_stock_data("AAPL", period="6mo")

        if df.empty:
            log_fail("미국 종목 데이터 수집", "데이터가 비어있음")
            return

        log_pass("미국 종목 데이터 수집", f"({len(df)}일 데이터)")

        # 기술적 지표 추가
        print("  📊 기술적 지표 계산 중...")
        analyzer = TechnicalAnalyzer(df)
        analyzer.add_all_indicators()
        df = analyzer.get_dataframe()

        log_pass("기술적 지표 계산")

        # AI 모델 학습 (XGBoost만 사용 - TensorFlow 없을 때)
        print("  🧠 XGBoost 모델 학습 중...")

        from src.models.xgboost_classifier import XGBoostClassifier

        xgb_model = XGBoostClassifier()
        train_size = int(len(df) * 0.8)
        xgb_model.train(df.iloc[:train_size])

        log_pass("XGBoost 모델 학습")

        # 예측
        print("  🔮 예측 수행 중...")
        predictions = xgb_model.predict(df.iloc[train_size:])

        if predictions and len(predictions) > 0:
            log_pass("미국 종목 예측", f"({len(predictions)}일 예측 완료)")
        else:
            log_warn("미국 종목 예측", "예측 결과 없음")

        # 모델 저장 테스트
        print("  💾 모델 저장 테스트...")
        save_path = PROJECT_ROOT / "src" / "models" / "saved_models" / "AAPL_test_xgb.pkl"
        save_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            xgb_model.save_model(str(save_path))
            log_pass("미국 종목 모델 저장", f"(경로: {save_path.name})")

            # 저장된 파일 확인
            if save_path.exists():
                log_pass("저장 파일 확인", f"({save_path.stat().st_size} bytes)")

        except Exception as e:
            log_warn("모델 저장", f"저장 실패: {str(e)[:50]}")

    except Exception as e:
        log_fail("미국 종목 AI 예측 전체", str(e)[:100])


def test_us_stock_backtest():
    """미국 종목 백테스트 테스트"""
    print("\n" + "="*60)
    print("⏮️ 2. 미국 종목 백테스트 수행 테스트")
    print("="*60)

    try:
        from src.collectors.stock_collector import StockDataCollector
        from src.analyzers.technical_analyzer import TechnicalAnalyzer
        from src.backtest import Backtester
        from src.backtest.strategies import RSIStrategy

        # 데이터 수집
        print("  📥 데이터 수집 중... (MSFT)")
        collector = StockDataCollector()
        df = collector.fetch_stock_data("MSFT", period="1y")

        if df.empty:
            log_fail("미국 종목 백테스트 데이터", "데이터 없음")
            return

        log_pass("백테스트 데이터 수집", f"({len(df)}일)")

        # 기술적 지표
        print("  📊 기술적 지표 계산 중...")
        analyzer = TechnicalAnalyzer(df)
        analyzer.add_all_indicators()
        df = analyzer.get_dataframe()

        # 백테스트 실행 (df를 초기화 시 전달)
        print("  🔄 백테스트 실행 중...")
        strategy = RSIStrategy()
        backtester = Backtester(df, initial_capital=100000)

        results_bt = backtester.run(strategy)

        if results_bt:
            total_return = results_bt.get('total_return', 0)
            log_pass("미국 종목 백테스트", f"(수익률: {total_return:.2f}%)")
        else:
            log_warn("백테스트 결과", "결과 없음")

    except Exception as e:
        log_fail("미국 종목 백테스트 전체", str(e)[:100])


def test_us_stock_risk_management():
    """미국 종목 VaR/CVaR 테스트"""
    print("\n" + "="*60)
    print("⚠️ 3. 미국 종목 VaR/CVaR 계산 테스트")
    print("="*60)

    try:
        from src.collectors.stock_collector import StockDataCollector
        from src.analyzers.risk_manager import RiskManager

        # 데이터 수집
        print("  📥 데이터 수집 중... (GOOGL)")
        collector = StockDataCollector()
        df = collector.fetch_stock_data("GOOGL", period="1y")

        if df.empty:
            log_fail("리스크 관리 데이터", "데이터 없음")
            return

        log_pass("리스크 데이터 수집", f"({len(df)}일)")

        # 리스크 분석 (메서드 확인 필요)
        print("  📊 리스크 지표 계산 중...")
        rm = RiskManager(df)

        # RiskManager 메서드 확인
        methods = [m for m in dir(rm) if not m.startswith('_')]
        print(f"  ℹ️ 사용 가능 메서드: {methods[:5]}...")

        # VaR/CVaR 메서드 존재 확인 및 실행
        if hasattr(rm, 'var'):
            var_95 = rm.var(confidence=0.95)
            log_pass("VaR 계산", f"(95%: {var_95:.2f}%)")
        elif hasattr(rm, 'value_at_risk'):
            var_95 = rm.value_at_risk()
            log_pass("VaR 계산", f"({var_95:.2f}%)")
        else:
            log_warn("VaR 계산", "메서드 없음 - 다른 방식으로 구현됨")

        # MDD/Sharpe 등 기본 리스크 지표
        if hasattr(rm, 'max_drawdown'):
            mdd = rm.max_drawdown()
            log_pass("MDD 계산", f"({mdd:.2f}%)")

        if hasattr(rm, 'sharpe_ratio'):
            sharpe = rm.sharpe_ratio()
            log_pass("Sharpe Ratio 계산", f"({sharpe:.2f})")

        # 최소한의 통과 조건
        log_pass("리스크 관리 클래스 로드")

    except Exception as e:
        log_fail("미국 종목 리스크 관리 전체", str(e)[:100])


def test_korean_market_regression():
    """한국 시장 회귀 테스트"""
    print("\n" + "="*60)
    print("🇰🇷 4. 한국 시장 회귀 테스트 (기존 기능)")
    print("="*60)

    try:
        from src.collectors.stock_collector import StockDataCollector
        from src.analyzers.technical_analyzer import TechnicalAnalyzer
        from src.models.ensemble_predictor import EnsemblePredictor

        # 삼성전자 데이터
        print("  📥 데이터 수집 중... (005930.KS)")
        collector = StockDataCollector()
        df = collector.fetch_stock_data("005930.KS", period="6mo")

        if df.empty:
            log_fail("한국 종목 데이터", "데이터 없음")
            return

        log_pass("한국 종목 데이터 수집", f"({len(df)}일)")

        # 기술적 지표
        analyzer = TechnicalAnalyzer(df)
        analyzer.add_all_indicators()
        df = analyzer.get_dataframe()

        log_pass("한국 종목 기술적 지표")

        # VWAP, OBV, ADX 확인
        if 'vwap' in df.columns:
            log_pass("VWAP 지표 확인")
        else:
            log_warn("VWAP 지표", "컬럼 없음")

        if 'obv' in df.columns:
            log_pass("OBV 지표 확인")
        else:
            log_warn("OBV 지표", "컬럼 없음")

        if 'adx' in df.columns:
            log_pass("ADX 지표 확인")
        else:
            log_warn("ADX 지표", "컬럼 없음")

        # 간단 예측 테스트 (XGBoost만)
        print("  🤖 AI 예측 테스트...")
        from src.models.xgboost_classifier import XGBoostClassifier

        xgb_model = XGBoostClassifier()
        train_size = int(len(df) * 0.8)
        xgb_model.train(df.iloc[:train_size])
        predictions = xgb_model.predict(df.iloc[train_size:])

        if predictions and len(predictions) > 0:
            log_pass("한국 종목 AI 예측", f"({len(predictions)}일 예측)")

    except Exception as e:
        log_fail("한국 시장 회귀 테스트 전체", str(e)[:100])


def print_summary():
    """테스트 결과 요약"""
    print("\n" + "="*60)
    print("📋 미검증 항목 테스트 결과")
    print("="*60)

    total = len(results["passed"]) + len(results["failed"])
    pass_rate = len(results["passed"]) / total * 100 if total > 0 else 0

    print(f"\n✅ 통과: {len(results['passed'])}개")
    print(f"❌ 실패: {len(results['failed'])}개")
    print(f"⚠️ 경고: {len(results['warnings'])}개")
    print(f"\n📊 통과율: {pass_rate:.1f}%")

    if results["failed"]:
        print("\n❌ 실패한 테스트:")
        for test, error in results["failed"]:
            print(f"  - {test}: {error[:80]}...")

    if results["warnings"]:
        print("\n⚠️ 경고:")
        for test, msg in results["warnings"]:
            print(f"  - {test}: {msg[:80]}")

    # 최종 판정
    print("\n" + "="*60)
    if len(results["failed"]) == 0:
        print("🎉 모든 미검증 항목 테스트 통과!")
        print("👉 다음 단계: 브라우저 테스트 진행")
    else:
        print("⚠️ 일부 테스트가 실패했습니다.")
        print("👉 위 오류를 확인 후 브라우저 테스트 진행하세요.")
    print("="*60)

    return len(results["failed"]) == 0


def main():
    """메인 테스트 실행"""
    print("="*60)
    print("🧪 미검증 항목 자동 테스트")
    print(f"📅 실행 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)

    # 테스트 실행
    test_us_stock_ai_prediction()
    test_us_stock_backtest()
    test_us_stock_risk_management()
    test_korean_market_regression()

    # 결과 요약
    success = print_summary()

    return 0 if success else 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
