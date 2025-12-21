"""
다중 종목 동시 수집 모듈 - ThreadPoolExecutor를 활용한 병렬 데이터 수집
"""
import pandas as pd
from typing import Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import sys

# 프로젝트 루트 경로 설정
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config import DEFAULT_TICKERS, US_TICKERS, DEFAULT_PERIOD
from src.collectors.stock_collector import StockDataCollector

try:
    from tqdm import tqdm
    TQDM_AVAILABLE = True
except ImportError:
    TQDM_AVAILABLE = False


class MultiStockCollector:
    """여러 종목을 동시에 수집하는 클래스"""
    
    def __init__(self, max_workers: int = 5, db_path: Optional[Path] = None):
        """
        Args:
            max_workers: 최대 병렬 워커 수
            db_path: SQLite 데이터베이스 경로
        """
        self.max_workers = max_workers
        self.collector = StockDataCollector(db_path)
        self.results: Dict[str, pd.DataFrame] = {}
        self.errors: Dict[str, str] = {}
    
    def _fetch_single_stock(self, ticker: str, period: str) -> tuple:
        """단일 종목 데이터 수집 (내부용)"""
        try:
            df = self.collector.fetch_stock_data(ticker, period=period)
            return ticker, df, None
        except Exception as e:
            return ticker, pd.DataFrame(), str(e)
    
    def collect_multiple(
        self, 
        tickers: List[str], 
        period: str = DEFAULT_PERIOD,
        show_progress: bool = True
    ) -> Dict[str, pd.DataFrame]:
        """
        여러 종목 데이터를 병렬로 수집합니다.
        
        Args:
            tickers: 종목 코드 리스트
            period: 조회 기간
            show_progress: 진행률 표시 여부
            
        Returns:
            종목별 DataFrame 딕셔너리
        """
        self.results = {}
        self.errors = {}
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(self._fetch_single_stock, ticker, period): ticker
                for ticker in tickers
            }
            
            if show_progress and TQDM_AVAILABLE:
                iterator = tqdm(as_completed(futures), total=len(tickers), desc="수집 중")
            else:
                iterator = as_completed(futures)
            
            for future in iterator:
                ticker, df, error = future.result()
                if error:
                    self.errors[ticker] = error
                    print(f"[ERROR] {ticker}: {error}")
                elif not df.empty:
                    self.results[ticker] = df
        
        print(f"\n[INFO] 수집 완료: {len(self.results)}/{len(tickers)} 종목")
        if self.errors:
            print(f"[WARNING] 실패: {len(self.errors)} 종목")
        
        return self.results
    
    def collect_default_stocks(
        self, 
        include_us: bool = False,
        period: str = DEFAULT_PERIOD
    ) -> Dict[str, pd.DataFrame]:
        """
        기본 설정된 종목들을 수집합니다.
        
        Args:
            include_us: 미국 주식 포함 여부
            period: 조회 기간
            
        Returns:
            종목별 DataFrame 딕셔너리
        """
        tickers = list(DEFAULT_TICKERS.values())
        if include_us:
            tickers.extend(US_TICKERS.values())
        
        return self.collect_multiple(tickers, period)
    
    def collect_stock_info(self, tickers: List[str]) -> Dict[str, Dict]:
        """
        여러 종목의 정보를 병렬로 수집합니다.
        
        Returns:
            종목별 정보 딕셔너리
        """
        info_results = {}
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(self.collector.get_stock_info, ticker): ticker
                for ticker in tickers
            }
            
            for future in as_completed(futures):
                ticker = futures[future]
                try:
                    info = future.result()
                    if info:
                        info_results[ticker] = info
                except Exception as e:
                    print(f"[ERROR] {ticker} 정보 조회 실패: {e}")
        
        return info_results
    
    def get_combined_dataframe(self) -> pd.DataFrame:
        """
        수집된 모든 종목의 데이터를 하나의 DataFrame으로 결합합니다.
        
        Returns:
            결합된 DataFrame (ticker 컬럼으로 구분)
        """
        if not self.results:
            return pd.DataFrame()
        
        dfs = []
        for ticker, df in self.results.items():
            df = df.copy()
            df['ticker'] = ticker
            dfs.append(df)
        
        return pd.concat(dfs, ignore_index=True)
    
    def get_normalized_returns(self) -> pd.DataFrame:
        """
        각 종목의 정규화된 수익률을 계산합니다.
        (첫 날 = 100 기준)
        
        Returns:
            정규화된 수익률 DataFrame
        """
        if not self.results:
            return pd.DataFrame()
        
        returns_data = {}
        for ticker, df in self.results.items():
            if 'close' in df.columns and 'date' in df.columns:
                df = df.sort_values('date')
                first_close = df['close'].iloc[0]
                returns_data[ticker] = (df.set_index('date')['close'] / first_close * 100)
        
        return pd.DataFrame(returns_data)
    
    def get_correlation_matrix(self) -> pd.DataFrame:
        """
        종목 간 수익률 상관관계 행렬을 계산합니다.
        
        Returns:
            상관관계 DataFrame
        """
        returns_df = self.get_normalized_returns()
        if returns_df.empty:
            return pd.DataFrame()
        
        # 일별 수익률로 변환
        daily_returns = returns_df.pct_change().dropna()
        return daily_returns.corr()


# 사용 예시
if __name__ == "__main__":
    print("=== 다중 종목 수집 테스트 ===\n")
    
    collector = MultiStockCollector(max_workers=5)
    
    # 국내 주식만 수집
    results = collector.collect_default_stocks(include_us=False, period="3mo")
    
    print(f"\n수집된 종목: {list(results.keys())}")
    
    # 정규화된 수익률
    returns_df = collector.get_normalized_returns()
    print(f"\n정규화된 수익률:\n{returns_df.tail()}")
    
    # 상관관계
    corr_matrix = collector.get_correlation_matrix()
    print(f"\n상관관계 행렬:\n{corr_matrix}")
