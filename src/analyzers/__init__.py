"""
⚠️ DEPRECATED: analyzers 패키지

이 패키지는 Clean Architecture 마이그레이션으로 인해 Deprecated 되었습니다.
대신 src.services 패키지를 사용하세요.

Migration Guide:
- VolatilityAnalyzer → from src.services import VolatilityAnalyzer
- MarketBreadthAnalyzer → from src.services import MarketBreadthAnalyzer
- MacroAnalyzer → from src.services import MacroAnalyzer
- FactorAnalyzer → from src.services import FactorAnalyzer
- RegimeClassifier → from src.services import RegimeClassifier
"""
import warnings

# 하위 호환성을 위해 기존 import 유지 (Deprecated)
from .technical_analyzer import TechnicalAnalyzer
from .sentiment_analyzer import SentimentAnalyzer

# 재배치된 모듈도 여기서 re-export (하위 호환성)
from .volatility_analyzer import VolatilityAnalyzer
from .market_breadth import MarketBreadthAnalyzer
from .macro_analyzer import MacroAnalyzer
from .factor_analyzer import FactorAnalyzer, FactorScreener
from .social_analyzer import GoogleTrendsAnalyzer, SocialTrendAnalyzer
from .regime_classifier import RegimeClassifier, RegimeAwareModelSelector

# Deprecated 경고 (일시적으로 비활성화)
# TODO: 모든 import를 src.services로 마이그레이션 후 활성화
# warnings.warn(
#     "src.analyzers 패키지는 Deprecated 되었습니다. "
#     "대신 src.services를 사용하세요.",
#     DeprecationWarning,
#     stacklevel=2
# )

__all__ = [
    'TechnicalAnalyzer', 
    'SentimentAnalyzer',
    'VolatilityAnalyzer',
    'MarketBreadthAnalyzer',
    'MacroAnalyzer',
    'FactorAnalyzer',
    'FactorScreener',
    'GoogleTrendsAnalyzer',
    'SocialTrendAnalyzer',
    'RegimeClassifier',
    'RegimeAwareModelSelector'
]
