# 앙상블 모델 Quick Reference Card

## 빠른 시작 (30초)

```python
from src.models import EnsemblePredictor
import yfinance as yf
from src.analyzers.technical_analyzer import TechnicalAnalyzer

# 1. 데이터 로드
df = yf.Ticker("005930.KS").history(period="2y")
df.columns = [col.lower().replace(' ', '_') for col in df.columns]
df = df.reset_index()

# 2. 기술적 지표 추가
analyzer = TechnicalAnalyzer(df)
analyzer.add_all_indicators()
df = analyzer.get_dataframe()

# 3. 앙상블 생성 및 학습
ensemble = EnsemblePredictor()
ensemble.train_models(df, verbose=0)

# 4. 예측
price = ensemble.predict_price(df)
direction = ensemble.predict_direction(df)

print(f"예측 가격: {price['ensemble_prediction']:,.0f}원 (신뢰도: {price['confidence_score']:.2%})")
print(f"예측 방향: {direction['ensemble_prediction'].upper()} (신뢰도: {direction['confidence_score']:.2%})")
```

---

## 전략 선택

```python
# 가중 평균 (기본)
ensemble = EnsemblePredictor(strategy='weighted_average')

# 투표 (등락 예측)
ensemble = EnsemblePredictor(strategy='voting')

# 스태킹 (고정확도)
ensemble = EnsemblePredictor(strategy='stacking')
```

---

## 가중치 조정

```python
# 보수적
ensemble.set_weights({'lstm': 0.7, 'xgboost': 0.2, 'rule_based': 0.1})

# 균형잡힌
ensemble.set_weights({'lstm': 0.5, 'xgboost': 0.3, 'rule_based': 0.2})

# 공격적
ensemble.set_weights({'lstm': 0.3, 'xgboost': 0.5, 'rule_based': 0.2})
```

---

## 예측 해석

### 신뢰도 레벨
- **75% 이상**: HIGH - 강한 확신
- **60-75%**: MEDIUM - 보통 확신
- **45-60%**: LOW - 약한 확신

### 예측 방향
- **up**: 상승 예상
- **down**: 하락 예상

---

## 모델 저장/로드

```python
# 저장
ensemble.save_models(prefix='my_model')

# 로드
new_ensemble = EnsemblePredictor()
new_ensemble.load_models(prefix='my_model')
```

---

## 성능 모니터링

```python
metrics = ensemble.get_confidence_metrics()
print(f"평균 신뢰도: {metrics['average_confidence']:.2%}")
print(f"총 예측 횟수: {metrics['total_predictions']}")
```

---

## 주요 파일

- **코드**: `D:\Stock\src\models\ensemble_predictor.py`
- **설정**: `D:\Stock\config.py` (ENSEMBLE_CONFIG)
- **테스트**: `D:\Stock\test_ensemble.py`
- **예제**: `D:\Stock\ensemble_usage_example.py`
- **가이드**: `D:\Stock\ENSEMBLE_README.md`

---

## 테스트 명령

```bash
# 빠른 검증
python quick_test_ensemble.py

# 종합 테스트
python test_ensemble.py

# 사용 예제
python ensemble_usage_example.py
```

---

## 문제 해결

### ImportError
```bash
pip install tensorflow xgboost scikit-learn
```

### 메모리 부족
```python
# 데이터 기간 축소
df = ticker.history(period="1y")  # 2y → 1y
```

### 학습 느림
```python
# 배치 크기 증가 (config.py)
MODEL_CONFIG['LSTM']['batch_size'] = 64  # 32 → 64
```

---

## API 요약

| 메서드 | 용도 | 반환값 |
|--------|------|--------|
| `train_models(df)` | 모델 학습 | dict |
| `predict_price(df)` | 가격 예측 | dict |
| `predict_direction(df)` | 등락 예측 | dict |
| `set_weights(weights)` | 가중치 설정 | None |
| `get_confidence_metrics()` | 신뢰도 통계 | dict |
| `save_models(prefix)` | 모델 저장 | None |
| `load_models(prefix)` | 모델 로드 | None |

---

## 예측 결과 구조

### predict_price() 반환값
```python
{
    'individual_predictions': {
        'lstm': 70000.0,
        'xgboost_direction': 'up',
        'xgboost_confidence': 0.85
    },
    'ensemble_prediction': 70000.0,
    'confidence_score': 0.75,
    'strategy': 'weighted_average',
    'current_price': 68000.0
}
```

### predict_direction() 반환값
```python
{
    'individual_predictions': {
        'lstm': 1,
        'xgboost': 1,
        'rule_based': 0,
        'xgboost_probability': 0.85
    },
    'ensemble_prediction': 'up',
    'confidence_score': 0.82,
    'strategy': 'voting',
    'votes': [1, 1, 0],
    'current_price': 68000.0
}
```

---

## 설정 파일 (config.py)

```python
ENSEMBLE_CONFIG = {
    "strategy": "weighted_average",
    "weights": {
        "lstm": 0.5,
        "xgboost": 0.3,
        "rule_based": 0.2,
    },
    "confidence_threshold": {
        "high": 0.75,
        "medium": 0.60,
        "low": 0.45,
    },
}
```

---

## 실전 팁

1. **충분한 데이터**: 최소 1년, 권장 2년 이상
2. **정기 재학습**: 매주 또는 매월 새 데이터로 재학습
3. **신뢰도 확인**: 낮은 신뢰도는 불확실성 의미
4. **백테스팅**: 실제 투자 전 과거 데이터로 검증
5. **리스크 관리**: 예측은 참고용, 최종 판단은 투자자 몫
