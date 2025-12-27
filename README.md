# 🚀 Intelligent Investment Platform
# 스마트 투자 분석 플랫폼 v3.1

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.30+-red.svg)](https://streamlit.io)
[![TensorFlow](https://img.shields.io/badge/TensorFlow-2.15+-orange.svg)](https://tensorflow.org)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

> AI 기반 주식 분석, 예측, 포트폴리오 최적화를 위한 종합 투자 대시보드

## 📋 목차
- [✨ 주요 기능](#-주요-기능)
- [🆕 v3.0 신규 기능](#-v30-신규-기능)
- [🏗️ 아키텍처](#️-아키텍처)
- [🛠️ 설치 방법](#️-설치-방법)
- [🚀 실행 방법](#-실행-방법)
- [📂 프로젝트 구조](#-프로젝트-구조)
- [🎯 기능 상세](#-기능-상세)

---

## ✨ 주요 기능

### 📊 시장 분석
| 기능 | 설명 |
|------|------|
| **실시간 시세** | 한국/미국 시장 실시간 주가 조회 |
| **단일 종목 분석** | 기술적 지표, 차트 패턴, 지지/저항선 분석 |
| **다중 종목 비교** | 여러 종목 수익률/변동성 비교 |
| **시장 체력 진단** | 상승/하락 종목 비율, 52주 신고가/신저가 분석 |

### 🔥 Market Buzz
| 기능 | 설명 |
|------|------|
| **섹터 히트맵** | 업종별 등락률 시각화 (Finviz 스타일) |
| **거래량 급증 감지** | 평소 대비 거래량 급등 종목 알림 |
| **Buzz Score** | 거래량+변동성 기반 관심도 점수 (0~100) |
| **투자 성향 연동** | 사용자 성향에 맞는 종목 필터링 |

### 🤖 AI 예측
| 기능 | 설명 |
|------|------|
| **앙상블 모델** | LSTM + XGBoost + Transformer 결합 예측 |
| **점진적 학습** | 신규 데이터로 모델 자동 업데이트 |
| **신뢰도 평가** | 예측 결과 신뢰 구간 제공 |
| **자동 가중치 조절** | 모델 성능 기반 앙상블 가중치 자동 최적화 |

### 📰 뉴스 감성 분석
| 기능 | 설명 |
|------|------|
| **Gemini LLM 분석** | 🆕 Google Gemini 기반 고급 감성 분석 |
| **한국어 분석** | KR-FinBERT 기반 금융 뉴스 감성 분석 |
| **영어 분석** | VADER 기반 영문 뉴스 감성 분석 |
| **예측 통합** | 감성 점수를 AI 예측 모델에 반영 |

### 👤 투자 성향 진단
| 기능 | 설명 |
|------|------|
| **심리 테스트** | 10문항 투자 성향 진단 |
| **맞춤 추천** | 성향 기반 종목 순위 제공 |
| **리스크 매칭** | 위험 감수 성향별 포트폴리오 추천 |

### 💼 포트폴리오 & 리스크
| 기능 | 설명 |
|------|------|
| **최적화** | Markowitz 평균-분산 최적 포트폴리오 |
| **VaR/CVaR** | Value at Risk 리스크 분석 |
| **백테스팅** | 과거 데이터 기반 전략 검증 |
| **팩터 투자** | 가치/모멘텀/품질 팩터 분석 |

---

## 🆕 v3.0 신규 기능

### 🗣️ AI 챗봇 어시스턴트
- 자연어 대화형 투자 상담
- 컨텍스트 인식 (현재 보고 있는 종목/탭 파악)
- **Agentic Control**: 채팅으로 탭 이동, 종목 선택, 스크리너 실행 가능
- 대화 이력 저장 및 활용

### 🧠 Gemini LLM 감성 분석
- Google Gemini API 활용 고급 감성 분석
- 기존 VADER/키워드 대비 높은 정확도
- AI 예측 시 "🧠 Gemini LLM 감성 분석" 옵션

### 📊 MarketDataService (강화된 데이터 파이프라인)
- **멀티 소스 Fallback**: pykrx(한국) → Yahoo Finance 자동 전환
- **SQLite 캐싱**: 24시간 TTL 기반 데이터 캐싱
- Clean Architecture 기반 의존성 역전

### 📈 FeatureEngineeringService (15+ 기술적 지표)
- RSI, MACD, Bollinger Bands, ATR, Stochastic
- 모멘텀, 변동성, 거래량 피처 자동 생성
- AI 모델에 최적화된 피처 벡터 생성

### 🎯 AI 스크리너
- RSI 과매도 + 기관 3일 연속 매수 종목 발굴
- 투자 성향 기반 개인화 순위
- **한글 종목명 지원**

### 🎛️ 사이드바 UX 최적화 (v3.1)
- **탭별 설정 최상단 배치**: 자주 사용하는 설정이 즉시 접근 가능
- **시장 선택 토글 버튼**: 가로 2열 버튼으로 공간 50% 절약
- **설정 통합 Expander**: 사용자/API/알림 설정을 탭으로 통합
- **AI 투자 비서 하단 고정**: 모든 탭에서 일관된 접근성

---

## 🏗️ 아키텍처

### Clean Architecture 적용
```
┌─────────────────────────────────────────────────────────┐
│                   Presentation Layer                     │
│          (Streamlit Views, UI Components, Chat)          │
├─────────────────────────────────────────────────────────┤
│                   Application Layer                      │
│    (ChatService, MarketDataService, ScreenerService)     │
├─────────────────────────────────────────────────────────┤
│                     Domain Layer                         │
│          (Entities, Value Objects, Interfaces)           │
├─────────────────────────────────────────────────────────┤
│                 Infrastructure Layer                     │
│    (Repositories, Gateways, GeminiClient, pykrx)         │
└─────────────────────────────────────────────────────────┘
```

### 핵심 설계 원칙
- **의존성 역전 원칙 (DIP)**: 상위 계층이 하위 계층에 의존하지 않음
- **단일 책임 원칙 (SRP)**: 각 모듈은 하나의 책임만 담당
- **Fallback Pattern**: 데이터 소스 실패 시 자동 대체
- **캐싱 전략**: 메모리 캐시 + SQLite 캐시 + TTL 관리

---

## 🛠️ 설치 방법

### 요구사항
- Python 3.11+
- pip 또는 conda

### 설치
```bash
# 저장소 클론
git clone https://github.com/Mingyu-Song-0519/myeeeeeng.git
cd myeeeeeng

# 의존성 설치
pip install -r requirements.txt
```

### 환경 변수 설정 (선택)
```bash
# Gemini API 키 (AI 챗봇 및 LLM 감성 분석용)
export GEMINI_API_KEY="your-api-key"
```

### 선택 설치 (GPU 가속)
```bash
# CUDA 지원 TensorFlow (GPU 사용 시)
pip install tensorflow[and-cuda]
```

---

## 🚀 실행 방법

```bash
# 대시보드 실행
streamlit run src/dashboard/app.py

# 또는 루트 경로에서
python -m streamlit run src/dashboard/app.py
```

**접속**: http://localhost:8501

---

## 📂 프로젝트 구조

```
Intelligent-Investment-Platform/
├── 📁 src/
│   ├── 📁 domain/                    # 도메인 계층
│   │   ├── 📁 chat/                  # 🆕 채팅 도메인
│   │   │   ├── entities.py           # ChatMessage, ChatSession
│   │   │   └── actions.py            # UIAction, Agentic Control
│   │   ├── 📁 market_data/           # 🆕 시장 데이터 도메인
│   │   │   └── interfaces.py         # IStockDataGateway, OHLCV
│   │   ├── 📁 prediction/            # 🆕 예측 도메인
│   │   │   └── value_objects.py      # TechnicalFeatures
│   │   ├── 📁 investment_profile/    # 투자 성향 도메인
│   │   └── 📁 market_buzz/           # Market Buzz 도메인
│   │
│   ├── 📁 infrastructure/            # 인프라 계층
│   │   ├── 📁 external/              # 외부 API
│   │   │   ├── gemini_client.py      # 🆕 Gemini LLM 클라이언트
│   │   │   └── pykrx_gateway.py      # KRX 데이터 게이트웨이
│   │   ├── 📁 market_data/           # 🆕 시장 데이터 게이트웨이
│   │   │   ├── yahoo_gateway.py      # Yahoo Finance
│   │   │   ├── pykrx_gateway.py      # PyKRX
│   │   │   └── fallback_gateway.py   # Fallback 체인
│   │   ├── 📁 sentiment/             # 🆕 감성 분석
│   │   │   └── llm_sentiment_analyzer.py  # Gemini 감성 분석
│   │   └── 📁 repositories/          # 저장소 구현체
│   │       ├── chat_history_repository.py  # 🆕 대화 이력
│   │       └── market_data_cache_repository.py  # 🆕 데이터 캐시
│   │
│   ├── 📁 services/                  # 애플리케이션 계층
│   │   ├── 📁 chat/                  # 🆕 채팅 서비스
│   │   │   ├── chat_service.py       # 채팅 오케스트레이션
│   │   │   ├── context_assembler.py  # 컨텍스트 조립
│   │   │   └── action_executor.py    # Agentic Action 실행
│   │   ├── market_data_service.py    # 🆕 시장 데이터 서비스
│   │   ├── feature_engineering_service.py  # 🆕 피처 엔지니어링
│   │   ├── screener_service.py       # AI 스크리너
│   │   └── ...
│   │
│   ├── 📁 dashboard/                 # 프레젠테이션 계층
│   │   ├── app.py                    # 메인 앱
│   │   ├── 📁 components/            # 🆕 UI 컴포넌트
│   │   │   └── sidebar_chat.py       # 사이드바 챗봇
│   │   └── views/                    # UI 뷰
│   │
│   ├── 📁 models/                    # AI 모델
│   │   ├── ensemble_predictor.py     # 앙상블 모델 (auto_adjust_weights 🆕)
│   │   └── saved_models/             # 학습된 모델
│   │
│   └── 📁 analyzers/                 # 분석 모듈
│       ├── sentiment_analyzer.py     # 감성 분석 (LLM 지원 🆕)
│       └── technical_analyzer.py     # 기술적 분석
│
├── 📁 tests/                         # 테스트
│   └── integration/                  # 통합 테스트
├── 📄 requirements.txt               # 의존성
├── 📄 config.py                      # 설정
└── 📄 README.md
```

---

## 🎯 기능 상세

### 🗣️ AI 챗봇 사용법
1. 사이드바에서 **"💬 AI 챗봇"** 열기
2. Gemini API 키 입력 (최초 1회)
3. 자연어로 질문하기:
   - "삼성전자 분석해줘"
   - "AI 스크리너 실행해줘"
   - "포트폴리오 탭으로 이동해줘"

### 📊 AI 예측 옵션
```
☑️ 🤖 Transformer 포함
☑️ 🌍 시장 국면 반영
☑️ 📰 감성 분석 포함
   └── ☑️ 🧠 Gemini LLM 감성 분석  ← NEW!
☑️ 💾 학습된 모델 저장
```

### 🔄 데이터 파이프라인
```
요청 → MarketDataService
         ├── 캐시 확인 (SQLite, 24h TTL)
         │   └── 캐시 Hit → 반환
         └── 캐시 Miss
             ├── pykrx Gateway (한국)
             │   └── 실패 → Yahoo Gateway (Fallback)
             └── 저장 → 캐시
```

---

## 🔧 기술 스택

| 분류 | 기술 |
|------|------|
| **Backend** | Python 3.11, Pandas, NumPy |
| **AI/ML** | TensorFlow, XGBoost, Scikit-learn |
| **LLM** | 🆕 Google Gemini API |
| **NLP** | Transformers (KR-FinBERT), VADER |
| **Frontend** | Streamlit, Plotly |
| **Data** | yfinance, pykrx, FinanceDataReader |
| **Architecture** | Clean Architecture, DDD, DIP |
| **Cache** | SQLite (TTL-based) |

---

## ⚙️ 환경 변수

| 변수명 | 설명 | 필수 |
|--------|------|------|
| `GEMINI_API_KEY` | Gemini API 키 (챗봇, LLM 감성 분석) | 선택 |

**설정 방법:**
```bash
# 환경 변수
export GEMINI_API_KEY="your-key"

# 또는 .streamlit/secrets.toml
GEMINI_API_KEY = "your-key"
```

---

## 📝 라이선스

MIT License - 자유롭게 사용 및 수정 가능

---

## 👨‍💻 개발자

**Mingyu Song**
- GitHub: [@Mingyu-Song-0519](https://github.com/Mingyu-Song-0519)

---

## 🙏 감사의 말

이 프로젝트는 다음 오픈소스 라이브러리들의 도움을 받았습니다:
- [Streamlit](https://streamlit.io/) - 웹 대시보드 프레임워크
- [yfinance](https://github.com/ranaroussi/yfinance) - 주가 데이터 수집
- [pykrx](https://github.com/sharebook-kr/pykrx) - 한국 주식 데이터
- [Plotly](https://plotly.com/) - 인터랙티브 차트
- [Google Generative AI](https://ai.google.dev/) - Gemini API
