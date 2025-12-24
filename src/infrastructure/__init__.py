# Infrastructure Layer __init__.py
from src.infrastructure.repositories.stock_repository import YFinanceStockRepository, KISStockRepository
from src.infrastructure.adapters.legacy_adapter import (
    LegacyCollectorAdapter,
    LegacyNewsAdapter,
    LegacyAnalyzerAdapter
)

__all__ = [
    # Repositories
    "YFinanceStockRepository",
    "KISStockRepository",
    # Adapters
    "LegacyCollectorAdapter",
    "LegacyNewsAdapter",
    "LegacyAnalyzerAdapter"
]
