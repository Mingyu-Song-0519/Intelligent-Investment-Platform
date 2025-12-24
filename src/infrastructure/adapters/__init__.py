# Infrastructure Adapters __init__.py
from src.infrastructure.adapters.legacy_adapter import (
    LegacyCollectorAdapter,
    LegacyNewsAdapter,
    LegacyAnalyzerAdapter
)

__all__ = ["LegacyCollectorAdapter", "LegacyNewsAdapter", "LegacyAnalyzerAdapter"]
