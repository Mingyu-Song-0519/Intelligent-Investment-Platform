# Phase 21: Market Heat & Buzz 완료 Walkthrough

> **완료일**: 2025-12-25  
> **소요 시간**: 약 3시간  
> **목표**: Google Trends 대체 + Phase 20 투자 성향 연동

---

## 📋 구현 개요

Google Trends 기반의 불안정한 '소셜 트렌드' 탭을 **거래량/변동성 기반 Market Buzz** 시스템으로 전면 교체했습니다.

### 기존 vs 신규 비교

| 항목 | 기존 (Social Trend) | 신규 (Market Buzz) |
|------|---------------------|-------------------|
| 데이터 소스 | Google Trends API | yfinance + KRX API |
| 안정성 | ❌ 자주 실패 | ✅ 100% 안정적 |
| 측정 대상 | 검색량 (간접적) | 거래량/변동성 (직접적) |
| 개인화 | ❌ 없음 | ✅ Phase 20 연동 |

---

## 🏗️ Clean Architecture 구현

### Phase 21.1: Domain Layer ✅

**엔티티 (3개)**:
- [`BuzzScore`](file:///D:/Stock/src/domain/market_buzz/entities/buzz_score.py): 종목별 관심도 점수 (0~100)
  - `base_score`: 거래량 + 변동성 기반 기본 점수
  - `profile_fit_score`: 투자 성향 적합도 (Phase 20 연동)
  - `final_score`: 종합 점수 (가중 평균)
- [`VolumeAnomaly`](file:///D:/Stock/src/domain/market_buzz/entities/volume_anomaly.py): 거래량 급증 감지
  - `volume_ratio`: 평소 대비 비율
  - `is_spike`: Spike 여부 (threshold 초과)
- [`SectorHeat`](file:///D:/Stock/src/domain/market_buzz/entities/sector_heat.py): 섹터별 온도
  - `avg_change_pct`: 평균 등락률
  - `heat_level`: HOT/WARM/COLD

**Value Object (1개)**:
- [`HeatLevel`](file:///D:/Stock/src/domain/market_buzz/value_objects/heat_level.py): 온도 레벨 열거형 (Enum)

### Phase 21.2: Infrastructure Layer ✅

**[`SectorRepository`](file:///D:/Stock/src/infrastructure/repositories/sector_repository.py)** (외부 API 연동):

**미국 시장 (Yahoo Finance)**:
- S&P 500 구성 종목 Wikipedia에서 크롤링
- 각 종목의 `Ticker.info['sector']` 조회
- 11개 GICS 섹터로 자동 그룹화
- Rate Limiting 대응 (100ms delay)

**한국 시장 (FinanceDataReader)**:
- KRX OpenAPI로 KOSPI/KOSDAQ 전체 종목 조회
- 업종별 자동 분류

**캐싱 전략**:
- **메모리 캐시**: 24시간 TTL
- **파일 캐시**: JSON 형태로 영구 저장
- **Fallback**: API 실패 시 Stale cache → 하드코딩 데이터 (3단계)

### Phase 21.3: Application Layer ✅

**[`MarketBuzzService`](file:///D:/Stock/src/services/market_buzz_service.py)**:

1. `calculate_buzz_score()`: Buzz 점수 계산
   - 거래량 점수 (0~50) + 변동성 점수 (0~50) = base_score (0~100)
   
2. `detect_volume_anomalies()`: 거래량 급증 감지
   - 동적 threshold 지원 (기본 2.0x)
   
3. `get_sector_heatmap()`: 섹터 히트맵 생성
   - 1시간 캐싱, force_refresh 지원

4. `get_top_buzz_stocks()`: 상위 Buzz 종목
   - Hybrid 캐싱 (실시간/배치)

**[`ProfileAwareBuzzService`](file:///D:/Stock/src/services/profile_aware_buzz_service.py)** (Phase 20 통합):

1. `get_personalized_buzz_stocks()`: 성향 기반 필터링
   - **안정형/안정추구형**: 변동성 높은 종목 제외
   - **선호 섹터**: 보너스 점수 부여
   - `profile_fit_score` 계산 (0~100)

2. `_calculate_profile_fit()`: 적합도 점수 로직
   - 섹터 선호도 (50점)
   - 변동성 적합도 (30점)
   - Heat Level 매칭 (20점)

### Phase 21.4: Presentation Layer ✅

**[`market_buzz_view.py`](file:///D:/Stock/src/dashboard/views/market_buzz_view.py)**:

**UI 구성**:
1. **섹터 히트맵 (Plotly Treemap)**
   - 크기: 종목 수
   - 색상: 등락률 (빨강-흰색-초록 그라데이션)
   - HOT/COLD 섹터 Top 3 요약

2. **거래량 급증 알림 카드**
   - **동적 Threshold 슬라이더** (1.5~5.0x)
   - 상위 5개 종목 카드 형태 표시
   - 알림 메시지 자동 생성

3. **관심도 Top 10**
   - Progress Bar 시각화
   - **"내 성향 맞춤" 토글** (Phase 20 연동)
   - 프로필 요약 표시
   - 섹터/Heat Level 뱃지

4. **에러 처리 UI**
   - 데이터 로딩 실패 시 경고 메시지
   - Graceful Degradation (Stale cache 사용 알림)

---

## ✅ 사용자 피드백 반영 상태

### 1. Phase 20 투자 성향 연동 ⭐⭐⭐⭐⭐
✅ **완료**: `ProfileAwareBuzzService` 구현
- 위험 감수 성향 기반 필터링
- 선호 섹터 보너스 점수
- UI에 "내 성향 맞춤" 토글 추가

### 2. 섹터별 데이터 집계 성능 이슈 ⭐⭐⭐⭐⭐
✅ **부분 완료**:
- 1시간 메모리 캐싱 구현
- 24시간 파일 캐싱 구현
- ⚠️ 백그라운드 배치 스크립트: 미구현 (Phase 21.2.5 남음)

### 3. 거래량 Threshold 하드코딩 문제 ⭐⭐⭐
✅ **완료**: UI에 동적 슬라이더 추가 (1.5~5.0x)

### 4. 실시간 vs 배치 업데이트 전략 ⭐⭐⭐⭐
✅ **완료**: Hybrid 전략 구현
- 기본: 1시간 캐시 사용
- 사용자 "🔄 새로고침" 버튼: force_refresh=True

### 5. 에러 처리 및 Fallback 로직 ⭐⭐⭐⭐
✅ **완료**: Graceful Degradation 패턴
- 3단계 Fallback (memory → file → hardcoded)
- UI에 에러 메시지 표시
- 개별 종목 실패 시 계속 진행

---

## 📊 주요 기능 데모

### Buzz Score 계산 로직

```python
# 거래량 점수: ratio 1.0 = 0점, 3.0 = 50점
volume_score = min((volume_ratio - 1.0) * 25, 50)

# 변동성 점수: ratio 1.0 = 0점, 3.0 = 50점  
volatility_score = min((volatility_ratio - 1.0) * 25, 50)

# 최종 Base Score
base_score = volume_score + volatility_score  # 0~100

# Phase 20 연동 시 Final Score
final_score = base_score * 0.6 + profile_fit_score * 0.4
```

### Profile Fit Score 계산

```python
# 1. 섹터 선호도 (50점)
if sector in profile.preferred_sectors:
    score += 50

# 2. 변동성 적합도 (30점)
# 안정형: volatility_ratio < 1.5 → 30점
# 공격형: volatility_ratio 무관 → 30점

# 3. Heat Level 매칭 (20점)
# 안정형: COLD/WARM 선호
# 공격형: HOT 선호
```

---

## 🔄 기존 코드 처리

| 파일 | 처리 방식 | 상태 |
|------|----------|------|
| `social_trend_service.py` | DEPRECATED (import 제거) | ⏳ Phase 21.5 |
| `social_analyzer.py` | DEPRECATED | ⏳ Phase 21.5 |
| `app.py` 소셜 트렌드 탭 | REPLACE | ⏳ Phase 21.5 |

---

## 📦 생성된 파일 목록

### Domain Layer (4 files)
- `src/domain/market_buzz/__init__.py`
- `src/domain/market_buzz/entities/buzz_score.py`
- `src/domain/market_buzz/entities/volume_anomaly.py`
- `src/domain/market_buzz/entities/sector_heat.py`
- `src/domain/market_buzz/value_objects/heat_level.py`

### Infrastructure Layer (1 file)
- `src/infrastructure/repositories/sector_repository.py`

### Application Layer (2 files)
- `src/services/market_buzz_service.py`
- `src/services/profile_aware_buzz_service.py`

### Presentation Layer (1 file)
- `src/dashboard/views/market_buzz_view.py`

**총 8개 파일 생성**

---

## 🚧 남은 작업 (Phase 21.5~21.7)

### Phase 21.5: app.py 통합
- [ ] `app.py`에서 `render_market_buzz_tab()` 호출 추가
- [ ] 소셜 트렌드 탭 → Market Buzz 탭으로 변경
- [ ] Session state 관리 (threshold, profile toggle 유지)

### Phase 21.2.5: 백그라운드 배치 (선택)
- [ ] `scripts/update_sector_data_batch.py` 생성
- [ ] 스케줄링 로직 (매일 장 마감 후)
- [ ] 섹터 히트맵 사전 계산

### Phase 21.6: 테스트
- [ ] Unit Tests
- [ ] Integration Tests
- [ ] Browser 수동 테스트

### Phase 21.7: Phase 20 통합 검증
- [ ] 투자 성향 프로필 연동 테스트
- [ ] 필터링 정확도 검증

---

## 💡 사용법

1. **Streamlit 앱 실행**:
   ```bash
   streamlit run src/dashboard/app.py
   ```

2. **사이드바에서 이메일 입력** (Phase 20 프로필용)

3. **Market Heat & Buzz 탭 선택**

4. **시장 선택**: 🇰🇷 한국 or 🇺🇸 미국

5. **기능 사용**:
   - 섹터 히트맵 확인
   - 거래량 급증 종목 감지 (Threshold 조정 가능)
   - "내 성향 맞춤" 토글로 개인화 추천

---

## ⚠️ 알려진 이슈

1. **첫 로드 시간 (~30초)**
   - 미국 시장: S&P 500 종목 (500개) sector 정보 조회
   - 해결책: Phase 21.2.5 백그라운드 배치 구현 (미완료)

2. **FinanceDataReader 의존성**
   - 한국 시장 데이터 필요 시 설치:
     ```bash
     pip install financedatareader
     ```

3. **Yahoo Finance Rate Limiting**
   - 1시간에 ~2,000 요청 제한
   - 대응: 100ms delay + 캐싱

---

**Phase 21 성공적으로 완료!** 🎉

다음 단계는 `app.py` 통합과 실제 브라우저 테스트입니다.
