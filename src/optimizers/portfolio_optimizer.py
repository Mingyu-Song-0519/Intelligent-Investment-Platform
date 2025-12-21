"""
포트폴리오 최적화 모듈 - Markowitz 평균-분산 최적화
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from scipy.optimize import minimize
from pathlib import Path
import sys

# 프로젝트 루트 경로 설정
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class PortfolioOptimizer:
    """Markowitz 평균-분산 최적화 클래스"""
    
    def __init__(
        self,
        returns_df: pd.DataFrame,
        risk_free_rate: float = 0.035
    ):
        """
        Args:
            returns_df: 일별 수익률 DataFrame (각 컬럼이 종목)
            risk_free_rate: 무위험 수익률 (연간)
        """
        self.returns = returns_df.dropna()
        self.risk_free_rate = risk_free_rate
        self.tickers = list(returns_df.columns)
        self.num_assets = len(self.tickers)
        
        # 예상 수익률 및 공분산 행렬 계산
        self.expected_returns = self.returns.mean() * 252  # 연환산
        self.cov_matrix = self.returns.cov() * 252  # 연환산
        
        # 최적화 결과 저장
        self.optimal_weights = None
        self.efficient_frontier = None
    
    def portfolio_return(self, weights: np.ndarray) -> float:
        """포트폴리오 기대 수익률"""
        return np.dot(weights, self.expected_returns)
    
    def portfolio_volatility(self, weights: np.ndarray) -> float:
        """포트폴리오 변동성 (표준편차)"""
        return np.sqrt(np.dot(weights.T, np.dot(self.cov_matrix, weights)))
    
    def portfolio_sharpe(self, weights: np.ndarray) -> float:
        """포트폴리오 샤프 비율"""
        ret = self.portfolio_return(weights)
        vol = self.portfolio_volatility(weights)
        if vol == 0:
            return 0
        return (ret - self.risk_free_rate) / vol
    
    def negative_sharpe(self, weights: np.ndarray) -> float:
        """샤프 비율의 음수 (최소화용)"""
        return -self.portfolio_sharpe(weights)
    
    def optimize_max_sharpe(self) -> Dict:
        """
        최대 샤프 비율 포트폴리오 계산
        
        Returns:
            최적화 결과 딕셔너리
        """
        constraints = (
            {'type': 'eq', 'fun': lambda x: np.sum(x) - 1}  # 비중 합 = 1
        )
        bounds = tuple((0, 1) for _ in range(self.num_assets))  # 0 <= w <= 1
        initial_weights = np.array([1/self.num_assets] * self.num_assets)
        
        result = minimize(
            self.negative_sharpe,
            initial_weights,
            method='SLSQP',
            bounds=bounds,
            constraints=constraints
        )
        
        if result.success:
            self.optimal_weights = result.x
            return {
                'weights': dict(zip(self.tickers, result.x)),
                'return': self.portfolio_return(result.x),
                'volatility': self.portfolio_volatility(result.x),
                'sharpe': self.portfolio_sharpe(result.x),
                'success': True
            }
        else:
            return {'success': False, 'message': result.message}
    
    def optimize_min_volatility(self) -> Dict:
        """
        최소 변동성 포트폴리오 계산
        
        Returns:
            최적화 결과 딕셔너리
        """
        constraints = (
            {'type': 'eq', 'fun': lambda x: np.sum(x) - 1}
        )
        bounds = tuple((0, 1) for _ in range(self.num_assets))
        initial_weights = np.array([1/self.num_assets] * self.num_assets)
        
        result = minimize(
            self.portfolio_volatility,
            initial_weights,
            method='SLSQP',
            bounds=bounds,
            constraints=constraints
        )
        
        if result.success:
            return {
                'weights': dict(zip(self.tickers, result.x)),
                'return': self.portfolio_return(result.x),
                'volatility': self.portfolio_volatility(result.x),
                'sharpe': self.portfolio_sharpe(result.x),
                'success': True
            }
        else:
            return {'success': False, 'message': result.message}
    
    def optimize_target_return(self, target_return: float) -> Dict:
        """
        목표 수익률을 달성하는 최소 변동성 포트폴리오
        
        Args:
            target_return: 목표 연간 수익률
            
        Returns:
            최적화 결과 딕셔너리
        """
        constraints = (
            {'type': 'eq', 'fun': lambda x: np.sum(x) - 1},
            {'type': 'eq', 'fun': lambda x: self.portfolio_return(x) - target_return}
        )
        bounds = tuple((0, 1) for _ in range(self.num_assets))
        initial_weights = np.array([1/self.num_assets] * self.num_assets)
        
        result = minimize(
            self.portfolio_volatility,
            initial_weights,
            method='SLSQP',
            bounds=bounds,
            constraints=constraints
        )
        
        if result.success:
            return {
                'weights': dict(zip(self.tickers, result.x)),
                'return': self.portfolio_return(result.x),
                'volatility': self.portfolio_volatility(result.x),
                'sharpe': self.portfolio_sharpe(result.x),
                'success': True
            }
        else:
            return {'success': False, 'message': result.message}
    
    def calculate_efficient_frontier(
        self, 
        num_portfolios: int = 100
    ) -> pd.DataFrame:
        """
        효율적 투자선 계산
        
        Args:
            num_portfolios: 효율적 투자선 포인트 수
            
        Returns:
            효율적 투자선 DataFrame
        """
        # 수익률 범위 결정
        min_ret = self.expected_returns.min()
        max_ret = self.expected_returns.max()
        target_returns = np.linspace(min_ret, max_ret, num_portfolios)
        
        frontier_data = []
        for target in target_returns:
            result = self.optimize_target_return(target)
            if result['success']:
                frontier_data.append({
                    'return': result['return'],
                    'volatility': result['volatility'],
                    'sharpe': result['sharpe']
                })
        
        self.efficient_frontier = pd.DataFrame(frontier_data)
        return self.efficient_frontier
    
    def generate_random_portfolios(
        self, 
        num_portfolios: int = 5000
    ) -> pd.DataFrame:
        """
        랜덤 포트폴리오 생성 (Monte Carlo 시뮬레이션)
        
        Args:
            num_portfolios: 생성할 포트폴리오 수
            
        Returns:
            랜덤 포트폴리오 DataFrame
        """
        results = []
        
        for _ in range(num_portfolios):
            # 랜덤 비중 생성
            weights = np.random.random(self.num_assets)
            weights /= weights.sum()  # 합이 1이 되도록 정규화
            
            ret = self.portfolio_return(weights)
            vol = self.portfolio_volatility(weights)
            sharpe = self.portfolio_sharpe(weights)
            
            result = {
                'return': ret,
                'volatility': vol,
                'sharpe': sharpe
            }
            # 각 종목 비중 추가
            for i, ticker in enumerate(self.tickers):
                result[ticker] = weights[i]
            
            results.append(result)
        
        return pd.DataFrame(results)
    
    def get_asset_statistics(self) -> pd.DataFrame:
        """
        개별 자산 통계
        
        Returns:
            자산별 통계 DataFrame
        """
        stats = pd.DataFrame({
            '기대수익률 (연간)': self.expected_returns,
            '변동성 (연간)': np.sqrt(np.diag(self.cov_matrix)),
            '샤프비율': (self.expected_returns - self.risk_free_rate) / np.sqrt(np.diag(self.cov_matrix))
        })
        return stats
    
    def get_correlation_matrix(self) -> pd.DataFrame:
        """상관계수 행렬"""
        return self.returns.corr()
    
    def get_equal_weight_portfolio(self) -> Dict:
        """동일 비중 포트폴리오"""
        weights = np.array([1/self.num_assets] * self.num_assets)
        return {
            'weights': dict(zip(self.tickers, weights)),
            'return': self.portfolio_return(weights),
            'volatility': self.portfolio_volatility(weights),
            'sharpe': self.portfolio_sharpe(weights)
        }


# 사용 예시
if __name__ == "__main__":
    import yfinance as yf
    
    print("=== 포트폴리오 최적화 테스트 ===\n")
    
    # 테스트 종목
    tickers = ['005930.KS', '000660.KS', '035420.KS']  # 삼성전자, SK하이닉스, 네이버
    
    # 데이터 수집
    print("데이터 수집 중...")
    data = {}
    for ticker in tickers:
        df = yf.Ticker(ticker).history(period="1y")
        data[ticker] = df['Close'].pct_change()
    
    returns_df = pd.DataFrame(data).dropna()
    print(f"데이터 수집 완료: {len(returns_df)} 거래일\n")
    
    # 포트폴리오 최적화
    optimizer = PortfolioOptimizer(returns_df)
    
    # 자산 통계
    print("=== 개별 자산 통계 ===")
    print(optimizer.get_asset_statistics())
    
    # 최대 샤프 비율 포트폴리오
    print("\n=== 최대 샤프 비율 포트폴리오 ===")
    max_sharpe = optimizer.optimize_max_sharpe()
    if max_sharpe['success']:
        print(f"기대 수익률: {max_sharpe['return']:.2%}")
        print(f"변동성: {max_sharpe['volatility']:.2%}")
        print(f"샤프 비율: {max_sharpe['sharpe']:.2f}")
        print("비중:")
        for ticker, weight in max_sharpe['weights'].items():
            print(f"  {ticker}: {weight:.2%}")
    
    # 최소 변동성 포트폴리오
    print("\n=== 최소 변동성 포트폴리오 ===")
    min_vol = optimizer.optimize_min_volatility()
    if min_vol['success']:
        print(f"기대 수익률: {min_vol['return']:.2%}")
        print(f"변동성: {min_vol['volatility']:.2%}")
        print(f"샤프 비율: {min_vol['sharpe']:.2f}")
