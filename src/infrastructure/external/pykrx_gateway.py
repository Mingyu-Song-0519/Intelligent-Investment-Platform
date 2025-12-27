"""
PyKRX Gateway
한국 주식 수급 데이터(외국인/기관) 수집
Clean Architecture: Infrastructure Layer
"""
import logging
import pandas as pd
from datetime import datetime, timedelta
from json.decoder import JSONDecodeError  # Phase 1: for API error handling
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class PyKRXGateway:
    """
    pykrx를 이용한 한국 주식 데이터 수집
    
    주요 기능:
    - 투자자별 매매동향 (외국인/기관/개인)
    - 거래량 및 거래대금 추이
    
    Phase 2: 거래일 캐싱 (1시간 TTL)
    """
    
    # Phase 2: 거래일 캐싱
    _trading_day_cache: Optional[str] = None
    _cache_timestamp: Optional[datetime] = None
    _CACHE_TTL_SECONDS = 3600  # 1시간
    
    def __init__(self):
        """PyKRX Gateway 초기화"""
        self._initialized = False
        self._init_pykrx()
    
    def _init_pykrx(self):
        """pykrx 라이브러리 초기화"""
        try:
            # pykrx 임포트 확인
            import pykrx
            self._initialized = True
            logger.info("[PyKRXGateway] Initialized successfully")
        except ImportError:
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
        """
        연속 매수 추세 감지
        
        Args:
            ticker: 종목 코드
            days: 전체 조회 기간
            streak_days: 연속 일수 기준 (기본 3일)
            
        Returns:
            dict: {
                'foreign_streak': 외국인 N일 연속 매수 여부,
                'institution_streak': 기관 N일 연속 매수 여부
            }
        """
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
    
    def batch_get_investor_trading(
        self,
        tickers: list,
        days: int = 20
    ) -> Dict[str, pd.DataFrame]:
        """
        다수 종목의 투자자별 매매동향 배치 조회 (병렬 처리)
        
        Phase 2: 개별 API 호출 대신 병렬 처리로 성능 개선
        
        Args:
            tickers: 조회할 티커 리스트 (최대 50개 권장)
            days: 조회 기간 (기본 20일)
            
        Returns:
            {ticker: DataFrame} 형태의 딕셔너리
            DataFrame columns: 날짜, 외국인순매수, 기관순매수, 개인순매수
            
        Performance:
            - Sequential: 50 × 0.5s = 25s
            - Parallel (10 workers): ~2.5s (10배 빠름)
            
        Example:
            >>> data = gateway.batch_get_investor_trading(['005930', '000660'], days=20)
            >>> data['005930'].head()
                      날짜  외국인순매수  기관순매수  개인순매수
            0  2025-12-01      1000      -500      -500
        """
        if not self._initialized:
            logger.warning("[PyKRXGateway] Not initialized")
            return {}
        
        try:
            from concurrent.futures import ThreadPoolExecutor, as_completed
            from pykrx import stock
            import time
            
            start_time = time.time()
            
            # 날짜 범위 계산
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            start_str = start_date.strftime("%Y%m%d")
            end_str = end_date.strftime("%Y%m%d")
            
            def fetch_investor_data(ticker):
                """개별 종목 투자자 데이터 조회"""
                try:
                    clean_ticker = ticker.replace(".KS", "").replace(".KQ", "")
                    
                    df = stock.get_market_trading_value_by_date(
                        start_str,
                        end_str,
                        clean_ticker
                    )
                    
                    if df is None or df.empty:
                        return ticker, None
                    
                    # 컬럼 정규화
                    result_df = pd.DataFrame({
                        '날짜': df.index,
                        '외국인순매수': df.get('외국인합계', df.get('외국인', 0)),
                        '기관순매수': df.get('기관합계', df.get('기관', 0)),
                        '개인순매수': df.get('개인', 0)
                    })
                    
                    time.sleep(0.05)  # Rate limiting: 20 req/sec
                    return ticker, result_df
                    
                except Exception as e:
                    logger.debug(f"[PyKRXGateway] Investor data fetch failed for {ticker}: {e}")
                    return ticker, None
            
            result = {}
            failed_count = 0
            
            # 병렬 처리 (10 workers)
            with ThreadPoolExecutor(max_workers=10) as executor:
                future_to_ticker = {
                    executor.submit(fetch_investor_data, ticker): ticker
                    for ticker in tickers
                }
                
                for future in as_completed(future_to_ticker):
                    try:
                        ticker, df = future.result(timeout=5)
                        if df is not None:
                            result[ticker] = df
                        else:
                            failed_count += 1
                    except Exception as e:
                        failed_count += 1
                        logger.debug(f"[PyKRXGateway] Future failed: {e}")
            
            elapsed = time.time() - start_time
            logger.info(f"[PyKRXGateway] Batch investor data: {len(result)}/{len(tickers)} stocks in {elapsed:.2f}s, {failed_count} failed")
            
            return result
            
        except Exception as e:
            logger.error(f"[PyKRXGateway] Batch investor trading failed: {e}")
            return {}

    # =============================================
    # Phase G: Batch Market Data Methods
    # =============================================
    
    def _get_last_trading_day(self) -> str:
        """
        최근 거래일 조회 (주말/공휴일 제외) + Phase 2: 1시간 캐싱
        
        pykrx API가 휴장일에는 0값을 반환하므로,
        실제 거래 데이터가 있는 최근 날짜를 찾습니다.
        
        크리스마스(4일), 설날(5-6일) 등 긴 연휴 대응을 위해
        최대 14일 전까지 검색합니다.
        
        Cache:
            거래일 정보는 1시간 동안 메모리에 캐싱됩니다.
            invalidate_trading_day_cache()로 수동 무효화 가능.
        
        Returns:
            YYYYMMDD 형식의 최근 거래일
        
        Note:
            - 주말(토요일, 일요일) 자동 스킵
            - 삼성전자(005930) 시가총액으로 유효성 검증
            - 14일 검색 실패 시 10일 전 날짜 반환 (fallback)
        """
        from pykrx import stock as pykrx_stock
        
        # Phase 2: 캐시 확인
        if self._trading_day_cache and self._cache_timestamp:
            age_seconds = (datetime.now() - self._cache_timestamp).total_seconds()
            if age_seconds < self._CACHE_TTL_SECONDS:
                logger.debug(f"[PyKRXGateway] Using cached trading day: {self._trading_day_cache} (age: {age_seconds:.0f}s)")
                return self._trading_day_cache
        
        today = datetime.now()
        
        # Phase 0: 최대 14일 전까지 검색 (긴 연휴 대응: 크리스마스 4일 + 설날 5-6일)
        for days_back in range(14):
            candidate = today - timedelta(days=days_back)
            
            # 주말 스킵 (토요일=5, 일요일=6)
            if candidate.weekday() >= 5:
                continue
            
            date_str = candidate.strftime("%Y%m%d")
            
            try:
                # 삼성전자(005930) 시가총액으로 거래일 여부 확인
                test_df = pykrx_stock.get_market_cap_by_ticker(date_str, market="KOSPI")
                
                if test_df is not None and not test_df.empty and '005930' in test_df.index:
                    # 삼성전자 시가총액이 0이 아니면 유효한 거래일
                    samsung_cap = test_df.loc['005930', '시가총액']
                    if samsung_cap > 0:
                        logger.info(f"[PyKRXGateway] Using trading day: {date_str}")
                        
                        # Phase 2: 캐시 저장
                        self._trading_day_cache = date_str
                        self._cache_timestamp = datetime.now()
                        
                        return date_str
            except Exception as e:
                logger.debug(f"[PyKRXGateway] Date {date_str} check failed: {e}")
                continue
        
        # Phase 0: 폴백 10일 전으로 확대 (14일 검색 실패 시 백업)
        fallback = (today - timedelta(days=10)).strftime("%Y%m%d")
        logger.warning(
            f"[PyKRXGateway] Could not find trading day in 14 days, using fallback: {fallback}. "
            f"This may indicate a long holiday or API outage."
        )
        
        # Phase 2: Fallback도 캐싱 (반복 실패 방지)
        self._trading_day_cache = fallback
        self._cache_timestamp = datetime.now()
        
        return fallback
    
    def invalidate_trading_day_cache(self):
        """Phase 2: 거래일 캐시 수동 무효화"""
        self._trading_day_cache = None
        self._cache_timestamp = None
        logger.info("[PyKRXGateway] Trading day cache invalidated")

    
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
    
    def get_market_snapshot(self, date: str = None, market: str = "ALL") -> pd.DataFrame:
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
                date = self._get_last_trading_day()  # ✅ FIXED: 최근 거래일 사용

            
            result_dfs = []
            markets_to_fetch = ["KOSPI", "KOSDAQ"] if market == "ALL" else [market]
            
            for mkt in markets_to_fetch:
                try:
                    # 시가총액 데이터 (종가, 거래량 포함)
                    cap_df = pykrx_stock.get_market_cap_by_ticker(date, market=mkt)
                    
                    if cap_df is not None and not cap_df.empty:
                        cap_df = cap_df.reset_index()
                        # pykrx 실제 컬럼 순서: 티커(index), 종가, 시가총액, 거래량, 거래대금, 상장주식수
                        cap_df.columns = ['ticker', '종가', '시가총액', '거래량', '거래대금', '상장주식수']
                        cap_df['market'] = mkt
                        result_dfs.append(cap_df)
                except Exception as e:
                    logger.warning(f"[PyKRXGateway] Failed to get {mkt} snapshot: {e}")
            
            if not result_dfs:
                return pd.DataFrame()
            
            combined = pd.concat(result_dfs, ignore_index=True)
            
            # 등락률 조회 (별도 API)
            try:
                for mkt in markets_to_fetch:
                    ohlcv_df = pykrx_stock.get_market_ohlcv_by_ticker(date, market=mkt)
                    if ohlcv_df is not None and not ohlcv_df.empty:
                        ohlcv_df = ohlcv_df.reset_index()
                        ohlcv_df.columns = ['ticker', '시가', '고가', '저가', '종가2', '거래량2', '거래대금2', '등락률']
                        # 등락률만 병합
                        combined = combined.merge(
                            ohlcv_df[['ticker', '등락률']], 
                            on='ticker', 
                            how='left'
                        )
            except Exception as e:
                logger.debug(f"[PyKRXGateway] 등락률 조회 생략: {e}")
                combined['등락률'] = 0.0
            
            elapsed = time.time() - start_time
            logger.info(f"[PyKRXGateway] Market snapshot: {len(combined)} stocks in {elapsed:.2f}s")
            
            return combined
            
        except Exception as e:
            logger.error(f"[PyKRXGateway] Failed to get market snapshot: {e}")
            return pd.DataFrame()
    
    def get_market_ohlcv_multi_day(
        self,
        days: int = 20,
        market: str = "ALL"
    ) -> pd.DataFrame:
        """
        전체 시장의 다일간 OHLCV 데이터 조회 (RSI 계산용)
        
        각 일자별로 전체 시장 OHLCV를 조회하여 MultiIndex DataFrame 반환.
        개별 종목 조회보다 훨씬 빠름 (500개 × 30초 → 14일 × 0.5초 = 7초)
        
        Args:
            days: 조회할 과거 일수 (기본 20일)
            market: "KOSPI", "KOSDAQ", or "ALL"
            
        Returns:
            MultiIndex DataFrame (ticker, date) with OHLCV columns
            
        Example:
            >>> df = gateway.get_market_ohlcv_multi_day(days=20)
            >>> df.head()
                                시가    고가    저가    종가      거래량
            ticker  date
            005930  2025-12-10  56000  58000  55500  57500  12345678
        """
        if not self._initialized:
            logger.warning("[PyKRXGateway] Not initialized")
            return pd.DataFrame()
        
        try:
            from pykrx import stock as pykrx_stock
            import time
            
            start_time = time.time()
            
            # 거래일 리스트 생성 (주말/공휴일 제외)
            trading_days = self._get_trading_days(days)
            
            if not trading_days:
                logger.warning("[PyKRXGateway] No trading days found")
                return pd.DataFrame()
            
            logger.info(f"[PyKRXGateway] Fetching {len(trading_days)} days of market OHLCV...")
            
            all_data = []
            markets_to_fetch = ["KOSPI", "KOSDAQ"] if market == "ALL" else [market]
            
            # Phase 0.1: 병렬 처리로 성능 개선 (15s → 1.5s)
            from concurrent.futures import ThreadPoolExecutor, as_completed
            
            def fetch_day_market(date_str, mkt):
                """단일 날짜/시장 OHLCV 조회"""
                try:
                    df = pykrx_stock.get_market_ohlcv_by_ticker(date_str, market=mkt)
                    
                    if df is not None and not df.empty:
                        df = df.reset_index()
                        # pykrx 반환 컨럼: 티커, 시가, 고가, 저가, 종가, 거래량, 거래대금, 등락률, 시가총액 (9개)
                        df.columns = ['ticker', '시가', '고가', '저가', '종가', '거래량', '거래대금', '등락률', '시가총액']
                        df['date'] = date_str
                        df['market'] = mkt
                        return df
                except Exception as e:
                    logger.debug(f"[PyKRXGateway] OHLCV fetch failed for {date_str}/{mkt}: {e}")
                return None
            
            # 작업 목록 생성
            tasks = [(date_str, mkt) for date_str in trading_days for mkt in markets_to_fetch]
            
            # 병렬 실행 (최대 10 workers)
            with ThreadPoolExecutor(max_workers=10) as executor:
                future_to_task = {
                    executor.submit(fetch_day_market, date_str, mkt): (date_str, mkt)
                    for date_str, mkt in tasks
                }
                
                for future in as_completed(future_to_task):
                    result = future.result()
                    if result is not None:
                        all_data.append(result)
            
            if not all_data:
                return pd.DataFrame()
            
            # MultiIndex DataFrame 생성
            combined = pd.concat(all_data, ignore_index=True)
            combined['date'] = pd.to_datetime(combined['date'], format='%Y%m%d')
            combined = combined.set_index(['ticker', 'date']).sort_index()
            
            elapsed = time.time() - start_time
            unique_tickers = combined.index.get_level_values('ticker').nunique()
            logger.info(f"[PyKRXGateway] Multi-day OHLCV: {unique_tickers} stocks × {len(trading_days)} days in {elapsed:.2f}s")
            
            return combined
            
        except Exception as e:
            logger.error(f"[PyKRXGateway] Multi-day OHLCV failed: {e}")
            return pd.DataFrame()
    
    def _get_trading_days(self, days: int = 20) -> list:
        """
        최근 N 거래일 리스트 반환 (주말/공휴일 제외)
        """
        from pykrx import stock as pykrx_stock
        
        today = datetime.now()
        start_date = today - timedelta(days=days + 10)  # 여유있게 조회
        
        start_str = start_date.strftime("%Y%m%d")
        end_str = today.strftime("%Y%m%d")
        
        try:
            # pykrx에서 거래일 목록 조회
            trading_days = pykrx_stock.get_index_ohlcv_by_date(
                start_str, end_str, "1001"  # KOSPI 지수
            ).index.strftime("%Y%m%d").tolist()
            
            # 최근 N일만 반환
            return trading_days[-days:] if len(trading_days) > days else trading_days
            
        except Exception as e:
            logger.debug(f"[PyKRXGateway] Trading days fetch failed: {e}")
            # 폴백: 평일만 반환
            trading_days = []
            candidate = today
            while len(trading_days) < days:
                candidate = candidate - timedelta(days=1)
                if candidate.weekday() < 5:  # 월-금
                    trading_days.append(candidate.strftime("%Y%m%d"))
            return trading_days[::-1]  # 오래된 순서로

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
                        # 컬럼 정규화
                        df.columns = ['시가', '고가', '저가', '종가', '거래량', '거래대금', '등락률']
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
    
    def _empty_fundamental_dict(self) -> dict:
        """Phase 1: 빈 기본 정보 딕셔너리 생성 (API 실패 시)"""
        return {
            'marketcap': None,
            'per': None,
            'pbr': None,
            'dividend_yield': None,
            'week52_high': None,
            'week52_low': None
        }
    
    def get_stock_fundamental(self, ticker: str, date: str = None) -> dict:
        """
        종목의 기본 투자 지표 조회 (Phase 1)
        
        Args:
            ticker: 종목 코드 (6자리, 예: '005930')
            date: 날짜 (YYYYMMDD), None이면 최근 거래일
            
        Returns:
            dict with keys: marketcap, per, pbr, dividend_yield, week52_high, week52_low
        """
        if not self._initialized:
            return {}
        
        try:
            from pykrx import stock as pykrx_stock
            import yfinance as yf
            
            # Phase 1: 거래일 감지 에러 처리
            if date is None:
                try:
                    date = self._get_last_trading_day()
                except Exception as e:
                    logger.error(
                        f"[PyKRXGateway] Trading day detection failed for {ticker}: {e}. "
                        f"Returning empty fundamental data."
                    )
                    return self._empty_fundamental_dict()
            
            result = {}
            
            # 1. pykrx: 시가총액
            try:
                cap_df = pykrx_stock.get_market_cap_by_ticker(date, market="ALL")
                if ticker in cap_df.index:
                    ticker_data = cap_df.loc[ticker]
                    result['marketcap'] = float(ticker_data['시가총액'])
                else:
                    result['marketcap'] = None
            except JSONDecodeError as e:
                logger.warning(f"[PyKRXGateway] pykrx API returned empty response for {ticker} on {date}: {e}")
                result['marketcap'] = None
            except Exception as e:
                logger.debug(f"[PyKRXGateway] marketcap fetch failed for {ticker}: {e}")
                result['marketcap'] = None
            
            # 2. yfinance: PER, PBR, 배당, 52주 고/저
            try:
                yf_ticker = f"{ticker}.KS"
                ticker_obj = yf.Ticker(yf_ticker)
                info = ticker_obj.info
                
                if not info or info.get('regularMarketPrice') is None:
                    yf_ticker = f"{ticker}.KQ"
                    ticker_obj = yf.Ticker(yf_ticker)
                    info = ticker_obj.info
                
                if info:
                    result['per'] = info.get('forwardPE') or info.get('trailingPE')
                    result['pbr'] = info.get('priceToBook')
                    
                    div_yield = info.get('dividendYield')
                    if div_yield:
                        result['dividend_yield'] = round(div_yield * 100, 2)
                    
                    result['week52_high'] = info.get('fiftyTwoWeekHigh')
                    result['week52_low'] = info.get('fiftyTwoWeekLow')
                    
            except Exception as e:
                logger.debug(f"[PyKRXGateway] yfinance fetch failed for {ticker}: {e}")
                # Phase 1: Ensure keys exist even if yfinance fails
                result.setdefault('per', None)
                result.setdefault('pbr', None)
                result.setdefault('dividend_yield', None)
                result.setdefault('week52_high', None)
                result.setdefault('week52_low', None)
            
            # Phase 1: 최소한 모든 키는 존재하도록 보장
            for key in ['marketcap', 'per', 'pbr', 'dividend_yield', 'week52_high', 'week52_low']:
                result.setdefault(key, None)
            
            return result
            
        except Exception as e:
            logger.error(f"[PyKRXGateway] get_stock_fundamental failed for {ticker}: {e}")
            return self._empty_fundamental_dict()

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
