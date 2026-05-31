# ADR-001: 도메인 구조 — 바운디드 컨텍스트 방향 채택

- **상태**: 채택됨 (Active)
- **작성일**: 2026-05-31
- **관련 리뷰**: W3 (코드 리뷰 2026-05-31)

---

## 컨텍스트

현재 코드베이스에는 두 가지 도메인 구조가 공존합니다:

### 구조 A — 플랫(Flat) 엔티티 레이어

```
src/domain/entities/stock.py        (StockEntity, PortfolioEntity, SignalEntity)
src/domain/repositories/interfaces.py
src/domain/value_objects/
```

### 구조 B — 바운디드 컨텍스트

```
src/domain/market_buzz/entities/buzz_score.py
src/domain/market_buzz/entities/volume_anomaly.py
src/domain/market_buzz/value_objects/heat_level.py
src/domain/investment_profile/entities/investor_profile.py
src/domain/watchlist/entities/watchlist.py
src/domain/ai_report/entities/investment_report.py
src/domain/signal/entities/trading_signal.py
src/domain/chat/
src/domain/market_data/interfaces.py
src/domain/prediction/
src/domain/technical_indicators/
```

---

## 결정

**바운디드 컨텍스트(구조 B)로 통일한다.**

구조 A의 `src/domain/entities/stock.py`는 마이그레이션 완료 후 제거 대상이다.

---

## 근거

1. **DDD 전술 패턴 준수**: 바운디드 컨텍스트는 집합체(Aggregate), 엔티티, 값 객체, 리포지토리 인터페이스를 컨텍스트별로 캡슐화한다. 플랫 구조는 "God Entity"로 성장하는 경향이 있다.

2. **기존 신규 코드가 이미 구조 B를 따름**: `market_buzz`, `investment_profile`, `watchlist`, `ai_report`, `signal` 등 최근 도메인 코드는 모두 바운디드 컨텍스트 패턴을 사용한다.

3. **Strangler Fig 패턴과 정합성**: `LegacyCollectorAdapter`는 구조 A의 `StockEntity`를 사용하지만 레거시 인터페이스 뒤에 숨겨져 있다. 구조 B로의 전환이 완료되면 어댑터를 제거할 수 있다.

4. **테스트 가능성**: 바운디드 컨텍스트는 컨텍스트 경계에서 단위 테스트가 명확하다.

---

## 목표 아키텍처

```
src/
  domain/
    market_data/          ← OHLCV 데이터 컨텍스트 (인터페이스 + 값 객체)
    market_buzz/          ← 시장 화제성 컨텍스트
    investment_profile/   ← 투자 성향 컨텍스트
    watchlist/            ← 관심 종목 컨텍스트
    ai_report/            ← AI 분석 보고서 컨텍스트
    signal/               ← 매매 신호 컨텍스트
    chat/                 ← AI 채팅 컨텍스트
    prediction/           ← 가격 예측 값 객체
    technical_indicators/ ← 기술 지표 인터페이스
    # entities/ → 마이그레이션 완료 후 제거 예정
  application/            ← (현재 services/) 유스케이스 오케스트레이션
  infrastructure/         ← 게이트웨이, 리포지토리, 외부 연동
  presentation/           ← (현재 dashboard/) 얇은 Streamlit 뷰
  models/                 ← ML 아티팩트 (도메인 예측 인터페이스 뒤로)
```

---

## 마이그레이션 경로

| 단계 | 대상 | 방법 |
|------|------|------|
| 1 | `StockEntity` → `market_data` 컨텍스트 | `domain/market_data/` 하위로 이동 |
| 2 | `SignalEntity` → `signal` 컨텍스트 | `domain/signal/entities/`로 통합 |
| 3 | `PortfolioEntity` → `watchlist` 또는 새 `portfolio` 컨텍스트 | 신규 컨텍스트 생성 |
| 4 | `src/domain/entities/` 디렉터리 제거 | 모든 참조 이전 후 |
| 5 | `services/` → `application/` 리네임 | 선택적 (IDE 전체 치환) |

**주의**: 각 단계는 특성화 테스트(`tests/characterization/`) 녹색 상태를 유지하며 진행한다.

---

## 미채택 대안

- **구조 A 유지**: 기존 코드와의 하위 호환성이 높지만 장기적으로 God Entity 문제가 악화됨
- **레이어드 아키텍처로 회귀**: 단순하지만 도메인 격리가 불가능하고 테스트 어려움
- **마이크로서비스 분리**: 현재 단일 Streamlit 앱 규모에서 오버엔지니어링

---

## 결과

- `IStockDataGateway`, `IStockRepository`, `GatewayFactory`에 `@MX:ANCHOR` 태그 부여 (S5)
- 마이그레이션 진행 중인 이음새 코드는 `LegacyCollectorAdapter`로 캡슐화 유지
- 테스트는 `tests/characterization/`에서 세 핵심 이음새를 커버 (C1)
