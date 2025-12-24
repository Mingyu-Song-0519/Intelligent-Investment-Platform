# 📊 Phase 10+ 기능 개발 로드맵

> **작성일**: 2025-12-24  
> **기반**: Phase 9 완료 후 향후 개발 방향 수립  
> **아키텍처**: Clean Architecture 원칙 적용

---

## 🎯 현재 완료 상태

### ✅ Phase 9 완료 (2025-12-23)
| 단계 | 내용 | 상태 |
|------|------|------|
| 9-0 | VWAP, OBV, ADX 기술 지표 | ✅ |
| 9-1 | VIX, 시장 폭, 시장 체력 진단 탭 | ✅ |
| 9-2 | 옵션 P/C Ratio, IV, Max Pain | ✅ |
| 9-3 | 펀더멘털 PER, ROE, 배당 | ✅ |
| 9-4 | AI + 감성 분석 통합 | ✅ |
| 9-5 | 알림 시스템 (Email/Telegram) | ✅ |
| 9-6 | 매크로 금리, 달러, 원자재 | ✅ |

---

## 🏗️ Clean Architecture 구조

```
┌─────────────────────────────────────────────────────────────┐
│                    🖥️ Presentation Layer                     │
│  (UI, Controllers, ViewModels)                              │
│  src/dashboard/app.py, realtime_tab.py                     │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                    📦 Application Layer                      │
│  (Use Cases, Service Orchestration)                         │
│  src/services/ (NEW)                                        │
│  - trading_signal_service.py                                │
│  - portfolio_management_service.py                          │
│  - alert_orchestrator.py                                    │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                    🧠 Domain Layer                           │
│  (Business Logic, Entities, Value Objects)                  │
│  src/analyzers/ (기존)                                      │
│  src/models/ (기존)                                         │
│  src/domain/ (NEW)                                          │
│  - entities/stock.py, portfolio.py, signal.py              │
│  - value_objects/price.py, indicator.py                    │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                    💾 Infrastructure Layer                   │
│  (External APIs, DB, Cache, Notifications)                  │
│  src/collectors/ (기존)                                     │
│  src/infrastructure/ (NEW)                                  │
│  - repositories/stock_repository.py                        │
│  - external/kis_api.py, yfinance_gateway.py               │
│  - cache/redis_cache.py                                    │
└─────────────────────────────────────────────────────────────┘
```

---

## 🚀 Phase 10: 아키텍처 리팩토링

### 목표
현재 모놀리식 구조를 Clean Architecture로 전환하여 유지보수성 향상

### 10-0. 인터페이스 레이어 구축 ✅
- [x] `src/domain/entities/` - StockEntity, PortfolioEntity, SignalEntity
- [x] `src/domain/repositories/` - IStockRepository, IPortfolioRepository, INewsRepository
- [x] `src/infrastructure/repositories/` - YFinanceStockRepository
- [x] `src/infrastructure/adapters/` - LegacyCollectorAdapter, LegacyAnalyzerAdapter
- [x] `src/services/` - TradingSignalService, FactorScoringService
- [x] 검증 스크립트 (verify_phase10.py) 통과율 100%

### 10-1. Domain Layer 분리 ✅
- [x] StockEntity에 추가 비즈니스 로직 구현 (수익률, 변동성, 추세, MDD)
- [x] PortfolioEntity 영속화 연동 (JSONPortfolioRepository, SessionPortfolioRepository)

### 10-2. Application Layer (Use Cases) ✅
- [x] AlertOrchestratorService 추가
- [x] PortfolioManagementService 추가

### 10-3. Repository Pattern 적용 ✅
- [x] `portfolio_repository.py`: JSON/SQLite 저장

---

## 🚀 Phase 11: 멀티팩터 분석

### 목표
Fama-French 5팩터 모델 기반 종목 스코어링 시스템

### 11-1. FactorAnalyzer 모듈
```python
# src/analyzers/factor_analyzer.py
class FactorAnalyzer:
    - momentum_score()      # 12개월 수익률 기반
    - quality_score()       # ROE, 현금흐름 마진
    - value_score()         # PER, PBR 역수
    - size_score()          # 시가총액 팩터
    - volatility_score()    # 저변동성 팩터
    - composite_score()     # 종합 점수 (0-100)
```

### 11-2. 팩터 스코어보드 UI
- [ ] 새 탭: `🏆 팩터 스코어보드`
- [ ] 레이더 차트 시각화
- [ ] 종목 순위표 (팩터별 필터링)

---

## 🚀 Phase 12: 소셜 미디어 분석

### 목표
Reddit, Twitter 등 소셜 미디어에서 밈주식 트렌드 감지

### 12-1. SocialMediaCollector
- [ ] Reddit API 연동 (r/wallstreetbets)
- [ ] Twitter API 연동 (Cashtag 분석)
- [ ] 키워드 빈도 분석

### 12-2. 트렌드 감지 UI
- [ ] 새 탭: `🔥 소셜 트렌드`
- [ ] 급등 키워드 워드클라우드
- [ ] 밈주식 경고 시스템

---

## 🚀 Phase 13: 통합 대시보드 (투자 컨트롤 센터)

### 목표
모든 분석을 한눈에 볼 수 있는 메인 랜딩 페이지

### 13-1. 4분할 레이아웃
```
┌─────────────────┬─────────────────┐
│  📊 시장 체력    │  😱 변동성      │
│  (Breadth)      │  (VIX 스트레스) │
├─────────────────┼─────────────────┤
│  🏆 팩터 TOP 5   │  🌍 매크로 환경  │
│  (Best Stocks)  │  (금리/달러)    │
└─────────────────┴─────────────────┘
```

### 13-2. 색상 코드 시스템
- 🟢 안전: 투자 적극 가능
- 🟡 주의: 리스크 관리 필요
- 🔴 경고: 방어적 포지션 권장

---

## 🚀 Phase 14: 고급 AI 예측

### 목표
시장 상황별 적응형 AI 모델

### 14-1. Regime-Aware Training
- [ ] 저변동성/고변동성 구간 분류 모델
- [ ] 구간별 별도 LSTM/XGBoost 학습

### 14-2. 앙상블 고도화
- [ ] 감성 점수 + 기술 지표 + 팩터 스코어 통합 입력
- [ ] 시장 리짐(Regime)별 모델 가중치 동적 조절

---

## 🚀 Phase 15: 실시간 트레이딩 봇

### 목표
알림을 넘어 자동 매매 시스템 (선택적)

### 15-1. Trading Bot Framework
- [ ] 한국투자증권 API 자동 주문 연동
- [ ] 전략 기반 자동 매수/매도

### 15-2. 백테스트 → 실전 전환
- [ ] Paper Trading 모드 (모의 투자)
- [ ] Risk 한도 설정 (일일 최대 손실 등)

---

## 📋 우선순위 요약

| 우선순위 | Phase | 내용 | 예상 소요 |
|----------|-------|------|----------|
| 🔥 높음 | 10 | Clean Architecture 리팩토링 | 3-5일 |
| 🔥 높음 | 11 | 멀티팩터 분석 | 2-3일 |
| ⚡ 중간 | 12 | 소셜 미디어 분석 | 3-4일 |
| ⚡ 중간 | 13 | 투자 컨트롤 센터 | 2-3일 |
| 💡 낮음 | 14 | 고급 AI 예측 | 4-5일 |
| 💡 낮음 | 15 | 트레이딩 봇 | 5-7일 |

---

## 📁 신규 디렉토리 구조 (예정)

```
src/
├── domain/                    # [NEW] 도메인 레이어
│   ├── entities/
│   │   ├── stock.py
│   │   ├── portfolio.py
│   │   └── signal.py
│   └── value_objects/
│       ├── price.py
│       └── indicator.py
│
├── services/                  # [NEW] 애플리케이션 레이어
│   ├── trading_signal_service.py
│   ├── portfolio_management_service.py
│   └── alert_orchestrator.py
│
├── infrastructure/            # [NEW] 인프라 레이어
│   ├── repositories/
│   │   └── stock_repository.py
│   ├── external/
│   │   └── yfinance_gateway.py
│   └── cache/
│       └── memory_cache.py
│
├── analyzers/                 # [기존] 도메인 로직
│   ├── factor_analyzer.py     # [NEW]
│   └── social_analyzer.py     # [NEW]
│
└── collectors/                # [기존] 데이터 수집
    └── social_collector.py    # [NEW]
```

---

## 🔍 기획안 검토 결과 (2025-12-24)

> **검토자**: Claude Code (Clean Architecture 원칙 기반)
> **검토 방법**: Feature Planner Skill + Dependency Inversion Principle 적용

---

## ⚠️ 개선이 필요한 사항

### 1. Phase 10: 아키텍처 리팩토링 리스크 관리

**문제점**: 대규모 리팩토링은 기존 기능의 동작을 보장하기 어렵고, 회귀 버그 발생 가능성 높음

**해결 방안: Strangler Fig Pattern 적용**

```
┌────────────────────────────────────────────────────────────┐
│  Phase 10-0: 점진적 마이그레이션 전략                       │
└────────────────────────────────────────────────────────────┘

1단계: Interface 레이어 구축 (1-2일)
  - [ ] src/domain/repositories/interfaces/ 생성
  - [ ] IStockRepository, IPortfolioRepository 인터페이스 정의
  - [ ] 기존 코드는 그대로 유지

2단계: Adapter 패턴으로 기존 코드 래핑 (2-3일)
  - [ ] src/infrastructure/adapters/ 생성
  - [ ] LegacyCollectorAdapter: 기존 collectors/ → IStockRepository
  - [ ] LegacyAnalyzerAdapter: 기존 analyzers/ → Domain Service
  - [ ] 양방향 호환성 유지 (새 코드 ↔ 구 코드)

3단계: 점진적 전환 (3-4일)
  - [ ] 새 기능은 Clean Architecture로 개발
  - [ ] 기존 기능은 Adapter를 통해 접근
  - [ ] E2E 테스트로 동작 검증

4단계: 레거시 제거 (1-2일)
  - [ ] 모든 기능이 신규 구조로 전환 완료 후
  - [ ] Adapter 제거 및 레거시 코드 삭제
  - [ ] 최종 통합 테스트

📌 총 소요 기간: 7-11일 (기존 3-5일 → 수정)
```

---

### 2. 의존성 역전 원칙(DIP) 명시

**현재 문제**: 도메인 레이어가 인프라 레이어를 직접 참조할 위험

**Clean Architecture 핵심 규칙**:
```
Infrastructure → Domain (❌ 금지)
Domain → Infrastructure (✅ 허용, 단 인터페이스를 통해서만)
```

**구체적 구현 예시**:

```python
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# src/domain/repositories/stock_repository_interface.py
# (Domain Layer - 추상화)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
from abc import ABC, abstractmethod
from src.domain.entities.stock import StockEntity

class IStockRepository(ABC):
    """종목 데이터 저장/조회 인터페이스 (도메인 레이어)"""

    @abstractmethod
    def get_stock_data(self, ticker: str, period: str) -> StockEntity:
        """종목 데이터 조회 (구현체는 Infrastructure에서)"""
        pass

    @abstractmethod
    def save_stock_data(self, stock: StockEntity) -> bool:
        """종목 데이터 저장"""
        pass


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# src/infrastructure/repositories/yfinance_stock_repository.py
# (Infrastructure Layer - 구현체)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
import yfinance as yf
from src.domain.repositories.stock_repository_interface import IStockRepository
from src.domain.entities.stock import StockEntity

class YFinanceStockRepository(IStockRepository):
    """yfinance API를 이용한 구현체"""

    def get_stock_data(self, ticker: str, period: str) -> StockEntity:
        ticker_obj = yf.Ticker(ticker)
        df = ticker_obj.history(period=period)
        return StockEntity.from_dataframe(ticker, df)

    def save_stock_data(self, stock: StockEntity) -> bool:
        # 캐시나 DB에 저장 로직
        pass


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# src/services/trading_signal_service.py
# (Application Layer - 유즈케이스)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
from src.domain.repositories.stock_repository_interface import IStockRepository

class TradingSignalService:
    """매매 신호 생성 유즈케이스"""

    def __init__(self, stock_repo: IStockRepository):
        # ✅ 인터페이스만 의존 (구체적인 구현체 모름)
        self.stock_repo = stock_repo

    def generate_signal(self, ticker: str):
        stock = self.stock_repo.get_stock_data(ticker, "1mo")
        # 신호 생성 로직...


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# src/dashboard/app.py (Presentation Layer)
# Dependency Injection 적용
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
from src.infrastructure.repositories.yfinance_stock_repository import YFinanceStockRepository
from src.services.trading_signal_service import TradingSignalService

# DI Container (수동)
stock_repo = YFinanceStockRepository()
signal_service = TradingSignalService(stock_repo)

signal = signal_service.generate_signal("AAPL")
```

**핵심 포인트**:
- ✅ `TradingSignalService`는 `IStockRepository` 인터페이스만 알고 있음
- ✅ `YFinanceStockRepository`는 언제든지 `KISStockRepository`로 교체 가능
- ✅ 테스트 시 `MockStockRepository` 주입 가능

---

### 3. Phase 11: 데이터 출처 명확화

**문제점**: 한국 주식의 ROE, 현금흐름 데이터 출처 불명확

**해결 방안**:

#### 11-0. 데이터 소스 전략 (선행 작업)
```
┌─────────────────────────────────────────────────┐
│  미국 주식 (✅ 즉시 가능)                        │
├─────────────────────────────────────────────────┤
│  - yfinance API (info.trailingPE, info.roe)     │
│  - Alpha Vantage (fundamentals)                 │
│  - 데이터 품질: ⭐⭐⭐⭐⭐                         │
└─────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────┐
│  한국 주식 (⚠️ 제한적)                           │
├─────────────────────────────────────────────────┤
│  - DART Open API (공시 데이터, 재무제표)        │
│  - FinanceDataReader (제한적 fundamental)       │
│  - 네이버 증권 크롤링 (법적 리스크 검토 필요)   │
│  - 데이터 품질: ⭐⭐⭐☆☆                         │
└─────────────────────────────────────────────────┘

📌 Phase 11 1차 목표: 미국 주식만 적용
📌 Phase 11 2차 목표: DART API 연동 후 한국 주식 확장
```

#### 수정된 Phase 11-1
```python
# src/analyzers/factor_analyzer.py
class FactorAnalyzer:
    """Fama-French 5팩터 + 추가 팩터 분석"""

    def __init__(self, market: str = 'US'):
        """
        Args:
            market: 'US' (미국 주식) 또는 'KR' (한국 주식)
        """
        self.market = market

    def momentum_score(self, df: pd.DataFrame) -> float:
        """12개월 수익률 기반 모멘텀 팩터 (0-100)"""
        # US/KR 공통 적용 가능
        pass

    def quality_score(self, ticker: str) -> float:
        """품질 팩터 (ROE, 영업현금흐름)"""
        if self.market == 'US':
            # yfinance에서 ROE, FCF 추출
            pass
        elif self.market == 'KR':
            # DART API 또는 FinanceDataReader 사용
            # ⚠️ 데이터 없을 경우 None 반환
            pass

    def value_score(self, ticker: str) -> float:
        """가치 팩터 (PER, PBR 역수)"""
        # US: yfinance, KR: FinanceDataReader
        pass
```

---

### 4. Phase 12: API 비용 및 대안 검토

**문제점**: Reddit API, Twitter API 2023년부터 유료화

**API 비용 현황**:
| API | 무료 플랜 | 유료 플랜 | 비고 |
|-----|----------|----------|------|
| Reddit API | ❌ 제한 | $0.24/1000 requests | 2023년 7월 유료화 |
| Twitter API | ❌ 중단 | $100/월 (Basic) | 2023년 2월 유료화 |
| Google Trends | ✅ 무료 | - | 키워드 트렌드만 |

**수정된 Phase 12 계획**:

#### 12-0. 무료 대안 전략
```
- [ ] Pushshift API (Reddit 아카이브)
  - 과거 데이터 무료 제공 (실시간 X)
  - r/wallstreetbets 히스토리 분석 가능

- [ ] Google Trends API
  - 종목 티커 검색량 추적
  - 관련 키워드 트렌드 분석

- [ ] 한국 커뮤니티 크롤링
  - 네이버 증권 토론방 (robots.txt 확인 필수)
  - 디시인사이드 주식 갤러리
  - ⚠️ 법적 리스크: 이용약관 검토 필요
```

#### 12-1. SocialTrendAnalyzer (수정)
```python
# src/analyzers/social_analyzer.py
class SocialTrendAnalyzer:
    """소셜 미디어 트렌드 분석 (무료 데이터 소스)"""

    def __init__(self, source: str = 'google_trends'):
        """
        Args:
            source: 'google_trends', 'pushshift', 'naver'
        """
        self.source = source

    def get_keyword_trend(self, ticker: str, days: int = 30):
        """키워드 검색량 트렌드"""
        if self.source == 'google_trends':
            # pytrends 라이브러리 사용
            pass
        elif self.source == 'pushshift':
            # Reddit 히스토리 분석
            pass

    def detect_meme_stock(self, threshold: float = 2.0):
        """급등 키워드 감지 (평소 대비 2배 이상)"""
        pass
```

---

### 5. Phase 15: 법적/기술적 리스크 관리

**문제점**: 자동 매매는 법적 책임, 기술적 장애, 사용자 오해 리스크 존재

**필수 사전 작업: Phase 15-0**

```
┌────────────────────────────────────────────────────────────┐
│  Phase 15-0: 자동매매 사전 준비 (필수)                     │
└────────────────────────────────────────────────────────────┘

법적 준비 (1-2일)
  - [ ] 한국투자증권 OpenAPI 이용약관 검토
    - 자동매매 허용 범위 확인
    - API 호출 제한 (초당 요청 수, 일일 한도)
  - [ ] 금융투자업 관련 법규 검토
    - 투자 권유/자문 해당 여부 확인
  - [ ] 면책 조항 작성
    - "본 시스템은 투자 조언이 아니며, 손실 책임은 사용자에게 있음"

기술적 안전장치 (2-3일)
  - [ ] Kill Switch (긴급 정지 버튼)
    - Streamlit UI에 대형 빨간 버튼 배치
    - 모든 진행 중인 주문 즉시 취소
  - [ ] Circuit Breaker (자동 차단)
    - 일일 손실 한도 초과 시 자동 중지
    - 연속 실패 3회 시 알림 + 중지
  - [ ] 로깅 및 감사 추적
    - 모든 주문 기록 DB 저장
    - 사용자가 언제든 확인 가능
  - [ ] 네트워크 재시도 로직
    - API 실패 시 3회 재시도
    - 타임아웃 10초 설정

사용자 교육 (1일)
  - [ ] 초보자 가이드 작성
    - "Paper Trading으로 먼저 테스트하세요"
    - "소액으로 시작하세요"
  - [ ] 동의 체크박스 (3단계)
    1. "자동매매 리스크를 이해했습니다"
    2. "손실 발생 시 책임은 저에게 있습니다"
    3. "긴급 정지 버튼 위치를 확인했습니다"

📌 총 소요 기간: 4-6일 (기존 5-7일에 추가)
```

---

## 📋 수정된 우선순위 및 일정

| 우선순위 | Phase | 내용 | 기존 예상 | **수정 예상** | 변경 사유 |
|----------|-------|------|----------|--------------|----------|
| 🔥 높음 | 10 | Clean Architecture 리팩토링 | 3-5일 | **7-11일** | Strangler Fig Pattern 적용, 점진적 마이그레이션 |
| 🔥 높음 | 11 | 멀티팩터 분석 | 2-3일 | **4-6일** | DART API 연동, 데이터 정제 작업 추가 |
| ⚡ 중간 | 12 | 소셜 미디어 분석 | 3-4일 | **3-4일** | 무료 API로 전환 (유지) |
| ⚡ 중간 | 13 | 투자 컨트롤 센터 | 2-3일 | **2-3일** | 변경 없음 |
| 💡 낮음 | 14 | 고급 AI 예측 | 4-5일 | **4-5일** | 변경 없음 |
| 💡 낮음 | 15 | 트레이딩 봇 | 5-7일 | **10-14일** | 법적 검토, 안전장치 개발 추가 |

---

## 🚀 추가 제안 Phase

### Phase 16: 사용자 커스터마이징

**목표**: 사용자별 맞춤형 대시보드 (Netflix 스타일)

```
┌────────────────────────────────────────────────────────────┐
│  16-1. 위젯 시스템                                          │
└────────────────────────────────────────────────────────────┘

- [ ] 드래그 앤 드롭 레이아웃 (Streamlit-AgGrid 활용)
- [ ] 위젯 라이브러리
  - 📊 차트 위젯 (캔들스틱, 라인, 히트맵)
  - 🏆 팩터 스코어보드 위젯
  - 🔔 알림 피드 위젯
  - 📰 뉴스 감성 위젯
- [ ] 레이아웃 저장/불러오기 (JSON 파일)
  - 예: my_dashboard_layout.json

┌────────────────────────────────────────────────────────────┐
│  16-2. 테마 시스템                                          │
└────────────────────────────────────────────────────────────┘

- [ ] 다크 모드 / 라이트 모드 토글
- [ ] 색상 팔레트 커스터마이징
  - 상승: 빨강 vs 파랑 (미국/한국 스타일)
  - 차트 배경색, 폰트 크기

📌 예상 소요: 3-4일
```

---

### Phase 17: 모바일 반응형 UI

**목표**: 스마트폰에서도 쾌적한 사용 경험

**현재 문제점**: Streamlit은 모바일 최적화 부족
- 작은 화면에서 차트 겹침
- 터치 제스처 미지원

**해결 방안**:

#### 17-1. Streamlit + Custom CSS (단기)
```python
# src/dashboard/mobile_styles.py
def inject_mobile_css():
    st.markdown("""
    <style>
    @media (max-width: 768px) {
        .stPlotlyChart {
            height: 300px !important;
        }
        .stDataFrame {
            font-size: 12px;
        }
    }
    </style>
    """, unsafe_allow_html=True)
```

#### 17-2. React + FastAPI (장기)
```
Frontend: React Native (iOS/Android 앱)
Backend: FastAPI (RESTful API)
WebSocket: 실시간 알림

📌 예상 소요: 10-14일 (별도 프로젝트 레벨)
```

---

## 📁 최종 디렉토리 구조 (DIP 적용)

```
src/
├── domain/                           # 🧠 Domain Layer (핵심 비즈니스 로직)
│   ├── entities/
│   │   ├── stock.py                  # StockEntity (ticker, name, price)
│   │   ├── portfolio.py              # PortfolioEntity (holdings, cash)
│   │   └── signal.py                 # SignalEntity (BUY/SELL/HOLD)
│   │
│   ├── value_objects/
│   │   ├── price.py                  # PriceVO (open, high, low, close)
│   │   └── indicator.py              # IndicatorVO (RSI, MACD 값)
│   │
│   └── repositories/                 # ⚡ 인터페이스 (추상화)
│       ├── stock_repository_interface.py       # IStockRepository
│       ├── portfolio_repository_interface.py   # IPortfolioRepository
│       └── news_repository_interface.py        # INewsRepository
│
├── services/                         # 📦 Application Layer (유즈케이스)
│   ├── trading_signal_service.py     # 매매 신호 생성 유즈케이스
│   ├── portfolio_management_service.py  # 포트폴리오 관리
│   ├── alert_orchestrator.py         # 알림 발송 오케스트레이션
│   └── factor_scoring_service.py     # [NEW] 멀티팩터 스코어링
│
├── infrastructure/                   # 💾 Infrastructure Layer (구현체)
│   ├── repositories/                 # Repository 구현체
│   │   ├── yfinance_stock_repository.py      # yfinance 구현
│   │   ├── kis_stock_repository.py           # 한국투자증권 API
│   │   └── json_portfolio_repository.py      # JSON 파일 저장
│   │
│   ├── external/                     # 외부 API Gateway
│   │   ├── yfinance_gateway.py
│   │   ├── dart_gateway.py           # [NEW] DART Open API
│   │   └── google_trends_gateway.py  # [NEW] Google Trends
│   │
│   ├── cache/
│   │   └── memory_cache.py           # In-Memory 캐시
│   │
│   └── adapters/                     # [NEW] Strangler Fig Adapter
│       ├── legacy_collector_adapter.py   # 기존 collectors/ 래핑
│       └── legacy_analyzer_adapter.py    # 기존 analyzers/ 래핑
│
├── analyzers/                        # [기존] 도메인 로직 (점진적 이동 예정)
│   ├── technical_analyzer.py         # ✅ 유지
│   ├── factor_analyzer.py            # [NEW] 멀티팩터 분석
│   └── social_analyzer.py            # [NEW] 소셜 트렌드
│
├── collectors/                       # [기존] 데이터 수집 (점진적 이동 예정)
│   └── social_collector.py           # [NEW]
│
└── dashboard/                        # 🖥️ Presentation Layer (UI)
    ├── app.py                        # Main Streamlit App
    ├── pages/
    │   ├── factor_scoreboard.py      # [NEW] 팩터 스코어보드
    │   └── social_trends.py          # [NEW] 소셜 트렌드
    └── components/
        ├── widget_system.py          # [NEW] 위젯 시스템
        └── mobile_styles.py          # [NEW] 모바일 CSS
```

**핵심 변경 사항**:
1. ✅ `domain/repositories/` - 인터페이스만 정의 (DIP 원칙)
2. ✅ `infrastructure/adapters/` - 레거시 코드 래핑 (Strangler Fig)
3. ✅ `infrastructure/external/` - DART, Google Trends 추가
4. ✅ `services/` - 유즈케이스 레이어 명확화

---

## 🎯 권장 실행 순서 (수정)

### 즉시 실행 가능 (Phase 9 완료 상태)
1. **Phase 11 (멀티팩터 분석)** - 독립적 기능, Clean Architecture 미적용 가능
2. **Phase 13 (투자 컨트롤 센터)** - 기존 지표 통합만으로 구현 가능

### 별도 브랜치에서 진행
3. **Phase 10 (Clean Architecture)** - `feature/clean-architecture` 브랜치
   - Strangler Fig Pattern으로 점진적 전환
   - 매주 main 브랜치와 동기화

### 사전 검토 후 진행
4. **Phase 12 (소셜 미디어)** - API 비용/법적 리스크 확인 후
5. **Phase 15 (트레이딩 봇)** - 법률 자문 후

### 선택적 진행
6. **Phase 16 (커스터마이징)** - 사용자 피드백 후
7. **Phase 17 (모바일)** - React 별도 프로젝트

---

## ✅ 다음 단계 제안

### 옵션 A: 빠른 성과 우선 (추천)
```
1. Phase 11 (멀티팩터) 먼저 구현 (4-6일)
   → 사용자에게 즉시 가치 제공
2. Phase 13 (대시보드) 통합 (2-3일)
   → Phase 11 결과를 시각화
3. Phase 10 (리팩토링) 병행 진행
   → 별도 브랜치에서 점진적 작업
```

### 옵션 B: 기반 구축 우선 (안정적)
```
1. Phase 10 (Clean Architecture) 먼저 완료 (7-11일)
   → Strangler Fig로 안전하게 전환
2. Phase 11, 12, 13을 새 구조에서 개발
   → 처음부터 깔끔한 아키텍처
```

### 옵션 C: 하이브리드 (균형)
```
1. Phase 10-0 (인터페이스 정의) 먼저 (1-2일)
2. Phase 11을 새 인터페이스로 개발 (4-6일)
3. Phase 10 나머지 작업 (5-7일)
```

**추천**: **옵션 C (하이브리드)** - 빠른 성과 + 깔끔한 구조

---

**다음 단계**: 어떤 옵션을 선택하시겠습니까?
- [ ] 옵션 A: Phase 11 먼저 구현
- [ ] 옵션 B: Phase 10 먼저 완료
- [ ] 옵션 C: 하이브리드 (추천)
