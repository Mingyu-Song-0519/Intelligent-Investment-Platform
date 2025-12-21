# AI 모델 앙상블 전략 가이드

## 개요

D:\Stock 프로젝트의 앙상블 예측 시스템은 LSTM 회귀 모델과 XGBoost 분류 모델을 결합하여 더욱 신뢰성 있는 주가 예측을 제공합니다.

## 주요 기능

### 1. 앙상블 전략

#### 가중 평균 (Weighted Average)
- LSTM과 XGBoost의 예측을 가중치에 따라 결합
- 회귀 예측(가격)에 적합
- 각 모델의 신뢰도를 가중치로 반영

```python
ensemble = EnsemblePredictor(strategy='weighted_average')
ensemble.set_weights({'lstm': 0.6, 'xgboost': 0.3, 'rule_based': 0.1})
```

#### 투표 (Voting)
- 여러 모델의 예측을 다수결로 결정
- 분류 예측(등락)에 적합
- 규칙 기반 시그널 포함 가능

```python
ensemble = EnsemblePredictor(strategy='voting')
pred = ensemble.predict_direction(df, include_rule_based=True)
```

#### 스태킹 (Stacking)
- 기본 모델의 예측을 메타 모델의 입력으로 사용
- 더 높은 정확도 기대
- 학습 데이터가 충분할 때 효과적

```python
ensemble = EnsemblePredictor(strategy='stacking')
ensemble.train_models(df)  # 메타 모델 자동 학습
```

### 2. 신뢰도 점수

모든 예측에는 신뢰도 점수가 포함됩니다:

- **높음 (HIGH)**: 75% 이상
- **중간 (MEDIUM)**: 60-75%
- **낮음 (LOW)**: 45-60%

```python
pred = ensemble.predict_price(df)
print(f"신뢰도: {pred['confidence_score']:.2%}")
```

### 3. 규칙 기반 시그널

기술적 지표를 활용한 트레이딩 시그널:

- **RSI**: 과매수/과매도 구간
- **MACD**: 골든/데드 크로스
- **볼린저 밴드**: 상단/하단 돌파
- **이동평균**: 크로스오버

## 설치 및 설정

### 필수 패키지

```bash
pip install tensorflow xgboost scikit-learn yfinance pandas numpy
```

### 설정 파일 (config.py)

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

## 사용 방법

### 기본 사용

```python
from src.models import EnsemblePredictor
from src.analyzers.technical_analyzer import TechnicalAnalyzer
import yfinance as yf

# 데이터 로드
ticker = yf.Ticker("005930.KS")
df = ticker.history(period="2y")
df.columns = [col.lower().replace(' ', '_') for col in df.columns]
df = df.reset_index()

# 기술적 지표 추가
analyzer = TechnicalAnalyzer(df)
analyzer.add_all_indicators()
df = analyzer.get_dataframe()

# 앙상블 모델 생성 및 학습
ensemble = EnsemblePredictor()
ensemble.train_models(df)

# 가격 예측
price_pred = ensemble.predict_price(df)
print(f"예측 가격: {price_pred['ensemble_prediction']:,.0f}원")

# 등락 예측
direction_pred = ensemble.predict_direction(df)
print(f"예측 방향: {direction_pred['ensemble_prediction']}")
```

### 고급 사용

#### 커스텀 가중치

```python
# 시나리오별 가중치 조정
ensemble.set_weights({
    'lstm': 0.7,        # LSTM 중심 (보수적)
    'xgboost': 0.2,
    'rule_based': 0.1
})
```

#### 모델 저장 및 로드

```python
# 학습 후 저장
ensemble.save_models(prefix='my_ensemble')

# 나중에 로드
new_ensemble = EnsemblePredictor()
new_ensemble.load_models(prefix='my_ensemble')
```

#### 신뢰도 모니터링

```python
# 여러 예측 수행 후
metrics = ensemble.get_confidence_metrics()
print(f"평균 신뢰도: {metrics['average_confidence']:.2%}")
```

## 파일 구조

```
D:\Stock\
├── src\
│   └── models\
│       ├── __init__.py
│       ├── predictor.py          # LSTM, XGBoost 모델
│       └── ensemble_predictor.py  # 앙상블 전략
├── config.py                      # 설정 파일
├── test_ensemble.py              # 종합 테스트
├── quick_test_ensemble.py        # 빠른 검증
└── ensemble_usage_example.py     # 사용 예제
```

## 테스트 실행

### 빠른 검증

```bash
python quick_test_ensemble.py
```

### 종합 테스트

```bash
python test_ensemble.py
```

### 사용 예제

```bash
python ensemble_usage_example.py
```

## API 레퍼런스

### EnsemblePredictor

#### 생성자

```python
EnsemblePredictor(
    lstm_predictor=None,
    xgboost_classifier=None,
    weights=None,
    strategy='weighted_average'
)
```

#### 주요 메서드

##### train_models()
```python
results = ensemble.train_models(
    df,
    train_lstm=True,
    train_xgboost=True,
    feature_cols=None,
    verbose=1
)
```

모든 모델을 학습합니다.

##### predict_price()
```python
result = ensemble.predict_price(df, feature_cols=None)
```

주가를 예측합니다 (회귀).

**반환값:**
```python
{
    'individual_predictions': {...},
    'ensemble_prediction': 70000.0,
    'confidence_score': 0.75,
    'strategy': 'weighted_average',
    'current_price': 68000.0
}
```

##### predict_direction()
```python
result = ensemble.predict_direction(
    df,
    feature_cols=None,
    include_rule_based=True
)
```

등락을 예측합니다 (분류).

**반환값:**
```python
{
    'individual_predictions': {...},
    'ensemble_prediction': 'up',
    'confidence_score': 0.82,
    'strategy': 'voting',
    'votes': [1, 1, 0],
    'current_price': 68000.0
}
```

##### set_weights()
```python
ensemble.set_weights({'lstm': 0.6, 'xgboost': 0.3, 'rule_based': 0.1})
```

모델 가중치를 동적으로 설정합니다.

##### get_confidence_metrics()
```python
metrics = ensemble.get_confidence_metrics()
```

신뢰도 통계를 반환합니다.

##### save_models() / load_models()
```python
ensemble.save_models(prefix='my_model')
ensemble.load_models(prefix='my_model')
```

모델을 저장하거나 로드합니다.

## 예측 전략 선택 가이드

### Weighted Average (가중 평균)
- **장점**: 간단하고 직관적, 빠른 추론
- **단점**: 모델 간 상호작용 미반영
- **적합한 경우**: 일반적인 가격 예측, 실시간 예측

### Voting (투표)
- **장점**: 등락 예측에 효과적, 해석 가능
- **단점**: 회귀 예측에는 부적합
- **적합한 경우**: 매수/매도 시그널 생성

### Stacking (스태킹)
- **장점**: 높은 정확도, 복잡한 패턴 학습
- **단점**: 학습 시간 증가, 데이터 필요량 증가
- **적합한 경우**: 충분한 데이터, 정확도 최우선

## 성능 최적화 팁

1. **데이터 품질**: 충분한 기간(최소 1년)의 데이터 사용
2. **기술적 지표**: 다양한 지표 추가로 신뢰도 향상
3. **가중치 조정**: 백테스팅 결과에 따라 최적 가중치 탐색
4. **앙상블 전략**: 상황에 맞는 전략 선택
5. **정기 재학습**: 시장 환경 변화에 대응

## 주의사항

1. **과적합 방지**: 너무 복잡한 앙상블은 오히려 성능 저하
2. **신뢰도 해석**: 낮은 신뢰도는 불확실성을 의미
3. **시장 상황**: 급격한 시장 변동 시 예측 정확도 하락 가능
4. **투자 판단**: 예측 결과는 참고용, 최종 판단은 투자자 몫

## 문제 해결

### TensorFlow 관련 오류
```bash
pip install --upgrade tensorflow
```

### XGBoost 관련 오류
```bash
pip install --upgrade xgboost
```

### 메모리 부족
- 데이터 크기 축소 (`period="1y"`)
- 배치 크기 감소 (config.py에서 `batch_size` 조정)

## 향후 개선 계획

- [ ] Transformer 모델 추가
- [ ] Auto-ML 기반 가중치 최적화
- [ ] 실시간 스트리밍 예측
- [ ] 멀티 타임프레임 앙상블
- [ ] 감성 분석 통합

## 라이선스

이 프로젝트는 교육 및 연구 목적으로 제공됩니다.

## 문의

프로젝트 관련 문의사항은 이슈 트래커를 이용해주세요.
