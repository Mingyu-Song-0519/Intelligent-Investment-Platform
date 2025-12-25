"""
Risk Management Service - Application Layer
리스크 관리를 위한 Application Service
"""
from typing import Dict, List, Optional
import numpy as np

from src.domain.repositories.interfaces import IStockRepository, IPortfolioRepository
from src.domain.entities.stock import PortfolioEntity


class RiskManagementService:
    """
    리스크 관리 Service
    
    DI: IStockRepository, IPortfolioRepository를 주입받아 사용
    """
    
    def __init__(
        self, 
        stock_repo: IStockRepository,
        portfolio_repo: Optional[IPortfolioRepository] = None
    ):
        """
        Args:
            stock_repo: IStockRepository 구현체
            portfolio_repo: IPortfolioRepository 구현체 (옵션)
        """
        self.stock_repo = stock_repo
        self.portfolio_repo = portfolio_repo
    
    def calculate_portfolio_risk(
        self, 
        portfolio: PortfolioEntity,
        confidence_level: float = 0.95
    ) -> Dict:
        """
        포트폴리오 리스크 계산
        
        Args:
            portfolio: 포트폴리오 Entity
            confidence_level: 신뢰 수준 (기본값: 95%)
            
        Returns:
            {
                'var': float,          # Value at Risk
                'cvar': float,         # Conditional VaR
                'volatility': float,   # 포트폴리오 변동성
                'sharpe_ratio': float  # 샤프 비율
            }
        """
        try:
            # 포트폴리오 내 종목들의 수익률 계산
            returns = []
            weights = []
            
            for ticker, weight in portfolio.holdings.items():
                stock = self.stock_repo.get_stock_data(ticker, period="3mo")
                if stock:
                    ret = stock.calculate_return()
                    if ret:
                        returns.append(ret)
                        weights.append(weight)
            
            if not returns:
                return None
            
            # 포트폴리오 수익률
            portfolio_return = np.dot(returns, weights)
            
            # 간단한 변동성 계산 (개별 종목 변동성의 가중 평균)
            volatilities = []
            for ticker in portfolio.holdings.keys():
                stock = self.stock_repo.get_stock_data(ticker, period="3mo")
                if stock:
                    vol = stock.calculate_volatility()
                    if vol:
                        volatilities.append(vol)
            
            portfolio_vol = np.mean(volatilities) if volatilities else 0
            
            # VaR 계산 (간단화된 버전)
            var = portfolio_vol * 1.65  # 95% 신뢰 수준
            cvar = portfolio_vol * 2.0  # Conditional VaR
            
            # 샤프 비율 (간단화: 무위험 이자율 0 가정)
            sharpe = portfolio_return / portfolio_vol if portfolio_vol > 0 else 0
            
            return {
                'var': var,
                'cvar': cvar,
                'volatility': portfolio_vol,
                'sharpe_ratio': sharpe
            }
            
        except Exception as e:
            print(f"[ERROR] RiskManagementService.calculate_portfolio_risk: {e}")
            return None
    
    def check_risk_limits(
        self, 
        portfolio: PortfolioEntity,
        max_volatility: float = 0.3,
        min_sharpe: float = 0.5
    ) -> List[str]:
        """
        리스크 한도 체크
        
        Args:
            portfolio: 포트폴리오 Entity
            max_volatility: 최대 허용 변동성
            min_sharpe: 최소 샤프 비율
            
        Returns:
            경고 메시지 리스트
        """
        warnings = []
        
        risk_metrics = self.calculate_portfolio_risk(portfolio)
        
        if not risk_metrics:
            warnings.append("리스크 계산 실패")
            return warnings
        
        # 변동성 체크
        if risk_metrics['volatility'] > max_volatility:
            warnings.append(
                f"⚠️ 변동성 초과: {risk_metrics['volatility']:.2%} > {max_volatility:.2%}"
            )
        
        # 샤프 비율 체크
        if risk_metrics['sharpe_ratio'] < min_sharpe:
            warnings.append(
                f"⚠️ 샤프 비율 부족: {risk_metrics['sharpe_ratio']:.2f} < {min_sharpe:.2f}"
            )
        
        return warnings
