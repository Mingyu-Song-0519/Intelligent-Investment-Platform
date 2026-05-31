"""
Stock Market Analysis & Prediction System - Configuration
주식 시장 분석 및 예측 시스템 설정 파일
"""
import os
from pathlib import Path


def _load_tickers_yaml(path: Path) -> dict:
    """data/tickers.yaml에서 종목 목록 로드 (S2: 비개발자 편집 가능)"""
    try:
        import yaml
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return data
    except Exception:
        return {}

# =============================================================================
# 프로젝트 경로 설정
# =============================================================================
BASE_DIR = Path(__file__).parent.absolute()
DATA_DIR = BASE_DIR / "data"
PROCESSED_DIR = BASE_DIR / "processed"
MODELS_DIR = BASE_DIR / "src" / "models" / "saved_models"  # 저장된 모델 디렉토리

# =============================================================================
# 데이터베이스 설정
# =============================================================================
DATABASE_PATH = DATA_DIR / "stock_data.db"

# =============================================================================
# 주식 데이터 설정 (S2: data/tickers.yaml에서 로드, 파일 없으면 기본값)
# =============================================================================
_TICKERS_YAML = DATA_DIR / "tickers.yaml"
_yaml_data = _load_tickers_yaml(_TICKERS_YAML)

DEFAULT_TICKERS: dict = _yaml_data.get("korean") or {
    "삼성전자": "005930.KS",
    "SK하이닉스": "000660.KS",
    "NAVER": "035420.KS",
    "카카오": "035720.KS",
    "현대차": "005380.KS",
}

US_TICKERS: dict = _yaml_data.get("us") or {
    "Apple": "AAPL",
    "Microsoft": "MSFT",
    "Google": "GOOGL",
    "Amazon": "AMZN",
    "Tesla": "TSLA",
}

# =============================================================================
# 시장별 설정 (통합 관리)
# =============================================================================
MARKET_CONFIG = {
    "KR": {
        "name": "한국 (KRX)",
        "suffix": ".KS",  # KOSPI (KOSDAQ은 .KQ)
        "currency": "KRW",
        "currency_symbol": "₩",
        "realtime_api": "KIS",  # 한국투자증권
        "news_sources": ["naver", "google_kr"],
        "sentiment_model": "kr_finbert",  # 한글 딥러닝 모델
    },
    "US": {
        "name": "미국 (NYSE/NASDAQ)",
        "suffix": "",  # 접미사 없음
        "currency": "USD",
        "currency_symbol": "$",
        "realtime_api": None,  # 실시간 미지원
        "news_sources": ["yahoo", "google_en"],
        "sentiment_model": "vader",  # 영문 VADER
    }
}

# 환율 설정
EXCHANGE_RATE_CONFIG = {
    "source": "yfinance",  # yfinance 또는 한국은행 API
    "pair": "USDKRW=X",  # yfinance 환율 심볼
    "cache_ttl": 3600,  # 1시간 캐싱
}

# 데이터 수집 기간 (기본값)
DEFAULT_PERIOD = "2y"  # 2년
DEFAULT_INTERVAL = "1d"  # 일봉

# =============================================================================
# 기술적 지표 설정
# =============================================================================
INDICATOR_PARAMS = {
    "RSI": {"period": 14},
    "MACD": {"fast": 12, "slow": 26, "signal": 9},
    "SMA": {"periods": [5, 20, 60, 120]},
    "EMA": {"periods": [5, 20, 60]},
    "BOLLINGER": {"period": 20, "std": 2},
}

# =============================================================================
# AI 모델 설정
# =============================================================================
MODEL_CONFIG = {
    "LSTM": {
        "sequence_length": 60,  # 60일 시퀀스
        "units": [128, 64, 32],
        "dropout": 0.2,
        "epochs": 100,
        "batch_size": 32,
    },
    "XGBOOST": {
        "n_estimators": 100,
        "max_depth": 6,
        "learning_rate": 0.1,
        "objective": "binary:logistic",  # 등락 예측
    },
}

# =============================================================================
# 앙상블 모델 설정 (Phase 2)
# =============================================================================
ENSEMBLE_CONFIG = {
    # 앙상블 전략: 'weighted_average', 'voting', 'stacking'
    "strategy": "weighted_average",

    # 모델별 가중치 (합이 1이 되도록 설정)
    "weights": {
        "lstm": 0.5,          # LSTM 회귀 모델
        "xgboost": 0.3,       # XGBoost 분류 모델
        "rule_based": 0.2,    # 규칙 기반 시그널
    },

    # 스태킹 전략용 메타 모델 설정
    "meta_window_size": 100,  # 메타 모델 학습용 윈도우 크기

    # 신뢰도 임계값
    "confidence_threshold": {
        "high": 0.75,   # 높은 신뢰도
        "medium": 0.60,  # 중간 신뢰도
        "low": 0.45,    # 낮은 신뢰도
    },

    # 앙상블 예측 옵션
    "options": {
        "include_rule_based": True,  # 규칙 기반 시그널 포함 여부
        "min_models": 2,             # 최소 필요 모델 수
        "normalize_weights": True,   # 가중치 자동 정규화
    },

    # 레거시 설정 (호환성 유지)
    "voting_threshold": 0.6,  # 60% 이상 동의 시 시그널 발생
    "confidence_min": 0.5,    # 최소 신뢰도
}

# =============================================================================
# 뉴스 크롤링 설정 (Phase 2)
# =============================================================================
NEWS_CONFIG = {
    "sources": {
        "naver_finance": "https://finance.naver.com/news/news_search.naver",
        "google_news_rss": "https://news.google.com/rss/search",
    },
    "max_articles": 50,
    "crawl_delay": 1.0,  # 초 단위
    "sentiment_keywords": {
        "positive": ["상승", "급등", "호재", "최고", "성장", "증가", "개선", "긍정"],
        "negative": ["하락", "급락", "악재", "최저", "감소", "하향", "부정", "우려"],
    },
}

# =============================================================================
# 백테스팅 설정 (Phase 2)
# =============================================================================
BACKTEST_CONFIG = {
    "initial_capital": 10_000_000,  # 초기 자본금 1천만원
    "commission": 0.00015,           # 거래 수수료 0.015%
    "slippage": 0.001,              # 슬리피지 0.1%
    "position_size": 0.2,            # 포지션 크기 (자본금의 20%)
    "strategies": {
        "rsi": {"oversold": 30, "overbought": 70},
        "macd": {"use_histogram": True},
        "ma_cross": {"fast": 20, "slow": 60},
    },
}

# =============================================================================
# 다중 종목 분석 설정 (Phase 2)
# =============================================================================
MULTI_STOCK_CONFIG = {
    "max_workers": 5,  # 병렬 처리 워커 수
    "timeout": 30,     # 각 종목당 타임아웃 (초)
    "cache_enabled": True,
}

# =============================================================================
# 대시보드 설정
# =============================================================================
DASHBOARD_CONFIG = {
    "page_title": "📈 주식 분석 대시보드",
    "page_icon": "📊",
    "layout": "wide",
    "theme": "dark",
}

# =============================================================================
# 디렉토리 자동 생성
# =============================================================================
BACKTEST_DIR = BASE_DIR / "backtest_results"
for dir_path in [DATA_DIR, PROCESSED_DIR, MODELS_DIR, BACKTEST_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)
