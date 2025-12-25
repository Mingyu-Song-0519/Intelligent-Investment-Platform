"""
AI 모델 앙상블 전략 - LSTM + XGBoost + Transformer 결합 예측
다중 모델의 예측을 결합하여 신뢰도 높은 예측 제공
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any
from pathlib import Path
import sys

# 프로젝트 루트 경로 설정
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config import ENSEMBLE_CONFIG
from src.models.predictor import LSTMPredictor, XGBoostClassifier, DataPreprocessor

# Transformer 모델
try:
    from src.models.transformer_predictor import TransformerPredictor
    TRANSFORMER_AVAILABLE = True
except ImportError:
    TRANSFORMER_AVAILABLE = False
    print("[WARNING] Transformer model not available.")

# 메타 모델용 (선택적)
try:
    from sklearn.linear_model import LinearRegression, LogisticRegression
    from sklearn.ensemble import RandomForestRegressor
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    print("[WARNING] scikit-learn not fully available. Meta models may be limited.")


class EnsemblePredictor:
    """
    LSTM과 XGBoost를 결합한 앙상블 예측기

    지원하는 앙상블 전략:
    1. Weighted Average (가중 평균) - 회귀 예측
    2. Voting (투표) - 분류 예측
    3. Stacking (스태킹) - 메타 모델 학습
    """

    def __init__(
        self,
        lstm_predictor: Optional[LSTMPredictor] = None,
        xgboost_classifier: Optional[XGBoostClassifier] = None,
        weights: Optional[Dict[str, float]] = None,
        strategy: str = 'weighted_average'
    ):
        """
        Args:
            lstm_predictor: LSTM 예측 모델 (옵션)
            xgboost_classifier: XGBoost 분류 모델 (옵션)
            weights: 각 모델의 가중치 {'lstm': 0.4, 'xgboost': 0.3, 'transformer': 0.3}
            strategy: 앙상블 전략 ('weighted_average', 'voting', 'stacking')
        """
        self.lstm_predictor = lstm_predictor
        self.xgboost_classifier = xgboost_classifier
        self.transformer_predictor = None  # Transformer 모델

        # 기본 가중치 설정 (Transformer 포함)
        config_weights = ENSEMBLE_CONFIG.get('weights', {})
        self.weights = weights or config_weights
        if 'transformer' not in self.weights:
            self.weights['transformer'] = 0.3  # 기본 Transformer 가중치

        # 전략 검증
        valid_strategies = ['weighted_average', 'voting', 'stacking']
        if strategy not in valid_strategies:
            raise ValueError(f"전략은 {valid_strategies} 중 하나여야 합니다.")
        self.strategy = strategy

        # 메타 모델 (스태킹용)
        self.meta_model_regression = None
        self.meta_model_classification = None

        # 예측 히스토리 (신뢰도 계산용)
        self.prediction_history = []

    def train_models(
        self,
        df: pd.DataFrame,
        train_lstm: bool = True,
        train_xgboost: bool = True,
        train_transformer: bool = False,
        feature_cols: Optional[List[str]] = None,
        verbose: int = 1,
        incremental: bool = False,
        replay_buffer: Optional[pd.DataFrame] = None
    ) -> Dict[str, Any]:
        """
        앙상블 모델들을 학습 (점진적 학습 지원)

        Args:
            df: 학습 데이터프레임
            train_lstm: LSTM 모델 학습 여부
            train_xgboost: XGBoost 모델 학습 여부
            train_transformer: Transformer 모델 학습 여부
            feature_cols: 특성 컬럼들
            verbose: 출력 레벨
            incremental: 점진적 학습 모드
            replay_buffer: 점진적 학습 시 과거 데이터 샘플

        Returns:
            학습 결과 딕셔너리
        """
        results = {}
        
        if incremental:
            print("[INFO] === Incremental Learning Mode ===")

        # LSTM 학습
        if train_lstm:
            if self.lstm_predictor is None:
                self.lstm_predictor = LSTMPredictor()

            print("[INFO] LSTM 모델 학습 중...")
            lstm_result = self.lstm_predictor.train(
                df=df,
                feature_cols=feature_cols,
                verbose=verbose,
                incremental=incremental,
                replay_buffer=replay_buffer
            )
            results['lstm'] = lstm_result
            
            if incremental and lstm_result.get('incremental'):
                print(f"[SUCCESS] LSTM Fine-tuning 완료 - RMSE: {lstm_result['rmse']:.2f} "
                      f"(Replay: {lstm_result.get('replay_samples', 0)}, New: {lstm_result.get('new_samples', 0)})")
            else:
                print(f"[SUCCESS] LSTM 학습 완료 - RMSE: {lstm_result['rmse']:.2f}")

        # XGBoost 학습
        if train_xgboost:
            if self.xgboost_classifier is None:
                self.xgboost_classifier = XGBoostClassifier()

            print("[INFO] XGBoost 모델 학습 중...")
            xgb_result = self.xgboost_classifier.train(
                df=df,
                feature_cols=feature_cols,
                incremental=incremental,
                replay_buffer=replay_buffer
            )
            results['xgboost'] = xgb_result
            
            if incremental and xgb_result.get('incremental'):
                print(f"[SUCCESS] XGBoost Incremental 완료 - Accuracy: {xgb_result['accuracy']:.2%} "
                      f"(Estimators: {xgb_result.get('total_estimators', 'N/A')})")
            else:
                print(f"[SUCCESS] XGBoost 학습 완료 - Accuracy: {xgb_result['accuracy']:.2%}")

        # Transformer 학습
        if train_transformer and TRANSFORMER_AVAILABLE:
            if self.transformer_predictor is None:
                self.transformer_predictor = TransformerPredictor()

            print("[INFO] Transformer 모델 학습 중...")
            transformer_result = self.transformer_predictor.train(
                df=df,
                epochs=50 if not incremental else 5,  # Incremental 시 적은 epochs
                verbose=verbose
            )
            results['transformer'] = transformer_result
            print(f"[SUCCESS] Transformer 학습 완료 - Val Loss: {transformer_result['val_loss']:.4f}")

        # 스태킹 전략인 경우 메타 모델 학습 (점진적 학습 시 스킵)
        if self.strategy == 'stacking' and train_lstm and train_xgboost and not incremental:
            print("[INFO] 메타 모델 학습 중...")
            self._train_meta_models(df, feature_cols)
            print("[SUCCESS] 메타 모델 학습 완료")

        return results

    def _train_meta_models(
        self,
        df: pd.DataFrame,
        feature_cols: Optional[List[str]] = None
    ):
        """메타 모델 학습 (스태킹)"""
        if not SKLEARN_AVAILABLE:
            print("[WARNING] scikit-learn이 없어 메타 모델을 학습할 수 없습니다.")
            return

        # 기본 모델들의 예측을 입력으로 사용
        # LSTM 예측 (회귀)
        lstm_predictions = []
        xgb_predictions = []
        actual_prices = []
        actual_directions = []

        # 데이터를 윈도우로 순회하며 예측 수집
        window_size = ENSEMBLE_CONFIG.get('meta_window_size', 100)

        for i in range(len(df) - window_size - 10):
            window_df = df.iloc[i:i+window_size]

            try:
                # LSTM 예측
                lstm_pred = self.lstm_predictor.predict(window_df, feature_cols)
                lstm_predictions.append(lstm_pred[0])

                # XGBoost 예측
                xgb_pred, xgb_prob = self.xgboost_classifier.predict(window_df)
                xgb_predictions.append(xgb_prob)

                # 실제 값
                actual_price = df.iloc[i+window_size]['close']
                actual_prices.append(actual_price)

                # 실제 방향 (다음 날 상승 여부)
                next_price = df.iloc[i+window_size+1]['close']
                actual_directions.append(1 if next_price > actual_price else 0)

            except Exception as e:
                continue

        if len(lstm_predictions) < 10:
            print("[WARNING] 메타 모델 학습 데이터가 부족합니다.")
            return

        # 메타 모델 입력 생성
        X_meta = np.column_stack([lstm_predictions, xgb_predictions])

        # 회귀 메타 모델 (가격 예측)
        self.meta_model_regression = LinearRegression()
        self.meta_model_regression.fit(X_meta, actual_prices)

        # 분류 메타 모델 (등락 예측)
        self.meta_model_classification = LogisticRegression()
        self.meta_model_classification.fit(X_meta, actual_directions)

        print(f"[INFO] 메타 모델 학습 샘플 수: {len(lstm_predictions)}")

    def predict_price(
        self,
        df: pd.DataFrame,
        feature_cols: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        주가 예측 (회귀)

        Args:
            df: 예측용 데이터프레임
            feature_cols: 특성 컬럼들

        Returns:
            예측 결과 딕셔너리
        """
        predictions = {}

        # LSTM 예측
        if self.lstm_predictor and self.lstm_predictor.model:
            lstm_pred = self.lstm_predictor.predict(df, feature_cols)
            predictions['lstm'] = float(lstm_pred[0])

        # XGBoost는 분류 모델이지만, 확률을 이용해 방향성 제공
        if self.xgboost_classifier and self.xgboost_classifier.model:
            xgb_class, xgb_prob = self.xgboost_classifier.predict(df)
            predictions['xgboost_direction'] = 'up' if xgb_class == 1 else 'down'
            predictions['xgboost_confidence'] = float(xgb_prob)

        # Transformer 예측
        if self.transformer_predictor and self.transformer_predictor.is_trained:
            try:
                transformer_pred = self.transformer_predictor.predict(df)
                predictions['transformer'] = float(transformer_pred)
            except Exception as e:
                print(f"[WARNING] Transformer 예측 실패: {e}")

        # 앙상블 전략에 따른 최종 예측
        ensemble_pred = None
        confidence = 0.0

        if self.strategy == 'weighted_average':
            ensemble_pred, confidence = self._weighted_average_predict(predictions, df)

        elif self.strategy == 'stacking':
            ensemble_pred, confidence = self._stacking_predict(predictions, df)

        # 결과 구성
        result = {
            'individual_predictions': predictions,
            'ensemble_prediction': ensemble_pred,
            'confidence_score': confidence,
            'strategy': self.strategy,
            'current_price': float(df['close'].iloc[-1])
        }

        # 예측 히스토리에 추가
        self.prediction_history.append(result)

        return result

    def predict_direction(
        self,
        df: pd.DataFrame,
        feature_cols: Optional[List[str]] = None,
        include_rule_based: bool = True
    ) -> Dict[str, Any]:
        """
        등락 예측 (분류)

        Args:
            df: 예측용 데이터프레임
            feature_cols: 특성 컬럼들
            include_rule_based: 규칙 기반 시그널 포함 여부

        Returns:
            예측 결과 딕셔너리
        """
        predictions = {}
        votes = []

        # LSTM 기반 방향 예측 (가격 변화율로 변환)
        if self.lstm_predictor and self.lstm_predictor.model:
            lstm_pred = self.lstm_predictor.predict(df, feature_cols)
            current_price = df['close'].iloc[-1]
            lstm_direction = 1 if lstm_pred[0] > current_price else 0
            predictions['lstm'] = lstm_direction
            votes.append(lstm_direction)

        # XGBoost 예측
        if self.xgboost_classifier and self.xgboost_classifier.model:
            xgb_class, xgb_prob = self.xgboost_classifier.predict(df)
            predictions['xgboost'] = int(xgb_class)
            predictions['xgboost_probability'] = float(xgb_prob)
            votes.append(int(xgb_class))

        # 규칙 기반 시그널 (기술적 지표)
        if include_rule_based:
            rule_signal = self._get_rule_based_signal(df)
            predictions['rule_based'] = rule_signal
            votes.append(rule_signal)

        # 앙상블 전략에 따른 최종 예측
        if self.strategy == 'voting':
            # 다수결 투표
            final_prediction = 1 if sum(votes) > len(votes) / 2 else 0
            confidence = sum(votes) / len(votes) if final_prediction == 1 else 1 - sum(votes) / len(votes)

        elif self.strategy == 'stacking' and self.meta_model_classification:
            # 메타 모델 예측
            X_meta = self._prepare_meta_input(predictions)
            final_prediction = int(self.meta_model_classification.predict([X_meta])[0])
            proba = self.meta_model_classification.predict_proba([X_meta])[0]
            confidence = float(proba[final_prediction])

        else:
            # 기본: 가중 투표
            weighted_sum = 0
            total_weight = 0

            if 'lstm' in predictions:
                weighted_sum += predictions['lstm'] * self.weights.get('lstm', 0.4)
                total_weight += self.weights.get('lstm', 0.4)

            if 'xgboost' in predictions:
                weighted_sum += predictions['xgboost'] * self.weights.get('xgboost', 0.4)
                total_weight += self.weights.get('xgboost', 0.4)

            if 'rule_based' in predictions:
                weighted_sum += predictions['rule_based'] * self.weights.get('rule_based', 0.2)
                total_weight += self.weights.get('rule_based', 0.2)

            final_prediction = 1 if (weighted_sum / total_weight) > 0.5 else 0
            confidence = weighted_sum / total_weight if final_prediction == 1 else 1 - weighted_sum / total_weight

        result = {
            'individual_predictions': predictions,
            'ensemble_prediction': 'up' if final_prediction == 1 else 'down',
            'confidence_score': float(confidence),
            'strategy': self.strategy,
            'votes': votes,
            'current_price': float(df['close'].iloc[-1])
        }

        return result

    def _weighted_average_predict(
        self,
        predictions: Dict[str, Any],
        df: pd.DataFrame
    ) -> Tuple[float, float]:
        """가중 평균 예측 (LSTM + Transformer)"""
        price_predictions = []
        weights = []
        
        # LSTM 예측
        if 'lstm' in predictions:
            price_predictions.append(predictions['lstm'])
            weights.append(self.weights.get('lstm', 0.4))
        
        # Transformer 예측
        if 'transformer' in predictions:
            price_predictions.append(predictions['transformer'])
            weights.append(self.weights.get('transformer', 0.3))
        
        if not price_predictions:
            return None, 0.0
        
        # 가중 평균 계산
        total_weight = sum(weights)
        ensemble_pred = sum(p * w for p, w in zip(price_predictions, weights)) / total_weight
        
        # 신뢰도 계산
        confidence = total_weight
        
        # XGBoost 방향성을 신뢰도에 반영
        if 'xgboost_confidence' in predictions:
            xgb_conf = predictions['xgboost_confidence']
            confidence = (confidence + xgb_conf * self.weights.get('xgboost', 0.3)) / 2

        return ensemble_pred, min(confidence, 1.0)

    def _stacking_predict(
        self,
        predictions: Dict[str, Any],
        df: pd.DataFrame
    ) -> Tuple[float, float]:
        """스태킹 예측 (메타 모델)"""
        if not self.meta_model_regression or 'lstm' not in predictions:
            # 메타 모델이 없으면 가중 평균으로 폴백
            return self._weighted_average_predict(predictions, df)

        # 메타 모델 입력 준비
        X_meta = [
            predictions['lstm'],
            predictions.get('xgboost_confidence', 0.5)
        ]

        # 메타 모델 예측
        ensemble_pred = float(self.meta_model_regression.predict([X_meta])[0])

        # 신뢰도: 개별 모델들의 일치도로 계산
        current_price = df['close'].iloc[-1]
        lstm_direction = 1 if predictions['lstm'] > current_price else 0
        xgb_direction = 1 if predictions.get('xgboost_direction') == 'up' else 0

        agreement = 1.0 if lstm_direction == xgb_direction else 0.5
        confidence = agreement * predictions.get('xgboost_confidence', 0.7)

        return ensemble_pred, confidence

    def _get_rule_based_signal(self, df: pd.DataFrame) -> int:
        """
        규칙 기반 트레이딩 시그널 생성

        기술적 지표를 이용한 간단한 규칙:
        - RSI < 30: 과매도 (매수 신호)
        - RSI > 70: 과매수 (매도 신호)
        - MACD 크로스오버: 매수/매도 신호
        - 볼린저 밴드: 상단/하단 돌파

        Returns:
            1: 상승 예상 (매수), 0: 하락 예상 (매도)
        """
        signals = []

        # RSI 시그널
        if 'rsi' in df.columns:
            rsi = df['rsi'].iloc[-1]
            if rsi < 30:
                signals.append(1)  # 과매도 -> 매수
            elif rsi > 70:
                signals.append(0)  # 과매수 -> 매도
            else:
                signals.append(1 if rsi < 50 else 0)

        # MACD 시그널
        if 'macd' in df.columns and 'macd_signal' in df.columns:
            macd = df['macd'].iloc[-1]
            macd_signal = df['macd_signal'].iloc[-1]
            signals.append(1 if macd > macd_signal else 0)

        # 볼린저 밴드 시그널
        if 'bb_percent' in df.columns:
            bb_percent = df['bb_percent'].iloc[-1]
            if bb_percent < 0.2:
                signals.append(1)  # 하단 근처 -> 매수
            elif bb_percent > 0.8:
                signals.append(0)  # 상단 근처 -> 매도
            else:
                signals.append(1 if bb_percent < 0.5 else 0)

        # 이동평균 크로스 시그널
        if 'sma_20' in df.columns and 'sma_60' in df.columns:
            sma_20 = df['sma_20'].iloc[-1]
            sma_60 = df['sma_60'].iloc[-1]
            signals.append(1 if sma_20 > sma_60 else 0)

        # 다수결
        if len(signals) == 0:
            return 1  # 기본값

        return 1 if sum(signals) > len(signals) / 2 else 0

    def _prepare_meta_input(self, predictions: Dict[str, Any]) -> List[float]:
        """메타 모델 입력 준비"""
        return [
            float(predictions.get('lstm', 0.5)),
            float(predictions.get('xgboost_probability', 0.5))
        ]

    def get_confidence_metrics(self) -> Dict[str, Any]:
        """
        신뢰도 메트릭 계산

        Returns:
            신뢰도 관련 통계
        """
        if len(self.prediction_history) == 0:
            return {'message': '예측 히스토리가 없습니다.'}

        confidences = [p['confidence_score'] for p in self.prediction_history]

        return {
            'average_confidence': np.mean(confidences),
            'min_confidence': np.min(confidences),
            'max_confidence': np.max(confidences),
            'std_confidence': np.std(confidences),
            'total_predictions': len(self.prediction_history),
            'recent_confidence': confidences[-5:] if len(confidences) >= 5 else confidences
        }

    def save_models(self, prefix: str = 'ensemble', metadata: Optional[Dict[str, Any]] = None):
        """앙상블 모델들 저장 (메타데이터 포함)"""
        if self.lstm_predictor and self.lstm_predictor.model:
            self.lstm_predictor.save(f"{prefix}_lstm", metadata=metadata)

        if self.xgboost_classifier and self.xgboost_classifier.model:
            self.xgboost_classifier.save(f"{prefix}_xgboost", metadata=metadata)

        if self.transformer_predictor and self.transformer_predictor.model:
            self.transformer_predictor.save_model(f"{prefix}_transformer.keras")

        print(f"[INFO] 앙상블 모델 저장 완료: {prefix}")

    def load_models(self, prefix: str = 'ensemble'):
        """앙상블 모델들 로드"""
        try:
            if self.lstm_predictor is None:
                self.lstm_predictor = LSTMPredictor()
            self.lstm_predictor.load(f"{prefix}_lstm")
        except Exception as e:
            print(f"[WARNING] LSTM 모델 로드 실패: {e}")

        try:
            if self.xgboost_classifier is None:
                self.xgboost_classifier = XGBoostClassifier()
            self.xgboost_classifier.load(f"{prefix}_xgboost")
        except Exception as e:
            print(f"[WARNING] XGBoost 모델 로드 실패: {e}")

        try:
            if TRANSFORMER_AVAILABLE:
                if self.transformer_predictor is None:
                    self.transformer_predictor = TransformerPredictor()
                self.transformer_predictor.load_model(f"{prefix}_transformer.keras")
        except Exception as e:
            print(f"[WARNING] Transformer 모델 로드 실패: {e}")

        print(f"[INFO] 앙상블 모델 로드 완료: {prefix}")

    def set_weights(self, weights: Dict[str, float]):
        """
        모델 가중치 동적 설정

        Args:
            weights: {'lstm': 0.6, 'xgboost': 0.3, 'rule_based': 0.1}
        """
        total = sum(weights.values())
        if abs(total - 1.0) > 0.01:
            print(f"[WARNING] 가중치 합이 1이 아닙니다: {total}. 정규화합니다.")
            weights = {k: v/total for k, v in weights.items()}

        self.weights = weights
        print(f"[INFO] 가중치 업데이트: {weights}")


# 사용 예시
if __name__ == "__main__":
    print("=== AI 모델 앙상블 테스트 ===\n")

    # 샘플 데이터 로드
    import yfinance as yf
    from src.analyzers.technical_analyzer import TechnicalAnalyzer

    ticker = yf.Ticker("005930.KS")  # 삼성전자
    df = ticker.history(period="2y")
    df.columns = [col.lower().replace(' ', '_') for col in df.columns]
    df = df.reset_index()

    # 기술적 지표 추가
    analyzer = TechnicalAnalyzer(df)
    analyzer.add_all_indicators()
    df = analyzer.get_dataframe()

    print(f"데이터 크기: {len(df)} rows\n")

    # 앙상블 예측기 생성
    ensemble = EnsemblePredictor(strategy='weighted_average')

    # 모델 학습
    print("=" * 50)
    results = ensemble.train_models(df, verbose=0)
    print("=" * 50)

    # 가격 예측 테스트
    print("\n--- 가격 예측 (회귀) ---")
    price_pred = ensemble.predict_price(df)
    print(f"현재 가격: {price_pred['current_price']:,.0f}원")
    print(f"예측 가격: {price_pred['ensemble_prediction']:,.0f}원")
    print(f"신뢰도: {price_pred['confidence_score']:.2%}")
    print(f"개별 예측: {price_pred['individual_predictions']}")

    # 등락 예측 테스트
    print("\n--- 등락 예측 (분류) ---")
    direction_pred = ensemble.predict_direction(df)
    print(f"예측 방향: {direction_pred['ensemble_prediction'].upper()}")
    print(f"신뢰도: {direction_pred['confidence_score']:.2%}")
    print(f"개별 예측: {direction_pred['individual_predictions']}")
    print(f"투표 결과: {direction_pred['votes']}")

    # 신뢰도 메트릭
    print("\n--- 신뢰도 메트릭 ---")
    metrics = ensemble.get_confidence_metrics()
    print(f"평균 신뢰도: {metrics.get('average_confidence', 0):.2%}")
    print(f"총 예측 횟수: {metrics.get('total_predictions', 0)}")
