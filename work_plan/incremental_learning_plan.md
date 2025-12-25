# 점진적 학습(Incremental Learning) 구현 기획서

> **작성일**: 2025-12-25  
> **목표**: 저장된 AI 모델에 새로운 데이터만 추가 학습하여 효율성 향상

---

## 1. 문제 정의

### 현재 상황
- **12/21** 학습: 과거 1년 데이터(~12/20) → 모델 저장
- **12/25** 예측: 과거 1년 데이터(~12/24) → **전체 재학습** (비효율)

### 사용자 요구사항
- 12/25에 예측 시, **12/21~12/24 신규 데이터만** 학습하고 기존 지식 유지
- 학습 시간 단축 및 컴퓨팅 자원 절약

---

## 2. 기술적 배경

### 점진적 학습(Incremental Learning)이란?
기존 모델의 가중치를 보존하면서 새로운 데이터로 **부분 업데이트**하는 기법.

### 주요 도전 과제: Catastrophic Forgetting
- **문제**: 새 데이터 학습 시 이전에 학습한 패턴을 잊어버림
- **해결 방안**:
  1. **낮은 Learning Rate** (기존 0.001 → 0.0001)
  2. **적은 Epochs** (기존 50 → 3~5 에폭)
  3. **Replay Buffer**: 과거 데이터 일부(10%)를 함께 학습
  4. **Early Stopping**: 검증 손실 모니터링

---

## 3. 구현 계획

### Phase A: 메타데이터 및 인프라 구축

#### Task 1: 학습 메타데이터 저장
- **파일**: `src/models/predictor.py`
- **내용**:
  ```python
  # 모델 저장 시 메타데이터 추가
  metadata = {
      'last_train_date': '2025-12-21',
      'data_end_date': '2025-12-20',
      'total_samples': 252,
      'feature_cols': [...],
      'model_type': 'lstm'
  }
  # metadata.json으로 저장
  ```
- **저장 위치**: `saved_models/{ticker}_{date}_metadata.json`

#### Task 2: 신규 데이터 감지 로직
- **파일**: `src/dashboard/app.py`
- **로직**:
  ```python
  if use_saved_model:
      metadata = load_metadata(model_path)
      last_date = metadata['data_end_date']
      new_data = df[df['date'] > last_date]
      
      if len(new_data) > 0:
          show_incremental_option = True
  ```

---

### Phase B: 모델별 점진적 학습 구현

#### Task 3: LSTM/Transformer Fine-tuning
- **파일**: `src/models/predictor.py` → `LSTMPredictor.train()`
- **변경사항**:
  
  **Before**:
  ```python
  def train(self, df, ...):
      X_train, X_test, y_train, y_test = prepare_lstm_data(df)
      self.model = self.build_model(input_shape)  # 새 모델 생성
      self.model.fit(X_train, y_train, epochs=50, ...)
  ```
  
  **After**:
  ```python
  def train(self, df, incremental=False, new_data_only=None, ...):
      if incremental and self.model is not None:
          # Fine-tuning 모드
          X_new, y_new = prepare_lstm_data(new_data_only)
          
          # 낮은 학습률 설정
          from tensorflow.keras.optimizers import Adam
          self.model.compile(
              optimizer=Adam(learning_rate=0.0001),  # 기존의 1/10
              loss='mse'
          )
          
          # Replay Buffer: 과거 데이터 10% 샘플링
          X_old_sample = sample_old_data(df, ratio=0.1)
          X_combined = concat([X_old_sample, X_new])
          
          self.model.fit(
              X_combined, y_combined,
              epochs=5,  # 적은 에폭
              callbacks=[EarlyStopping(patience=3)],
              verbose=1
          )
      else:
          # 기존 전체 학습 로직
          ...
  ```

#### Task 4: XGBoost Incremental Training
- **파일**: `src/models/predictor.py` → `XGBoostClassifier.train()`
- **변경사항**:
  
  ```python
  def train(self, df, incremental=False, new_data_only=None):
      if incremental and hasattr(self, 'model') and self.model is not None:
          import xgboost as xgb
          
          X_new, y_new = prepare_classification_data(new_data_only)
          dtrain_new = xgb.DMatrix(X_new, label=y_new)
          
          # 기존 모델에서 이어받기
          params = self.model.get_params()
          self.model = xgb.train(
              params,
              dtrain_new,
              num_boost_round=10,  # 적은 반복
              xgb_model=self.model.get_booster()  # 핵심: 기존 모델 전달
          )
      else:
          # 기존 전체 학습
          ...
  ```

---

### Phase C: UI 및 사용자 경험

#### Task 5: 대시보드 UI 수정
- **파일**: `src/dashboard/app.py` → `display_ai_prediction()`
- **위치**: "💾 저장된 모델 불러오기" 체크박스 아래
- **추가 UI**:
  
  ```python
  if use_saved_model and new_data_available:
      with st.expander("🔄 **점진적 학습 옵션**", expanded=False):
          st.markdown(f"""
          **감지된 신규 데이터**: {len(new_data)}일치 ({new_data_start} ~ {new_data_end})
          
          점진적 학습은 기존 모델에 새 데이터만 추가로 학습합니다.
          - ⚡ **장점**: 빠른 학습 (약 1/5 시간)
          - ⚠️ **주의**: 신규 데이터가 매우 적으면(~5일) 효과가 제한적일 수 있음
          """)
          
          use_incremental = st.checkbox(
              "🔄 점진적 학습 사용",
              value=True,
              help="체크 해제 시 전체 데이터로 처음부터 재학습합니다."
          )
  ```

#### Task 6: 학습 진행 상황 표시
- **개선**: `st.status`에서 점진적 학습 모드 표시
  
  ```python
  if use_incremental:
      status.write(f"🔄 점진적 학습 중... (신규 데이터 {len(new_data)}일치)")
  else:
      status.write("📊 전체 데이터 재학습 중...")
  ```

---

### Phase D: Ensemble 통합

#### Task 7: EnsemblePredictor 수정
- **파일**: `src/models/ensemble_predictor.py` → `train_models()`
- **파라미터 추가**:
  
  ```python
  def train_models(
      self,
      df,
      train_lstm=True,
      train_xgboost=True,
      train_transformer=False,
      incremental=False,       # 신규
      new_data_only=None,      # 신규
      ...
  ):
      if train_lstm and self.lstm:
          self.lstm.train(
              df,
              incremental=incremental,
              new_data_only=new_data_only,
              ...
          )
      
      if train_xgboost and self.xgboost:
          self.xgboost.train(
              df,
              incremental=incremental,
              new_data_only=new_data_only
          )
  ```

---

## 4. 검증 계획

### 자동 테스트
1. **유닛 테스트**: `tests/test_incremental_learning.py`
   - 메타데이터 저장/로드
   - 신규 데이터 감지 로직
   - Fine-tuning 호출 여부

### 수동 검증 시나리오
1. **12/21 전체 학습** → 저장
2. **12/25 점진적 학습** (12/22~12/24 데이터 추가)
   - 예측 정확도 비교 (전체 재학습 vs 점진적)
   - 학습 시간 측정
3. **에지 케이스**:
   - 신규 데이터 1일치만 있을 때
   - 메타데이터 없는 구 모델 호환성

---

## 5. 기대 효과

| 항목 | 전체 재학습 | 점진적 학습 |
|---|---|---|
| **학습 시간** (1년 데이터) | ~3분 | ~30초 ⚡ |
| **데이터 사용량** | 252일치 전체 | 4일치 신규 + 25일치 Replay |
| **성능 유지** | ✅ | ✅ (Replay Buffer로 보장) |

---

## 6. 리스크 관리

| 리스크 | 완화 방안 |
|---|---|
| Catastrophic Forgetting | Replay Buffer 10% + 낮은 LR |
| 신규 데이터 너무 적음 (1~2일) | 최소 3일 이상일 때만 점진적 학습 권장 UI 표시 |
| 메타데이터 손실 | 호환성 레이어: 메타데이터 없으면 전체 학습 |

---

## 7. 구현 우선순위

- [P0] Task 1, 2: 메타데이터 인프라 (다른 기능 호환성 영향)
- [P0] Task 3: LSTM Fine-tuning (핵심 모델)
- [P1] Task 4: XGBoost Incremental
- [P1] Task 5, 6: UI/UX
- [P1] Task 7: Ensemble 통합
- [P2] 검증 및 최적화
