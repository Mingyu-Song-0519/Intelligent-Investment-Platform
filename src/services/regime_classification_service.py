"""
Market Regime Classifier - Phase 14
시장 상황(레짐) 분류 및 감지

레짐 종류:
1. 저변동성 강세장 (Low Vol Bull)
2. 고변동성 약세장 (High Vol Bear)
3. 횡보장 (Sideways)
"""
from typing import Dict, Tuple, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
import pandas as pd
import numpy as np


@dataclass
class MarketRegime:
    """시장 레짐 정보"""
    regime_type: str  # "LOW_VOL_BULL", "HIGH_VOL_BEAR", "SIDEWAYS", "TRANSITION"
    confidence: float  # 0.0 ~ 1.0
    vix_level: float
    trend: str  # "UP", "DOWN", "FLAT"
    description: str


class RegimeClassifier:
    """
    시장 레짐 분류기
    
    VIX + 시장 추세(S&P 500)를 조합하여 현재 시장 상황 판단
    """
    
    # VIX 임계값
    VIX_LOW = 15      # 저변동성
    VIX_MED = 25      # 중변동성
    VIX_HIGH = 35     # 고변동성
    
    # 추세 임계값 (20일 수익률)
    TREND_UP = 2.0    # 상승 추세 (%)
    TREND_DOWN = -2.0 # 하락 추세 (%)
    
    def __init__(self):
        """초기화"""
        self._cache = None
        self._cache_time = None
        self._cache_ttl = 300  # 5분
    
    def classify(self, vix: float, market_return_20d: float) -> MarketRegime:
        """
        시장 레짐 분류
        
        Args:
            vix: 현재 VIX 값
            market_return_20d: 20일 시장 수익률 (%)
        
        Returns:
            MarketRegime
        """
        # VIX 수준 판단
        if vix < self.VIX_LOW:
            vol_regime = "LOW"
        elif vix < self.VIX_MED:
            vol_regime = "MED"
        elif vix < self.VIX_HIGH:
            vol_regime = "HIGH"
        else:
            vol_regime = "EXTREME"
        
        # 추세 판단
        if market_return_20d > self.TREND_UP:
            trend = "UP"
        elif market_return_20d < self.TREND_DOWN:
            trend = "DOWN"
        else:
            trend = "FLAT"
        
        # 레짐 조합
        regime_type, confidence, description = self._determine_regime(
            vol_regime, trend, vix, market_return_20d
        )
        
        return MarketRegime(
            regime_type=regime_type,
            confidence=confidence,
            vix_level=vix,
            trend=trend,
            description=description
        )
    
    def _determine_regime(
        self, 
        vol_regime: str, 
        trend: str,
        vix: float,
        market_return: float
    ) -> Tuple[str, float, str]:
        """레짐 결정 로직"""
        
        # 저변동성 강세장
        if vol_regime == "LOW" and trend == "UP":
            return ("LOW_VOL_BULL", 0.9, 
                    f"🟢 저변동성 강세장 (VIX {vix:.1f}, 수익률 +{market_return:.1f}%)")
        
        # 저변동성 횡보
        elif vol_regime == "LOW" and trend == "FLAT":
            return ("SIDEWAYS", 0.8,
                    f"🟡 저변동성 횡보장 (VIX {vix:.1f})")
        
        # 고변동성 약세장
        elif vol_regime in ["HIGH", "EXTREME"] and trend == "DOWN":
            return ("HIGH_VOL_BEAR", 0.9,
                    f"🔴 고변동성 약세장 (VIX {vix:.1f}, 수익률 {market_return:.1f}%)")
        
        # 고변동성 강세장 (변동성 돌파)
        elif vol_regime in ["HIGH", "EXTREME"] and trend == "UP":
            return ("HIGH_VOL_BULL", 0.7,
                    f"🟠 고변동성 강세장 (VIX {vix:.1f}, 주의 필요)")
        
        # 중변동성 횡보
        elif vol_regime == "MED" and trend == "FLAT":
            return ("SIDEWAYS", 0.85,
                    f"🟡 중변동성 횡보장 (VIX {vix:.1f})")
        
        # 전환 구간
        else:
            return ("TRANSITION", 0.6,
                    f"⚪ 전환 구간 (VIX {vix:.1f}, 불확실)")
    
    def get_regime_from_data(self, df: pd.DataFrame) -> MarketRegime:
        """
        DataFrame에서 레짐 판단
        
        Args:
            df: OHLCV DataFrame (최소 20일 데이터 필요)
        
        Returns:
            MarketRegime
        """
        if len(df) < 20:
            return MarketRegime(
                regime_type="UNKNOWN",
                confidence=0.0,
                vix_level=0.0,
                trend="UNKNOWN",
                description="데이터 부족 (최소 20일 필요)"
            )
        
        # VIX 조회
        from src.analyzers.volatility_analyzer import VolatilityAnalyzer
        vix_analyzer = VolatilityAnalyzer()
        vix = vix_analyzer.get_current_vix()
        
        if not vix:
            return MarketRegime(
                regime_type="UNKNOWN",
                confidence=0.0,
                vix_level=0.0,
                trend="UNKNOWN",
                description="VIX 데이터 없음"
            )
        
        # 20일 수익률 계산
        close_prices = df['Close'].values if 'Close' in df.columns else df['close'].values
        ret_20d = (close_prices[-1] - close_prices[-20]) / close_prices[-20] * 100
        
        return self.classify(vix, ret_20d)


class RegimeAwareModelSelector:
    """
    레짐별 모델 선택 및 가중치 조절
    
    각 시장 상황에 맞는 최적의 AI 모델 조합 제공
    """
    
    # 레짐별 모델 가중치 (LSTM, XGBoost, Transformer)
    REGIME_WEIGHTS = {
        "LOW_VOL_BULL": {
            "lstm": 0.4,
            "xgboost": 0.4,
            "transformer": 0.2,
            "description": "안정적 추세 환경 - 균형잡힌 앙상블"
        },
        "HIGH_VOL_BEAR": {
            "lstm": 0.2,
            "xgboost": 0.6,
            "transformer": 0.2,
            "description": "변동성 높은 환경 - XGBoost 중심 (빠른 반응)"
        },
        "SIDEWAYS": {
            "lstm": 0.5,
            "xgboost": 0.3,
            "transformer": 0.2,
            "description": "횡보 환경 - LSTM 중심 (패턴 인식)"
        },
        "HIGH_VOL_BULL": {
            "lstm": 0.3,
            "xgboost": 0.5,
            "transformer": 0.2,
            "description": "변동성 돌파 - XGBoost 우선"
        },
        "TRANSITION": {
            "lstm": 0.35,
            "xgboost": 0.35,
            "transformer": 0.3,
            "description": "전환 구간 - 균등 분산"
        },
        "UNKNOWN": {
            "lstm": 0.4,
            "xgboost": 0.4,
            "transformer": 0.2,
            "description": "기본 설정"
        }
    }
    
    def __init__(self, regime_classifier: RegimeClassifier):
        """
        Args:
            regime_classifier: RegimeClassifier 인스턴스
        """
        self.classifier = regime_classifier
    
    def get_model_weights(self, regime: MarketRegime) -> Dict[str, float]:
        """
        현재 레짐에 맞는 모델 가중치 반환
        
        Args:
            regime: MarketRegime
        
        Returns:
            {"lstm": 0.4, "xgboost": 0.4, "transformer": 0.2}
        """
        weights_config = self.REGIME_WEIGHTS.get(
            regime.regime_type,
            self.REGIME_WEIGHTS["UNKNOWN"]
        )
        
        return {
            "lstm": weights_config["lstm"],
            "xgboost": weights_config["xgboost"],
            "transformer": weights_config["transformer"]
        }
    
    def get_recommendation(self, regime: MarketRegime) -> str:
        """레짐별 투자 권고"""
        
        recommendations = {
            "LOW_VOL_BULL": "✅ 적극 투자 권장 - 안정적 상승장",
            "HIGH_VOL_BEAR": "⛔ 방어적 포지션 - 변동성 높은 하락장",
            "SIDEWAYS": "⚠️ 선별 투자 - 횡보장, 팩터 분석 활용",
            "HIGH_VOL_BULL": "⚡ 신중한 접근 - 변동성 높은 상승, 리스크 관리 필수",
            "TRANSITION": "⏸️ 관망 추천 - 방향성 불명확",
            "UNKNOWN": "❓ 데이터 부족 - 추가 분석 필요"
        }
        
        return recommendations.get(regime.regime_type, "분석 필요")
