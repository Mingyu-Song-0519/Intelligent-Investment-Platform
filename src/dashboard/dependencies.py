"""
Dependency Injection Container
모든 Repository와 Service 인스턴스를 중앙 관리

Clean Architecture:
- Repository는 Infrastructure Layer에서 생성
- Service는 Application Layer에서 생성
- UI (Streamlit)는 이 Container에서 필요한 인스턴스를 가져감
"""
from pathlib import Path

# ===== Repository Layer =====
from src.infrastructure.repositories.stock_repository import YFinanceStockRepository
from src.infrastructure.repositories.portfolio_repository import (
    JSONPortfolioRepository, 
    SessionPortfolioRepository
)
from src.infrastructure.repositories.news_repository import (
    NaverNewsRepository,
    GoogleNewsRepository
)
from src.infrastructure.repositories.kis_repository import KISRepository

# ===== Service Layer =====
from src.services.trading_signal_service import TradingSignalService, FactorScoringService
from src.services.portfolio_management_service import PortfolioManagementService
from src.services.alert_orchestrator_service import AlertOrchestratorService
from src.services.technical_analysis_service import TechnicalAnalysisService
from src.services.risk_management_service import RiskManagementService

# ===== Legacy Adapters (점진적 제거 예정) =====
from src.infrastructure.adapters.legacy_adapter import (
    LegacyCollectorAdapter,
    LegacyNewsAdapter,
    LegacyAnalyzerAdapter
)


# ==================================================================================
# Configuration
# ==================================================================================

# 데이터베이스 경로
PROJECT_ROOT = Path(__file__).parent.parent
DATABASE_DIR = PROJECT_ROOT / "data"
DATABASE_PATH = DATABASE_DIR / "stocks.db"

# 디렉토리 생성
DATABASE_DIR.mkdir(parents=True, exist_ok=True)

# KIS API 설정 (환경 변수나 config 파일에서 로드 권장)
KIS_APP_KEY = ""
KIS_APP_SECRET = ""
KIS_ACCOUNT_NO = ""


# ==================================================================================
# Repository Instances (싱글톤)
# ==================================================================================

# Stock Repository (미국 + 한국)
yfinance_repo = YFinanceStockRepository(
    cache_ttl=300,
    db_path=str(DATABASE_PATH)
)

# KIS Repository (한국 실시간 - 선택적)
kis_repo = None
if KIS_APP_KEY and KIS_APP_SECRET:
    kis_repo = KISRepository(
        app_key=KIS_APP_KEY,
        app_secret=KIS_APP_SECRET,
        account_no=KIS_ACCOUNT_NO,
        is_virtual=True
    )

# Portfolio Repository
portfolio_repo_json = JSONPortfolioRepository()
portfolio_repo_session = SessionPortfolioRepository()

# News Repository
naver_news_repo = NaverNewsRepository()
google_news_repo = GoogleNewsRepository()


# ==================================================================================
# Service Instances (DI 적용)
# ==================================================================================

# Trading Signal Service
trading_signal_service = TradingSignalService(
    stock_repo=yfinance_repo
)

# Factor Scoring Service
factor_scoring_service = FactorScoringService(
    stock_repo=yfinance_repo
)

# Portfolio Management Service
portfolio_management_service = PortfolioManagementService(
    portfolio_repo=portfolio_repo_json,
    stock_repo=yfinance_repo
)

# Alert Orchestrator Service
alert_orchestrator_service = AlertOrchestratorService(
    stock_repo=yfinance_repo
)

# Technical Analysis Service (NEW)
technical_analysis_service = TechnicalAnalysisService(
    stock_repo=yfinance_repo
)

# Risk Management Service (NEW)
risk_management_service = RiskManagementService(
    stock_repo=yfinance_repo,
    portfolio_repo=portfolio_repo_json
)


# ==================================================================================
# Legacy Adapters (Deprecated - 점진적 제거 예정)
# ==================================================================================

# ⚠️ DEPRECATED: 대신 yfinance_repo 사용 권장
legacy_stock_collector = LegacyCollectorAdapter()

# ⚠️ DEPRECATED: 대신 naver_news_repo 또는 google_news_repo 사용 권장
legacy_news_collector = LegacyNewsAdapter()

# ⚠️ DEPRECATED: 대신 technical_analysis_service 사용 권장
legacy_analyzer = LegacyAnalyzerAdapter()


# ==================================================================================
# Public API (Streamlit UI에서 사용)
# ==================================================================================

__all__ = [
    # Repositories
    "yfinance_repo",
    "kis_repo",
    "portfolio_repo_json",
    "portfolio_repo_session",
    "naver_news_repo",
    "google_news_repo",
    
    # Services
    "trading_signal_service",
    "factor_scoring_service",
    "portfolio_management_service",
    "alert_orchestrator_service",
    "technical_analysis_service",
    "risk_management_service",
    
    # Legacy (Deprecated)
    "legacy_stock_collector",
    "legacy_news_collector",
    "legacy_analyzer"
]
