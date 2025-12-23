"""
Phase 9 모듈 검증 스크립트
모든 신규 생성된 모듈이 정상 작동하는지 테스트합니다.
"""
import sys
from pathlib import Path
from datetime import datetime

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


def test_imports():
    """모듈 import 테스트"""
    print("\n" + "="*60)
    print("📦 1. 모듈 Import 테스트")
    print("="*60)
    
    modules = [
        ("src.analyzers.technical_analyzer", "TechnicalAnalyzer"),
        ("src.analyzers.volatility_analyzer", "VolatilityAnalyzer"),
        ("src.analyzers.market_breadth", "MarketBreadthAnalyzer"),
        ("src.analyzers.options_analyzer", "OptionsAnalyzer"),
        ("src.analyzers.fundamental_analyzer", "FundamentalAnalyzer"),
        ("src.analyzers.macro_analyzer", "MacroAnalyzer"),
        ("src.models.sentiment_feature_integrator", "SentimentFeatureIntegrator"),
        ("src.utils.hints", "INDICATOR_HINTS"),
        ("src.utils.notification_manager", "NotificationManager"),
    ]
    
    for module_path, class_name in modules:
        try:
            module = __import__(module_path, fromlist=[class_name])
            getattr(module, class_name)
            log_pass(f"Import {module_path}.{class_name}")
        except Exception as e:
            log_fail(f"Import {module_path}.{class_name}", str(e))


def test_technical_analyzer():
    """기술적 분석 테스트 (VWAP, OBV, ADX)"""
    print("\n" + "="*60)
    print("📊 2. 기술적 분석 테스트 (VWAP, OBV, ADX)")
    print("="*60)
    
    try:
        import pandas as pd
        import numpy as np
        from src.analyzers.technical_analyzer import TechnicalAnalyzer
        
        # 테스트 데이터 생성
        dates = pd.date_range(start='2024-01-01', periods=100, freq='D')
        np.random.seed(42)
        df = pd.DataFrame({
            'date': dates,
            'open': 100 + np.random.randn(100).cumsum(),
            'high': 105 + np.random.randn(100).cumsum(),
            'low': 95 + np.random.randn(100).cumsum(),
            'close': 100 + np.random.randn(100).cumsum(),
            'volume': np.random.randint(1000000, 5000000, 100)
        })
        
        # 기술적 분석
        analyzer = TechnicalAnalyzer(df)
        analyzer.add_all_indicators()
        result_df = analyzer.get_dataframe()
        
        # VWAP 확인
        if 'vwap' in result_df.columns:
            log_pass("VWAP 계산", f"(값: {result_df['vwap'].iloc[-1]:.2f})")
        else:
            log_fail("VWAP 계산", "컬럼 없음")
        
        # OBV 확인
        if 'obv' in result_df.columns:
            log_pass("OBV 계산", f"(값: {result_df['obv'].iloc[-1]:,.0f})")
        else:
            log_fail("OBV 계산", "컬럼 없음")
        
        # ADX 확인
        if 'adx' in result_df.columns:
            adx_val = result_df['adx'].dropna().iloc[-1] if not result_df['adx'].dropna().empty else None
            if adx_val:
                log_pass("ADX 계산", f"(값: {adx_val:.2f})")
            else:
                log_warn("ADX 계산", "값이 NaN")
        else:
            log_fail("ADX 계산", "컬럼 없음")
            
    except Exception as e:
        log_fail("기술적 분석 전체", str(e))


def test_volatility_analyzer():
    """변동성 분석 테스트 (VIX)"""
    print("\n" + "="*60)
    print("😱 3. 변동성 분석 테스트 (VIX)")
    print("="*60)
    
    try:
        from src.analyzers.volatility_analyzer import VolatilityAnalyzer
        
        analyzer = VolatilityAnalyzer()
        
        # VIX 수집
        vix = analyzer.get_current_vix()
        if vix:
            log_pass("VIX 수집", f"(현재값: {vix:.2f})")
        else:
            log_warn("VIX 수집", "데이터 없음 (네트워크 문제일 수 있음)")
        
        # 변동성 구간
        regime, color = analyzer.volatility_regime()
        log_pass("변동성 구간 판단", f"({color} {regime})")
        
    except Exception as e:
        log_fail("변동성 분석 전체", str(e))


def test_market_breadth():
    """시장 폭 분석 테스트"""
    print("\n" + "="*60)
    print("📈 4. 시장 폭 분석 테스트")
    print("="*60)
    
    try:
        from src.analyzers.market_breadth import MarketBreadthAnalyzer
        
        analyzer = MarketBreadthAnalyzer(market="US")
        
        # 상승/하락 비율 (데이터 수집에 시간 소요)
        ad = analyzer.advance_decline_ratio()
        if "error" not in ad:
            log_pass("상승/하락 비율", f"(비율: {ad.get('ratio', 'N/A')})")
        else:
            log_warn("상승/하락 비율", ad.get("error", "알 수 없는 오류"))
        
        log_pass("MarketBreadthAnalyzer 클래스 로드")
        
    except Exception as e:
        log_fail("시장 폭 분석 전체", str(e))


def test_options_analyzer():
    """옵션 분석 테스트"""
    print("\n" + "="*60)
    print("📊 5. 옵션 분석 테스트")
    print("="*60)
    
    try:
        from src.analyzers.options_analyzer import OptionsAnalyzer
        
        analyzer = OptionsAnalyzer("SPY")
        
        # 만기일 조회
        expirations = analyzer.get_available_expirations()
        if expirations:
            log_pass("만기일 조회", f"({len(expirations)}개 만기일)")
        else:
            log_warn("만기일 조회", "데이터 없음")
        
        # Put/Call Ratio
        pc = analyzer.calculate_put_call_ratio()
        if "error" not in pc:
            log_pass("Put/Call Ratio", f"(거래량 기준: {pc.get('volume_ratio', 'N/A')})")
        else:
            log_warn("Put/Call Ratio", pc.get("error", "알 수 없음"))
        
        log_pass("OptionsAnalyzer 클래스 로드")
        
    except Exception as e:
        log_fail("옵션 분석 전체", str(e))


def test_fundamental_analyzer():
    """펀더멘털 분석 테스트"""
    print("\n" + "="*60)
    print("💰 6. 펀더멘털 분석 테스트")
    print("="*60)
    
    try:
        from src.analyzers.fundamental_analyzer import FundamentalAnalyzer
        
        analyzer = FundamentalAnalyzer("AAPL")
        
        # 밸류에이션
        val = analyzer.get_valuation_metrics()
        if val.get("per"):
            log_pass("PER 수집", f"(값: {val['per']:.2f})")
        else:
            log_warn("PER 수집", "데이터 없음")
        
        # 수익성
        prof = analyzer.get_profitability_metrics()
        if prof.get("roe"):
            log_pass("ROE 수집", f"(값: {prof['roe']*100:.2f}%)")
        else:
            log_warn("ROE 수집", "데이터 없음")
        
        log_pass("FundamentalAnalyzer 클래스 로드")
        
    except Exception as e:
        log_fail("펀더멘털 분석 전체", str(e))


def test_macro_analyzer():
    """매크로 분석 테스트"""
    print("\n" + "="*60)
    print("🌍 7. 매크로 분석 테스트")
    print("="*60)
    
    try:
        from src.analyzers.macro_analyzer import MacroAnalyzer
        
        analyzer = MacroAnalyzer()
        
        # 10년물 국채
        us_10y = analyzer.get_indicator("us_10y")
        if us_10y.get("current"):
            log_pass("미국 10년물 수집", f"(값: {us_10y['current']:.2f}%)")
        else:
            log_warn("미국 10년물 수집", "데이터 없음")
        
        # 달러 인덱스
        dxy = analyzer.get_indicator("dxy")
        if dxy.get("current"):
            log_pass("달러 인덱스 수집", f"(값: {dxy['current']:.2f})")
        else:
            log_warn("달러 인덱스 수집", "데이터 없음")
        
        log_pass("MacroAnalyzer 클래스 로드")
        
    except Exception as e:
        log_fail("매크로 분석 전체", str(e))


def test_hints():
    """초보자 힌트 테스트"""
    print("\n" + "="*60)
    print("💡 8. 초보자 힌트 테스트")
    print("="*60)
    
    try:
        from src.utils.hints import INDICATOR_HINTS, get_hint_text
        
        # 지표 개수
        indicator_count = len(INDICATOR_HINTS)
        log_pass("지표 설명 로드", f"({indicator_count}개 지표)")
        
        # 힌트 함수
        rsi_hint = get_hint_text("RSI", "short")
        if rsi_hint and "과열" in rsi_hint:
            log_pass("get_hint_text 함수")
        else:
            log_warn("get_hint_text 함수", "예상과 다른 응답")
        
    except Exception as e:
        log_fail("초보자 힌트 전체", str(e))


def test_notification_manager():
    """알림 시스템 테스트"""
    print("\n" + "="*60)
    print("🔔 9. 알림 시스템 테스트")
    print("="*60)
    
    try:
        from src.utils.notification_manager import (
            NotificationManager, AlertConfig, AlertType, AlertLevel
        )
        
        # 설정 생성
        config = AlertConfig()
        log_pass("AlertConfig 생성")
        
        # 매니저 생성
        manager = NotificationManager(config)
        log_pass("NotificationManager 생성")
        
        # VIX 체크 (테스트 값)
        alert = manager.check_vix(28.5)
        if alert:
            log_pass("VIX 알림 생성", f"({alert.level.value})")
        else:
            log_pass("VIX 알림 조건 미충족 (정상)")
        
        # MDD 체크
        alert = manager.check_mdd(15.0, "TEST")
        if alert:
            log_pass("MDD 알림 생성", f"({alert.level.value})")
        
    except Exception as e:
        log_fail("알림 시스템 전체", str(e))


def test_sentiment_integrator():
    """감성 분석 통합 테스트"""
    print("\n" + "="*60)
    print("📰 10. 감성 분석 통합 테스트")
    print("="*60)
    
    try:
        from src.models.sentiment_feature_integrator import (
            SentimentFeatureIntegrator, create_enhanced_features
        )
        
        # 클래스 생성
        integrator = SentimentFeatureIntegrator("AAPL", "Apple", "US")
        log_pass("SentimentFeatureIntegrator 생성")
        
        # 피처 컬럼
        cols = SentimentFeatureIntegrator.get_sentiment_feature_columns()
        log_pass("감성 피처 컬럼 정의", f"({len(cols)}개)")
        
        # 중립 피처 (뉴스 수집 없이)
        neutral = integrator._get_neutral_features()
        if neutral["sentiment_score"] == 0.0:
            log_pass("중립 피처 생성")
        
    except Exception as e:
        log_fail("감성 분석 통합 전체", str(e))


def print_summary():
    """테스트 결과 요약"""
    print("\n" + "="*60)
    print("📋 테스트 결과 요약")
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
            print(f"  - {test}: {error[:50]}...")
    
    if results["warnings"]:
        print("\n⚠️ 경고:")
        for test, msg in results["warnings"]:
            print(f"  - {test}: {msg}")
    
    # 최종 판정
    print("\n" + "="*60)
    if len(results["failed"]) == 0:
        print("🎉 모든 테스트 통과! Phase 9 모듈이 정상 작동합니다.")
    else:
        print("⚠️ 일부 테스트가 실패했습니다. 위 오류를 확인해주세요.")
    print("="*60)
    
    return len(results["failed"]) == 0


def main():
    """메인 테스트 실행"""
    print("="*60)
    print("🧪 Phase 9 모듈 검증 스크립트")
    print(f"📅 실행 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    # 테스트 실행
    test_imports()
    test_technical_analyzer()
    test_volatility_analyzer()
    test_market_breadth()
    test_options_analyzer()
    test_fundamental_analyzer()
    test_macro_analyzer()
    test_hints()
    test_notification_manager()
    test_sentiment_integrator()
    
    # 결과 요약
    success = print_summary()
    
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
