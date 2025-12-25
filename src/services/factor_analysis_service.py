"""
Factor Analyzer - 멀티팩터 분석 모듈
Fama-French 5팩터 + 추가 팩터 기반 종목 스코어링

Phase 11: Clean Architecture 기반으로 구현
"""
from typing import Dict, Optional, List
from dataclasses import dataclass
import pandas as pd
import numpy as np

from src.domain.entities.stock import StockEntity
from src.domain.repositories.interfaces import IStockRepository


@dataclass
class FactorScores:
    """팩터 스코어 결과"""
    ticker: str
    momentum: float  # 모멘텀 팩터 (0-100)
    value: float     # 가치 팩터 (0-100)
    quality: float   # 품질 팩터 (0-100)
    size: float      # 규모 팩터 (0-100)
    volatility: float  # 저변동성 팩터 (0-100)
    composite: float  # 종합 점수 (0-100)
    
    def to_dict(self) -> Dict:
        return {
            "ticker": self.ticker,
            "momentum": round(self.momentum, 2),
            "value": round(self.value, 2),
            "quality": round(self.quality, 2),
            "size": round(self.size, 2),
            "volatility": round(self.volatility, 2),
            "composite": round(self.composite, 2)
        }


class FactorAnalyzer:
    """
    Fama-French 5팩터 + 저변동성 팩터 분석
    
    팩터 설명:
    1. Momentum (모멘텀): 12개월 수익률 (최근 1개월 제외)
    2. Value (가치): PER, PBR이 낮을수록 높은 점수
    3. Quality (품질): ROE, 이익 마진이 높을수록 높은 점수
    4. Size (규모): 시가총액 (중소형주 선호)
    5. Volatility (저변동성): 변동성이 낮을수록 높은 점수
    """
    
    def __init__(self, market: str = "US"):
        """
        Args:
            market: "US" (미국 주식) 또는 "KR" (한국 주식)
                    Phase 11 1차: 미국 주식만 지원
        """
        self.market = market
        
        # 팩터 가중치 (커스터마이징 가능)
        self.weights = {
            "momentum": 0.2,
            "value": 0.2,
            "quality": 0.2,
            "size": 0.2,
            "volatility": 0.2
        }
    
    def analyze(
        self,
        stock: StockEntity,
        stock_info: Optional[Dict] = None
    ) -> FactorScores:
        """
        종목에 대한 전체 팩터 분석
        
        Args:
            stock: StockEntity (가격 데이터)
            stock_info: 종목 기본 정보 (PER, ROE 등)
            
        Returns:
            FactorScores
        """
        scores = {
            "momentum": self.momentum_score(stock),
            "value": self.value_score(stock_info) if stock_info else 50.0,
            "quality": self.quality_score(stock_info) if stock_info else 50.0,
            "size": self.size_score(stock_info) if stock_info else 50.0,
            "volatility": self.volatility_score(stock)
        }
        
        # 종합 점수 (가중 평균)
        composite = sum(
            scores[factor] * self.weights[factor]
            for factor in scores.keys()
        )
        
        return FactorScores(
            ticker=stock.ticker,
            momentum=scores["momentum"],
            value=scores["value"],
            quality=scores["quality"],
            size=scores["size"],
            volatility=scores["volatility"],
            composite=composite
        )
    
    def momentum_score(self, stock: StockEntity) -> float:
        """
        모멘텀 팩터 (0-100)
        
        12개월 수익률 기반 (최근 1개월 제외)
        - Fama-French 원칙: 단기 반전 효과 제거
        """
        if len(stock.price_history) < 252:  # 1년 데이터 필요
            return 50.0  # 중립
        
        # 11개월 수익률 (12개월 - 최근 1개월)
        start_idx = -252
        end_idx = -21  # 최근 1개월(21 거래일) 제외
        
        start_price = stock.price_history[start_idx].close
        end_price = stock.price_history[end_idx].close
        
        if start_price == 0:
            return 50.0
        
        return_11m = (end_price - start_price) / start_price * 100
        
        # 점수 변환: -50% ~ +100% → 0 ~ 100점
        score = (return_11m + 50) / 1.5
        
        return max(0, min(100, score))
    
    def value_score(self, stock_info: Dict) -> float:
        """
        가치 팩터 (0-100)
        
        PER, PBR이 낮을수록 높은 점수
        """
        if not stock_info:
            return 50.0
        
        pe = stock_info.get("pe_ratio")
        pb = stock_info.get("pb_ratio")
        
        if not pe and not pb:
            return 50.0
        
        scores = []
        
        # PER 점수 (낮을수록 좋음)
        if pe and pe > 0:
            # PER 0~50 → 100~0점
            pe_score = max(0, 100 - pe * 2)
            scores.append(pe_score)
        
        # PBR 점수 (낮을수록 좋음)
        if pb and pb > 0:
            # PBR 0~5 → 100~0점
            pb_score = max(0, 100 - pb * 20)
            scores.append(pb_score)
        
        return sum(scores) / len(scores) if scores else 50.0
    
    def quality_score(self, stock_info: Dict) -> float:
        """
        품질 팩터 (0-100)
        
        ROE, 이익 마진이 높을수록 높은 점수
        """
        if not stock_info:
            return 50.0
        
        roe = stock_info.get("roe")
        profit_margin = stock_info.get("profit_margin")
        
        if not roe and not profit_margin:
            return 50.0
        
        scores = []
        
        # ROE 점수 (높을수록 좋음)
        if roe:
            # ROE 0~30% → 0~100점
            roe_score = min(100, max(0, roe * 100 / 0.3))
            scores.append(roe_score)
        
        # 이익 마진 점수
        if profit_margin:
            # Profit Margin 0~20% → 0~100점
            margin_score = min(100, max(0, profit_margin * 100 / 0.2))
            scores.append(margin_score)
        
        return sum(scores) / len(scores) if scores else 50.0
    
    def size_score(self, stock_info: Dict) -> float:
        """
        규모 팩터 (0-100)
        
        Fama-French: 중소형주가 대형주보다 높은 수익
        시가총액이 작을수록 높은 점수
        """
        if not stock_info:
            return 50.0
        
        market_cap = stock_info.get("market_cap")
        
        if not market_cap or market_cap <= 0:
            return 50.0
        
        # 미국 주식 기준
        # 시총 1조 달러 이상 → 0점
        # 시총 100억 달러 이하 → 100점
        
        cap_billion = market_cap / 1e9
        
        if cap_billion >= 1000:  # 1조 이상 (대형주)
            return 0
        elif cap_billion <= 10:  # 100억 이하 (소형주)
            return 100
        else:
            # 로그 스케일 점수
            score = 100 - (np.log10(cap_billion) - 1) / 2 * 100
            return max(0, min(100, score))
    
    def volatility_score(self, stock: StockEntity) -> float:
        """
        저변동성 팩터 (0-100)
        
        변동성이 낮을수록 높은 점수
        """
        vol = stock.calculate_volatility(days=60)
        
        if vol is None:
            return 50.0
        
        # 연율화 변동성 기준
        # 10% 이하 → 100점
        # 50% 이상 → 0점
        
        if vol <= 10:
            return 100
        elif vol >= 50:
            return 0
        else:
            score = 100 - (vol - 10) * 2.5
            return max(0, min(100, score))
    
    def set_custom_weights(self, weights: Dict[str, float]):
        """
        팩터 가중치 커스터마이징
        
        Args:
            weights: {"momentum": 0.3, "value": 0.2, ...}
        """
        total = sum(weights.values())
        if abs(total - 1.0) > 0.01:
            raise ValueError(f"가중치 합계는 1.0이어야 합니다 (현재: {total})")
        
        self.weights.update(weights)


class FactorScreener:
    """
    멀티팩터 기반 종목 스크리닝
    
    사용 예:
        screener = FactorScreener(stock_repo)
        top_stocks = screener.screen_top_stocks(["AAPL", "MSFT", ...], top_n=10)
    """
    
    def __init__(self, stock_repo: IStockRepository, market: str = "US"):
        """
        Args:
            stock_repo: IStockRepository 구현체 (DI)
            market: 시장 코드
        """
        self.stock_repo = stock_repo
        self.analyzer = FactorAnalyzer(market=market)
    
    def screen_top_stocks(
        self,
        tickers: List[str],
        top_n: int = 10,
        sort_by: str = "composite"
    ) -> List[FactorScores]:
        """
        종목 스크리닝 (팩터 점수 기준)
        
        Args:
            tickers: 종목 코드 리스트
            top_n: 상위 N개
            sort_by: 정렬 기준 ("composite", "momentum", "value" 등)
            
        Returns:
            FactorScores 리스트 (정렬됨)
        """
        results = []
        
        for ticker in tickers:
            # 가격 데이터
            stock = self.stock_repo.get_stock_data(ticker, period="1y")
            if not stock:
                continue
            
            # 기본 정보 (PER, ROE 등)
            stock_info = self.stock_repo.get_stock_info(ticker)
            
            # 팩터 분석
            scores = self.analyzer.analyze(stock, stock_info)
            results.append(scores)
        
        # 정렬
        results.sort(key=lambda x: getattr(x, sort_by), reverse=True)
        
        return results[:top_n]
    
    def get_factor_distribution(
        self,
        tickers: List[str]
    ) -> Dict:
        """
        팩터별 분포 통계
        
        Returns:
            {
                "momentum": {"mean": 60, "std": 20, ...},
                "value": {...},
                ...
            }
        """
        all_scores = []
        
        for ticker in tickers:
            stock = self.stock_repo.get_stock_data(ticker, period="1y")
            if not stock:
                continue
            
            stock_info = self.stock_repo.get_stock_info(ticker)
            scores = self.analyzer.analyze(stock, stock_info)
            all_scores.append(scores)
        
        if not all_scores:
            return {}
        
        # 통계 계산
        factors = ["momentum", "value", "quality", "size", "volatility", "composite"]
        distribution = {}
        
        for factor in factors:
            values = [getattr(s, factor) for s in all_scores]
            
            distribution[factor] = {
                "mean": round(np.mean(values), 2),
                "std": round(np.std(values), 2),
                "min": round(min(values), 2),
                "max": round(max(values), 2)
            }
        
        return distribution
