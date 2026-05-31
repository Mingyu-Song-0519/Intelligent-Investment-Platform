"""
데이터 캐싱 유틸리티 모듈

클린 아키텍처 준수:
- Presentation Layer: Streamlit 캐싱 데코레이터 활용
- Application Layer: MarketDataService, StockDataCollector 호출
- 캐싱 전략: TTL 기반 (1시간~24시간)
"""
import logging
import streamlit as st
import pandas as pd
from typing import Tuple, Dict, List

logger = logging.getLogger(__name__)

# Application Services
from src.services.market_data_service import MarketDataService
from src.collectors.stock_collector import StockDataCollector
from src.collectors.multi_stock_collector import MultiStockCollector


@st.cache_data(ttl=3600, show_spinner="📊 데이터 로딩 중...")
def get_cached_stock_data(ticker: str, period: str, _cache_version: int = 0) -> pd.DataFrame:
    """
    주식 데이터 수집 (MarketDataService + 캐싱 적용)
    
    Args:
        ticker: 종목 코드
        period: 조회 기간 (1mo, 3mo, 6mo, 1y, etc.)
        _cache_version: 캐시 무효화 버전 (변경 시 캐시 재생성)
    
    Returns:
        DataFrame: OHLCV 데이터
    
    Note:
        - TTL: 1시간
        - MarketDataService 우선 사용 (Fallback + SQLite 캐싱 포함)
        - Fallback: StockDataCollector
    """
    try:
        # Phase F: MarketDataService 우선 사용 (Fallback + SQLite 캐싱)
        market = st.session_state.get('current_market', 'KR')
        service = MarketDataService(market=market)
        ohlcv = service.get_ohlcv(ticker, period=period)
        df = ohlcv.to_dataframe()
        
        # 차트 호환성: index를 date 컬럼으로 변환
        if 'date' not in df.columns:
            df = df.reset_index()
            # 컬럼명 정규화 (Date, index 등 → date)
            if 'Date' in df.columns:
                df = df.rename(columns={'Date': 'date'})
            elif 'index' in df.columns:
                df = df.rename(columns={'index': 'date'})
            elif df.columns[0] != 'date':
                df = df.rename(columns={df.columns[0]: 'date'})
        
        return df
    except Exception as e:
        # Fallback: 기존 StockDataCollector
        try:
            collector = StockDataCollector()
            return collector.fetch_stock_data(ticker, period)
        except Exception as fallback_error:
            st.error(f"데이터 수집 오류: {e}, Fallback 오류: {fallback_error}")
            return pd.DataFrame()


@st.cache_data(ttl=3600, show_spinner="📊 다중 종목 데이터 로딩 중...")
def get_cached_multi_stock_data(tickers: List[str], period: str) -> Dict[str, pd.DataFrame]:
    """
    다중 종목 데이터 수집 (캐싱 적용, 1시간)
    
    Args:
        tickers: 종목 코드 리스트 (예: ['005930.KS', '000660.KS'])
        period: 조회 기간
    
    Returns:
        Dict[ticker, DataFrame]: 종목별 OHLCV 데이터
    
    Note:
        - MarketDataService 사용 (pykrx 우선, yfinance fallback)
        - yfinance에서 실패하는 신규 상장 종목도 pykrx로 조회 가능
    """
    from tqdm import tqdm
    
    result = {}
    market = st.session_state.get('current_market', 'KR')
    
    try:
        for ticker in tqdm(tickers, desc="수집 중"):
            try:
                # MarketDataService 사용 (pykrx 우선)
                service = MarketDataService(market=market)
                ohlcv = service.get_ohlcv(ticker, period=period)
                df = ohlcv.to_dataframe()
                
                # 차트 호환성: index를 date 컬럼으로 변환
                if 'date' not in df.columns:
                    df = df.reset_index()
                    if 'Date' in df.columns:
                        df = df.rename(columns={'Date': 'date'})
                    elif 'index' in df.columns:
                        df = df.rename(columns={'index': 'date'})
                    elif df.columns[0] != 'date':
                        df = df.rename(columns={df.columns[0]: 'date'})
                
                if not df.empty:
                    result[ticker] = df
                    logger.info(f"{ticker}: {len(df)}개 데이터 수집 완료")
                else:
                    logger.warning(f"{ticker}: 빈 데이터")
                    
            except Exception as e:
                logger.warning(f"{ticker}: 데이터를 가져올 수 없습니다. ({e})")
                continue
                
    except Exception as e:
        st.error(f"다중 데이터 수집 오류: {e}")
    
    logger.info(f"수집 완료: {len(result)}/{len(tickers)} 종목")
    return result


@st.cache_data(ttl=86400, show_spinner=False)
def get_cached_stock_listing_v3(market: str) -> Tuple[Dict[str, str], List[str]]:
    """
    종목 리스트 수집 (캐싱 적용, 24시간) - v3 (KIND 적용)
    
    Args:
        market: 시장 코드 ('KR' or 'US')
    
    Returns:
        Tuple:
            - stock_dict: {종목명 (코드): 코드}
            - stock_names: 종목명 리스트
    
    Note:
        - KR: KRX KIND Download (Official)
        - US: FinanceDataReader NYSE + NASDAQ
    """
    try:
        import FinanceDataReader as fdr
        logger.debug(f"get_cached_stock_listing_v3 called for {market}")
        
        if market == 'US':
            df_nyse = fdr.StockListing('NYSE')
            df_nasdaq = fdr.StockListing('NASDAQ')
            df = pd.concat([df_nyse, df_nasdaq], ignore_index=True)
            df = df.dropna(subset=['Symbol', 'Name'])
            df = df.drop_duplicates(subset=['Symbol'])
            stock_dict = dict(zip(
                df['Name'] + ' (' + df['Symbol'] + ')',
                df['Symbol']
            ))
            logger.info(f"Loaded {len(stock_dict)} US stocks")
        else:  # KR
            stock_dict = {}
            
            # Attempt: KRX KIND (Official Corporate List)
            try:
                logger.debug("Attempting KIND download via pandas...")
                # 상장법인목록 다운로드 (Official KRX)
                url = 'http://kind.krx.co.kr/corpgeneral/corpList.do?method=download&searchType=13'
                # html5lib parser used implicitly or explicitly if installed
                df = pd.read_html(url, header=0, encoding='euc-kr')[0]
                
                logger.debug(f"KIND raw df shape: {df.shape}")
                
                # Preprocessing
                df = df.rename(columns={'회사명': 'Name', '종목코드': 'Code'})
                
                # Format Code safely (int or str -> 6 digit str)
                df['Code'] = df['Code'].astype(str).str.zfill(6)
                df['Name'] = df['Name'].astype(str)
                
                # 🔧 유효한 6자리 숫자 코드만 필터링 (특수 코드 제외: $로 시작하거나 문자 포함)
                df = df[df['Code'].str.match(r'^\d{6}$', na=False)]
                
                # Deduplicate just in case
                df = df.drop_duplicates(subset=['Code'])
                
                stock_dict = dict(zip(
                    df['Name'] + ' (' + df['Code'] + ')',
                    df['Code']
                ))
                
                logger.info(f"Loaded {len(stock_dict)} stocks from KRX KIND (after filtering)")
                
            except Exception as e:
                logger.error(f"KIND listings failed: {e}")
                import traceback
                traceback.print_exc()
                
            # If still empty, raise error to trigger SessionManager fallback
            if not stock_dict:
                logger.critical("stock_dict is empty. Raising exception.")
                raise Exception("All KR fetching methods failed")
        
        return stock_dict, list(stock_dict.keys())
    except Exception as e:
        import traceback
        logger.error(f"종목 리스트 로딩 실패: {e}")
        # traceback.print_exc() # Reduce noise
        return {}, []


@st.cache_data(ttl=3600, show_spinner=False)
def get_cached_exchange_rate() -> float:
    """
    환율 데이터 수집 (캐싱 적용, 1시간)
    
    Returns:
        float: USD/KRW 환율
    
    Note:
        - 소스: Yahoo Finance (USDKRW=X)
        - 기본값: 1350.0 (데이터 수집 실패 시)
    """
    try:
        import yfinance as yf
        usdkrw = yf.Ticker("USDKRW=X")
        rate = usdkrw.info.get('regularMarketPrice', None)
        if rate is None:
            rate = usdkrw.history(period="1d")['Close'].iloc[-1]
        return float(rate)
    except Exception as e:
        logger.error(f"환율 데이터 수집 실패: {e}")
        return 1350.0  # 기본값
