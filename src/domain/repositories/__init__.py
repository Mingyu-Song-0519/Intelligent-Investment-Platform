# Repositories __init__.py
from src.domain.repositories.interfaces import (
    IStockRepository,
    IPortfolioRepository,
    INewsRepository,
    IIndicatorRepository,
    IKISRepository
)

__all__ = [
    "IStockRepository",
    "IPortfolioRepository", 
    "INewsRepository",
    "IIndicatorRepository",
    "IKISRepository"
]
