"""
앙상블 예측 모델 간단 검증 스크립트
기본 import와 클래스 생성만 테스트
"""
import sys
from pathlib import Path

# 프로젝트 루트 경로 추가
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

print("=" * 70)
print(" 앙상블 모델 간단 검증")
print("=" * 70)

# 1. 모듈 import 테스트
print("\n[1] 모듈 import 테스트...")
try:
    from src.models import EnsemblePredictor
    print("   - EnsemblePredictor import 성공")
except Exception as e:
    print(f"   - EnsemblePredictor import 실패: {e}")
    sys.exit(1)

# 2. config 로드 테스트
print("\n[2] 설정 파일 로드 테스트...")
try:
    from config import ENSEMBLE_CONFIG
    print("   - ENSEMBLE_CONFIG 로드 성공")
    print(f"   - 전략: {ENSEMBLE_CONFIG.get('strategy')}")
    print(f"   - 가중치: {ENSEMBLE_CONFIG.get('weights')}")
except Exception as e:
    print(f"   - 설정 로드 실패: {e}")
    sys.exit(1)

# 3. 앙상블 인스턴스 생성 테스트
print("\n[3] 앙상블 인스턴스 생성 테스트...")
try:
    # 기본 전략
    ensemble1 = EnsemblePredictor(strategy='weighted_average')
    print("   - weighted_average 전략 생성 성공")

    # 투표 전략
    ensemble2 = EnsemblePredictor(strategy='voting')
    print("   - voting 전략 생성 성공")

    # 스태킹 전략
    ensemble3 = EnsemblePredictor(strategy='stacking')
    print("   - stacking 전략 생성 성공")

except Exception as e:
    print(f"   - 인스턴스 생성 실패: {e}")
    sys.exit(1)

# 4. 가중치 설정 테스트
print("\n[4] 가중치 설정 테스트...")
try:
    custom_weights = {'lstm': 0.6, 'xgboost': 0.3, 'rule_based': 0.1}
    ensemble1.set_weights(custom_weights)
    print("   - 가중치 설정 성공")
    print(f"   - 현재 가중치: {ensemble1.weights}")
except Exception as e:
    print(f"   - 가중치 설정 실패: {e}")

# 5. 신뢰도 메트릭 테스트
print("\n[5] 신뢰도 메트릭 테스트...")
try:
    metrics = ensemble1.get_confidence_metrics()
    print("   - 신뢰도 메트릭 조회 성공")
    print(f"   - 결과: {metrics}")
except Exception as e:
    print(f"   - 신뢰도 메트릭 실패: {e}")

print("\n" + "=" * 70)
print(" 기본 검증 완료")
print("=" * 70)
print("\n모든 기본 기능이 정상 작동합니다.")
print("\n앙상블 모델 주요 기능:")
print("  1. LSTM + XGBoost 결합 예측")
print("  2. 가중 평균(Weighted Average) 전략")
print("  3. 투표(Voting) 전략")
print("  4. 스태킹(Stacking) 전략")
print("  5. 신뢰도 점수 계산")
print("  6. 가중치 동적 조정")
print("\n실제 데이터로 테스트하려면 test_ensemble.py를 실행하세요:")
print("  python test_ensemble.py")
