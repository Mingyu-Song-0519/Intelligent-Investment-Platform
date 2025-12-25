"""
Regime-Aware Predictor - Phase 14
시장 레짐별 적응형 AI 예측

기존 EnsemblePredictor를 래핑하여 시장 상황에 따라 모델 가중치를 동적으로 조절
"""
from typing import Dict, Optional, List
import pandas as pd
import numpy as np
from datetime import datetime

from src.analyzers.regime_classifier import RegimeClassifier, RegimeAwareModelSelector, MarketRegime


class RegimeAwarePredictor:
    """
    레짐 인식 AI 예측기
    
    시장 상황을 자동 감지하고, 해당 상황에 최적화된 모델 가중치로 예측
    
    사용 예:
        predictor = RegimeAwarePredictor()
        prediction = predictor.predict(stock_data)
    """
    
    def __init__(self, ensemble_predictor=None):
        """
        Args:
            ensemble_predictor: EnsemblePredictor 인스턴스 (옵션)
        """
        self.regime_classifier = RegimeClassifier()
        self.model_selector = RegimeAwareModelSelector(self.regime_classifier)
        self.ensemble_predictor = ensemble_predictor
        
        # 예측 히스토리
        self.prediction_history = []
    
    def predict(
        self,
        df: pd.DataFrame,
        feature_cols: Optional[List[str]] = None,
        use_regime_weights: bool = True
    ) -> Dict:
        """
        레짐 인식 예측
        
        Args:
            df: OHLCV DataFrame
            feature_cols: 특성 컬럼 (없으면 자동 생성)
            use_regime_weights: 레짐별 가중치 사용 여부
        
        Returns:
            {
                "prediction": 예측값,
                "regime": MarketRegime,
                "model_weights": 사용된 모델 가중치,
                "confidence": 신뢰도,
                "recommendation": 투자 권고
            }
        """
        # 1. 현재 시장 레짐 분류
        regime = self.regime_classifier.get_regime_from_data(df)
        
        # 2. 레짐별 모델 가중치 결정
        if use_regime_weights:
            model_weights = self.model_selector.get_model_weights(regime)
        else:
            model_weights = {"lstm": 0.4, "xgboost": 0.4, "transformer": 0.2}
        
        # 3. AI 예측 (EnsemblePredictor가 있으면 사용)
        if self.ensemble_predictor:
            # 기존 앙상블 모델로 예측
            raw_prediction = self._predict_with_ensemble(
                df, 
                feature_cols, 
                model_weights
            )
        else:
            # 간단한 추세 기반 예측 (폴백)
            raw_prediction = self._simple_trend_prediction(df)
        
        # 4. 레짐 신뢰도 반영
        final_confidence = raw_prediction.get("confidence", 0.5) * regime.confidence
        
        # 5. 투자 권고
        recommendation = self.model_selector.get_recommendation(regime)
        
        result = {
            "prediction": raw_prediction.get("prediction"),
            "regime": regime,
            "model_weights": model_weights,
            "confidence": round(final_confidence, 3),
            "recommendation": recommendation,
            "timestamp": datetime.now().isoformat()
        }
        
        # 히스토리 저장
        self.prediction_history.append(result)
        
        return result
    
    def _predict_with_ensemble(
        self,
        df: pd.DataFrame,
        feature_cols: Optional[List[str]],
        model_weights: Dict[str, float]
    ) -> Dict:
        """EnsemblePredictor로 예측"""
        
        try:
            # 앙상블 예측 수행 (가격 예측)
            price_result = self.ensemble_predictor.predict_price(
                df=df,
                feature_cols=feature_cols
            )
            
            # 방향 예측도 수행
            direction_result = self.ensemble_predictor.predict_direction(
                df=df,
                feature_cols=feature_cols
            )
            
            # 가격 예측 결과 사용
            predicted_price = price_result.get('ensemble_prediction')
            confidence = direction_result.get('confidence_score', 0.7)
            
            return {
                "prediction": predicted_price,
                "confidence": confidence,
                "individual_predictions": price_result.get('individual_predictions', {})
            }
            
        except Exception as e:
            print(f"[ERROR] Ensemble 예측 실패: {e}")
            import traceback
            traceback.print_exc()
            # 폴백
            return self._simple_trend_prediction(df)
    
    def _simple_trend_prediction(self, df: pd.DataFrame) -> Dict:
        """간단한 추세 기반 예측 (폴백)"""
        
        if len(df) < 5:
            return {"prediction": None, "confidence": 0.0}
        
        # 최근 5일 추세
        close_col = 'Close' if 'Close' in df.columns else 'close'
        recent_prices = df[close_col].tail(5).values
        
        # 선형 회귀 기울기
        x = np.arange(len(recent_prices))
        slope = np.polyfit(x, recent_prices, 1)[0]
        
        # 다음 날 예측
        next_pred = recent_prices[-1] + slope
        
        # 신뢰도 (R^2 기반)
        fitted = np.poly1d(np.polyfit(x, recent_prices, 1))(x)
        ss_res = np.sum((recent_prices - fitted) ** 2)
        ss_tot = np.sum((recent_prices - np.mean(recent_prices)) ** 2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0
        
        return {
            "prediction": next_pred,
            "confidence": max(0, min(1, r_squared)),
            "method": "linear_trend"
        }
    
    def get_training_strategy(self, regime: MarketRegime) -> Dict:
        """
        레짐별 모델 학습 전략 제안
        
        Args:
            regime: 현재 시장 레짐
        
        Returns:
            학습 전략 딕셔너리
        """
        strategies = {
            "LOW_VOL_BULL": {
                "training_window": 252,  # 1년
                "batch_size": 32,
                "learning_rate": 0.001,
                "focus": "장기 추세 학습"
            },
            "HIGH_VOL_BEAR": {
                "training_window": 63,   # 3개월 (최근 중시)
                "batch_size": 16,
                "learning_rate": 0.002,
                "focus": "빠른 반응성, 손절 중요"
            },
            "SIDEWAYS": {
                "training_window": 126,  # 6개월
                "batch_size": 24,
                "learning_rate": 0.0015,
                "focus": "범위 매매 패턴 학습"
            },
            "TRANSITION": {
                "training_window": 189,  # 9개월
                "batch_size": 28,
                "learning_rate": 0.0012,
                "focus": "다양한 시나리오 대비"
            }
        }
        
        return strategies.get(
            regime.regime_type,
            strategies["TRANSITION"]
        )
    
    def get_regime_summary(self) -> str:
        """현재 레짐 요약"""
        
        if not self.prediction_history:
            return "예측 히스토리 없음"
        
        latest = self.prediction_history[-1]
        regime = latest["regime"]
        
        summary = f"""
📊 시장 레짐 분석
━━━━━━━━━━━━━━━━━━━━
레짐: {regime.description}
신뢰도: {regime.confidence:.1%}
VIX: {regime.vix_level:.2f}
추세: {regime.trend}

🤖 AI 모델 설정
━━━━━━━━━━━━━━━━━━━━
LSTM: {latest['model_weights']['lstm']:.0%}
XGBoost: {latest['model_weights']['xgboost']:.0%}
Transformer: {latest['model_weights']['transformer']:.0%}

💡 투자 권고
━━━━━━━━━━━━━━━━━━━━
{latest['recommendation']}
        """.strip()
        
        return summary
