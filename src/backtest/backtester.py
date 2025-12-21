"""
백테스팅 엔진 모듈 - 포트폴리오 시뮬레이션 및 성과 평가
"""
import pandas as pd
import numpy as np
from typing import Optional, Dict, List, Any
from pathlib import Path
import sys

# 프로젝트 루트 경로 설정
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config import MODELS_DIR
from src.backtest.strategies import BaseStrategy
from src.backtest.metrics import PerformanceMetrics


class Backtester:
    """백테스팅 엔진 클래스"""
    
    def __init__(
        self,
        df: pd.DataFrame,
        initial_capital: float = 10_000_000,
        commission: float = 0.00015,  # 0.015% 매매 수수료
        slippage: float = 0.001       # 0.1% 슬리피지
    ):
        """
        Args:
            df: OHLCV + 지표가 포함된 DataFrame
            initial_capital: 초기 자본금
            commission: 매매 수수료 (비율)
            slippage: 슬리피지 (비율)
        """
        self.df = df.copy()
        self.initial_capital = initial_capital
        self.commission = commission
        self.slippage = slippage
        
        self.trades: List[Dict] = []
        self.equity_curve: pd.Series = None
        self.positions: pd.Series = None
        
        self._validate_data()
    
    def _validate_data(self):
        """데이터 유효성 검증"""
        required_cols = ['open', 'high', 'low', 'close', 'volume']
        missing = [col for col in required_cols if col not in self.df.columns]
        if missing:
            raise ValueError(f"필수 컬럼 누락: {missing}")
        
        # date 컬럼이 있으면 인덱스로 설정
        if 'date' in self.df.columns:
            self.df = self.df.set_index('date').sort_index()
        else:
            self.df = self.df.sort_index()
    
    def run(self, strategy: BaseStrategy) -> Dict[str, Any]:
        """
        백테스팅 실행
        
        Args:
            strategy: 매매 전략 객체
            
        Returns:
            백테스팅 결과 딕셔너리
        """
        # 시그널 생성
        signals = strategy.generate_signals(self.df)
        
        # 초기화
        capital = self.initial_capital
        position = 0  # 보유 주식 수
        entry_price = 0
        entry_date = None
        
        equity = []
        self.trades = []
        
        for i in range(len(self.df)):
            row = self.df.iloc[i]
            signal = signals.iloc[i]
            current_price = row['close']
            current_date = self.df.index[i]  # 인덱스에서 날짜 가져오기
            
            # 포트폴리오 가치 계산
            portfolio_value = capital + (position * current_price)
            equity.append(portfolio_value)
            
            # 매수 시그널
            if signal == 1 and position == 0:
                # 슬리피지 적용
                buy_price = current_price * (1 + self.slippage)
                
                # 최대 매수 가능 수량
                max_shares = int(capital / (buy_price * (1 + self.commission)))
                
                if max_shares > 0:
                    position = max_shares
                    cost = position * buy_price * (1 + self.commission)
                    capital -= cost
                    entry_price = buy_price
                    entry_date = current_date
            
            # 매도 시그널
            elif signal == -1 and position > 0:
                # 슬리피지 적용
                sell_price = current_price * (1 - self.slippage)
                
                # 매도 실행
                proceeds = position * sell_price * (1 - self.commission)
                pnl = proceeds - (position * entry_price)
                pnl_pct = (sell_price / entry_price - 1)
                
                self.trades.append({
                    'entry_date': entry_date,
                    'entry_price': entry_price,
                    'exit_date': current_date,
                    'exit_price': sell_price,
                    'shares': position,
                    'pnl': pnl,
                    'pnl_pct': pnl_pct
                })
                
                capital += proceeds
                position = 0
                entry_price = 0
                entry_date = None
        
        # 마지막에 포지션이 있으면 청산
        if position > 0:
            final_price = self.df.iloc[-1]['close'] * (1 - self.slippage)
            proceeds = position * final_price * (1 - self.commission)
            pnl = proceeds - (position * entry_price)
            pnl_pct = (final_price / entry_price - 1)
            
            self.trades.append({
                'entry_date': entry_date,
                'entry_price': entry_price,
                'exit_date': self.df.index[-1],  # 인덱스에서 날짜 가져오기
                'exit_price': final_price,
                'shares': position,
                'pnl': pnl,
                'pnl_pct': pnl_pct
            })
            
            capital += proceeds
            position = 0
        
        self.equity_curve = pd.Series(equity)
        
        # Buy & Hold 비교
        buy_hold_shares = int(self.initial_capital / 
                             (self.df.iloc[0]['close'] * (1 + self.commission)))
        buy_hold_equity = buy_hold_shares * self.df['close'].values
        
        return {
            'strategy_name': strategy.name,
            'equity': self.equity_curve,
            'trades': self.trades,
            'final_capital': equity[-1],
            'buy_hold_equity': pd.Series(buy_hold_equity),
            'buy_hold_final': buy_hold_equity[-1]
        }
    
    def get_trades_df(self) -> pd.DataFrame:
        """거래 내역을 DataFrame으로 반환"""
        if not self.trades:
            return pd.DataFrame()
        return pd.DataFrame(self.trades)
    
    def get_metrics(self) -> PerformanceMetrics:
        """성과 지표 객체 반환"""
        if self.equity_curve is None:
            raise ValueError("먼저 run() 메서드를 실행하세요.")
        return PerformanceMetrics(self.equity_curve, self.initial_capital)
    
    def compare_strategies(
        self, 
        strategies: List[BaseStrategy]
    ) -> pd.DataFrame:
        """
        여러 전략 비교
        
        Args:
            strategies: 비교할 전략 리스트
            
        Returns:
            전략별 성과 비교 DataFrame
        """
        results = []
        
        for strategy in strategies:
            result = self.run(strategy)
            metrics = self.get_metrics()
            trades_df = self.get_trades_df()
            
            all_metrics = metrics.get_all_metrics(trades_df)
            all_metrics['strategy'] = strategy.name
            results.append(all_metrics)
        
        return pd.DataFrame(results).set_index('strategy')
    
    def plot_results(self, result: Dict, save_path: Optional[Path] = None):
        """
        백테스팅 결과 시각화
        
        Args:
            result: run() 메서드의 반환값
            save_path: 저장 경로 (None이면 표시만)
        """
        try:
            import matplotlib.pyplot as plt
            
            fig, axes = plt.subplots(2, 1, figsize=(14, 10))
            
            # 포트폴리오 가치 곡선
            ax1 = axes[0]
            ax1.plot(result['equity'], label=result['strategy_name'], linewidth=2)
            ax1.plot(result['buy_hold_equity'], label='Buy & Hold', 
                    linestyle='--', alpha=0.7)
            ax1.set_title('Portfolio Value', fontsize=14)
            ax1.set_xlabel('Trading Days')
            ax1.set_ylabel('Value (KRW)')
            ax1.legend()
            ax1.grid(True, alpha=0.3)
            
            # 누적 수익률
            ax2 = axes[1]
            strategy_returns = (result['equity'] / self.initial_capital - 1) * 100
            buy_hold_returns = (result['buy_hold_equity'] / self.initial_capital - 1) * 100
            
            ax2.plot(strategy_returns, label=result['strategy_name'], linewidth=2)
            ax2.plot(buy_hold_returns, label='Buy & Hold', 
                    linestyle='--', alpha=0.7)
            ax2.set_title('Cumulative Returns (%)', fontsize=14)
            ax2.set_xlabel('Trading Days')
            ax2.set_ylabel('Return (%)')
            ax2.legend()
            ax2.grid(True, alpha=0.3)
            ax2.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
            
            plt.tight_layout()
            
            if save_path:
                plt.savefig(save_path, dpi=150, bbox_inches='tight')
                print(f"[INFO] 차트 저장: {save_path}")
            else:
                plt.show()
            
            plt.close()
            
        except ImportError:
            print("[WARNING] matplotlib가 설치되지 않아 시각화를 건너뜁니다.")


# 사용 예시
if __name__ == "__main__":
    import yfinance as yf
    from src.analyzers.technical_analyzer import TechnicalAnalyzer
    from src.backtest.strategies import RSIStrategy, MACDStrategy, CombinedStrategy
    
    print("=== 백테스팅 테스트 ===\n")
    
    # 데이터 준비
    ticker = yf.Ticker("005930.KS")
    df = ticker.history(period="2y")
    df.columns = [col.lower().replace(' ', '_') for col in df.columns]
    df = df.reset_index()
    
    # 기술적 지표 추가
    analyzer = TechnicalAnalyzer(df)
    analyzer.add_all_indicators()
    df = analyzer.get_dataframe()
    
    # 백테스터 생성
    backtester = Backtester(df, initial_capital=10_000_000)
    
    # RSI 전략 테스트
    rsi_strategy = RSIStrategy(oversold=30, overbought=70)
    result = backtester.run(rsi_strategy)
    
    print(f"전략: {result['strategy_name']}")
    print(f"최종 자산: ₩{result['final_capital']:,.0f}")
    print(f"Buy & Hold: ₩{result['buy_hold_final']:,.0f}")
    
    # 성과 지표 출력
    metrics = backtester.get_metrics()
    trades_df = backtester.get_trades_df()
    metrics.print_metrics(trades_df)
    
    # 여러 전략 비교
    print("\n=== 전략 비교 ===")
    strategies = [
        RSIStrategy(),
        MACDStrategy(),
        CombinedStrategy(use_rsi=True, use_macd=True)
    ]
    comparison = backtester.compare_strategies(strategies)
    print(comparison[['total_return', 'max_drawdown', 'sharpe_ratio', 'win_rate']])
