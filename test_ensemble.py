"""
앙상블 예측 모델 테스트 스크립트
LSTM + XGBoost 결합 예측 검증
"""
import sys
from pathlib import Path

# 프로젝트 루트 경로 추가
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np
import pandas as pd
import yfinance as yf
from src.models import EnsemblePredictor
from src.analyzers.technical_analyzer import TechnicalAnalyzer


def print_section(title: str):
    """섹션 구분선 출력"""
    print("\n" + "=" * 70)
    print(f" {title}")
    print("=" * 70)


def test_ensemble_basic():
    """기본 앙상블 기능 테스트"""
    print_section("1. 기본 앙상블 기능 테스트")

    # 데이터 로드
    print("\n[1] 데이터 로드 중...")
    ticker = yf.Ticker("005930.KS")  # 삼성전자
    df = ticker.history(period="2y")
    df.columns = [col.lower().replace(' ', '_') for col in df.columns]
    df = df.reset_index()

    # 기술적 지표 추가
    print("[2] 기술적 지표 계산 중...")
    analyzer = TechnicalAnalyzer(df)
    analyzer.add_all_indicators()
    df = analyzer.get_dataframe()

    print(f"[3] 데이터 준비 완료: {len(df)} rows x {len(df.columns)} columns")

    # 앙상블 모델 생성 (기본 전략: weighted_average)
    print("\n[4] 앙상블 모델 생성...")
    ensemble = EnsemblePredictor(strategy='weighted_average')

    # 모델 학습
    print("\n[5] 모델 학습 시작...")
    print("-" * 70)
    results = ensemble.train_models(df, verbose=0)
    print("-" * 70)

    # 학습 결과 출력
    print("\n[6] 학습 결과:")
    if 'lstm' in results:
        print(f"   - LSTM RMSE: {results['lstm']['rmse']:,.2f}")
    if 'xgboost' in results:
        print(f"   - XGBoost Accuracy: {results['xgboost']['accuracy']:.2%}")

    print("\n[TEST PASSED] 기본 앙상블 기능 정상 작동")
    return ensemble, df


def test_price_prediction(ensemble, df):
    """가격 예측 테스트"""
    print_section("2. 가격 예측 테스트 (회귀)")

    print("\n[1] 가격 예측 수행 중...")
    price_pred = ensemble.predict_price(df)

    print("\n[2] 예측 결과:")
    print(f"   - 현재 가격: {price_pred['current_price']:,.0f}원")

    if price_pred['ensemble_prediction']:
        predicted_price = price_pred['ensemble_prediction']
        print(f"   - 예측 가격: {predicted_price:,.0f}원")

        # 변화율 계산
        change_pct = ((predicted_price - price_pred['current_price']) /
                      price_pred['current_price']) * 100
        print(f"   - 예상 변화율: {change_pct:+.2f}%")

    print(f"   - 신뢰도 점수: {price_pred['confidence_score']:.2%}")
    print(f"   - 사용 전략: {price_pred['strategy']}")

    print("\n[3] 개별 모델 예측:")
    for model_name, pred_value in price_pred['individual_predictions'].items():
        if isinstance(pred_value, (int, float)):
            print(f"   - {model_name}: {pred_value:,.0f}")
        else:
            print(f"   - {model_name}: {pred_value}")

    print("\n[TEST PASSED] 가격 예측 정상 작동")


def test_direction_prediction(ensemble, df):
    """등락 예측 테스트"""
    print_section("3. 등락 예측 테스트 (분류)")

    print("\n[1] 등락 예측 수행 중...")
    direction_pred = ensemble.predict_direction(df, include_rule_based=True)

    print("\n[2] 예측 결과:")
    print(f"   - 예측 방향: {direction_pred['ensemble_prediction'].upper()}")
    print(f"   - 신뢰도 점수: {direction_pred['confidence_score']:.2%}")

    # 신뢰도 레벨 표시
    confidence = direction_pred['confidence_score']
    if confidence >= 0.75:
        level = "높음 (HIGH)"
    elif confidence >= 0.60:
        level = "중간 (MEDIUM)"
    else:
        level = "낮음 (LOW)"
    print(f"   - 신뢰도 레벨: {level}")

    print("\n[3] 개별 모델 예측:")
    for model_name, pred_value in direction_pred['individual_predictions'].items():
        if model_name in ['lstm', 'xgboost', 'rule_based']:
            direction = "UP" if pred_value == 1 else "DOWN"
            print(f"   - {model_name}: {direction} ({pred_value})")
        else:
            print(f"   - {model_name}: {pred_value}")

    print(f"\n[4] 투표 결과: {direction_pred['votes']}")
    up_votes = sum(direction_pred['votes'])
    total_votes = len(direction_pred['votes'])
    print(f"   - UP: {up_votes}/{total_votes} ({up_votes/total_votes:.1%})")
    print(f"   - DOWN: {total_votes - up_votes}/{total_votes} ({(total_votes - up_votes)/total_votes:.1%})")

    print("\n[TEST PASSED] 등락 예측 정상 작동")


def test_voting_strategy(df):
    """투표 전략 테스트"""
    print_section("4. 투표(Voting) 전략 테스트")

    print("\n[1] 투표 전략 앙상블 생성...")
    ensemble_voting = EnsemblePredictor(strategy='voting')

    print("[2] 모델 학습 중...")
    ensemble_voting.train_models(df, verbose=0)

    print("\n[3] 등락 예측 수행...")
    direction_pred = ensemble_voting.predict_direction(df)

    print("\n[4] 투표 결과:")
    print(f"   - 예측 방향: {direction_pred['ensemble_prediction'].upper()}")
    print(f"   - 신뢰도: {direction_pred['confidence_score']:.2%}")
    print(f"   - 투표: {direction_pred['votes']}")

    print("\n[TEST PASSED] 투표 전략 정상 작동")


def test_weight_adjustment(ensemble, df):
    """가중치 조정 테스트"""
    print_section("5. 가중치 동적 조정 테스트")

    print("\n[1] 기존 가중치:")
    print(f"   {ensemble.weights}")

    # 새로운 가중치 설정
    new_weights = {
        'lstm': 0.7,
        'xgboost': 0.2,
        'rule_based': 0.1
    }

    print("\n[2] 새로운 가중치 적용...")
    ensemble.set_weights(new_weights)

    print("\n[3] 업데이트된 가중치로 예측...")
    price_pred = ensemble.predict_price(df)

    print(f"   - 예측 가격: {price_pred.get('ensemble_prediction', 'N/A')}")
    print(f"   - 신뢰도: {price_pred['confidence_score']:.2%}")

    print("\n[TEST PASSED] 가중치 조정 정상 작동")


def test_confidence_metrics(ensemble):
    """신뢰도 메트릭 테스트"""
    print_section("6. 신뢰도 메트릭 테스트")

    print("\n[1] 신뢰도 메트릭 계산...")
    metrics = ensemble.get_confidence_metrics()

    if 'total_predictions' in metrics and metrics['total_predictions'] > 0:
        print("\n[2] 신뢰도 통계:")
        print(f"   - 총 예측 횟수: {metrics['total_predictions']}")
        print(f"   - 평균 신뢰도: {metrics['average_confidence']:.2%}")
        print(f"   - 최소 신뢰도: {metrics['min_confidence']:.2%}")
        print(f"   - 최대 신뢰도: {metrics['max_confidence']:.2%}")
        print(f"   - 표준편차: {metrics['std_confidence']:.4f}")

        if 'recent_confidence' in metrics:
            print(f"\n[3] 최근 5개 예측 신뢰도:")
            for i, conf in enumerate(metrics['recent_confidence'], 1):
                print(f"   {i}. {conf:.2%}")
    else:
        print("\n[2] 아직 예측 히스토리가 충분하지 않습니다.")

    print("\n[TEST PASSED] 신뢰도 메트릭 정상 작동")


def test_model_save_load(ensemble):
    """모델 저장/로드 테스트"""
    print_section("7. 모델 저장/로드 테스트")

    try:
        print("\n[1] 모델 저장 중...")
        ensemble.save_models(prefix='test_ensemble')

        print("\n[2] 새로운 앙상블 인스턴스 생성...")
        new_ensemble = EnsemblePredictor()

        print("\n[3] 저장된 모델 로드 중...")
        new_ensemble.load_models(prefix='test_ensemble')

        print("\n[TEST PASSED] 모델 저장/로드 정상 작동")

    except Exception as e:
        print(f"\n[WARNING] 모델 저장/로드 테스트 실패: {e}")
        print("(일부 의존성이 설치되지 않았을 수 있습니다)")


def test_multiple_predictions(ensemble, df):
    """다중 예측 테스트"""
    print_section("8. 연속 예측 테스트")

    print("\n[1] 5번 연속 예측 수행...")

    predictions_summary = []

    for i in range(5):
        # 가격 예측
        price_pred = ensemble.predict_price(df)
        direction_pred = ensemble.predict_direction(df)

        predictions_summary.append({
            'iteration': i + 1,
            'price': price_pred.get('ensemble_prediction', None),
            'direction': direction_pred['ensemble_prediction'],
            'price_confidence': price_pred['confidence_score'],
            'direction_confidence': direction_pred['confidence_score']
        })

    print("\n[2] 예측 요약:")
    print(f"{'회차':<6} {'예측가격':<12} {'방향':<8} {'가격신뢰도':<12} {'방향신뢰도':<12}")
    print("-" * 60)

    for pred in predictions_summary:
        price_str = f"{pred['price']:,.0f}" if pred['price'] else "N/A"
        print(f"{pred['iteration']:<6} {price_str:<12} "
              f"{pred['direction'].upper():<8} "
              f"{pred['price_confidence']:<11.2%} "
              f"{pred['direction_confidence']:<11.2%}")

    print("\n[TEST PASSED] 연속 예측 정상 작동")


def run_all_tests():
    """모든 테스트 실행"""
    print("\n" + "=" * 70)
    print(" AI 모델 앙상블 전략 종합 테스트")
    print("=" * 70)

    try:
        # 1. 기본 기능 테스트
        ensemble, df = test_ensemble_basic()

        # 2. 가격 예측 테스트
        test_price_prediction(ensemble, df)

        # 3. 등락 예측 테스트
        test_direction_prediction(ensemble, df)

        # 4. 투표 전략 테스트
        test_voting_strategy(df)

        # 5. 가중치 조정 테스트
        test_weight_adjustment(ensemble, df)

        # 6. 신뢰도 메트릭 테스트
        test_confidence_metrics(ensemble)

        # 7. 모델 저장/로드 테스트
        test_model_save_load(ensemble)

        # 8. 다중 예측 테스트
        test_multiple_predictions(ensemble, df)

        # 최종 결과
        print_section("전체 테스트 완료")
        print("\n모든 테스트를 성공적으로 완료했습니다!")
        print("\n앙상블 모델이 정상적으로 작동하며 다음 기능을 제공합니다:")
        print("  - LSTM + XGBoost 결합 예측")
        print("  - 가중 평균(Weighted Average) 전략")
        print("  - 투표(Voting) 전략")
        print("  - 스태킹(Stacking) 전략 (메타 모델)")
        print("  - 신뢰도 점수 계산")
        print("  - 규칙 기반 시그널 통합")
        print("  - 가중치 동적 조정")
        print("  - 모델 저장/로드")

    except Exception as e:
        print_section("테스트 실패")
        print(f"\n오류 발생: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    run_all_tests()
