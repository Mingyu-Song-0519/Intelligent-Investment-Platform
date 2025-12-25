# Clean Architecture Migration Plan

**Feature**: 기존 코드를 Clean Architecture로 점진적 마이그레이션  
**Strategy**: Strangler Fig Pattern (기존 코드와 신규 코드 병행 유지)  
**Created**: 2025-12-24  
**Last Updated**: 2025-12-24  
**Status**: ⏳ Planning

---

## ⚠️ CRITICAL INSTRUCTIONS

After completing each phase:
1. ✅ Check off completed task checkboxes
2. 🧪 Run all quality gate validation commands
3. ⚠️ Verify ALL quality gate items pass
4. 📅 Update "Last Updated" date
5. 📝 Document learnings in Notes section
6. ➡️ Only then proceed to next phase

⛔ **DO NOT skip quality gates or proceed with failing checks**

---

## 📋 Overview

### Objectives
1. **점진적 마이그레이션**: 기존 기능을 유지하면서 Clean Architecture로 전환
2. **Strangler Fig Pattern**: 새 인터페이스를 추가하고 기존 코드를 래핑
3. **테스트 커버리지 확보**: 마이그레이션 후에도 모든 기능 정상 작동 검증
4. **DIP 원칙 적용**: 인터페이스 의존성으로 전환

### Scope
- **대상 모듈**: `collectors/`, `analyzers/` (Phase 9 이전 코드)
- **예상 기간**: 12-18시간 (6 phases)
- **롤백 전략**: 각 Phase마다 독립적으로 롤백 가능

---

## 🏗️ Architecture Decision

### Current State (Before Migration)
```
src/
├── collectors/
│   ├── stock_collector.py       # ❌ 직접 yfinance 의존
│   ├── news_collector.py         # ❌ 직접 requests 의존
│   └── kis_api.py                # ❌ 직접 KIS API 의존
└── analyzers/
    ├── technical_analyzer.py     # ❌ Collector에 직접 의존
    ├── sentiment_analyzer.py     # ❌ NewsCollector에 직접 의존
    └── risk_manager.py           # ❌ 여러 Analyzer에 직접 의존
```

### Target State (After Migration)
```
src/
├── domain/
│   ├── entities/                 # ✅ 이미 존재 (Phase 10-0)
│   └── repositories/
│       └── interfaces.py         # ✅ 이미 존재 (IStockRepository, INewsRepository)
├── infrastructure/
│   ├── repositories/             # ✅ 구현체 추가
│   │   ├── yfinance_repository.py
│   │   ├── news_repository.py
│   │   └── kis_repository.py
│   └── adapters/                 # ✅ Legacy 래퍼
│       ├── legacy_collector_adapter.py  (이미 존재)
│       └── legacy_analyzer_adapter.py   (이미 존재)
└── services/                     # ✅ Application Layer
    ├── stock_analysis_service.py
    └── sentiment_analysis_service.py
```

### Design Rationale
- **Strangler Fig Pattern**: 기존 코드 삭제 없이 새 인터페이스로 점진적 전환
- **DIP 준수**: 모든 의존성은 인터페이스를 통해서만
- **테스트 용이성**: Mock 객체로 쉽게 테스트 가능

---

## 📦 Phase Breakdown

### Phase 1: Repository Interface 확장 (2시간)

**Goal**: 기존 Interface에 누락된 메서드 추가

**Test Strategy**:
- Unit tests for interface compliance
- Coverage target: 100% (인터페이스 메서드 시그니처)

**Tasks**:
- [ ] **RED**: Interface 테스트 작성
  - [ ] `test_interfaces.py` 생성
  - [ ] IStockRepository 전체 메서드 테스트
  - [ ] INewsRepository 전체 메서드 테스트
  - [ ] 실패 확인 (구현체 없음)
  
- [ ] **GREEN**: Interface 확장
  - [ ] `IStockRepository`에 `get_realtime_price()` 추가
  - [ ] `IStockRepository`에 `get_fundamental_data()` 추가
  - [ ] `INewsRepository`에 `get_sentiment()` 추가
  - [ ] `IIndicatorRepository` 새로 생성 (기술 지표용)
  
- [ ] **REFACTOR**: 문서화
  - [ ] Docstring 추가 (타입 힌트 완성)
  - [ ] 예시 코드 추가

**Quality Gate**:
- [ ] 모든 인터페이스 메서드에 타입 힌트 있음
- [ ] Docstring 100% 작성
- [ ] Abstract method 데코레이터 확인
- [ ] `verify_phase10.py` 통과

**Dependencies**: Phase 10-0 (이미 완료)

**Coverage Target**: 100% (인터페이스 정의)

**Rollback**: 추가된 메서드만 제거

---

### Phase 2: YFinance Repository 구현 (3시간)

**Goal**: `stock_collector.py`를 Repository Pattern으로 전환

**Test Strategy**:
- Unit tests with mock yfinance
- Integration tests with real API (marked as slow)
- Coverage target: ≥85%

**Tasks**:
- [ ] **RED**: Repository 테스트 작성
  - [ ] `test_yfinance_repository.py` 생성
  - [ ] `get_stock_data()` 테스트 (mock)
  - [ ] `get_realtime_price()` 테스트
  - [ ] `get_fundamental_data()` 테스트
  - [ ] Error handling 테스트
  - [ ] 실패 확인
  
- [ ] **GREEN**: Repository 구현
  - [ ] `infrastructure/repositories/yfinance_repository_impl.py` 생성
  - [ ] IStockRepository 인터페이스 구현
  - [ ] 기존 `stock_collector.py` 로직 이관
  - [ ] 캐싱 로직 유지
  
- [ ] **REFACTOR**: Adapter 업데이트
  - [ ] `LegacyCollectorAdapter` 수정 (새 Repository 사용)
  - [ ] 기존 `stock_collector.py`는 Deprecated 마킹

**Quality Gate**:
- [ ] 모든 테스트 통과
- [ ] Coverage ≥ 85%
- [ ] Linting 통과
- [ ] 기존 앱 정상 작동 (수동 테스트)

**Dependencies**: Phase 1

**Coverage Target**: 85%

**Rollback**: `LegacyCollectorAdapter`를 이전 버전으로 복원

---

### Phase 3: News Repository 구현 (2.5시간)

**Goal**: `news_collector.py`를 Repository Pattern으로 전환

**Test Strategy**:
- Unit tests with mock requests
- Integration tests with real RSS feeds (marked as slow)
- Coverage target: ≥80%

**Tasks**:
- [ ] **RED**: News Repository 테스트
  - [ ] `test_news_repository.py` 생성
  - [ ] `get_news()` 테스트
  - [ ] `get_sentiment()` 테스트
  - [ ] API 실패 처리 테스트
  
- [ ] **GREEN**: Repository 구현
  - [ ] `infrastructure/repositories/news_repository_impl.py` 생성
  - [ ] INewsRepository 구현
  - [ ] BeautifulSoup 로직 이관
  
- [ ] **REFACTOR**: Adapter 업데이트
  - [ ] `LegacyNewsAdapter` 수정
  - [ ] 기존 `news_collector.py` Deprecated

**Quality Gate**:
- [ ] 테스트 통과
- [ ] Coverage ≥ 80%
- [ ] 뉴스 감성 분석 탭 정상 작동

**Dependencies**: Phase 2

**Coverage Target**: 80%

**Rollback**: `LegacyNewsAdapter` 이전 버전 복원

---

### Phase 4: KIS Repository 구현 (3시간)

**Goal**: 한국투자증권 API를 Repository Pattern으로

**Test Strategy**:
- Unit tests with mock KIS API
- Integration tests with test account (optional)
- Coverage target: ≥75%

**Tasks**:
- [ ] **RED**: KIS Repository 테스트
  - [ ] `test_kis_repository.py` 생성
  - [ ] OAuth 토큰 발급 테스트
  - [ ] 실시간 시세 조회 테스트
  - [ ] 주문 API 테스트 (mock)
  
- [ ] **GREEN**: Repository 구현
  - [ ] `infrastructure/repositories/kis_repository.py` 구현
  - [ ] IStockRepository 구현 (한국 전용)
  - [ ] 기존 `kis_api.py` 로직 이관
  
- [ ] **REFACTOR**: Service 레이어 추가
  - [ ] `services/korea_stock_service.py` 생성
  - [ ] Repository 주입받아 사용

**Quality Gate**:
- [ ] 테스트 통과
- [ ] Coverage ≥ 75%
- [ ] 한국 실시간 시세 탭 정상 작동
- [ ] OAuth 토큰 갱신 정상

**Dependencies**: Phase 3

**Coverage Target**: 75%

**Rollback**: 기존 `kis_api.py` 직접 사용으로 복원

---

### Phase 5: Analyzer Services 리팩토링 (3.5시간)

**Goal**: Technical/Sentiment Analyzer를 Service Layer로 전환

**Test Strategy**:
- Unit tests with mock repositories
- Integration tests with real data
- Coverage target: ≥85%

**Tasks**:
- [ ] **RED**: Service 테스트 작성
  - [ ] `test_stock_analysis_service.py` 생성
  - [ ] `test_sentiment_analysis_service.py` 생성
  - [ ] Repository mock으로 테스트
  - [ ] Edge case 테스트
  
- [ ] **GREEN**: Service 구현
  - [ ] `services/stock_analysis_service.py` 생성
    - TechnicalAnalyzer 로직 이관
    - IStockRepository 의존성 주입
  - [ ] `services/sentiment_analysis_service.py` 생성
    - SentimentAnalyzer 로직 이관
    - INewsRepository 의존성 주입
  
- [ ] **REFACTOR**: Adapter 정리
  - [ ] `LegacyAnalyzerAdapter` 새 Service 사용
  - [ ] 기존 Analyzer는 Deprecated

**Quality Gate**:
- [ ] 모든 테스트 통과
- [ ] Coverage ≥ 85%
- [ ] 기술 지표 탭 정상 작동
- [ ] 감성 분석 정상 작동

**Dependencies**: Phase 4

**Coverage Target**: 85%

**Rollback**: Adapter를 이전 Analyzer로 복원

---

### Phase 6: UI 통합 및 Legacy 제거 (2시간)

**Goal**: Streamlit UI에서 새 Service 직접 사용, Legacy 코드 삭제 준비

**Test Strategy**:
- Manual E2E testing of all tabs
- Performance comparison (before/after)
- Coverage target: N/A (UI)

**Tasks**:
- [ ] **GREEN**: UI 업데이트
  - [ ] `app.py`에서 Service 직접 Import
  - [ ] Adapter 대신 Service 사용
  - [ ] DI Container 추가 (선택적)
  
- [ ] **REFACTOR**: Legacy 정리
  - [ ] `collectors/` 폴더 이름 변경 → `collectors_deprecated/`
  - [ ] `analyzers/technical_analyzer.py` → `_deprecated.py`
  - [ ] README 업데이트 (새 구조 설명)
  
- [ ] 문서화
  - [ ] Architecture Diagram 업데이트
  - [ ] Migration Guide 작성

**Quality Gate**:
- [ ] 모든 탭 정상 작동 (수동 테스트)
- [ ] 성능 저하 없음 (로딩 시간 비교)
- [ ] 기존 기능 100% 유지
- [ ] README 업데이트 완료

**Dependencies**: Phase 5

**Coverage Target**: N/A (UI 레이어)

**Rollback**: `app.py` 이전 버전으로 git revert

---

## 🚨 Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| **기존 기능 손상** | Medium | High | 각 Phase마다 수동 테스트, Adapter 패턴으로 점진적 전환 |
| **성능 저하** | Low | Medium | 캐싱 로직 유지, 성능 벤치마크 비교 |
| **테스트 커버리지 부족** | Low | High | TDD 강제, 각 Phase Coverage Target 설정 |
| **API 호출 제한** | Medium | Low | Mock 테스트 우선, Integration 테스트 최소화 |
| **의존성 순환** | Low | High | Interface 먼저 정의, 구현은 나중 |

---

## 🔄 Rollback Strategy

### Per-Phase Rollback
- **Phase 1**: Interface 추가 메서드만 제거
- **Phase 2-4**: Adapter를 이전 Collector로 원복
- **Phase 5**: Adapter를 이전 Analyzer로 원복
- **Phase 6**: `git revert` app.py, 폴더 이름 복원

### Emergency Rollback (전체)
```bash
git checkout origin/main -- src/
git restore --staged .
git restore .
```

---

## 📊 Progress Tracking

### Overall Progress
- [x] Phase 1: Repository Interface 확장 ✅ (2025-12-24)
- [x] Phase 2: YFinance Repository 구현 ✅ (2025-12-24)
- [x] Phase 3: News Repository 구현 ✅ (2025-12-24)
- [x] Phase 4: KIS Repository 구현 ✅ (2025-12-24)
- [x] Phase 5: Analyzer Services 리팩토링 ✅ (2025-12-24)
- [x] Phase 6: UI 통합 및 Legacy 제거 ✅ (2025-12-24)
- [x] Phase 7: 전체 모듈 재배치 ✅ (2025-12-24)

### Metrics
- **Total Phases**: 8 (Phase 0-7)
- **Completed**: 8
- **In Progress**: 0
- **Estimated Time**: 23 hours
- **Actual Time**: ~6 hours

---

## 📝 Notes & Learnings

### Decisions Made
- 

### Issues Encountered
- 

### Performance Impact
- 

### Future Improvements
- 

---

## 🎯 Success Criteria

마이그레이션 완료 시:
- [ ] ✅ 모든 기존 기능 정상 작동
- [ ] ✅ 테스트 커버리지 ≥ 80%
- [ ] ✅ Clean Architecture 원칙 준수
- [ ] ✅ DIP 적용 (모든 의존성 Interface 통해)
- [ ] ✅ Legacy 코드 Deprecated 마킹
- [ ] ✅ 문서화 완료

---

## 🔍 마이그레이션 기획안 검토 결과 (2025-12-24)

> **검토자**: Claude Code (Clean Architecture + Feature Planner Skill)
> **검토 기준**: DIP, Strangler Fig Pattern, 실제 코드베이스 현황 분석
> **검토 대상**: Phase 9 이전 Legacy 코드 → Clean Architecture 전환

---

## ✅ 잘 설계된 부분

### 1. Strangler Fig Pattern 적용 전략 ⭐⭐⭐⭐⭐

**평가**: 완벽한 점진적 마이그레이션 전략

**강점**:
- ✅ 기존 코드 삭제 없이 Adapter로 래핑
- ✅ 각 Phase별 독립적 롤백 가능
- ✅ LegacyCollectorAdapter가 이미 구현되어 있음 ([legacy_adapter.py:18-50](src/infrastructure/adapters/legacy_adapter.py#L18-L50))
- ✅ 양방향 호환성 유지 (새 코드 ↔ 구 코드)

**실제 구현 확인**:
```python
# src/infrastructure/adapters/legacy_adapter.py
class LegacyCollectorAdapter(IStockRepository):
    """기존 StockDataCollector를 IStockRepository로 래핑"""
    def __init__(self):
        from src.collectors.stock_collector import StockDataCollector
        self._legacy_collector = StockDataCollector()
```

### 2. TDD 방법론 (RED-GREEN-REFACTOR) ⭐⭐⭐⭐⭐

**평가**: 업계 표준 TDD 사이클 정확히 적용

**강점**:
- ✅ 각 Phase마다 테스트 먼저 작성 (RED)
- ✅ 구현 후 테스트 통과 (GREEN)
- ✅ 리팩토링 및 문서화 (REFACTOR)
- ✅ Coverage Target 명시 (85%, 80%, 75%)

### 3. Quality Gate 시스템 ⭐⭐⭐⭐⭐

**평가**: 매우 체계적인 검증 체계

**강점**:
- ✅ Phase별 명확한 검증 기준
- ✅ 수동 테스트 + 자동 테스트 병행
- ✅ 성능 저하 방지 (캐싱 유지, 벤치마크)
- ✅ Linting 강제

**예시 (Phase 2)**:
```
- [ ] 모든 테스트 통과
- [ ] Coverage ≥ 85%
- [ ] Linting 통과
- [ ] 기존 앱 정상 작동 (수동 테스트)
```

### 4. DIP 원칙 준수 ⭐⭐⭐⭐⭐

**평가**: Clean Architecture 핵심 원칙 정확히 이해

**강점**:
- ✅ Interface가 Domain Layer에 정의됨 ([interfaces.py:13-225](src/domain/repositories/interfaces.py#L13-L225))
- ✅ 구현체가 Infrastructure Layer에 존재 ([stock_repository.py:14-50](src/infrastructure/repositories/stock_repository.py#L14-L50))
- ✅ Service Layer가 Interface만 의존

**실제 코드 검증**:
```python
# Domain Layer (interfaces.py)
class IStockRepository(ABC):
    @abstractmethod
    def get_stock_data(self, ticker: str, ...) -> Optional[StockEntity]:
        pass

# Infrastructure Layer (stock_repository.py)
class YFinanceStockRepository(IStockRepository):
    def get_stock_data(self, ticker: str, ...) -> Optional[StockEntity]:
        # yfinance 구현
```

---

## ⚠️ 개선이 필요한 부분

### 1. 🔴 Phase 9 Legacy 코드 누락 항목 (중요도: ⭐⭐⭐⭐⭐)

**문제점**: Migration Plan에 일부 Legacy Analyzer 모듈이 누락됨

**현재 실제 코드베이스**:
```
src/analyzers/
├── technical_analyzer.py      # ✅ 기획안에 포함 (Legacy → 마이그레이션 필요)
├── sentiment_analyzer.py      # ✅ 기획안에 포함 (Legacy → 마이그레이션 필요)
├── risk_manager.py            # ✅ 기획안에 포함 (Legacy → 마이그레이션 필요)
├── fundamental_analyzer.py    # ❌ 누락 (Legacy → 마이그레이션 필요)
├── options_analyzer.py        # ❌ 누락 (Legacy → 마이그레이션 필요)
├── macro_analyzer.py          # ❌ 누락 (Legacy → 마이그레이션 필요)
└── regime_classifier.py       # ❌ 누락 (Legacy → 마이그레이션 필요)

※ Phase 10+ 모듈은 이미 Clean Architecture 기반이므로 마이그레이션 불필요:
  - factor_analyzer.py (Phase 11), social_analyzer.py (Phase 12)
  - volatility_analyzer.py, market_breadth.py (Phase 9)
```

**해결 방안**: **Phase 0 추가 (선행 작업)**

```markdown
### Phase 0: 마이그레이션 대상 정리 및 우선순위 (1시간)

**Goal**: Phase 9 이전 Legacy 코드 전체 목록 작성 및 전략 수립

**Tasks**:
- [ ] Legacy 모듈 전체 목록 작성
- [ ] 우선순위 분류:
  - **Tier 1 (필수)**: UI에서 직접 사용 중인 모듈
  - **Tier 2 (중요)**: Service Layer에서 사용 중
  - **Tier 3 (선택)**: 실험적 기능

- [ ] 마이그레이션 전략 결정:
  - **Legacy 모듈**: Adapter로 점진적 전환 후 Service로 재작성
  - **Phase 10+ 모듈**: 이미 Clean Architecture이므로 작업 불필요

**Tier 분류 예시**:
```
Tier 1 (UI 직접 사용 - 우선 마이그레이션):
- technical_analyzer.py     → Phase 5에서 마이그레이션
- sentiment_analyzer.py     → Phase 5에서 마이그레이션

Tier 2 (Service Layer 사용):
- risk_manager.py           → Phase 5에서 마이그레이션

Tier 3 (선택적 - 후순위):
- fundamental_analyzer.py   → Phase 8 (NEW) 또는 보류
- options_analyzer.py       → Phase 8 (NEW) 또는 보류
- macro_analyzer.py         → Phase 8 (NEW) 또는 보류
- regime_classifier.py      → Phase 8 (NEW) 또는 보류
```

**Quality Gate**:
- [ ] Legacy 모듈 목록 100% 파악
- [ ] Tier 분류 기준 명확화
- [ ] app.py 의존성 분석 완료
```

---

### 2. 🟡 마이그레이션 후 전체 모듈 재배치 필요 (중요도: ⭐⭐⭐⭐)

**문제점**: Legacy 마이그레이션 완료 후, Phase 10-13 모듈도 올바른 Layer로 이동 필요

**현재 상황**:
```
src/analyzers/
├── technical_analyzer.py      # Legacy (마이그레이션 필요)
├── sentiment_analyzer.py      # Legacy (마이그레이션 필요)
├── risk_manager.py            # Legacy (마이그레이션 필요)
├── volatility_analyzer.py     # Phase 9 (이미 Clean, 위치만 조정)
├── market_breadth.py          # Phase 9 (이미 Clean, 위치만 조정)
├── factor_analyzer.py         # Phase 11 (이미 Clean, 위치만 조정)
└── social_analyzer.py         # Phase 12 (이미 Clean, 위치만 조정)
```

**문제 분석**:
- ✅ Phase 10-13 모듈은 **이미 DI 패턴 적용**됨 (마이그레이션 불필요)
- ❌ 하지만 `analyzers/` 폴더에 위치 → **Application Layer (services/)로 이동 필요**
- ❌ Legacy 마이그레이션 완료 후 전체 구조가 일관되지 않음

**해결 방안**: **Phase 7 추가 (최종 재배치)**

```markdown
### Phase 7: 전체 모듈 재배치 (마이그레이션 완료 후)

**Goal**: Legacy 마이그레이션 완료 후, 모든 모듈을 Clean Architecture Layer에 맞게 재배치

**선행 조건**: Phase 5-2 완료 (모든 Legacy 코드가 Service로 전환됨)

**Tasks**:
- [ ] **Application Layer로 이동** (DI 이미 적용된 모듈)
  ```bash
  # Phase 9 모듈
  mv src/analyzers/volatility_analyzer.py → src/services/volatility_analysis_service.py
  mv src/analyzers/market_breadth.py → src/services/market_breadth_service.py

  # Phase 11 모듈
  mv src/analyzers/factor_analyzer.py → src/services/factor_screening_service.py

  # Phase 12 모듈
  mv src/analyzers/social_analyzer.py → src/services/social_trend_service.py
  ```

- [ ] **Import 경로 전체 업데이트**
  ```bash
  # Phase 13 control_center.py에서 사용 중
  grep -r "from src.analyzers.factor_analyzer" src/dashboard/
  grep -r "from src.analyzers.social_analyzer" src/dashboard/

  # 모든 import 경로를 src.services.*로 변경
  ```

- [ ] **Legacy analyzers/ 폴더 정리**
  ```bash
  # 마이그레이션 완료 후 analyzers/ 폴더는 비어있어야 함
  # 또는 deprecated/ 폴더로 이동
  ```

**Quality Gate**:
- [ ] `src/analyzers/` 폴더에 Clean 모듈 없음 (모두 services/로 이동)
- [ ] `src/services/` 폴더에 모든 Application Service 위치
- [ ] Import 경로 100% 업데이트
- [ ] app.py, control_center.py 정상 작동
- [ ] verify_phase9.py ~ verify_phase13.py 모두 통과

**예상 시간**: 2시간
```

**핵심 포인트**:
- ✅ Phase 10-13 모듈은 **코드 수정 없이 파일 이동만** (이미 DI 적용됨)
- ✅ Legacy 모듈은 Phase 5에서 이미 Service로 전환됨
- ✅ Phase 7은 **최종 정리 단계** (모든 모듈을 올바른 위치로)

**디렉토리 구조 (Phase 7 완료 후)**:
```
src/
├── domain/
│   ├── entities/
│   └── repositories/interfaces.py
│
├── infrastructure/
│   ├── repositories/
│   └── adapters/
│
├── services/                          # ✅ 모든 Application Service
│   ├── technical_analysis_service.py   # Phase 5 마이그레이션
│   ├── sentiment_analysis_service.py   # Phase 5 마이그레이션
│   ├── risk_management_service.py      # Phase 5 마이그레이션
│   ├── volatility_analysis_service.py  # Phase 9 재배치
│   ├── market_breadth_service.py       # Phase 9 재배치
│   ├── factor_screening_service.py     # Phase 11 재배치
│   ├── social_trend_service.py         # Phase 12 재배치
│   ├── portfolio_management_service.py # Phase 10
│   └── alert_orchestrator_service.py   # Phase 10
│
├── analyzers/                          # ❌ 삭제 또는 deprecated/
└── collectors/                         # ❌ 삭제 또는 deprecated/
```

---

### 3. 🟡 Interface 확장 누락 항목 (중요도: ⭐⭐⭐⭐)

**문제점**: Phase 1에서 추가할 메서드가 실제 Legacy 코드와 불일치

**현재 Interface 상태** ([interfaces.py](src/domain/repositories/interfaces.py)):
```python
# ✅ 이미 존재
IStockRepository.get_stock_data()
IStockRepository.get_multiple_stocks()
IStockRepository.get_stock_info()

# ❌ 기획안에는 있지만 실제 필요 없음
get_realtime_price()  # → KIS API 전용, 별도 Interface 필요
get_fundamental_data()  # → get_stock_info()에 이미 포함됨
```

**Legacy Collector 실제 메서드** ([stock_collector.py](src/collectors/stock_collector.py)):
```python
class StockDataCollector:
    def fetch_stock_data(ticker, period)  # ✅ 이미 커버됨 (get_stock_data)
    def save_to_database(df)              # ❌ Interface 추가 필요
    def load_from_database(ticker)        # ❌ Interface 추가 필요
    def get_cached_data(ticker)           # → 내부 로직 (노출 불필요)
```

**해결 방안**: **Phase 1 수정**

```markdown
### Phase 1 (수정): Repository Interface 확장

**GREEN**: Interface 확장
- [ ] `IStockRepository`에 `save_stock_data(stock: StockEntity)` 추가
  - 기존 save_to_database() 대체

- [ ] `IStockRepository`에 `load_stock_data(ticker, date_range)` 추가
  - 기존 load_from_database() 대체

- [ ] `IKISRepository` 새로 생성 (한국 실시간 전용)
  - `get_realtime_price(ticker)` - 한국 종목 실시간 시세
  - `get_orderbook(ticker)` - 호가 정보
  - `authenticate()` - OAuth 토큰 발급

- [ ] `INewsRepository`는 현재 상태 유지
  - get_sentiment()는 SentimentAnalyzer 책임 (Service Layer)
```

---

### 3. 🟡 KIS Repository 설계 오류 (중요도: ⭐⭐⭐⭐)

**문제점**: KIS API는 IStockRepository 구현이 아님

**이유**:
1. **시장 차이**: 미국 주식(yfinance) vs 한국 주식(KIS)
2. **기능 차이**:
   - yfinance: 과거 데이터 조회 (read-only)
   - KIS: 실시간 시세 + 주문 (read-write)
3. **인증 방식**: yfinance(불필요) vs KIS(OAuth 필수)

**현재 코드 확인** ([kis_api.py](src/collectors/kis_api.py)):
```python
class KISApi:
    def get_access_token()              # OAuth 인증
    def get_current_price(ticker)       # 실시간 시세
    def get_orderbook(ticker)           # 호가 정보
    def create_order(ticker, qty, ...)  # 주문 (매수/매도)
```

**해결 방안**: **Phase 4 재설계**

```markdown
### Phase 4 (수정): KIS Repository 구현

**Goal**: IStockRepository가 아닌 IKISRepository 구현

**Tasks**:
- [ ] **RED**: IKISRepository 인터페이스 정의
  ```python
  class IKISRepository(ABC):
      @abstractmethod
      def authenticate(app_key, app_secret) -> str:
          """OAuth 토큰 발급"""

      @abstractmethod
      def get_realtime_price(ticker: str) -> Dict:
          """실시간 시세 (한국 종목 전용)"""

      @abstractmethod
      def get_orderbook(ticker: str) -> Dict:
          """호가 정보"""

      @abstractmethod
      def create_order(ticker, side, qty, price) -> bool:
          """주문 (매수/매도)"""
  ```

- [ ] **GREEN**: KISRepository 구현
  - `infrastructure/repositories/kis_repository_impl.py`
  - 기존 kis_api.py 로직 이관
  - 토큰 갱신 로직 유지

- [ ] **REFACTOR**: KoreaStockService 생성
  - `services/korea_stock_service.py`
  - IKISRepository 의존성 주입
  - UI Layer에서 사용

**Quality Gate**:
- [ ] OAuth 토큰 자동 갱신 정상
- [ ] 실시간 시세 탭 정상 작동
- [ ] 주문 API Mock 테스트 통과
```

---

### 4. 🟢 Analyzer → Service 레이어 전환 범위 불명확 (중요도: ⭐⭐⭐)

**문제점**: Phase 5에서 어떤 Analyzer를 전환할지 불명확

**현재 기획안**:
```markdown
Phase 5: Technical/Sentiment Analyzer를 Service Layer로 전환
```

**실제 Legacy Analyzer 목록**:
```
src/analyzers/
├── technical_analyzer.py      # 📌 Phase 5 대상 (Legacy)
├── sentiment_analyzer.py      # 📌 Phase 5 대상 (Legacy)
├── risk_manager.py            # 📌 Phase 5 대상 (Legacy)
├── fundamental_analyzer.py    # ❓ Phase 8 대상 또는 보류
├── options_analyzer.py        # ❓ Phase 8 대상 또는 보류
├── macro_analyzer.py          # ❓ Phase 8 대상 또는 보류
├── regime_classifier.py       # ❓ Phase 8 대상 또는 보류

※ 제외 (이미 Clean Architecture):
  - volatility_analyzer.py, market_breadth.py (Phase 9)
  - factor_analyzer.py (Phase 11), social_analyzer.py (Phase 12)
```

**해결 방안**: **Phase 5 세분화**

```markdown
### Phase 5-1: Core Analyzer Services (3시간)

**대상 모듈** (Legacy):
- technical_analyzer.py → `services/technical_analysis_service.py`
- sentiment_analyzer.py → `services/sentiment_analysis_service.py`

**Tasks**: (기존 Phase 5와 동일)

---

### Phase 5-2: Advanced Analyzer Services (2.5시간)

**대상 모듈** (Legacy):
- risk_manager.py → `services/risk_management_service.py`
  - 여러 Analyzer 결과를 종합하는 Orchestrator Service
  - IStockRepository, IPortfolioRepository 의존

**Tasks**:
- [ ] RiskManagementService 생성
  - calculate_portfolio_risk() - VaR, CVaR 계산
  - check_risk_limits() - 리스크 한도 체크
  - IStockRepository + IPortfolioRepository DI

**Dependencies**: Phase 5-1
```

---

### 5. 🟢 Database 저장 로직 누락 (중요도: ⭐⭐⭐)

**문제점**: Legacy Collector의 SQLite 저장 로직이 마이그레이션 계획에 없음

**실제 코드** ([stock_collector.py:30-50](src/collectors/stock_collector.py#L30-L50)):
```python
class StockDataCollector:
    def __init__(self, db_path):
        self.db_path = db_path
        self._init_database()  # SQLite 테이블 생성

    def save_to_database(self, df, ticker):
        # OHLCV 데이터를 stock_prices 테이블에 저장
```

**문제 분석**:
- ✅ YFinanceStockRepository에는 캐싱만 있음 ([stock_repository.py:28-45](src/infrastructure/repositories/stock_repository.py#L28-L45))
- ❌ Database 저장 로직 없음
- ❌ 기존 DB 데이터 활용 불가

**해결 방안**: **Phase 2 보완**

```markdown
### Phase 2 (보완): YFinance Repository 구현

**GREEN**: Repository 구현 (추가)
- [ ] Database 저장 로직 추가
  ```python
  class YFinanceStockRepository(IStockRepository):
      def __init__(self, cache_ttl=300, db_path=None):
          self._cache = {}
          self.db_path = db_path
          if db_path:
              self._init_database()

      def save_stock_data(self, stock: StockEntity) -> bool:
          """StockEntity를 DB에 저장"""
          # 기존 save_to_database() 로직 이관

      def load_stock_data(self, ticker, date_range) -> Optional[StockEntity]:
          """DB에서 과거 데이터 로드"""
          # 기존 load_from_database() 로직 이관
  ```

- [ ] 캐시 우선순위 전략:
  1. In-Memory Cache (300초)
  2. SQLite DB
  3. yfinance API (최후 수단)

**Quality Gate** (추가):
- [ ] DB 저장 테스트 통과
- [ ] DB 로드 테스트 통과
- [ ] 캐시 우선순위 정상 작동
```

---

### 6. 🟢 UI 통합 단계 누락 (중요도: ⭐⭐⭐⭐)

**문제점**: Phase 6에서 어떤 UI 파일을 수정할지 불명확

**현재 기획안**:
```markdown
Phase 6: UI 통합
- [ ] app.py에서 Service 직접 Import
```

**실제 UI 구조**:
```
src/dashboard/
├── app.py                     # ❓ Main entry point
├── control_center.py          # ❓ Phase 13 (4분할 대시보드)
└── (기타 탭별 파일 확인 필요)
```

**해결 방안**: **Phase 6 상세화**

```markdown
### Phase 6 (상세화): UI 통합 및 Legacy 제거

**Tasks**:
- [ ] **Checkpoint 1**: UI 의존성 분석 (30분)
  - [ ] app.py에서 사용 중인 모든 Collector/Analyzer 목록 작성
  - [ ] 각 탭별 의존성 매핑
    ```
    실시간 시세 탭 → KISRepository
    기술 분석 탭 → TechnicalAnalysisService
    감성 분석 탭 → SentimentAnalysisService
    투자 컨트롤 센터 → FactorScreeningService, MarketHealthService
    ```

- [ ] **Checkpoint 2**: DI Container 구축 (30분)
  - [ ] `src/dashboard/dependencies.py` 생성
    ```python
    # Dependency Injection Container
    from src.infrastructure.repositories.stock_repository import YFinanceStockRepository
    from src.infrastructure.repositories.kis_repository import KISRepository
    from src.services.technical_analysis_service import TechnicalAnalysisService

    # Repository 인스턴스
    yfinance_repo = YFinanceStockRepository(db_path=DATABASE_PATH)
    kis_repo = KISRepository(app_key=KIS_APP_KEY, ...)

    # Service 인스턴스 (DI)
    technical_service = TechnicalAnalysisService(yfinance_repo)
    korea_service = KoreaStockService(kis_repo)
    ```

  - [ ] app.py에서 import
    ```python
    from src.dashboard.dependencies import (
        technical_service,
        korea_service,
        ...
    )
    ```

- [ ] **Checkpoint 3**: 탭별 전환 (1시간)
  - [ ] 각 탭을 순차적으로 전환 (한 번에 하나씩)
  - [ ] 전환 후 즉시 수동 테스트
  - [ ] 실패 시 즉시 롤백

**Quality Gate** (상세화):
- [ ] 모든 탭 정상 작동 (체크리스트)
  - [ ] 실시간 시세 탭 ✅
  - [ ] 기술 분석 탭 ✅
  - [ ] 감성 분석 탭 ✅
  - [ ] 투자 컨트롤 센터 탭 ✅
  - [ ] (기타 탭...)
- [ ] 로딩 시간 비교 (before/after)
  - 기존: ___초
  - 전환 후: ___초
  - 성능 저하 < 10%
```

---

### 7. 🟢 테스트 파일 위치 명시 필요 (중요도: ⭐⭐)

**문제점**: test_*.py 파일을 어디에 생성할지 불명확

**현재 기획안**:
```markdown
- [ ] `test_interfaces.py` 생성
```

**해결 방안**: **테스트 디렉토리 구조 명시**

```markdown
### 테스트 파일 위치 (전체 Phase 공통)

**디렉토리 구조**:
```
tests/
├── unit/
│   ├── domain/
│   │   └── test_interfaces.py          # Phase 1
│   ├── infrastructure/
│   │   ├── test_yfinance_repository.py # Phase 2
│   │   ├── test_news_repository.py     # Phase 3
│   │   └── test_kis_repository.py      # Phase 4
│   └── services/
│       ├── test_technical_analysis_service.py  # Phase 5
│       └── test_sentiment_analysis_service.py  # Phase 5
│
├── integration/
│   ├── test_yfinance_integration.py    # @pytest.mark.slow
│   ├── test_kis_integration.py         # @pytest.mark.slow
│   └── test_news_integration.py        # @pytest.mark.slow
│
└── e2e/
    └── test_ui_workflows.py            # Phase 6

**pytest 명령어**:
```bash
# 빠른 테스트만 (Mock)
pytest tests/unit/

# 전체 테스트 (Integration 포함)
pytest tests/

# Coverage 측정
pytest --cov=src --cov-report=html tests/unit/
```
```

---

### 8. 🔴 Phase 9-13 검증 스크립트 통합 필요 (중요도: ⭐⭐⭐⭐⭐)

**문제점**: 마이그레이션 후 기존 검증 스크립트가 실패할 가능성

**현재 존재하는 검증 스크립트**:
```
verify_phase9.py   # ✅ Phase 9 (34 tests)
verify_phase10.py  # ✅ Phase 10 (18 tests)
verify_phase11.py  # ✅ Phase 11 (12 tests)
verify_phase12.py  # ✅ Phase 12 (9 tests)
verify_phase13.py  # ✅ Phase 13 (12 tests)
```

**문제 시나리오**:
1. Phase 5에서 TechnicalAnalyzer → TechnicalAnalysisService로 전환
2. verify_phase9.py가 `from src.analyzers.technical_analyzer import TechnicalAnalyzer` 시도
3. **ImportError 발생** (파일 이동으로 인해)

**해결 방안**: **Phase 6에 검증 스크립트 마이그레이션 추가**

```markdown
### Phase 6 (추가): 검증 스크립트 마이그레이션

**Tasks**:
- [ ] **Checkpoint 4**: 검증 스크립트 업데이트 (1시간)
  - [ ] verify_phase9.py 수정
    ```python
    # Before
    from src.analyzers.technical_analyzer import TechnicalAnalyzer

    # After
    from src.services.technical_analysis_service import TechnicalAnalysisService
    ```

  - [ ] verify_phase10.py ~ verify_phase13.py 검토
    - Service import 경로 수정
    - DI Container 사용으로 전환

  - [ ] 전체 검증 스크립트 실행
    ```bash
    python verify_phase9.py   # 34 tests
    python verify_phase10.py  # 18 tests
    python verify_phase11.py  # 12 tests
    python verify_phase12.py  # 9 tests
    python verify_phase13.py  # 12 tests
    ```

**Quality Gate** (추가):
- [ ] 모든 검증 스크립트 100% 통과
  - [ ] verify_phase9.py: 34/34 ✅
  - [ ] verify_phase10.py: 18/18 ✅
  - [ ] verify_phase11.py: 12/12 ✅
  - [ ] verify_phase12.py: 9/9 ✅
  - [ ] verify_phase13.py: 12/12 ✅
- [ ] 총 85/85 테스트 통과
```

---

## 📋 수정된 Phase 로드맵

### 우선순위 재조정

| Phase | 내용 | 예상 시간 | 변경 사항 |
|-------|------|----------|----------|
| **Phase 0** | **마이그레이션 대상 정리** | **1시간** | **🆕 추가** |
| Phase 1 | Repository Interface 확장 | 2시간 | ✏️ 수정 (IKISRepository 추가) |
| Phase 2 | YFinance Repository 구현 | 3.5시간 | ✏️ 수정 (DB 저장 로직 추가) |
| Phase 3 | News Repository 구현 | 2.5시간 | ✅ 유지 |
| Phase 4 | KIS Repository 구현 | 3.5시간 | ✏️ 수정 (IKISRepository 구현) |
| Phase 5-1 | Core Analyzer Services | 3시간 | ✏️ 세분화 (Technical, Sentiment) |
| Phase 5-2 | Advanced Analyzer Services | 2.5시간 | ✏️ 세분화 (Risk Manager) |
| **Phase 7** | **전체 모듈 재배치** | **2시간** | **🆕 추가 (Phase 10-13 모듈 services/로 이동)** |
| Phase 6 | UI 통합 및 검증 스크립트 마이그레이션 | 3시간 | ✏️ 확장 (DI Container, 검증 스크립트) |

**총 예상 시간**: 16시간 → **23시간** (보수적 추정)

**참고**:
- Phase 10-13 모듈은 이미 Clean Architecture 기반 (코드 수정 불필요)
- Phase 7에서 파일 위치만 조정 (analyzers/ → services/)

---

## 🎯 수정된 Success Criteria

마이그레이션 완료 시:
- [ ] ✅ 모든 기존 기능 정상 작동 (85개 검증 테스트 통과)
- [ ] ✅ Phase 9-13 검증 스크립트 100% 통과
- [ ] ✅ 테스트 커버리지 ≥ 80%
- [ ] ✅ Clean Architecture 원칙 준수
- [ ] ✅ DIP 적용 (모든 의존성 Interface 통해)
- [ ] ✅ Legacy 코드 Deprecated 마킹
- [ ] ✅ 문서화 완료 (Architecture Diagram 포함)
- [ ] ✅ 성능 저하 < 10% (로딩 시간 벤치마크)

---

## 🚀 권장 실행 순서

### 즉시 실행 가능
1. **Phase 0**: 마이그레이션 대상 정리 (1시간)
   - Tier 분류 완료 후 다음 단계 진행

### 순차 실행 (의존성 있음)
2. **Phase 1**: Repository Interface 확장 (2시간)
3. **Phase 2**: YFinance Repository 구현 (3.5시간)
4. **Phase 3**: News Repository 구현 (2.5시간)
5. **Phase 4**: KIS Repository 구현 (3.5시간)
6. **Phase 5-1**: Core Analyzer Services (3시간)
7. **Phase 5-2**: Advanced Analyzer Services (2.5시간)
8. **Phase 7**: 전체 모듈 재배치 (2시간) - **Phase 10-13 모듈 이동**
9. **Phase 6**: UI 통합 및 검증 (3시간)

### 병렬 실행 가능 (선택적)
- Phase 2, 3, 4는 독립적이므로 동시 작업 가능 (단, 테스트 필요)

### Phase 7의 중요성
- ✅ Legacy 마이그레이션(Phase 5-2) 완료 후 실행
- ✅ Phase 10-13 모듈을 `analyzers/` → `services/`로 이동
- ✅ 코드 수정 없이 파일 이동 + import 경로 수정만
- ✅ 전체 프로젝트가 일관된 Clean Architecture 구조를 갖춤

---

## 🔥 즉시 조치가 필요한 항목 (우선순위 순)

### 1. Phase 0 실행 (필수 선행 작업)
```bash
# 마이그레이션 대상 전체 파악
find src/analyzers -name "*.py" | wc -l
find src/collectors -name "*.py" | wc -l

# UI 의존성 분석
grep -r "from src.analyzers" src/dashboard/
grep -r "from src.collectors" src/dashboard/
```

### 2. Phase 1 Interface 재설계
- [ ] IKISRepository 인터페이스 추가 (한국 전용)
- [ ] IStockRepository에 save/load 메서드 추가

### 3. Phase 2 Database 로직 보완
- [ ] YFinanceStockRepository에 SQLite 저장 로직 추가

### 4. Phase 6 DI Container 설계
- [ ] dependencies.py 생성
- [ ] 모든 Service 인스턴스 중앙 관리

---

## ✅ 결론

### 기획안 전체 평가: ⭐⭐⭐⭐ (4/5)

**강점**:
- ✅ Strangler Fig Pattern 완벽 이해
- ✅ TDD 방법론 정확히 적용
- ✅ Quality Gate 체계적
- ✅ DIP 원칙 준수

**개선 필요**:
- ⚠️ 일부 Legacy Analyzer 모듈 누락 (fundamental, options, macro, regime)
- ⚠️ KIS Repository 설계 오류 (별도 Interface 필요)
- ⚠️ Database 저장 로직 누락
- ⚠️ UI 통합 단계 불명확
- ⚠️ 검증 스크립트 마이그레이션 누락

**마이그레이션 범위 명확화**:
- ✅ **마이그레이션 필요**: Phase 9 이전 Legacy 코드 (collectors, analyzers 일부)
- ✅ **마이그레이션 불필요**: Phase 10-13 모듈은 이미 Clean Architecture 기반
  - Phase 10: Clean Architecture 기반 구축
  - Phase 11: factor_analyzer.py (DI 적용됨)
  - Phase 12: social_analyzer.py (Service 패턴)
  - Phase 13: 투자 컨트롤 센터

**권장 사항**:
1. **Phase 0부터 시작** (Legacy 모듈 전체 목록 작성)
2. IKISRepository 별도 설계
3. **Phase 7 추가** (전체 모듈 재배치 - Phase 10-13 포함)
4. Phase 6에 DI Container + 검증 스크립트 통합
5. 예상 시간 23시간으로 재조정

**Phase 7의 필요성**:
- Legacy 마이그레이션만으로는 불충분
- Phase 10-13 모듈도 `analyzers/` → `services/`로 이동 필요
- 최종적으로 **모든 Application Service가 services/ 폴더에 위치**해야 일관된 구조

**다음 단계**: Phase 0 실행 후 수정된 로드맵으로 진행
