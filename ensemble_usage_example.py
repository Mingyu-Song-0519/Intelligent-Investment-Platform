"""
앙상블 예측 모델 사용 예제
다양한 앙상블 전략을 활용한 주가 예측
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

import yfinance as yf
from src.models import EnsemblePredictor, LSTMPredictor, XGBoostClassifier
from src.analyzers.technical_analyzer import TechnicalAnalyzer


def example_1_weighted_average():
    """예제 1: 가중 평균(Weighted Average) 전략"""
    print("\n" + "=" * 70)
    print(" 예제 1: 가중 평균 전략으로 주가 예측")
    print("=" * 70)

    # 데이터 로드 및 전처리
    ticker = yf.Ticker("005930.KS")
    df = ticker.history(period="2y")
    df.columns = [col.lower().replace(' ', '_') for col in df.columns]
    df = df.reset_index()

    analyzer = TechnicalAnalyzer(df)
    analyzer.add_all_indicators()
    df = analyzer.get_dataframe()

    # 앙상블 모델 생성 (가중 평균 전략)
    ensemble = EnsemblePredictor(strategy='weighted_average')

    # 모델 학습
    print("\n[학습 시작]")
    ensemble.train_models(df, verbose=0)

    # 가격 예측
    print("\n[가격 예측]")
    price_pred = ensemble.predict_price(df)
    print(f"현재 가격: {price_pred['current_price']:,.0f}원")
    print(f"예측 가격: {price_pred['ensemble_prediction']:,.0f}원")
    print(f"신뢰도: {price_pred['confidence_score']:.2%}")

    # 등락 예측
    print("\n[등락 예측]")
    direction_pred = ensemble.predict_direction(df)
    print(f"예측 방향: {direction_pred['ensemble_prediction'].upper()}")
    print(f"신뢰도: {direction_pred['confidence_score']:.2%}")


def example_2_voting():
    """예제 2: 투표(Voting) 전략"""
    print("\n" + "=" * 70)
    print(" 예제 2: 투표 전략으로 등락 예측")
    print("=" * 70)

    # 데이터 로드
    ticker = yf.Ticker("035420.KS")  # NAVER
    df = ticker.history(period="2y")
    df.columns = [col.lower().replace(' ', '_') for col in df.columns]
    df = df.reset_index()

    analyzer = TechnicalAnalyzer(df)
    analyzer.add_all_indicators()
    df = analyzer.get_dataframe()

    # 투표 전략 앙상블
    ensemble = EnsemblePredictor(strategy='voting')
    ensemble.train_models(df, verbose=0)

    # 등락 예측 (규칙 기반 포함)
    direction_pred = ensemble.predict_direction(df, include_rule_based=True)

    print(f"\n현재 가격: {direction_pred['current_price']:,.0f}원")
    print(f"예측 방향: {direction_pred['ensemble_prediction'].upper()}")
    print(f"신뢰도: {direction_pred['confidence_score']:.2%}")

    print("\n[개별 모델 투표 결과]")
    for model, vote in direction_pred['individual_predictions'].items():
        if model in ['lstm', 'xgboost', 'rule_based']:
            direction = "UP" if vote == 1 else "DOWN"
            print(f"  {model:15s}: {direction}")


def example_3_custom_weights():
    """예제 3: 커스텀 가중치 설정"""
    print("\n" + "=" * 70)
    print(" 예제 3: 커스텀 가중치로 예측 조정")
    print("=" * 70)

    # 데이터 로드
    ticker = yf.Ticker("AAPL")  # Apple
    df = ticker.history(period="1y")
    df.columns = [col.lower().replace(' ', '_') for col in df.columns]
    df = df.reset_index()

    analyzer = TechnicalAnalyzer(df)
    analyzer.add_all_indicators()
    df = analyzer.get_dataframe()

    # 앙상블 생성
    ensemble = EnsemblePredictor()
    ensemble.train_models(df, verbose=0)

    # 시나리오 1: LSTM 중심 (보수적)
    print("\n[시나리오 1: LSTM 중심 (70%)]")
    ensemble.set_weights({'lstm': 0.7, 'xgboost': 0.2, 'rule_based': 0.1})
    pred1 = ensemble.predict_price(df)
    print(f"예측 가격: ${pred1['ensemble_prediction']:.2f}")
    print(f"신뢰도: {pred1['confidence_score']:.2%}")

    # 시나리오 2: 균형잡힌 접근
    print("\n[시나리오 2: 균형 (각 33%)]")
    ensemble.set_weights({'lstm': 0.33, 'xgboost': 0.33, 'rule_based': 0.34})
    pred2 = ensemble.predict_direction(df)
    print(f"예측 방향: {pred2['ensemble_prediction'].upper()}")
    print(f"신뢰도: {pred2['confidence_score']:.2%}")


def example_4_stacking():
    """예제 4: 스태킹(Stacking) 전략"""
    print("\n" + "=" * 70)
    print(" 예제 4: 스태킹 전략 (메타 모델)")
    print("=" * 70)

    # 데이터 로드
    ticker = yf.Ticker("MSFT")  # Microsoft
    df = ticker.history(period="2y")
    df.columns = [col.lower().replace(' ', '_') for col in df.columns]
    df = df.reset_index()

    analyzer = TechnicalAnalyzer(df)
    analyzer.add_all_indicators()
    df = analyzer.get_dataframe()

    # 스태킹 전략
    ensemble = EnsemblePredictor(strategy='stacking')

    print("\n[메타 모델 학습 포함]")
    ensemble.train_models(df, verbose=0)

    # 예측
    price_pred = ensemble.predict_price(df)
    print(f"\n현재 가격: ${price_pred['current_price']:.2f}")
    print(f"메타 모델 예측: ${price_pred['ensemble_prediction']:.2f}")
    print(f"신뢰도: {price_pred['confidence_score']:.2%}")


def example_5_model_persistence():
    """예제 5: 모델 저장 및 로드"""
    print("\n" + "=" * 70)
    print(" 예제 5: 모델 저장 및 재사용")
    print("=" * 70)

    # 데이터 로드 및 학습
    ticker = yf.Ticker("005930.KS")
    df = ticker.history(period="1y")
    df.columns = [col.lower().replace(' ', '_') for col in df.columns]
    df = df.reset_index()

    analyzer = TechnicalAnalyzer(df)
    analyzer.add_all_indicators()
    df = analyzer.get_dataframe()

    # 앙상블 생성 및 학습
    print("\n[1단계: 모델 학습 및 저장]")
    ensemble = EnsemblePredictor()
    ensemble.train_models(df, verbose=0)
    ensemble.save_models(prefix='production_ensemble')
    print("모델 저장 완료")

    # 새로운 인스턴스에서 로드
    print("\n[2단계: 저장된 모델 로드]")
    new_ensemble = EnsemblePredictor()
    new_ensemble.load_models(prefix='production_ensemble')
    print("모델 로드 완료")

    # 로드된 모델로 예측
    print("\n[3단계: 로드된 모델로 예측]")
    pred = new_ensemble.predict_direction(df)
    print(f"예측 방향: {pred['ensemble_prediction'].upper()}")
    print(f"신뢰도: {pred['confidence_score']:.2%}")


def example_6_confidence_analysis():
    """예제 6: 신뢰도 분석"""
    print("\n" + "=" * 70)
    print(" 예제 6: 신뢰도 분석 및 모니터링")
    print("=" * 70)

    # 데이터 로드
    ticker = yf.Ticker("TSLA")
    df = ticker.history(period="1y")
    df.columns = [col.lower().replace(' ', '_') for col in df.columns]
    df = df.reset_index()

    analyzer = TechnicalAnalyzer(df)
    analyzer.add_all_indicators()
    df = analyzer.get_dataframe()

    # 앙상블 생성 및 학습
    ensemble = EnsemblePredictor()
    ensemble.train_models(df, verbose=0)

    # 여러 번 예측 수행
    print("\n[10회 연속 예측 수행]")
    for i in range(10):
        ensemble.predict_price(df)
        ensemble.predict_direction(df)

    # 신뢰도 메트릭 분석
    print("\n[신뢰도 통계]")
    metrics = ensemble.get_confidence_metrics()
    print(f"총 예측 횟수: {metrics['total_predictions']}")
    print(f"평균 신뢰도: {metrics['average_confidence']:.2%}")
    print(f"최소 신뢰도: {metrics['min_confidence']:.2%}")
    print(f"최대 신뢰도: {metrics['max_confidence']:.2%}")
    print(f"표준편차: {metrics['std_confidence']:.4f}")


def example_7_pre_trained_models():
    """예제 7: 기존 학습된 모델 재사용"""
    print("\n" + "=" * 70)
    print(" 예제 7: 기존 학습된 모델과 앙상블 결합")
    print("=" * 70)

    # 데이터 로드
    ticker = yf.Ticker("GOOGL")
    df = ticker.history(period="1y")
    df.columns = [col.lower().replace(' ', '_') for col in df.columns]
    df = df.reset_index()

    analyzer = TechnicalAnalyzer(df)
    analyzer.add_all_indicators()
    df = analyzer.get_dataframe()

    # 개별 모델 사전 학습
    print("\n[개별 모델 학습]")
    lstm = LSTMPredictor()
    lstm.train(df, verbose=0)

    xgb = XGBoostClassifier()
    xgb.train(df)

    # 학습된 모델로 앙상블 생성
    print("\n[사전 학습된 모델로 앙상블 구성]")
    ensemble = EnsemblePredictor(
        lstm_predictor=lstm,
        xgboost_classifier=xgb,
        strategy='weighted_average'
    )

    # 바로 예측 가능
    print("\n[예측 수행]")
    pred = ensemble.predict_price(df)
    print(f"예측 가격: ${pred['ensemble_prediction']:.2f}")
    print(f"신뢰도: {pred['confidence_score']:.2%}")


def main():
    """모든 예제 실행"""
    print("\n" + "=" * 70)
    print(" 앙상블 예측 모델 사용 예제 모음")
    print("=" * 70)

    examples = [
        ("가중 평균 전략", example_1_weighted_average),
        ("투표 전략", example_2_voting),
        ("커스텀 가중치", example_3_custom_weights),
        ("스태킹 전략", example_4_stacking),
        ("모델 저장/로드", example_5_model_persistence),
        ("신뢰도 분석", example_6_confidence_analysis),
        ("기존 모델 재사용", example_7_pre_trained_models),
    ]

    print("\n실행할 예제를 선택하세요:")
    for i, (name, _) in enumerate(examples, 1):
        print(f"  {i}. {name}")
    print("  0. 모두 실행")

    try:
        choice = input("\n선택 (0-7): ").strip()

        if choice == '0':
            for name, func in examples:
                try:
                    func()
                except Exception as e:
                    print(f"\n[오류] {name} 실행 실패: {e}")
        elif choice.isdigit() and 1 <= int(choice) <= len(examples):
            examples[int(choice) - 1][1]()
        else:
            print("잘못된 선택입니다.")

    except KeyboardInterrupt:
        print("\n\n사용자에 의해 중단되었습니다.")
    except Exception as e:
        print(f"\n오류 발생: {e}")


if __name__ == "__main__":
    # 개별 예제를 직접 호출할 수도 있습니다
    # example_1_weighted_average()
    # example_2_voting()
    # example_3_custom_weights()

    # 또는 대화형 메뉴 실행
    main()
