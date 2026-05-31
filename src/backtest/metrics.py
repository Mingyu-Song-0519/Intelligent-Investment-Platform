"""
성과 지표 모듈 - 수익률, 위험, 거래 통계 계산
"""
import pandas as pd
import numpy as np
from typing import Optional, Dict


class PerformanceMetrics:
    """백테스팅 성과 지표 계산 클래스"""
    
    def __init__(
        self, 
        equity_curve: pd.Series, 
        initial_capital: float,
        risk_free_rate: float = 0.035  # 연 3.5% 무위험 수익률
    ):
        """
        Args:
            equity_curve: 포트폴리오 가치 시리즈
            initial_capital: 초기 자본금
            risk_free_rate: 무위험 수익률 (연간)
        """
        self.equity_curve = equity_curve
        self.initial_capital = initial_capital
        self.risk_free_rate = risk_free_rate
        self.daily_returns = equity_curve.pct_change().dropna()
    
    # =========================================================================
    # 수익성 지표
    # =========================================================================
    
    def total_return(self) -> float:
        """총 수익률"""
        if self.equity_curve.empty:
            return 0.0
        return (self.equity_curve.iloc[-1] - self.initial_capital) / self.initial_capital
    
    def cagr(self) -> float:
        """연환산 수익률 (CAGR)"""
        if self.equity_curve.empty:
            return 0.0
        total_days = len(self.equity_curve)
        years = total_days / 252  # 거래일 기준

        if years <= 0:
            return 0.0

        total_return = self.equity_curve.iloc[-1] / self.initial_capital
        return (total_return ** (1 / years)) - 1
    
    def profit_factor(self, trades_df: pd.DataFrame) -> float:
        """수익 팩터 (총이익 / 총손실)"""
        if trades_df.empty or 'pnl' not in trades_df.columns:
            return 0.0
        
        gross_profit = trades_df[trades_df['pnl'] > 0]['pnl'].sum()
        gross_loss = abs(trades_df[trades_df['pnl'] < 0]['pnl'].sum())
        
        if gross_loss == 0:
            return float('inf') if gross_profit > 0 else 0.0
        
        return gross_profit / gross_loss
    
    # =========================================================================
    # 위험 지표
    # =========================================================================
    
    def max_drawdown(self) -> float:
        """최대 낙폭 (MDD)"""
        cumulative_max = self.equity_curve.cummax()
        drawdown = (self.equity_curve - cumulative_max) / cumulative_max
        return drawdown.min()
    
    def max_drawdown_duration(self) -> int:
        """최대 낙폭 기간 (일)"""
        cumulative_max = self.equity_curve.cummax()
        drawdown = self.equity_curve < cumulative_max
        
        max_duration = 0
        current_duration = 0
        
        for is_dd in drawdown:
            if is_dd:
                current_duration += 1
                max_duration = max(max_duration, current_duration)
            else:
                current_duration = 0
        
        return max_duration
    
    def volatility(self) -> float:
        """연환산 변동성"""
        return self.daily_returns.std() * np.sqrt(252)
    
    def downside_volatility(self) -> float:
        """하방 변동성 (음의 수익률만)"""
        negative_returns = self.daily_returns[self.daily_returns < 0]
        if len(negative_returns) == 0:
            return 0.0
        return negative_returns.std() * np.sqrt(252)
    
    # =========================================================================
    # 위험 조정 수익률
    # =========================================================================
    
    def sharpe_ratio(self) -> float:
        """샤프 비율"""
        excess_return = self.cagr() - self.risk_free_rate
        volatility = self.volatility()
        
        if volatility == 0:
            return 0.0
        
        return excess_return / volatility
    
    def sortino_ratio(self) -> float:
        """소르티노 비율 (하방 위험 조정)"""
        excess_return = self.cagr() - self.risk_free_rate
        downside_vol = self.downside_volatility()
        
        if downside_vol == 0:
            return 0.0
        
        return excess_return / downside_vol
    
    def calmar_ratio(self) -> float:
        """칼마 비율 (CAGR / MDD)"""
        mdd = abs(self.max_drawdown())
        
        if mdd == 0:
            return 0.0
        
        return self.cagr() / mdd
    
    # =========================================================================
    # 거래 통계
    # =========================================================================
    
    def win_rate(self, trades_df: pd.DataFrame) -> float:
        """승률"""
        if trades_df.empty or 'pnl' not in trades_df.columns:
            return 0.0
        
        total_trades = len(trades_df)
        winning_trades = len(trades_df[trades_df['pnl'] > 0])
        
        return winning_trades / total_trades if total_trades > 0 else 0.0
    
    def avg_win(self, trades_df: pd.DataFrame) -> float:
        """평균 수익"""
        if trades_df.empty or 'pnl' not in trades_df.columns:
            return 0.0
        
        winners = trades_df[trades_df['pnl'] > 0]['pnl']
        return winners.mean() if len(winners) > 0 else 0.0
    
    def avg_loss(self, trades_df: pd.DataFrame) -> float:
        """평균 손실"""
        if trades_df.empty or 'pnl' not in trades_df.columns:
            return 0.0
        
        losers = trades_df[trades_df['pnl'] < 0]['pnl']
        return losers.mean() if len(losers) > 0 else 0.0
    
    def avg_trade_duration(self, trades_df: pd.DataFrame) -> float:
        """평균 거래 기간 (일)"""
        if trades_df.empty:
            return 0.0
        
        if 'entry_date' in trades_df.columns and 'exit_date' in trades_df.columns:
            durations = (pd.to_datetime(trades_df['exit_date']) - 
                        pd.to_datetime(trades_df['entry_date'])).dt.days
            return durations.mean()
        
        return 0.0
    
    # =========================================================================
    # 종합 리포트
    # =========================================================================
    
    def get_all_metrics(self, trades_df: Optional[pd.DataFrame] = None) -> Dict:
        """모든 지표를 딕셔너리로 반환"""
        if self.equity_curve.empty:
            return {}
        metrics = {
            # 수익성
            'total_return': self.total_return(),
            'cagr': self.cagr(),
            'final_equity': self.equity_curve.iloc[-1],
            '총 수익률': self.total_return(),
            '연환산 수익률 (CAGR)': self.cagr(),
            '최종 자산': self.equity_curve.iloc[-1],
            
            # 위험
            'max_drawdown': self.max_drawdown(),
            'max_dd_duration': self.max_drawdown_duration(),
            'volatility': self.volatility(),
            '최대 낙폭 (MDD)': self.max_drawdown(),
            'MDD 기간 (일)': self.max_drawdown_duration(),
            '연환산 변동성': self.volatility(),
            
            # 위험 조정 수익률
            'sharpe_ratio': self.sharpe_ratio(),
            'sortino_ratio': self.sortino_ratio(),
            'calmar_ratio': self.calmar_ratio(),
            '샤프 비율': self.sharpe_ratio(),
            '소르티노 비율': self.sortino_ratio(),
            '칼마 비율': self.calmar_ratio(),
        }
        
        if trades_df is not None and not trades_df.empty:
            metrics.update({
                'total_trades': len(trades_df),
                'win_rate': self.win_rate(trades_df),
                'profit_factor': self.profit_factor(trades_df),
                'avg_win': self.avg_win(trades_df),
                'avg_loss': self.avg_loss(trades_df),
                '총 거래 횟수': len(trades_df),
                '승률': self.win_rate(trades_df),
                '수익 팩터': self.profit_factor(trades_df),
                '평균 수익': self.avg_win(trades_df),
                '평균 손실': self.avg_loss(trades_df),
            })
        
        return metrics
    
    def print_metrics(self, trades_df: Optional[pd.DataFrame] = None):
        """성과 지표 출력"""
        metrics = self.get_all_metrics(trades_df)
        
        print("\n" + "=" * 50)
        print("📊 백테스팅 성과 리포트")
        print("=" * 50)
        
        print("\n📈 수익성 지표")
        print(f"  • 총 수익률: {metrics['total_return']:.2%}")
        print(f"  • 연환산 수익률 (CAGR): {metrics['cagr']:.2%}")
        print(f"  • 최종 자산: ₩{metrics['final_equity']:,.0f}")
        
        print("\n⚠️ 위험 지표")
        print(f"  • 최대 낙폭 (MDD): {metrics['max_drawdown']:.2%}")
        print(f"  • MDD 기간: {metrics['max_dd_duration']}일")
        print(f"  • 연환산 변동성: {metrics['volatility']:.2%}")
        
        print("\n📐 위험 조정 수익률")
        print(f"  • 샤프 비율: {metrics['sharpe_ratio']:.2f}")
        print(f"  • 소르티노 비율: {metrics['sortino_ratio']:.2f}")
        print(f"  • 칼마 비율: {metrics['calmar_ratio']:.2f}")
        
        if 'total_trades' in metrics:
            print("\n💹 거래 통계")
            print(f"  • 총 거래 횟수: {metrics['total_trades']}회")
            print(f"  • 승률: {metrics['win_rate']:.2%}")
            print(f"  • 수익 팩터: {metrics['profit_factor']:.2f}")
            print(f"  • 평균 수익: ₩{metrics['avg_win']:,.0f}")
            print(f"  • 평균 손실: ₩{metrics['avg_loss']:,.0f}")
        
        print("\n" + "=" * 50)


# 사용 예시
if __name__ == "__main__":
    # 샘플 데이터로 테스트
    np.random.seed(42)
    
    initial_capital = 10_000_000
    days = 252
    
    # 랜덤 수익률 생성
    daily_returns = np.random.normal(0.0005, 0.015, days)
    equity = [initial_capital]
    for r in daily_returns:
        equity.append(equity[-1] * (1 + r))
    
    equity_curve = pd.Series(equity)
    
    # 샘플 거래 데이터
    trades = pd.DataFrame({
        'entry_date': pd.date_range('2024-01-01', periods=10),
        'exit_date': pd.date_range('2024-01-15', periods=10),
        'pnl': [100000, -50000, 80000, 120000, -30000, 
                60000, -20000, 90000, -40000, 70000]
    })
    
    metrics = PerformanceMetrics(equity_curve, initial_capital)
    metrics.print_metrics(trades)
