"""
PyKRX Gateway
한국 주식 수급 데이터(외국인/기관) 수집
Clean Architecture: Infrastructure Layer
"""
import logging
import pandas as pd
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    from pykrx import stock as pykrx_stock
    PYKRX_AVAILABLE = True
except ImportError:
    PYKRX_AVAILABLE = False
    pykrx_stock = None

logger = logging.getLogger(__name__)


class PyKRXGateway:
    """
    pykrx를 이용한 한국 주식 데이터 수집
    
    주요 기능:
    - 투자자별 매매동향 (외국인/기관/개인)
    - 거래량 및 거래대금 추이
    """
    
    def __init__(self):
        """PyKRX Gateway 초기화"""
        self._initialized = False
        self._init_pykrx()
    
    def _init_pykrx(self):
        """pykrx 라이브러리 초기화"""
        if PYKRX_AVAILABLE:
            self._initialized = True
            logger.info("[PyKRXGateway] Initialized successfully")
        else:
            self._initialized = False
            logger.warning("[PyKRXGateway] pykrx not installed. Run: pip install pykrx")
    
    def is_available(self) -> bool:
        """서비스 사용 가능 여부"""
        return self._initialized
    
    def get_investor_trading(
        self,
        ticker: str,
        days: int = 20
    ) -> Optional[pd.DataFrame]:
        """
        투자자별 매매동향 조회 (외국인/기관/개인)
        
        Args:
            ticker: 종목 코드 (예: "005930.KS" 또는 "005930")
            days: 조회 기간 (일)
            
        Returns:
            DataFrame with columns: 날짜, 외국인순매수, 기관순매수, 개인순매수
            또는 None (데이터 없음 또는 오류 시)
        """
        if not self._initialized:
            logger.warning("[PyKRXGateway] Not initialized")
            return None
        
        try:
            from pykrx import stock
            
            # 티커에서 .KS, .KQ 제거
            clean_ticker = ticker.replace(".KS", "").replace(".KQ", "")
            
            # 날짜 범위 계산
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            # 날짜 포맷 변환 (YYYYMMDD)
            start_str = start_date.strftime("%Y%m%d")
            end_str = end_date.strftime("%Y%m%d")
            
            # 투자자별 순매수 데이터 조회
            df = stock.get_market_trading_value_by_date(
                start_str,
                end_str,
                clean_ticker
            )
            
            if df is None or df.empty:
                logger.debug(f"[PyKRXGateway] No data for {ticker}")
                return None
            
            # 컬럼명 정리 (한글 컬럼명이 있는 경우)
            # pykrx 반환 형식: 날짜(index), 기관합계, 기타법인, 개인, 외국인합계, 전체
            df_result = pd.DataFrame({
                '날짜': df.index,
                '외국인순매수': df.get('외국인합계', df.get('외국인', 0)),
                '기관순매수': df.get('기관합계', df.get('기관', 0)),
                '개인순매수': df.get('개인', 0)
            })
            
            logger.debug(f"[PyKRXGateway] Fetched {len(df_result)} days for {ticker}")
            return df_result
            
        except Exception as e:
            logger.error(f"[PyKRXGateway] Failed to get investor trading for {ticker}: {e}")
            return None
    
    def get_investor_summary(
        self,
        ticker: str,
        days: int = 20
    ) -> Optional[Dict[str, Any]]:
        """
        투자자별 매매동향 요약
        
        Args:
            ticker: 종목 코드
            days: 조회 기간
            
        Returns:
            dict: {
                'foreign_net': 외국인 순매수 합계,
                'institution_net': 기관 순매수 합계,
                'individual_net': 개인 순매수 합계,
                'trend': '외국인/기관 동반 매수' 등
            }
        """
        df = self.get_investor_trading(ticker, days)
        
        if df is None or df.empty:
            return None
        
        # 순매수 합계 계산
        foreign_net = df['외국인순매수'].sum()
        institution_net = df['기관순매수'].sum()
        individual_net = df['개인순매수'].sum()
        
        # 추세 판단
        trend = ""
        if foreign_net > 0 and institution_net > 0:
            trend = "외국인/기관 동반 매수세"
        elif foreign_net < 0 and institution_net < 0:
            trend = "외국인/기관 동반 매도세"
        elif foreign_net > 0:
            trend = "외국인 매수 우위"
        elif institution_net > 0:
            trend = "기관 매수 우위"
        else:
            trend = "개인 매수 우위"
        
        return {
            'foreign_net': foreign_net,
            'institution_net': institution_net,
            'individual_net': individual_net,
            'trend': trend,
            'days': days
        }
    
    def detect_buying_streak(
        self,
        ticker: str,
        days: int = 20,
        streak_days: int = 3
    ) -> Dict[str, bool]:
        """연속 매수 추세 감지"""
        df = self.get_investor_trading(ticker, days)
        
        if df is None or df.empty:
            return {'foreign_streak': False, 'institution_streak': False}
        
        # 최근 N일 데이터
        recent = df.tail(streak_days)
        
        # 연속 매수 체크
        foreign_streak = (recent['외국인순매수'] > 0).all()
        institution_streak = (recent['기관순매수'] > 0).all()
        
        return {
            'foreign_streak': foreign_streak,
            'institution_streak': institution_streak
        }

    def get_all_kr_tickers(self, market: str = "ALL") -> list:
        """
        전체 한국 주식 티커 조회

        Args:
            market: "KOSPI", "KOSDAQ", or "ALL"

        Returns:
            List of ticker codes (6-digit strings)

        Example:
            >>> gateway.get_all_kr_tickers("KOSPI")
            ['005930', '000660', '035420', ...]
        """
        if not self._initialized:
            logger.warning("[PyKRXGateway] Not initialized")
            return []

        try:
            from pykrx import stock as pykrx_stock
            import time

            start_time = time.time()

            if market == "ALL":
                kospi = pykrx_stock.get_market_ticker_list(market="KOSPI")
                kosdaq = pykrx_stock.get_market_ticker_list(market="KOSDAQ")
                tickers = kospi + kosdaq
            else:
                tickers = pykrx_stock.get_market_ticker_list(market=market)

            elapsed = time.time() - start_time
            logger.info(f"[PyKRXGateway] Fetched {len(tickers)} {market} tickers in {elapsed:.2f}s")

            return tickers

        except Exception as e:
            logger.error(f"[PyKRXGateway] Failed to get tickers: {e}")
            return []

    def get_ticker_name_map(self) -> Dict[str, str]:
        """전체 종목 코드:이름 매핑 획득"""
        if not self._initialized: return {}
        try:
            from pykrx import stock
            # 코스피/코스닥 합침
            kospi = stock.get_market_ticker_list(market="KOSPI")
            kosdaq = stock.get_market_ticker_list(market="KOSDAQ")
            
            mapping = {}
            for t in kospi + kosdaq:
                mapping[t] = stock.get_market_ticker_name(t)
            return mapping
        except Exception as e:
            logger.error(f"[PyKRXGateway] Failed to build name map: {e}")
            return {}

    def get_market_snapshot(self, market: str = "ALL", date: str = None) -> pd.DataFrame:
        """
        특정 날짜의 시장 전체 종목 스냅샷 (시가총액, OHLCV)

        Args:
            date: 날짜 (YYYYMMDD 형식), None이면 최근 거래일
            market: "KOSPI", "KOSDAQ", or "ALL"

        Returns:
            DataFrame with columns: ticker, 종가, 거래량, 시가총액, 등락률

        Example:
            >>> snapshot = gateway.get_market_snapshot("20251226", "KOSPI")
            >>> snapshot.head()
               ticker    종가     거래량        시가총액    등락률
            0  005930  58000  15234567  3456789000000   1.23
        """
        if not self._initialized:
            logger.warning("[PyKRXGateway] Not initialized")
            return pd.DataFrame()

        try:
            from pykrx import stock as pykrx_stock
            import time

            start_time = time.time()

            # Phase 0-A Critical Fix: 주말/공휴일 대응 거래일 자동 감지
            if date is None:
                date = self._get_last_trading_day()
            
            if date is None:
                logger.warning("[PyKRXGateway] No valid trading day detected within search range. (Possible IP Block or long holiday)")
                return pd.DataFrame()

            result_dfs = []
            markets_to_fetch = ["KOSPI", "KOSDAQ"] if market == "ALL" else [market]

            for mkt in markets_to_fetch:
                try:
                    # 시가총액 데이터 (종가, 거래량 포함)
                    cap_df = pykrx_stock.get_market_cap_by_ticker(date, market=mkt)

                    if cap_df is not None and not cap_df.empty:
                        # Reset index to make ticker a column
                        cap_df = cap_df.reset_index()
                        cap_df.columns = ['ticker', '종가', '시가총액', '거래량', '거래대금', '상장주식수']

                        # 등락률 데이터 추가 (옵션)
                        try:
                            ohlcv_df = pykrx_stock.get_market_ohlcv_by_ticker(date, market=mkt)
                            if ohlcv_df is not None and not ohlcv_df.empty:
                                ohlcv_df = ohlcv_df.reset_index()
                                # 등락률 컬럼만 병합
                                if '등락률' in ohlcv_df.columns:
                                    cap_df = cap_df.merge(
                                        ohlcv_df[['티커', '등락률']],
                                        left_on='ticker',
                                        right_on='티커',
                                        how='left'
                                    ).drop(columns=['티커'], errors='ignore')
                        except:
                            # 등락률 없어도 OK
                            pass

                        result_dfs.append(cap_df)

                except Exception as mkt_err:
                    logger.warning(f"[PyKRXGateway] Failed to fetch {mkt}: {mkt_err}")
                    continue

            if not result_dfs:
                return pd.DataFrame()

            # 결합
            result = pd.concat(result_dfs, ignore_index=True)

            elapsed = time.time() - start_time
            logger.info(f"[PyKRXGateway] Market snapshot: {len(result)} stocks from {market} in {elapsed:.2f}s")

            return result

        except Exception as e:
            logger.error(f"[PyKRXGateway] Market snapshot failed: {e}")
            return pd.DataFrame()

    def _get_last_trading_day(self) -> Optional[str]:
        """
        최근 거래일 (YYYYMMDD) 반환
        네트워크 오류나 차단 발생 시 None 반환하여 상위 계층에서 폴백하도록 함
        """
        try:
            from pykrx import stock
            now = datetime.now()
            # 최근 10일간 탐색하며 실제 데이터가 있는 날짜 탐색
            for i in range(10):
                target = (now - timedelta(days=i)).strftime("%Y%m%d")
                # 삼성전자(005930) 데이터를 통해 휴장 및 데이터 가용성 확인
                df = stock.get_market_ohlcv_by_date(target, target, "005930")
                if df is not None and not df.empty:
                    logger.debug(f"[PyKRXGateway] Found last trading day: {target}")
                    return target
            return None
        except Exception as e:
            logger.warning(f"[PyKRXGateway] Failed to detect last trading day (Possible IP Block): {e}")
            return None

    def batch_get_investor_trading(self, tickers: List[str], days: int = 20) -> Dict[str, pd.DataFrame]:
        """다수 종목의 매매동향 병렬 조회"""
        results = {}
        if not tickers: return results

        def _fetch(t):
            time.sleep(0.05) # Rate limit
            return t, self.get_investor_trading(t, days)

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {executor.submit(_fetch, t): t for t in tickers}
            count = 0
            for future in as_completed(futures):
                ticker, df = future.result()
                count += 1
                if df is not None:
                    results[ticker] = df
                    if count % 10 == 0:
                        logger.info(f"[PyKRXGateway] Investor data progress: {count}/{len(tickers)}")
                else:
                    logger.debug(f"[PyKRXGateway] Investor data fetch failed for {ticker}")
        return results

    def batch_get_ohlcv_parallel(
        self,
        tickers: List[str],
        period: str = "1mo",
        max_workers: int = 10
    ) -> Dict[str, pd.DataFrame]:
        """
        다수 종목의 OHLCV 데이터를 병렬로 로드 (ThreadPoolExecutor 사용)
        """
        if not self._initialized:
            logger.warning("[PyKRXGateway] Not initialized")
            return {}

        if not tickers:
            return {}

        try:
            start_time = time.time()

            # 기간 계산
            period_days = {"1mo": 30, "3mo": 90, "1y": 365}.get(period, 30)
            end_date = datetime.now()
            start_date = end_date - timedelta(days=period_days)

            start_str = start_date.strftime("%Y%m%d")
            end_str = end_date.strftime("%Y%m%d")

            results = {}
            failed_count = 0

            def _fetch_single_ohlcv(ticker: str):
                """단일 종목 OHLCV 조회"""
                try:
                    time.sleep(0.05)  # Rate limit
                    clean_ticker = ticker.replace(".KS", "").replace(".KQ", "")

                    df = pykrx_stock.get_market_ohlcv_by_date(start_str, end_str, clean_ticker)

                    if df is not None and not df.empty:
                        # 컬럼명 정규화
                        df = df.rename(columns={
                            '시가': '시가', '고가': '고가', '저가': '저가',
                            '종가': '종가', '거래량': '거래량', '거래대금': '거래대금', '등락률': '등락률'
                        })
                        df.index.name = 'date'
                        return ticker, df
                    return ticker, None
                except Exception as e:
                    logger.debug(f"[PyKRXGateway] OHLCV fetch failed for {ticker}: {e}")
                    return ticker, None

            # ThreadPoolExecutor로 병렬 처리
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {executor.submit(_fetch_single_ohlcv, t): t for t in tickers}

                for future in as_completed(futures):
                    ticker, df = future.result()
                    if df is not None:
                        results[ticker] = df
                    else:
                        failed_count += 1

            elapsed = time.time() - start_time
            logger.info(
                f"[PyKRXGateway] Parallel OHLCV: {len(results)}/{len(tickers)} stocks, "
                f"{failed_count} failed, {elapsed:.2f}s (workers={max_workers})"
            )

            return results

        except Exception as e:
            logger.error(f"[PyKRXGateway] Parallel OHLCV failed: {e}")
            return {}

    def batch_get_ohlcv(
        self,
        tickers: list,
        period: str = "1mo",
        max_tickers: int = 500
    ) -> Dict[str, pd.DataFrame]:
        """
        다수 종목의 OHLCV 데이터 배치 조회

        Args:
            tickers: 조회할 티커 리스트 (6자리 코드)
            period: 조회 기간 ("1mo", "3mo", "1y")
            max_tickers: 최대 조회 종목 수 (메모리 관리)

        Returns:
            {ticker: DataFrame} 형태의 딕셔너리

        Example:
            >>> data = gateway.batch_get_ohlcv(['005930', '000660'], period='1mo')
            >>> data['005930'].head()
                         시가   고가   저가   종가     거래량
            2025-12-01  57000  58500  56500  58000  12345678
        """
        if not self._initialized:
            logger.warning("[PyKRXGateway] Not initialized")
            return {}

        try:
            from pykrx import stock as pykrx_stock
            import time

            start_time = time.time()

            # 기간 계산
            period_days = {"1mo": 30, "3mo": 90, "1y": 365}.get(period, 30)
            end_date = datetime.now()
            start_date = end_date - timedelta(days=period_days)

            start_str = start_date.strftime("%Y%m%d")
            end_str = end_date.strftime("%Y%m%d")

            # 최대 개수 제한
            tickers_to_fetch = tickers[:max_tickers]

            result = {}
            failed_count = 0

            for ticker in tickers_to_fetch:
                try:
                    # .KS, .KQ 제거
                    clean_ticker = ticker.replace(".KS", "").replace(".KQ", "")

                    df = pykrx_stock.get_market_ohlcv_by_date(
                        start_str, end_str, clean_ticker
                    )

                    if df is not None and not df.empty:
                        # 컬럼명 정규화
                        df = df.rename(columns={
                            '시가': '시가', '고가': '고가', '저가': '저가',
                            '종가': '종가', '거래량': '거래량', '거래대금': '거래대금', '등락률': '등락률'
                        })
                        df.index.name = 'date'
                        result[ticker] = df
                except Exception as e:
                    failed_count += 1
                    continue

            elapsed = time.time() - start_time
            logger.info(
                f"[PyKRXGateway] Batch OHLCV: {len(result)}/{len(tickers_to_fetch)} stocks, "
                f"{failed_count} failed, {elapsed:.2f}s"
            )

            return result

        except Exception as e:
            logger.error(f"[PyKRXGateway] Batch OHLCV failed: {e}")
            return {}

    def fetch_ohlcv(
        self,
        ticker: str,
        start: Optional[str] = None,
        end: Optional[str] = None,
        period: str = "1mo"
    ) -> Optional[pd.DataFrame]:
        """IStockDataGateway 인터페이스 호환용 단일 종목 조회"""
        res = self.batch_get_ohlcv([ticker], period=period)
        df = res.get(ticker)
        if df is not None and not df.empty:
            # chart_utils.render_stock_chart 등은 영어 컬럼명을 기대함
            df = df.rename(columns={
                '시가': 'open', '고가': 'high', '저가': 'low',
                '종가': 'close', '거래량': 'volume', '거래대금': 'amount', '등락률': 'change'
            })
        return df

    def get_stock_fundamental(self, ticker: str) -> Dict[str, Any]:
        """종목 펀더멘털 상세 정보 (yfinance 하이브리드)"""
        try:
            import yfinance as yf
            
            clean_ticker = ticker.replace(".KS", "").replace(".KQ", "")
            results = {'ticker': ticker}
            
            # 1. PyKRX: 시가총액 (가장 정확)
            target_date = self._get_last_trading_day()
            cap_df = pykrx_stock.get_market_cap_by_ticker(target_date)
            if clean_ticker in cap_df.index:
                results['marketcap'] = float(cap_df.loc[clean_ticker, '시가총액'])
            
            # 2. yfinance: PER, PBR, 배당, 52주 고/저
            yf_ticker = f"{clean_ticker}.KS" if ".KS" in ticker or ticker.isdigit() else f"{clean_ticker}.KQ"
            obj = yf.Ticker(yf_ticker)
            info = obj.info
            
            results.update({
                'per': info.get('forwardPE') or info.get('trailingPE'),
                'pbr': info.get('priceToBook'),
                'dividend_yield': (info.get('dividendYield') or 0) * 100,
                'week52_high': info.get('fiftyTwoWeekHigh'),
                'week52_low': info.get('fiftyTwoWeekLow')
            })
            return results
        except Exception as e:
            logger.error(f"[PyKRXGateway] Fundamental fetch failed for {ticker}: {e}")
            return {}


class MockPyKRXGateway(PyKRXGateway):
    """
    테스트용 Mock PyKRX Gateway
    """
    
    def __init__(self):
        """Mock 초기화 (pykrx 없이도 작동)"""
        self._initialized = True
    
    def get_investor_trading(self, ticker: str, days: int = 20) -> Optional[pd.DataFrame]:
        """Mock 데이터 반환"""
        dates = pd.date_range(end=datetime.now(), periods=days, freq='D')
        
        return pd.DataFrame({
            '날짜': dates,
            '외국인순매수': [1000000 * i for i in range(days)],  # 증가 추세
            '기관순매수': [500000 * i for i in range(days)],
            '개인순매수': [-1500000 * i for i in range(days)]  # 매도 추세
        })
