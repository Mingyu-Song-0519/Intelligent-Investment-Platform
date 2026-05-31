"""
리스크 관리 모듈 - VaR, CVaR, 스트레스 테스팅
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from scipy import stats


class RiskManager:
    """
    리스크 관리 클래스
    
    VaR (Value at Risk): 특정 신뢰수준에서 최대 예상 손실
    CVaR (Conditional VaR): VaR을 초과하는 경우의 평균 손실
    """
    
    def __init__(
        self,
        returns: pd.Series,
        portfolio_value: float = 10_000_000
    ):
        """
        Args:
            returns: 일별 수익률 시리즈
            portfolio_value: 포트폴리오 가치 (원)
        """
        self.returns = returns.dropna()
        self.portfolio_value = portfolio_value
    
    # =========================================================================
    # VaR (Value at Risk) 계산
    # =========================================================================
    
    def historical_var(
        self, 
        confidence: float = 0.95,
        horizon: int = 1
    ) -> Dict:
        """
        Historical VaR (역사적 시뮬레이션)
        
        과거 수익률 분포를 기반으로 VaR 계산
        
        Args:
            confidence: 신뢰수준 (예: 0.95 = 95%)
            horizon: 투자 기간 (일)
            
        Returns:
            VaR 결과 딕셔너리
        """
        # 백분위수 계산
        var_percentile = (1 - confidence) * 100
        var_return = np.percentile(self.returns, var_percentile)
        
        # 다기간 조정 (제곱근 규칙)
        var_return_horizon = var_return * np.sqrt(horizon)
        
        # 손실금액 계산
        var_amount = abs(var_return_horizon * self.portfolio_value)
        
        return {
            'method': 'Historical',
            'confidence': confidence,
            'horizon_days': horizon,
            'var_return': var_return_horizon,
            'var_amount': var_amount,
            'description': f"{confidence*100:.0f}% 신뢰수준으로 {horizon}일 동안 최대 ₩{var_amount:,.0f} 손실 가능"
        }
    
    def parametric_var(
        self, 
        confidence: float = 0.95,
        horizon: int = 1
    ) -> Dict:
        """
        Parametric VaR (분산-공분산 방법)
        
        정규분포 가정 하에 VaR 계산
        
        Args:
            confidence: 신뢰수준
            horizon: 투자 기간 (일)
            
        Returns:
            VaR 결과 딕셔너리
        """
        if len(self.returns) == 0:
            return {
                'method': 'Parametric',
                'confidence': confidence,
                'horizon_days': horizon,
                'var_return': 0.0,
                'var_amount': 0.0
            }

        mean = self.returns.mean()
        std = self.returns.std()

        # Z-score 계산
        z_score = stats.norm.ppf(1 - confidence)
        
        # VaR 계산
        var_return = mean + z_score * std
        var_return_horizon = var_return * np.sqrt(horizon)
        var_amount = abs(var_return_horizon * self.portfolio_value)
        
        return {
            'method': 'Parametric',
            'confidence': confidence,
            'horizon_days': horizon,
            'var_return': var_return_horizon,
            'var_amount': var_amount,
            'mean': mean * 252,  # 연환산
            'std': std * np.sqrt(252),  # 연환산
            'description': f"{confidence*100:.0f}% 신뢰수준으로 {horizon}일 동안 최대 ₩{var_amount:,.0f} 손실 가능"
        }
    
    def monte_carlo_var(
        self, 
        confidence: float = 0.95,
        horizon: int = 1,
        simulations: int = 10000
    ) -> Dict:
        """
        Monte Carlo VaR
        
        시뮬레이션을 통한 VaR 계산
        
        Args:
            confidence: 신뢰수준
            horizon: 투자 기간 (일)
            simulations: 시뮬레이션 횟수
            
        Returns:
            VaR 결과 딕셔너리
        """
        if len(self.returns) == 0:
            return {
                'method': 'Monte Carlo',
                'confidence': confidence,
                'horizon_days': horizon,
                'var_return': 0.0,
                'var_amount': 0.0
            }

        mean = self.returns.mean()
        std = self.returns.std()

        # 시뮬레이션
        simulated_returns = np.random.normal(mean, std, simulations)
        
        # 다기간 조정
        simulated_returns_horizon = simulated_returns * np.sqrt(horizon)
        
        # VaR 계산
        var_percentile = (1 - confidence) * 100
        var_return = np.percentile(simulated_returns_horizon, var_percentile)
        var_amount = abs(var_return * self.portfolio_value)
        
        return {
            'method': 'Monte Carlo',
            'confidence': confidence,
            'horizon_days': horizon,
            'simulations': simulations,
            'var_return': var_return,
            'var_amount': var_amount,
            'description': f"{confidence*100:.0f}% 신뢰수준으로 {horizon}일 동안 최대 ₩{var_amount:,.0f} 손실 가능"
        }
    
    # =========================================================================
    # CVaR (Conditional VaR / Expected Shortfall)
    # =========================================================================
    
    def cvar(
        self, 
        confidence: float = 0.95,
        horizon: int = 1
    ) -> Dict:
        """
        CVaR (Conditional VaR) / Expected Shortfall
        
        VaR을 초과하는 손실의 평균
        
        Args:
            confidence: 신뢰수준
            horizon: 투자 기간 (일)
            
        Returns:
            CVaR 결과 딕셔너리
        """
        # VaR 임계값
        var_percentile = (1 - confidence) * 100
        var_threshold = np.percentile(self.returns, var_percentile)
        
        # VaR 이하 수익률의 평균 (더 큰 손실)
        tail_returns = self.returns[self.returns <= var_threshold]
        cvar_return = tail_returns.mean() if len(tail_returns) > 0 else var_threshold
        
        # 다기간 조정
        cvar_return_horizon = cvar_return * np.sqrt(horizon)
        cvar_amount = abs(cvar_return_horizon * self.portfolio_value)
        
        return {
            'method': 'CVaR (Expected Shortfall)',
            'confidence': confidence,
            'horizon_days': horizon,
            'cvar_return': cvar_return_horizon,
            'cvar_amount': cvar_amount,
            'num_tail_observations': len(tail_returns),
            'description': f"최악의 {(1-confidence)*100:.0f}% 시나리오에서 평균 ₩{cvar_amount:,.0f} 손실 예상"
        }
    
    # =========================================================================
    # 스트레스 테스팅
    # =========================================================================
    
    def stress_test(
        self, 
        scenarios: Optional[Dict[str, float]] = None
    ) -> pd.DataFrame:
        """
        스트레스 테스팅
        
        다양한 시나리오에서 포트폴리오 손실 계산
        
        Args:
            scenarios: 시나리오별 시장 하락률 딕셔너리
                      예: {'금융위기': -0.50, '코로나': -0.30}
                      
        Returns:
            스트레스 테스트 결과 DataFrame
        """
        if scenarios is None:
            scenarios = {
                '2008 금융위기': -0.50,  # 50% 하락
                '2020 코로나': -0.30,    # 30% 하락
                '중간 조정': -0.15,      # 15% 하락
                '경미한 조정': -0.10,    # 10% 하락
                '플래시 크래시': -0.08,  # 8% 하락
            }
        
        results = []
        for scenario_name, market_drop in scenarios.items():
            # 베타 추정 (시장 대비 민감도, 간단히 1로 가정)
            beta = 1.0
            portfolio_drop = market_drop * beta
            loss_amount = abs(portfolio_drop * self.portfolio_value)
            
            results.append({
                '시나리오': scenario_name,
                '시장 하락률': f"{market_drop*100:.1f}%",
                '예상 손실률': f"{portfolio_drop*100:.1f}%",
                '예상 손실금액': f"₩{loss_amount:,.0f}",
                '잔여 가치': f"₩{self.portfolio_value + portfolio_drop * self.portfolio_value:,.0f}"
            })
        
        return pd.DataFrame(results)
    
    # =========================================================================
    # 리스크 요약 리포트
    # =========================================================================
    
    def get_risk_summary(
        self, 
        confidence: float = 0.95,
        horizon: int = 1
    ) -> Dict:
        """
        종합 리스크 요약
        
        Returns:
            리스크 요약 딕셔너리
        """
        historical = self.historical_var(confidence, horizon)
        parametric = self.parametric_var(confidence, horizon)
        monte_carlo = self.monte_carlo_var(confidence, horizon)
        cvar_result = self.cvar(confidence, horizon)
        
        return {
            'portfolio_value': self.portfolio_value,
            'confidence': confidence,
            'horizon_days': horizon,
            'historical_var': historical,
            'parametric_var': parametric,
            'monte_carlo_var': monte_carlo,
            'cvar': cvar_result,
            'statistics': {
                'mean_daily_return': self.returns.mean(),
                'std_daily_return': self.returns.std(),
                'skewness': self.returns.skew(),
                'kurtosis': self.returns.kurtosis(),
                'min_return': self.returns.min(),
                'max_return': self.returns.max()
            }
        }
    
    def print_risk_report(
        self, 
        confidence: float = 0.95,
        horizon: int = 1
    ):
        """리스크 리포트 출력"""
        summary = self.get_risk_summary(confidence, horizon)
        
        print("\n" + "=" * 60)
        print("⚠️ 리스크 분석 리포트")
        print("=" * 60)
        
        print(f"\n📊 기본 정보")
        print(f"  • 포트폴리오 가치: ₩{summary['portfolio_value']:,.0f}")
        print(f"  • 신뢰수준: {summary['confidence']*100:.0f}%")
        print(f"  • 분석 기간: {summary['horizon_days']}일")
        
        print(f"\n📉 VaR (Value at Risk)")
        print(f"  • Historical VaR: ₩{summary['historical_var']['var_amount']:,.0f}")
        print(f"  • Parametric VaR: ₩{summary['parametric_var']['var_amount']:,.0f}")
        print(f"  • Monte Carlo VaR: ₩{summary['monte_carlo_var']['var_amount']:,.0f}")
        
        print(f"\n🔻 CVaR (Expected Shortfall)")
        print(f"  • CVaR: ₩{summary['cvar']['cvar_amount']:,.0f}")
        
        print(f"\n📈 수익률 통계")
        stats = summary['statistics']
        print(f"  • 일평균 수익률: {stats['mean_daily_return']*100:.3f}%")
        print(f"  • 일별 변동성: {stats['std_daily_return']*100:.3f}%")
        print(f"  • 왜도: {stats['skewness']:.2f}")
        print(f"  • 첨도: {stats['kurtosis']:.2f}")
        
        print("\n" + "=" * 60)


# 사용 예시
if __name__ == "__main__":
    import yfinance as yf
    
    print("=== 리스크 관리 테스트 ===\n")
    
    # 삼성전자 데이터 수집
    ticker = yf.Ticker("005930.KS")
    df = ticker.history(period="2y")
    returns = df['Close'].pct_change().dropna()
    
    print(f"데이터 수집 완료: {len(returns)} 거래일\n")
    
    # 리스크 분석
    rm = RiskManager(returns, portfolio_value=10_000_000)
    
    # 리스크 리포트 출력
    rm.print_risk_report(confidence=0.95, horizon=10)
    
    # 스트레스 테스트
    print("\n=== 스트레스 테스트 ===")
    stress_results = rm.stress_test()
    print(stress_results.to_string(index=False))
