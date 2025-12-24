"""
Trading Signal Service - Application Layer (Use Case)
매매 신호 생성 유즈케이스
"""
from typing import Optional, Dict, List
from datetime import datetime

from src.domain.repositories.interfaces import IStockRepository, IIndicatorRepository
from src.domain.entities.stock import StockEntity, SignalEntity


class TradingSignalService:
    """
    매매 신호 생성 유즈케이스
    
    Clean Architecture:
    - Application Layer에서 비즈니스 로직 조율
    - Repository 인터페이스만 의존 (DIP)
    - UI/Infrastructure와 독립적
    """
    
    def __init__(
        self, 
        stock_repo: IStockRepository,
        indicator_adapter = None  # LegacyAnalyzerAdapter
    ):
        """
        Args:
            stock_repo: IStockRepository 구현체 (DI)
            indicator_adapter: 기술적 지표 분석 어댑터
        """
        self.stock_repo = stock_repo
        self.indicator_adapter = indicator_adapter
    
    def generate_signal(
        self, 
        ticker: str, 
        period: str = "1mo"
    ) -> Optional[SignalEntity]:
        """
        단일 종목 매매 신호 생성
        
        Args:
            ticker: 종목 코드
            period: 분석 기간
            
        Returns:
            SignalEntity 또는 None
        """
        # 1. 종목 데이터 조회 (Repository)
        stock = self.stock_repo.get_stock_data(ticker, period)
        
        if not stock or not stock.price_history:
            return None
        
        # 2. 기술적 분석 (Adapter or Domain Service)
        if self.indicator_adapter:
            signal = self.indicator_adapter.get_signal(stock)
        else:
            # 기본 규칙 기반 신호
            signal = self._generate_basic_signal(stock)
        
        return signal
    
    def generate_multiple_signals(
        self, 
        tickers: List[str], 
        period: str = "1mo"
    ) -> Dict[str, SignalEntity]:
        """
        여러 종목 매매 신호 일괄 생성
        
        Returns:
            {ticker: SignalEntity}
        """
        result = {}
        
        for ticker in tickers:
            signal = self.generate_signal(ticker, period)
            if signal:
                result[ticker] = signal
        
        return result
    
    def _generate_basic_signal(self, stock: StockEntity) -> SignalEntity:
        """기본 규칙 기반 신호 생성 (폴백)"""
        
        # 간단한 모멘텀 전략
        if len(stock.price_history) < 5:
            return SignalEntity(
                ticker=stock.ticker,
                signal_type=SignalEntity.SignalType.HOLD,
                confidence=0.3,
                reason="데이터 부족"
            )
        
        # 5일 수익률 계산
        recent_prices = [p.close for p in stock.price_history[-5:]]
        return_5d = (recent_prices[-1] - recent_prices[0]) / recent_prices[0] * 100
        
        if return_5d > 5:
            signal_type = SignalEntity.SignalType.SELL
            reason = f"5일 급등 ({return_5d:.1f}%)"
        elif return_5d < -5:
            signal_type = SignalEntity.SignalType.BUY
            reason = f"5일 급락 ({return_5d:.1f}%)"
        else:
            signal_type = SignalEntity.SignalType.HOLD
            reason = f"횡보 ({return_5d:.1f}%)"
        
        return SignalEntity(
            ticker=stock.ticker,
            signal_type=signal_type,
            confidence=0.5,
            reason=reason,
            source="BASIC"
        )


class FactorScoringService:
    """
    팩터 스코어링 유즈케이스 (Phase 11 준비)
    """
    
    def __init__(self, stock_repo: IStockRepository):
        self.stock_repo = stock_repo
    
    def calculate_factor_scores(
        self, 
        ticker: str
    ) -> Dict[str, float]:
        """
        멀티팩터 스코어 계산
        
        Returns:
            {
                "momentum": 12개월 모멘텀 점수,
                "value": 가치 점수,
                "quality": 품질 점수,
                "volatility": 저변동성 점수,
                "composite": 종합 점수
            }
        """
        # Phase 11에서 상세 구현 예정
        stock = self.stock_repo.get_stock_data(ticker, period="1y")
        info = self.stock_repo.get_stock_info(ticker)
        
        if not stock or not info:
            return {}
        
        scores = {
            "momentum": self._momentum_score(stock),
            "value": self._value_score(info),
            "quality": self._quality_score(info),
            "volatility": self._volatility_score(stock),
        }
        
        # 종합 점수 (균등 가중)
        valid_scores = [s for s in scores.values() if s is not None]
        scores["composite"] = sum(valid_scores) / len(valid_scores) if valid_scores else 50
        
        return scores
    
    def _momentum_score(self, stock: StockEntity) -> float:
        """12개월 수익률 기반 모멘텀 점수 (0-100)"""
        if len(stock.price_history) < 252:  # 1년 데이터 필요
            return 50  # 중립
        
        start_price = stock.price_history[0].close
        end_price = stock.price_history[-1].close
        return_1y = (end_price - start_price) / start_price * 100
        
        # -50% ~ +100% → 0 ~ 100 점
        score = (return_1y + 50) / 1.5
        return max(0, min(100, score))
    
    def _value_score(self, info: Dict) -> float:
        """PER, PBR 기반 가치 점수"""
        pe = info.get("pe_ratio")
        pb = info.get("pb_ratio")
        
        if not pe and not pb:
            return 50
        
        # 낮을수록 좋음 (역수 사용)
        score = 50
        if pe and pe > 0:
            pe_score = max(0, 100 - pe * 2)  # PER 50 이상 → 0점
            score = (score + pe_score) / 2
        if pb and pb > 0:
            pb_score = max(0, 100 - pb * 20)  # PBR 5 이상 → 0점
            score = (score + pb_score) / 2
        
        return score
    
    def _quality_score(self, info: Dict) -> float:
        """ROE 기반 품질 점수"""
        roe = info.get("roe")
        
        if not roe:
            return 50
        
        # ROE 0~30% → 0~100점
        return min(100, max(0, roe * 100 / 0.3))
    
    def _volatility_score(self, stock: StockEntity) -> float:
        """저변동성 팩터 점수 (낮을수록 좋음)"""
        if len(stock.price_history) < 20:
            return 50
        
        # 일간 수익률 표준편차
        prices = [p.close for p in stock.price_history[-60:]]
        returns = [(prices[i] - prices[i-1]) / prices[i-1] for i in range(1, len(prices))]
        
        if not returns:
            return 50
        
        import statistics
        std = statistics.stdev(returns) * 100  # 백분율
        
        # 변동성 2% 이하 → 100점, 5% 이상 → 0점
        score = 100 - (std - 2) * 33
        return max(0, min(100, score))
