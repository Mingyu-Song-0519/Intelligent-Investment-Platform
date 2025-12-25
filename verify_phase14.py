"""
Phase 14 Regime-Aware AI 예측 검증 스크립트
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

print("="*60)
print("🤖 Phase 14: Regime-Aware AI 예측 검증")
print("="*60)

results = {"passed": [], "failed": []}


def log_pass(msg):
    results["passed"].append(msg)
    print(f"✅ PASS: {msg}")


def log_fail(msg, error):
    results["failed"].append((msg, error))
    print(f"❌ FAIL: {msg} - {error}")


# 1. 모듈 Import
print("\n" + "="*60)
print("📦 1. 모듈 Import 테스트")
print("="*60)

try:
    from src.analyzers.regime_classifier import (
        RegimeClassifier,
        RegimeAwareModelSelector,
        MarketRegime
    )
    log_pass("regime_classifier 모듈 import")
except Exception as e:
    log_fail("regime_classifier import", str(e))

try:
    from src.models.regime_predictor import RegimeAwarePredictor
    log_pass("regime_predictor 모듈 import")
except Exception as e:
    log_fail("regime_predictor import", str(e))

# 2. 레짐 분류 테스트
print("\n" + "="*60)
print("🎯 2. 시장 레짐 분류 테스트")
print("="*60)

try:
    from src.analyzers.regime_classifier import RegimeClassifier
    
    classifier = RegimeClassifier()
    
    # 저변동성 강세장
    regime1 = classifier.classify(vix=12.0, market_return_20d=5.0)
    if regime1.regime_type == "LOW_VOL_BULL":
        log_pass(f"저변동성 강세장 감지: {regime1.description}")
    else:
        log_fail("저변동성 강세장", f"잘못된 분류: {regime1.regime_type}")
    
    # 고변동성 약세장
    regime2 = classifier.classify(vix=30.0, market_return_20d=-8.0)
    if regime2.regime_type == "HIGH_VOL_BEAR":
        log_pass(f"고변동성 약세장 감지: {regime2.description}")
    else:
        log_fail("고변동성 약세장", f"잘못된 분류: {regime2.regime_type}")
    
    # 횡보장
    regime3 = classifier.classify(vix=18.0, market_return_20d=0.5)
    if regime3.regime_type == "SIDEWAYS":
        log_pass(f"횡보장 감지: {regime3.description}")
    else:
        log_fail("횡보장", f"잘못된 분류: {regime3.regime_type}")
    
except Exception as e:
    log_fail("레짐 분류", str(e))

# 3. 모델 가중치 선택 테스트
print("\n" + "="*60)
print("⚖️ 3. 레짐별 모델 가중치 선택")
print("="*60)

try:
    from src.analyzers.regime_classifier import RegimeAwareModelSelector
    
    selector = RegimeAwareModelSelector(classifier)
    
    # 저변동성 강세장 가중치
    weights1 = selector.get_model_weights(regime1)
    log_pass(f"LOW_VOL_BULL 가중치: LSTM={weights1['lstm']:.1f}, XGB={weights1['xgboost']:.1f}")
    
    # 고변동성 약세장 가중치
    weights2 = selector.get_model_weights(regime2)
    log_pass(f"HIGH_VOL_BEAR 가중치: LSTM={weights2['lstm']:.1f}, XGB={weights2['xgboost']:.1f}")
    
    # 투자 권고
    rec = selector.get_recommendation(regime1)
    log_pass(f"투자 권고: {rec}")
    
except Exception as e:
    log_fail("모델 가중치 선택", str(e))

# 4. Regime-Aware 예측 테스트
print("\n" + "="*60)
print("🔮 4. Regime-Aware 예측 테스트")
print("="*60)

try:
    from src.models.regime_predictor import RegimeAwarePredictor
    import yfinance as yf
    
    # 테스트 데이터 (AAPL)
    ticker = yf.Ticker("AAPL")
    df = ticker.history(period="3mo")
    
    if not df.empty:
        predictor = RegimeAwarePredictor()
        
        # 예측 수행
        result = predictor.predict(df, use_regime_weights=True)
        
        log_pass(f"예측 완료: {result['regime'].description}")
        
        print(f"\n  📊 예측 결과:")
        print(f"     레짐: {result['regime'].regime_type}")
        print(f"     신뢰도: {result['confidence']:.1%}")
        print(f"     모델 가중치: LSTM {result['model_weights']['lstm']:.0%}")
        print(f"     권고: {result['recommendation']}\n")
        
        # 레짐 요약
        summary = predictor.get_regime_summary()
        log_pass("레짐 요약 생성")
        
    else:
        log_fail("예측 테스트", "데이터 없음")
    
except Exception as e:
    log_fail("Regime-Aware 예측", str(e))

# 5. 학습 전략 제안 테스트
print("\n" + "="*60)
print("📚 5. 레짐별 학습 전략 제안")
print("="*60)

try:
    from src.models.regime_predictor import RegimeAwarePredictor
    
    predictor = RegimeAwarePredictor()
    
    # 저변동성 강세장 전략
    strategy1 = predictor.get_training_strategy(regime1)
    log_pass(f"LOW_VOL_BULL 전략: {strategy1['focus']}")
    
    # 고변동성 약세장 전략
    strategy2 = predictor.get_training_strategy(regime2)
    log_pass(f"HIGH_VOL_BEAR 전략: {strategy2['focus']}")
    
except Exception as e:
    log_fail("학습 전략 제안", str(e))

# 결과 요약
print("\n" + "="*60)
print("📋 Phase 14 테스트 결과")
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
    print("🎉 Phase 14 Regime-Aware AI 예측 검증 완료!")
    print("   - 시장 레짐 분류 (VIX + 추세) ✅")
    print("   - 레짐별 모델 가중치 적응 ✅")
    print("   - 적응형 예측 시스템 ✅")
    print("   - 학습 전략 제안 ✅")
else:
    print("⚠️ 일부 테스트 실패.")
print("="*60)
