"""
Portfolio Management Service - Application Layer
포트폴리오 관리 유즈케이스
"""
from typing import Dict, List, Optional
from datetime import datetime

from src.domain.entities.stock import PortfolioEntity, StockEntity
from src.domain.repositories.interfaces import IPortfolioRepository, IStockRepository


class PortfolioManagementService:
    """
    포트폴리오 관리 유즈케이스
    
    Clean Architecture:
    - 포트폴리오 생성/수정/삭제
    - 성과 분석
    - 리밸런싱 제안
    """
    
    def __init__(
        self,
        portfolio_repo: IPortfolioRepository,
        stock_repo: IStockRepository
    ):
        """
        Args:
            portfolio_repo: IPortfolioRepository 구현체 (DI)
            stock_repo: IStockRepository 구현체 (DI)
        """
        self.portfolio_repo = portfolio_repo
        self.stock_repo = stock_repo
    
    def create_portfolio(
        self,
        portfolio_id: str,
        name: str,
        holdings: Dict[str, float] = {},
        normalize: bool = True
    ) -> PortfolioEntity:
        """
        포트폴리오 생성
        
        Args:
            portfolio_id: 포트폴리오 ID
            name: 이름
            holdings: {ticker: 비중} 딕셔너리
            normalize: 비중 정규화 여부
            
        Returns:
            PortfolioEntity
        """
        portfolio = PortfolioEntity(
            portfolio_id=portfolio_id,
            name=name,
            holdings=holdings.copy()
        )
        
        if normalize and holdings:
            portfolio.normalize_weights()
        
        # 저장
        self.portfolio_repo.save(portfolio)
        
        return portfolio
    
    def add_stock_to_portfolio(
        self,
        portfolio_id: str,
        ticker: str,
        weight: float
    ) -> Optional[PortfolioEntity]:
        """
        포트폴리오에 종목 추가
        
        Args:
            portfolio_id: 포트폴리오 ID
            ticker: 종목 코드
            weight: 비중
        """
        portfolio = self.portfolio_repo.load(portfolio_id)
        
        if not portfolio:
            return None
        
        portfolio.add_holding(ticker, weight)
        self.portfolio_repo.save(portfolio)
        
        return portfolio
    
    def calculate_portfolio_return(
        self,
        portfolio_id: str,
        period: str = "1mo"
    ) -> Optional[Dict]:
        """
        포트폴리오 수익률 계산
        
        Args:
            portfolio_id: 포트폴리오 ID
            period: 분석 기간
            
        Returns:
            {
                "total_return": 전체 수익률 (%),
                "holdings_return": {ticker: 개별 수익률},
                "best_stock": 최고 수익 종목,
                "worst_stock": 최저 수익 종목
            }
        """
        portfolio = self.portfolio_repo.load(portfolio_id)
        
        if not portfolio or not portfolio.holdings:
            return None
        
        holdings_return = {}
        weighted_returns = []
        
        # 각 종목별 수익률 계산
        for ticker, weight in portfolio.holdings.items():
            stock = self.stock_repo.get_stock_data(ticker, period)
            
            if stock:
                # 30일 수익률 (또는 전체 기간)
                stock_return = stock.calculate_return(days=30) or 0
                holdings_return[ticker] = stock_return
                
                # 가중 수익률
                weighted_returns.append(stock_return * weight)
        
        if not weighted_returns:
            return None
        
        # 전체 수익률
        total_return = sum(weighted_returns)
        
        # 최고/최저 종목
        best_stock = max(holdings_return.items(), key=lambda x: x[1]) if holdings_return else ("", 0)
        worst_stock = min(holdings_return.items(), key=lambda x: x[1]) if holdings_return else ("", 0)
        
        return {
            "total_return": round(total_return, 2),
            "holdings_return": holdings_return,
            "best_stock": best_stock,
            "worst_stock": worst_stock
        }
    
    def calculate_portfolio_risk(
        self,
        portfolio_id: str,
        period: str = "1mo"
    ) -> Optional[Dict]:
        """
        포트폴리오 리스크 계산
        
        Returns:
            {
                "portfolio_volatility": 포트폴리오 변동성,
                "holdings_volatility": {ticker: 개별 변동성},
                "max_drawdown": 최대 낙폭
            }
        """
        portfolio = self.portfolio_repo.load(portfolio_id)
        
        if not portfolio or not portfolio.holdings:
            return None
        
        holdings_vol = {}
        weighted_vols = []
        max_dd = 0.0
        
        for ticker, weight in portfolio.holdings.items():
            stock = self.stock_repo.get_stock_data(ticker, period)
            
            if stock:
                # 변동성
                vol = stock.calculate_volatility(days=20) or 0
                holdings_vol[ticker] = vol
                weighted_vols.append(vol * weight)
                
                # MDD
                stock_mdd = stock.get_max_drawdown()
                max_dd = max(max_dd, stock_mdd)
        
        portfolio_vol = sum(weighted_vols) if weighted_vols else 0
        
        return {
            "portfolio_volatility": round(portfolio_vol, 2),
            "holdings_volatility": holdings_vol,
            "max_drawdown": round(max_dd, 2)
        }
    
    def suggest_rebalancing(
        self,
        portfolio_id: str,
        target_weights: Dict[str, float]
    ) -> Optional[Dict]:
        """
        리밸런싱 제안
        
        Args:
            portfolio_id: 포트폴리오 ID
            target_weights: 목표 비중
            
        Returns:
            {
                "current": 현재 비중,
                "target": 목표 비중,
                "diff": 차이,
                "actions": [{ticker: "AAPL", action: "BUY", amount: 5.0}, ...]
            }
        """
        portfolio = self.portfolio_repo.load(portfolio_id)
        
        if not portfolio:
            return None
        
        actions = []
        diff = {}
        
        # 모든 종목 확인 (현재 + 목표)
        all_tickers = set(portfolio.holdings.keys()) | set(target_weights.keys())
        
        for ticker in all_tickers:
            current = portfolio.holdings.get(ticker, 0.0)
            target = target_weights.get(ticker, 0.0)
            delta = target - current
            
            diff[ticker] = delta
            
            if delta > 0.01:  # 1% 이상 차이
                actions.append({
                    "ticker": ticker,
                    "action": "BUY",
                    "amount": round(delta * 100, 2)
                })
            elif delta < -0.01:
                actions.append({
                    "ticker": ticker,
                    "action": "SELL",
                    "amount": round(abs(delta) * 100, 2)
                })
        
        return {
            "current": portfolio.holdings,
            "target": target_weights,
            "diff": diff,
            "actions": actions
        }
