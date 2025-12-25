# Phase 9-13 종합 검증 프로토콜

**작성일**: 2024-12-24
**버전**: 1.0
**대상**: Phase 9 (Legacy + CA), Phase 10 (CA Foundation), Phase 11 (Factors), Phase 12 (Social), Phase 13 (Dashboard)
**목적**: 전체 시스템의 기능적 정확성, 아키텍처 준수, 성능, 안정성 검증

---

## 📋 목차

1. [검증 체계 개요](#1-검증-체계-개요)
2. [Level 1: 단위 검증](#2-level-1-단위-검증-unit-verification)
3. [Level 2: 통합 검증](#3-level-2-통합-검증-integration-verification)
4. [Level 3: 아키텍처 준수 검증](#4-level-3-아키텍처-준수-검증)
5. [Level 4: E2E 검증](#5-level-4-e2e-검증-end-to-end-scenarios)
6. [Level 5: 성능 및 안정성](#6-level-5-성능-및-안정성-검증)
7. [통합 검증 스크립트](#7-통합-검증-스크립트-verify_allpy)
8. [성공 기준](#8-성공-기준-success-criteria)
9. [CI/CD 통합](#9-cicd-통합)
10. [검증 체크리스트](#10-검증-체크리스트-실행-시-사용)

---

## 1. 검증 체계 개요

### 1.1 검증 계층 구조

```
Level 1: Unit Verification (단위 검증)
   └─> 개별 모듈/클래스 기능 검증
   └─> 비즈니스 로직 정확성

Level 2: Integration Verification (통합 검증)
   └─> Repository ↔ Service 상호작용
   └─> Service ↔ UI 데이터 흐름
   └─> Phase 간 의존성 검증

Level 3: Architecture Compliance (아키텍처 검증)
   └─> Clean Architecture Layer 분리
   └─> DIP (Dependency Inversion Principle)
   └─> Strangler Fig Pattern 적용

Level 4: E2E Verification (종단간 검증)
   └─> 실제 사용자 시나리오
   └─> UI → Service → Repository → External API

Level 5: Performance & Reliability (성능/안정성)
   └─> API 호출 최적화
   └─> 캐싱 효율성
   └─> 에러 핸들링
```

### 1.2 검증 원칙

1. **독립성**: 각 Phase는 독립적으로 검증 가능해야 함
2. **재현성**: 모든 테스트는 동일한 조건에서 재현 가능해야 함
3. **자동화**: 수동 개입 없이 스크립트로 실행 가능해야 함
4. **명확한 성공 기준**: Pass/Fail이 명확히 구분되어야 함
5. **빠른 피드백**: 전체 검증은 10분 이내 완료

---

## 2. Level 1: 단위 검증 (Unit Verification)

### 2.1 Phase 9 검증 (Legacy Features)

#### 2.1.1 기술적 지표 (Technical Indicators)

**검증 대상**: `src/analyzers/technical_analyzer.py`

**테스트 항목**:
```python
# verify_phase9.py 기반
1. VWAP 계산 정확성
   - 입력: 100일 OHLCV 데이터
   - 검증: vwap = sum(typical_price * volume) / sum(volume)
   - 성공 기준: 계산값이 수식과 일치 (오차 < 0.01%)

2. OBV (On-Balance Volume) 누적 정확성
   - 입력: 가격 상승/하락 패턴
   - 검증: 상승일 volume 누적, 하락일 volume 차감
   - 성공 기준: 단조증가/감소 패턴 검증

3. ADX (Average Directional Index) 계산
   - 입력: 14일 high/low 데이터
   - 검증: ADX ∈ [0, 100]
   - 성공 기준: 값 범위 준수, NaN 처리 정상
```

**실행 명령**:
```bash
python verify_phase9.py --focus technical_analyzer
```

**성공 기준**: 3/3 tests pass

---

#### 2.1.2 변동성 분석 (Volatility)

**검증 대상**: `src/analyzers/volatility_analyzer.py`

**테스트 항목**:
```python
1. VIX 데이터 수집
   - 수집: ^VIX 심볼로 yfinance 조회
   - 검증: 최신 종가 획득
   - 성공 기준: 값 ∈ [10, 80] (역사적 범위)

2. 변동성 구간 분류
   - 입력: VIX 값 (예: 15, 25, 35, 50)
   - 예상 출력: ("안정", "green"), ("주의", "yellow"), ("공포", "red"), ("극공포", "purple")
   - 성공 기준: 색상 코드 정확 매핑

3. 역사적 백분위 계산
   - 입력: 현재 VIX + 과거 1년 데이터
   - 계산: percentile(current, historical)
   - 성공 기준: 백분위 ∈ [0, 100]
```

**Mock 전략**:
- Network 없이 테스트 가능하도록 yfinance 응답 mocking
- `@pytest.mark.network` 데코레이터로 실제 API 테스트 분리

**성공 기준**: 3/3 tests pass (mock), 2/3 tests pass (network, VIX 수집 제외 가능)

---

#### 2.1.3 시장 폭 분석 (Market Breadth)

**검증 대상**: `src/analyzers/market_breadth.py`

**테스트 항목**:
```python
1. A/D Ratio 계산
   - 입력: S&P 500 종목 리스트 (샘플 50개)
   - 수집: 각 종목 1일 수익률
   - 계산: advancing / (advancing + declining)
   - 성공 기준: 비율 ∈ [0, 1], 상태 ("강세"/"약세"/"중립")

2. 52주 신고가/신저가 비율
   - 입력: 50개 종목 52주 데이터
   - 계산: 신고가 종목 수 / 전체
   - 성공 기준: 비율 ∈ [0, 1]

3. 시장 집중도 (Top 10 시가총액 비중)
   - 입력: 50개 종목 시가총액
   - 계산: sum(top10_cap) / sum(total_cap)
   - 성공 기준: 비율 > 0.5 (S&P 500 특성)
```

**Performance 요구사항**:
- 50개 종목 분석 < 30초 (병렬 처리)
- 캐싱 사용 시 < 5초

**성공 기준**: 3/3 tests pass, 성능 기준 충족

---

#### 2.1.4 초보자 힌트 시스템

**검증 대상**: `src/utils/hints.py`

**테스트 항목**:
```python
1. INDICATOR_HINTS 데이터 무결성
   - 검증: 모든 힌트에 'short', 'detail' 키 존재
   - 검증: 한글 인코딩 정상 (UTF-8)
   - 성공 기준: 6개 지표 (RSI, MACD, ADX, VWAP, VIX, Breadth) 설명 존재

2. get_hint_text() 함수
   - 입력: ("RSI", "short"), ("MACD", "detail")
   - 출력: 해당 힌트 텍스트
   - 성공 기준: 예외 없이 문자열 반환, "과열"/"추세" 키워드 포함
```

**성공 기준**: 2/2 tests pass

---

### 2.2 Phase 10 검증 (Clean Architecture Foundation)

#### 2.2.1 Domain Layer

**검증 대상**: `src/domain/entities/stock.py`

**테스트 항목**:
```python
1. StockEntity 비즈니스 로직
   - get_price_range(days=5): 5일 고가/저가
   - calculate_return(days=10): 10일 수익률
   - calculate_volatility(days=20): 20일 변동성 (표준편차)
   - is_trending_up(short=5, long=20): MA 교차 확인
   - get_max_drawdown(): MDD 계산

   성공 기준:
   - 수익률 계산: (latest_close - past_close) / past_close * 100
   - 변동성: std(returns) * sqrt(252) (연율화)
   - MDD: max(0, max(cummax(price) - price) / cummax(price))
   - 모든 계산 오차 < 0.01%

2. PriceData Value Object
   - typical_price: (high + low + close) / 3
   - is_bullish: close > open

   성공 기준: 속성 값 정확성

3. PortfolioEntity 비중 관리
   - add_holding("AAPL", 0.6): 종목 추가
   - total_weight 검증: sum(weights) == 1.0
   - rebalance() 기능: 목표 비중으로 조정

   성공 기준: 비중 합 1.0 유지
```

**실행 명령**:
```bash
python verify_phase10.py --focus domain_layer
```

**성공 기준**: 8/8 tests pass

---

#### 2.2.2 Repository Pattern

**검증 대상**: `src/infrastructure/repositories/`

**테스트 항목**:
```python
1. YFinanceStockRepository (IStockRepository 구현체)
   - get_stock_data("AAPL", "1mo"): StockEntity 반환
   - get_multiple_stocks(["AAPL", "MSFT"]): Dict[str, StockEntity]
   - get_stock_info("AAPL"): 종목 기본 정보 (sector, market_cap)

   성공 기준:
   - StockEntity.price_history 비어있지 않음
   - market 필드 정확 ("US")
   - 에러 시 None 반환 (예외 발생 안 함)

2. JSONPortfolioRepository (IPortfolioRepository 구현체)
   - save(portfolio): JSON 파일 저장
   - load(portfolio_id): JSON → PortfolioEntity
   - list_all(): 모든 포트폴리오 목록
   - delete(portfolio_id): 파일 삭제

   성공 기준:
   - 저장/로드 데이터 일치
   - 존재하지 않는 ID 조회 시 None
   - list_all() 성능 < 1초

3. SessionPortfolioRepository (Streamlit session_state)
   - save(): st.session_state에 저장
   - load(): session_state에서 로드

   성공 기준: 세션 내 데이터 유지
```

**Mock 전략**:
- yfinance API → `responses` 라이브러리로 mock
- 파일 시스템 → `pytest.tmpdir` 사용

**성공 기준**: 8/8 tests pass

---

#### 2.2.3 Application Services

**검증 대상**: `src/services/`

**테스트 항목**:
```python
1. PortfolioManagementService
   - create_portfolio(id, name, holdings): 포트폴리오 생성
   - calculate_portfolio_return(id, period): 수익률 계산
   - calculate_portfolio_risk(id, period): 변동성, Sharpe Ratio
   - suggest_rebalancing(id, target_weights): 리밸런싱 액션 제안

   성공 기준:
   - DI: IPortfolioRepository, IStockRepository 주입
   - 수익률 = weighted_sum(각 종목 수익률 * 비중)
   - Sharpe Ratio = (return - risk_free_rate) / volatility

2. AlertOrchestratorService
   - check_and_alert_vix(): VIX 스파이크 감지
   - check_and_alert_portfolio_mdd(ticker, threshold): MDD 임계값 초과
   - batch_check_watchlist(tickers): 일괄 체크

   성공 기준:
   - DI: IStockRepository, NotificationManager 주입
   - VIX > threshold → Alert 생성
   - MDD > threshold → Alert 생성
```

**실행 명령**:
```bash
python verify_phase10.py --focus services
```

**성공 기준**: 6/6 tests pass

---

### 2.3 Phase 11 검증 (Factor Analysis)

#### 2.3.1 팩터 분석 로직

**검증 대상**: `src/analyzers/factor_analyzer.py`

**테스트 항목**:
```python
1. FactorAnalyzer.analyze(stock, stock_info)
   - Momentum Factor: 12개월 수익률
   - Value Factor: P/E, P/B 기반
   - Quality Factor: ROE, ROA 기반
   - Size Factor: log(market_cap)
   - Volatility Factor: 1 / std(returns)

   성공 기준:
   - 모든 팩터 점수 ∈ [0, 100]
   - composite = weighted_sum(각 팩터 * 가중치)
   - 가중치 합 = 1.0

2. FactorScreener.screen_top_stocks(tickers, top_n, sort_by)
   - 입력: ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]
   - 정렬: composite 점수 기준
   - 출력: top_n개 FactorScores

   성공 기준:
   - 정렬 순서 정확 (내림차순)
   - DI: IStockRepository 주입

3. 커스텀 가중치 시스템
   - set_custom_weights({"momentum": 0.4, ...})
   - 검증: 가중치 합 != 1.0 → ValueError

   성공 기준: 입력 검증 정상
```

**실행 명령**:
```bash
python verify_phase11.py
```

**성공 기준**: 12/12 tests pass

---

### 2.4 Phase 12 검증 (Social Trends)

#### 2.4.1 Google Trends 분석

**검증 대상**: `src/analyzers/social_analyzer.py`

**테스트 항목**:
```python
1. GoogleTrendsAnalyzer.get_trend(keyword, timeframe)
   - 입력: "Tesla", "today 1-m"
   - 출력: TrendData (current_interest, avg, peak, direction, spike)

   성공 기준:
   - current_interest ∈ [0, 100]
   - trend_direction ∈ ["UP", "DOWN", "STABLE"]
   - spike_detected: current > avg * 2.0

2. SocialTrendAnalyzer.analyze_stock_buzz(ticker, name)
   - 입력: "TSLA", "Tesla"
   - 출력: {"alert_level": "HIGH/MEDIUM/LOW", "description": ...}

   성공 기준:
   - alert_level 기준: HIGH (spike), MEDIUM (관심 > 평균), LOW (정상)

3. detect_meme_stocks(watchlist, threshold)
   - 입력: ["GME", "AMC", "TSLA"], threshold=2.0
   - 출력: 스파이크 감지된 종목 리스트

   성공 기준: interest > avg * threshold
```

**Rate Limit 대응**:
- Google Trends API: 요청 간 2초 대기
- 테스트 시 Mock 데이터 사용 권장

**성공 기준**: 9/9 tests pass (or 6/9 with network issues)

---

#### 2.4.2 캐싱 시스템

**검증 대상**: `src/analyzers/social_analyzer.py` (TrendCache)

**테스트 항목**:
```python
1. TrendCache.set(key, value, ttl_minutes)
   - 저장: "TSLA" → TrendData
   - 검증: get("TSLA") == 저장한 데이터

2. TTL (Time To Live) 만료
   - 저장: ttl_minutes=1
   - 대기: 61초
   - 검증: get("TSLA") == None

3. clear() 초기화
   - 저장: 10개 키
   - clear()
   - 검증: 모든 get() == None
```

**성공 기준**: 3/3 tests pass

---

### 2.5 Phase 13 검증 (Dashboard Integration)

#### 2.5.1 컨트롤 센터 통합

**검증 대상**: `src/dashboard/control_center.py`

**테스트 항목**:
```python
1. render_market_health() 컴포넌트
   - 입력: MarketBreadthAnalyzer 결과
   - 출력: Streamlit UI 렌더링
   - 검증: st.metric(), st.progress() 호출 확인

2. render_volatility_stress() 컴포넌트
   - 입력: VolatilityAnalyzer 결과
   - 출력: VIX 게이지, 색상 코드
   - 검증: st.plotly_chart() 호출

3. render_factor_top5() 컴포넌트
   - 입력: FactorScreener.screen_top_stocks() 결과
   - 출력: 상위 5개 종목 테이블
   - 검증: st.dataframe() 호출

4. render_macro_summary() 컴포넌트
   - 입력: MacroAnalyzer 결과
   - 출력: 10년물 국채, DXY, 유가 표시
   - 검증: st.columns() 레이아웃
```

**UI 테스트 전략**:
- `streamlit.testing` 프레임워크 사용
- 또는 함수 호출만 검증 (렌더링 결과는 수동 확인)

**성공 기준**: 4/4 component functions callable without errors

---

## 3. Level 2: 통합 검증 (Integration Verification)

### 3.1 Repository ↔ Service 통합

**시나리오 1: 포트폴리오 생성 → 저장 → 조회**

```python
def test_portfolio_lifecycle():
    # Setup
    stock_repo = YFinanceStockRepository()
    portfolio_repo = JSONPortfolioRepository(storage_path="test_data")
    service = PortfolioManagementService(portfolio_repo, stock_repo)

    # 1. 포트폴리오 생성
    portfolio = service.create_portfolio(
        portfolio_id="integration_test_001",
        name="통합 테스트 포트폴리오",
        holdings={"AAPL": 0.6, "MSFT": 0.4}
    )
    assert portfolio.total_weight == 1.0

    # 2. 저장
    success = portfolio_repo.save(portfolio)
    assert success == True

    # 3. 조회
    loaded = portfolio_repo.load("integration_test_001")
    assert loaded.name == "통합 테스트 포트폴리오"
    assert len(loaded.holdings) == 2

    # 4. 수익률 계산 (StockRepository 사용)
    perf = service.calculate_portfolio_return("integration_test_001", period="5d")
    assert "total_return" in perf
    assert isinstance(perf["total_return"], float)

    # Cleanup
    portfolio_repo.delete("integration_test_001")
```

**성공 기준**: End-to-end 데이터 흐름 정상, 최종 수익률 계산됨

---

**시나리오 2: 팩터 분석 → TOP 5 선정 → UI 표시**

```python
def test_factor_screening_flow():
    # 1. Repository 생성
    stock_repo = YFinanceStockRepository()

    # 2. FactorScreener 생성 (DI)
    screener = FactorScreener(stock_repo=stock_repo, market="US")

    # 3. TOP 5 종목 스크리닝
    tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "META", "NVDA"]
    top_stocks = screener.screen_top_stocks(tickers, top_n=5, sort_by="composite")

    # 4. 결과 검증
    assert len(top_stocks) == 5
    assert all(0 <= score.composite <= 100 for score in top_stocks)

    # 5. UI 렌더링 가능성 검증
    # (실제 streamlit 환경 필요, 여기서는 호출만 확인)
    from src.dashboard.control_center import render_factor_top5
    # render_factor_top5(top_stocks)  # 함수 존재 확인
```

**성공 기준**: Repository → Service → UI 데이터 전달 정상

---

### 3.2 Phase 간 상호작용

**시나리오 3: Phase 9 (VIX) → Phase 10 (Alert Service) → Phase 13 (Dashboard)**

```python
def test_cross_phase_alert_flow():
    # Phase 9: VIX 분석
    from src.analyzers.volatility_analyzer import VolatilityAnalyzer
    vol_analyzer = VolatilityAnalyzer()
    vix = vol_analyzer.get_current_vix()
    regime, color = vol_analyzer.volatility_regime()

    # Phase 10: Alert Service
    from src.services.alert_orchestrator_service import AlertOrchestratorService
    from src.infrastructure.repositories.stock_repository import YFinanceStockRepository
    from src.utils.notification_manager import NotificationManager, AlertConfig

    stock_repo = YFinanceStockRepository()
    config = AlertConfig(vix_spike_threshold=25.0)
    notif_mgr = NotificationManager(config)
    alert_service = AlertOrchestratorService(stock_repo, notif_mgr)

    # VIX 알림 체크
    vix_alert = alert_service.check_and_alert_vix()

    # Phase 13: Dashboard 표시 (렌더링 가능성 확인)
    assert vix is not None
    assert color in ["green", "yellow", "red", "purple"]
    if vix_alert:
        assert vix_alert.level in ["INFO", "WARNING", "CRITICAL"]
```

**성공 기준**: 3개 Phase 연동 정상, VIX → Alert → UI 데이터 흐름 유지

---

### 3.3 Strangler Fig Pattern 검증

**시나리오 4: Legacy Adapter를 통한 데이터 조회**

```python
def test_legacy_adapter_compatibility():
    # Legacy Adapter (Phase 10-3)
    from src.infrastructure.adapters.legacy_adapter import LegacyCollectorAdapter

    adapter = LegacyCollectorAdapter()

    # IStockRepository 인터페이스 준수 확인
    stock = adapter.get_stock_data("AAPL", period="1mo")

    assert isinstance(stock, StockEntity)
    assert stock.ticker == "AAPL"
    assert stock.market == "US"
    assert len(stock.price_history) > 0

    # 기존 StockDataCollector와 동일한 결과 보장
    from src.collectors.stock_collector import StockDataCollector
    legacy = StockDataCollector()
    legacy_df = legacy.fetch_stock_data("AAPL", period="1mo")

    adapter_df = stock.to_dataframe()

    # 데이터 일치성 검증 (±0.01 허용)
    assert len(legacy_df) == len(adapter_df)
    assert abs(legacy_df['close'].iloc[-1] - adapter_df['close'].iloc[-1]) < 0.01
```

**성공 기준**: Legacy → Adapter 변환 정확성, 기존 코드와 결과 동일

---

## 4. Level 3: 아키텍처 준수 검증

### 4.1 Clean Architecture Layer 분리

**검증 스크립트**: `verify_architecture_compliance.py`

```python
def test_no_circular_dependencies():
    """
    Domain Layer는 Infrastructure/Services에 의존하지 않음
    """
    import ast

    domain_files = glob.glob("src/domain/**/*.py", recursive=True)

    for filepath in domain_files:
        with open(filepath) as f:
            tree = ast.parse(f.read())

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    # 금지: from src.infrastructure import ...
                    assert not alias.name.startswith("src.infrastructure")
                    # 금지: from src.services import ...
                    assert not alias.name.startswith("src.services")

            if isinstance(node, ast.ImportFrom):
                # 금지: from src.infrastructure.* import ...
                assert not node.module.startswith("src.infrastructure")
                assert not node.module.startswith("src.services")
```

**성공 기준**: Domain Layer 순수성 유지 (외부 의존성 0)

---

### 4.2 DIP (Dependency Inversion Principle) 검증

```python
def test_services_depend_on_interfaces():
    """
    Application Services는 인터페이스에만 의존
    """
    service_files = glob.glob("src/services/*.py")

    for filepath in service_files:
        with open(filepath) as f:
            content = f.read()

        # 허용: from src.domain.repositories.interfaces import IStockRepository
        # 금지: from src.infrastructure.repositories.stock_repository import YFinanceStockRepository

        assert "from src.domain.repositories.interfaces import" in content
        assert "from src.infrastructure.repositories" not in content
```

**성공 기준**: Services가 구현체가 아닌 인터페이스에만 의존

---

### 4.3 Repository 인터페이스 완전성

```python
def test_all_repositories_implement_interfaces():
    """
    모든 Repository 구현체는 인터페이스 메서드 구현
    """
    from src.domain.repositories.interfaces import IStockRepository
    from src.infrastructure.repositories.stock_repository import YFinanceStockRepository

    # 인터페이스 메서드 추출
    interface_methods = [m for m in dir(IStockRepository) if not m.startswith("_")]

    # 구현체 메서드 추출
    impl_methods = [m for m in dir(YFinanceStockRepository) if not m.startswith("_")]

    # 모든 인터페이스 메서드가 구현되어 있는지 확인
    for method in interface_methods:
        assert method in impl_methods, f"Missing implementation: {method}"
```

**성공 기준**: 모든 Repository가 인터페이스 완전 구현

---

## 5. Level 4: E2E 검증 (End-to-End Scenarios)

### 5.1 실제 사용자 시나리오

**시나리오 A: 초보 투자자의 첫 포트폴리오 구성**

```python
def test_beginner_portfolio_scenario():
    """
    1. 미국 인기 종목 TOP 5 조회
    2. 팩터 분석으로 우수 종목 선정
    3. 포트폴리오 생성 (균등 비중)
    4. 리스크 분석
    5. 결과 대시보드 표시
    """
    # 1. Repository 생성
    stock_repo = YFinanceStockRepository()
    portfolio_repo = SessionPortfolioRepository()

    # 2. TOP 5 종목 선정 (Phase 11)
    screener = FactorScreener(stock_repo=stock_repo, market="US")
    popular_tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "META", "NVDA"]
    top5 = screener.screen_top_stocks(popular_tickers, top_n=5)

    # 3. 포트폴리오 생성 (Phase 10)
    service = PortfolioManagementService(portfolio_repo, stock_repo)
    holdings = {score.ticker: 0.2 for score in top5}  # 균등 비중

    portfolio = service.create_portfolio(
        portfolio_id="beginner_001",
        name="초보자 추천 포트폴리오",
        holdings=holdings
    )

    # 4. 리스크 분석
    risk = service.calculate_portfolio_risk("beginner_001", period="1y")

    # 5. 검증
    assert portfolio.total_weight == 1.0
    assert len(portfolio.holdings) == 5
    assert "portfolio_volatility" in risk
    assert risk["portfolio_volatility"] > 0

    print(f"✅ 포트폴리오 생성 완료: {portfolio.name}")
    print(f"✅ 연 변동성: {risk['portfolio_volatility']:.2f}%")
```

**성공 기준**: 전체 플로우 성공, 변동성 < 30% (일반적 기준)

---

**시나리오 B: 고급 투자자의 밈주식 감지 및 리스크 관리**

```python
def test_advanced_meme_stock_scenario():
    """
    1. 소셜 트렌드로 밈주식 감지 (Phase 12)
    2. 감지된 종목의 VIX, Market Breadth 확인 (Phase 9)
    3. Alert 발생 시 알림 (Phase 10)
    4. 투자 컨트롤 센터에 경고 표시 (Phase 13)
    """
    # 1. 밈주식 감지
    from src.analyzers.social_analyzer import SocialTrendAnalyzer
    social = SocialTrendAnalyzer()

    watchlist = ["GME", "AMC", "BBBY", "TSLA"]
    meme_stocks = social.detect_meme_stocks(watchlist, threshold=2.5)

    # 2. 시장 환경 확인
    from src.analyzers.volatility_analyzer import VolatilityAnalyzer
    from src.analyzers.market_breadth import MarketBreadthAnalyzer

    vol = VolatilityAnalyzer()
    vix = vol.get_current_vix()
    regime, color = vol.volatility_regime()

    breadth = MarketBreadthAnalyzer(market="US")
    ad_ratio = breadth.advance_decline_ratio()

    # 3. Alert 발생 (VIX 고공행진 + 밈주식 스파이크)
    if vix > 25 and len(meme_stocks) > 0:
        from src.utils.notification_manager import NotificationManager, AlertConfig

        config = AlertConfig(vix_spike_threshold=25.0)
        notif = NotificationManager(config)

        alert = notif.check_vix(vix)

        if alert:
            print(f"⚠️ 경고: VIX {vix:.2f}, 밈주식 {len(meme_stocks)}개 감지")
            print(f"   - {color.upper()} 구간")
            print(f"   - 감지 종목: {[s['ticker'] for s in meme_stocks]}")

            # 4. 컨트롤 센터 경고 (실제 환경에서는 UI 렌더링)
            assert alert.level in ["WARNING", "CRITICAL"]

    # 검증
    assert vix is not None
    assert ad_ratio is not None
```

**성공 기준**: 밈주식 감지 정상, 알림 로직 작동, 컨트롤 센터 연동

---

### 5.2 성능 검증

**시나리오 C: 대규모 종목 분석 성능**

```python
import time

def test_bulk_analysis_performance():
    """
    50개 종목 팩터 분석 성능 테스트
    목표: 60초 이내 완료
    """
    stock_repo = YFinanceStockRepository()
    screener = FactorScreener(stock_repo=stock_repo, market="US")

    # S&P 500 샘플 50개
    tickers = [
        "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "META", "NVDA", "BRK-B", "JPM", "V",
        "JNJ", "WMT", "PG", "MA", "HD", "DIS", "PYPL", "NFLX", "ADBE", "CRM",
        # ... 30개 더
    ]

    start_time = time.time()
    top10 = screener.screen_top_stocks(tickers, top_n=10)
    elapsed = time.time() - start_time

    print(f"⏱️ 50개 종목 분석 소요 시간: {elapsed:.2f}초")

    assert elapsed < 60, f"성능 기준 미달: {elapsed:.2f}초 (목표 < 60초)"
    assert len(top10) == 10
```

**성능 기준**:
- 50개 종목 < 60초 (병렬 처리 없이)
- 캐싱 사용 시 < 10초

---

## 6. Level 5: 성능 및 안정성 검증

### 6.1 API 호출 최적화

**검증 항목**:
```python
def test_api_call_optimization():
    """
    yfinance API 호출 횟수 제한 준수
    """
    import unittest.mock as mock

    with mock.patch("yfinance.download") as mock_download:
        stock_repo = YFinanceStockRepository()

        # 같은 종목을 3번 조회
        stock_repo.get_stock_data("AAPL", "1mo")
        stock_repo.get_stock_data("AAPL", "1mo")
        stock_repo.get_stock_data("AAPL", "1mo")

        # 캐싱으로 API 호출은 1번만
        assert mock_download.call_count == 1
```

**성공 기준**: 캐싱 효과로 중복 호출 방지

---

### 6.2 에러 핸들링

**시나리오 D: 네트워크 오류 복원력**

```python
def test_network_failure_resilience():
    """
    외부 API 실패 시 graceful degradation
    """
    import unittest.mock as mock

    with mock.patch("yfinance.download", side_effect=Exception("Network error")):
        stock_repo = YFinanceStockRepository()

        # API 실패 시 None 반환 (예외 전파 안 함)
        stock = stock_repo.get_stock_data("AAPL", "1mo")

        assert stock is None

    # Service Layer에서 None 처리
    portfolio_repo = SessionPortfolioRepository()
    service = PortfolioManagementService(portfolio_repo, stock_repo)

    with mock.patch.object(stock_repo, "get_stock_data", return_value=None):
        perf = service.calculate_portfolio_return("test", period="5d")

        # None 반환 또는 빈 결과 (예외 발생 안 함)
        assert perf is None or perf == {}
```

**성공 기준**: 예외 발생 없이 None/빈 결과 반환

---

### 6.3 데이터 무결성

```python
def test_data_integrity():
    """
    StockEntity 비즈니스 로직 정확성
    """
    # 테스트 데이터 생성
    stock = StockEntity(ticker="TEST", name="Test", market="US")

    for i in range(100):
        price = PriceData(
            open=100 + i,
            high=105 + i,
            low=95 + i,
            close=100 + i + (i % 2),  # 지그재그 패턴
            volume=100000,
            date=datetime.now() - timedelta(days=100-i)
        )
        stock.price_history.append(price)

    # 수익률 검증
    ret = stock.calculate_return(days=10)
    expected_ret = ((100 + 99) - (100 + 89)) / (100 + 89) * 100
    assert abs(ret - expected_ret) < 0.01, f"수익률 계산 오류: {ret} != {expected_ret}"

    # MDD 검증 (지그재그 패턴 → MDD 작음)
    mdd = stock.get_max_drawdown()
    assert 0 <= mdd <= 100, f"MDD 범위 오류: {mdd}"
```

**성공 기준**: 모든 계산 값이 수학적 정의와 일치

---

## 7. 통합 검증 스크립트: `verify_all.py`

### 7.1 스크립트 구조

```python
"""
verify_all.py - Phase 9-13 전체 검증 마스터 스크립트
"""
import sys
import subprocess
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

# 검증 레벨별 스크립트 매핑
VERIFICATION_LEVELS = {
    "Level 1: Unit Tests": [
        ("Phase 9", "verify_phase9.py"),
        ("Phase 10", "verify_phase10.py"),
        ("Phase 11", "verify_phase11.py"),
        ("Phase 12", "verify_phase12.py"),
        ("Phase 13", "verify_phase13.py"),
    ],
    "Level 2: Integration": [
        ("Repository-Service", "verify_integration.py"),
    ],
    "Level 3: Architecture": [
        ("Clean Architecture Compliance", "verify_architecture.py"),
    ],
    "Level 4: E2E": [
        ("User Scenarios", "verify_e2e_scenarios.py"),
    ],
    "Level 5: Performance": [
        ("Performance & Reliability", "verify_performance.py"),
    ],
}

def run_verification_level(level_name, scripts):
    """레벨별 검증 실행"""
    print(f"\n{'='*60}")
    print(f"🔍 {level_name}")
    print(f"{'='*60}")

    results = []
    for script_name, script_path in scripts:
        print(f"\n▶ Running: {script_name} ({script_path})")

        try:
            result = subprocess.run(
                [sys.executable, str(PROJECT_ROOT / script_path)],
                capture_output=True,
                text=True,
                timeout=120  # 2분 타임아웃
            )

            if result.returncode == 0:
                print(f"  ✅ {script_name} PASSED")
                results.append((script_name, "PASS", None))
            else:
                print(f"  ❌ {script_name} FAILED")
                print(f"     Error: {result.stderr[:200]}")
                results.append((script_name, "FAIL", result.stderr))

        except subprocess.TimeoutExpired:
            print(f"  ⏱️ {script_name} TIMEOUT")
            results.append((script_name, "TIMEOUT", "120초 초과"))

        except Exception as e:
            print(f"  ⚠️ {script_name} ERROR: {e}")
            results.append((script_name, "ERROR", str(e)))

    return results

def main():
    print("="*60)
    print("🧪 Phase 9-13 종합 검증 프로토콜")
    print(f"📅 실행 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)

    all_results = {}

    # 레벨별 순차 실행
    for level_name, scripts in VERIFICATION_LEVELS.items():
        level_results = run_verification_level(level_name, scripts)
        all_results[level_name] = level_results

    # 최종 결과 요약
    print("\n" + "="*60)
    print("📋 최종 검증 결과")
    print("="*60)

    total_pass = 0
    total_fail = 0
    total_error = 0

    for level_name, results in all_results.items():
        print(f"\n{level_name}:")
        for script_name, status, error in results:
            status_icon = {"PASS": "✅", "FAIL": "❌", "TIMEOUT": "⏱️", "ERROR": "⚠️"}[status]
            print(f"  {status_icon} {script_name}: {status}")

            if status == "PASS":
                total_pass += 1
            elif status == "FAIL":
                total_fail += 1
            else:
                total_error += 1

    total = total_pass + total_fail + total_error
    pass_rate = total_pass / total * 100 if total > 0 else 0

    print(f"\n{'='*60}")
    print(f"📊 통계")
    print(f"{'='*60}")
    print(f"  총 테스트: {total}")
    print(f"  ✅ 통과: {total_pass}")
    print(f"  ❌ 실패: {total_fail}")
    print(f"  ⚠️ 오류: {total_error}")
    print(f"  📈 통과율: {pass_rate:.1f}%")

    print(f"\n{'='*60}")
    if total_fail == 0 and total_error == 0:
        print("🎉 모든 검증 통과! Phase 9-13 시스템이 안정적으로 작동합니다.")
        print("="*60)
        return 0
    else:
        print("⚠️ 일부 검증이 실패했습니다. 위 오류를 확인해주세요.")
        print("="*60)
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
```

### 7.2 실행 명령

```bash
# 전체 검증 (10분 소요)
python verify_all.py

# 특정 레벨만 검증
python verify_all.py --level 1  # Unit tests only
python verify_all.py --level 3  # Architecture compliance only

# 빠른 검증 (네트워크 테스트 제외)
python verify_all.py --fast

# 상세 로그
python verify_all.py --verbose
```

---

## 8. 성공 기준 (Success Criteria)

### 8.1 단계별 성공 기준

| Level | 항목 | 최소 통과율 | 비고 |
|-------|------|------------|------|
| Level 1 | Phase 9 Unit Tests | 90% | VIX 수집 실패 허용 |
| Level 1 | Phase 10 Unit Tests | 100% | Domain/Repository 필수 |
| Level 1 | Phase 11 Unit Tests | 100% | Factor 계산 정확성 필수 |
| Level 1 | Phase 12 Unit Tests | 80% | Network 이슈 허용 |
| Level 1 | Phase 13 Unit Tests | 100% | UI 컴포넌트 로드 필수 |
| Level 2 | Integration Tests | 90% | 일부 API 실패 허용 |
| Level 3 | Architecture Compliance | 100% | Layer 분리 필수 |
| Level 4 | E2E Scenarios | 80% | 외부 API 의존성 |
| Level 5 | Performance Tests | 100% | 성능 기준 준수 필수 |

### 8.2 전체 시스템 성공 기준

✅ **릴리즈 승인 조건**:
- Level 1-3: 모두 100% 통과
- Level 4-5: 80% 이상 통과
- Critical 버그 0개
- 문서화 완료

⚠️ **조건부 승인**:
- Level 4-5: 70-80% 통과
- Known issues 문서화됨
- Workaround 존재

❌ **릴리즈 불가**:
- Level 1-3 중 하나라도 90% 미만
- Critical 버그 존재
- Data integrity 문제

---

## 9. CI/CD 통합

### 9.1 GitHub Actions Workflow

```yaml
# .github/workflows/verification.yml
name: Phase 9-13 Verification

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.8, 3.9, 3.10]

    steps:
    - uses: actions/checkout@v3

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}

    - name: Install dependencies
      run: |
        pip install -r requirements.txt

    - name: Run Level 1 Tests
      run: |
        python verify_phase9.py
        python verify_phase10.py
        python verify_phase11.py
        python verify_phase12.py --skip-network
        python verify_phase13.py

  integration-tests:
    runs-on: ubuntu-latest
    needs: unit-tests

    steps:
    - uses: actions/checkout@v3

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: 3.10

    - name: Install dependencies
      run: pip install -r requirements.txt

    - name: Run Level 2-3 Tests
      run: |
        python verify_integration.py
        python verify_architecture.py

  e2e-tests:
    runs-on: ubuntu-latest
    needs: integration-tests

    steps:
    - uses: actions/checkout@v3

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: 3.10

    - name: Install dependencies
      run: pip install -r requirements.txt

    - name: Run Level 4-5 Tests
      run: |
        python verify_e2e_scenarios.py
        python verify_performance.py
      env:
        ENABLE_NETWORK_TESTS: true
```

### 9.2 Pre-commit Hook

```bash
# .git/hooks/pre-commit
#!/bin/bash

echo "🧪 Running pre-commit verification..."

# Level 1 Unit Tests (Fast)
python verify_phase10.py --fast
if [ $? -ne 0 ]; then
    echo "❌ Unit tests failed. Commit aborted."
    exit 1
fi

# Architecture Compliance
python verify_architecture.py
if [ $? -ne 0 ]; then
    echo "❌ Architecture compliance failed. Commit aborted."
    exit 1
fi

echo "✅ Pre-commit verification passed."
exit 0
```

---

## 10. 검증 체크리스트 (실행 시 사용)

### 10.1 검증 전 준비사항

- [ ] Python 3.8+ 설치
- [ ] `pip install -r requirements.txt` 완료
- [ ] 환경 변수 설정 (.env 파일)
  - [ ] KIS API 키 (한국 종목용, 선택)
  - [ ] 네트워크 연결 확인
- [ ] 테스트 데이터 디렉토리 생성
  - [ ] `data/test_portfolios/`
  - [ ] `data/cache/`

### 10.2 검증 실행 순서

1. [ ] **Level 1 검증** (5분)
   ```bash
   python verify_phase9.py
   python verify_phase10.py
   python verify_phase11.py
   python verify_phase12.py
   python verify_phase13.py
   ```
   - 예상 결과: 80/85 tests pass (94%)

2. [ ] **Level 2 검증** (3분)
   ```bash
   python verify_integration.py
   ```
   - 예상 결과: 15/15 tests pass

3. [ ] **Level 3 검증** (1분)
   ```bash
   python verify_architecture.py
   ```
   - 예상 결과: 10/10 tests pass (필수)

4. [ ] **Level 4 검증** (5분)
   ```bash
   python verify_e2e_scenarios.py
   ```
   - 예상 결과: 4/5 scenarios pass (80%)

5. [ ] **Level 5 검증** (3분)
   ```bash
   python verify_performance.py
   ```
   - 예상 결과: 5/5 tests pass

6. [ ] **통합 검증** (10분)
   ```bash
   python verify_all.py
   ```
   - 예상 결과: Overall 90%+ pass rate

### 10.3 브라우저 수동 테스트 (선택)

- [ ] Streamlit 앱 실행
  ```bash
  streamlit run streamlit_app.py
  ```
- [ ] 모든 탭 정상 작동 확인
- [ ] Phase 13 투자 컨트롤 센터 4분할 레이아웃 확인

---

## 11. 트러블슈팅

### 11.1 자주 발생하는 문제

**문제 1**: `UnicodeEncodeError` (Windows 한글 출력)
```bash
# 해결 방법
set PYTHONIOENCODING=utf-8
python verify_phase9.py
```

**문제 2**: Network timeout (VIX/Google Trends 수집 실패)
```bash
# 네트워크 테스트 스킵
python verify_phase12.py --skip-network
```

**문제 3**: TensorFlow 미설치로 LSTM 테스트 실패
```python
# verify_phase9.py에서 예상된 동작
# XGBoost만 사용하는 경우 경고로 처리
```

**문제 4**: JSONPortfolioRepository 파일 권한 오류
```bash
# 테스트 데이터 디렉토리 권한 확인
chmod 755 data/test_portfolios
```

---

## 12. 필요한 신규 검증 스크립트

다음 스크립트들을 추가로 작성해야 합니다:

### 12.1 우선순위 HIGH (필수)

1. **verify_all.py** - 마스터 검증 스크립트
   - 모든 레벨 통합 실행
   - 결과 리포팅
   - 통과율 계산

2. **verify_architecture.py** - Level 3 아키텍처 준수 검증
   - DIP (Dependency Inversion Principle) 검증
   - Clean Architecture Layer 분리 검증
   - Repository 인터페이스 완전성 검증

3. **verify_integration.py** - Level 2 통합 테스트
   - Repository ↔ Service 통합
   - Service ↔ UI 데이터 흐름
   - Strangler Fig Pattern 검증

### 12.2 우선순위 MEDIUM (권장)

4. **verify_e2e_scenarios.py** - Level 4 E2E 시나리오
   - 초보자 포트폴리오 구성 시나리오
   - 밈주식 감지 및 리스크 관리 시나리오
   - Phase 간 상호작용 검증

5. **verify_performance.py** - Level 5 성능/안정성
   - 대규모 종목 분석 성능
   - API 호출 최적화
   - 에러 핸들링 복원력

### 12.3 우선순위 LOW (선택)

6. **BROWSER_TEST_CHECKLIST.md** - 수동 UI 테스트 체크리스트
   - 각 탭별 검증 항목
   - 브라우저 호환성 체크
   - 반응형 디자인 확인

---

## 부록 A: 파일 구조 참조

```
D:\Stock\
├── verify_phase9.py         # ✅ Phase 9 검증 (34 tests)
├── verify_phase10.py        # ✅ Phase 10 검증 (18 tests)
├── verify_phase11.py        # ✅ Phase 11 검증 (12 tests)
├── verify_phase12.py        # ✅ Phase 12 검증 (9 tests)
├── verify_phase13.py        # ✅ Phase 13 검증 (12 tests)
├── verify_integration.py    # ❌ (신규 작성 필요)
├── verify_architecture.py   # ❌ (신규 작성 필요)
├── verify_e2e_scenarios.py  # ❌ (신규 작성 필요)
├── verify_performance.py    # ❌ (신규 작성 필요)
└── verify_all.py            # ❌ (신규 작성 필요) 마스터 스크립트
```

---

## 부록 B: 핵심 검증 메트릭

| 메트릭 | 목표 | 현재 | 상태 |
|--------|------|------|------|
| Unit Test Coverage | ≥85% | 94% | ✅ |
| Integration Test Pass Rate | ≥90% | TBD | - |
| Architecture Compliance | 100% | TBD | - |
| E2E Success Rate | ≥80% | TBD | - |
| Performance (50 stocks) | <60s | TBD | - |
| API Call Optimization | Cache hit ≥70% | TBD | - |

---

**검증 프로토콜 문서 끝**
