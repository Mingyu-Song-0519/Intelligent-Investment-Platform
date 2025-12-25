"""
Sector Repository - Infrastructure Layer
외부 API 기반 섹터-종목 매핑 관리

데이터 소스:
- 미국 시장: Yahoo Finance (yfinance)
- 한국 시장: FinanceDataReader (KRX API)

캐싱 전략:
- TTL: 24시간 (섹터 구성은 자주 바뀌지 않음)
- 첫 로드: ~30초, 이후: 즉시 (캐시 사용)
"""
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class SectorRepository:
    """
    섹터-종목 매핑 관리 (외부 API 기반)
    
    Features:
    - 24시간 캐싱
    - Graceful Degradation (API 실패 시 Fallback)
    - Rate Limiting 대응 (Yahoo Finance)
    """
    
    def __init__(self, cache_dir: Optional[Path] = None):
        """
        Args:
            cache_dir: 캐시 파일 저장 디렉토리 (기본: ./cache/sectors/)
        """
        self._cache_dir = cache_dir or Path(__file__).parent.parent.parent / "cache" / "sectors"
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        
        self._memory_cache: Dict[str, tuple] = {}  # {market: (data, timestamp)}
        self._cache_ttl = 86400  # 24시간
        
        # Yahoo Finance Rate Limiting 대응
        self._last_yf_call = datetime.min
        self._yf_delay = 0.1  # 100ms delay between calls
    
    # ===== Public API =====
    
    def get_sectors(self, market: str, force_refresh: bool = False) -> Dict[str, List[str]]:
        """
        섹터별 종목 리스트 반환
        
        Args:
            market: "US" 또는 "KR"
            force_refresh: 캐시 무시하고 강제 새로고침
        
        Returns:
            {sector_name: [ticker1, ticker2, ...]}
            
        Example:
            >>> repo = SectorRepository()
            >>> sectors = repo.get_sectors("US")
            >>> sectors["Technology"]
            ['AAPL', 'MSFT', 'GOOGL', 'NVDA', ...]
        """
        try:
            # 1. 메모리 캐시 확인
            if not force_refresh and self._is_memory_cache_valid(market):
                logger.info(f"[SectorRepo] Using memory cache for {market}")
                return self._memory_cache[market][0]
            
            # 2. 파일 캐시 확인
            if not force_refresh:
                file_cached = self._load_from_file_cache(market)
                if file_cached:
                    logger.info(f"[SectorRepo] Using file cache for {market}")
                    self._memory_cache[market] = (file_cached, datetime.now())
                    return file_cached
            
            # 3. 외부 API 호출 (캐시 없거나 강제 새로고침)
            logger.info(f"[SectorRepo] Fetching from external API for {market}")
            if market == "US":
                sectors = self._fetch_us_sectors()
            elif market == "KR":
                sectors = self._fetch_kr_sectors()
            else:
                raise ValueError(f"Unsupported market: {market}")
            
            # 4. 캐싱
            self._save_to_file_cache(market, sectors)
            self._memory_cache[market] = (sectors, datetime.now())
            
            logger.info(f"[SectorRepo] Fetched {len(sectors)} sectors for {market}")
            return sectors
            
        except Exception as e:
            logger.error(f"[SectorRepo] Failed to fetch sectors for {market}: {e}")
            # Graceful Degradation: Stale cache 반환
            return self._get_stale_cache(market)
    
    def get_stocks_by_sector(self, market: str, sector: str) -> List[str]:
        """
        특정 섹터의 종목 리스트 반환
        
        Args:
            market: "US" 또는 "KR"
            sector: 섹터명 (예: "Technology", "반도체")
        
        Returns:
            [ticker1, ticker2, ...]
        """
        sectors = self.get_sectors(market)
        return sectors.get(sector, [])
    
    def get_all_tickers(self, market: str) -> List[str]:
        """특정 시장의 모든 종목 리스트 반환"""
        sectors = self.get_sectors(market)
        all_tickers = []
        for tickers in sectors.values():
            all_tickers.extend(tickers)
        return list(set(all_tickers))  # 중복 제거
    
    # ===== US Market (Yahoo Finance) =====
    
    def _fetch_us_sectors(self) -> Dict[str, List[str]]:
        """
        Yahoo Finance로 S&P 500 섹터별 종목 조회
        
        GICS Sector 분류 (11개):
        - Information Technology
        - Health Care
        - Financials
        - Consumer Discretionary
        - Communication Services
        - Industrials
        - Consumer Staples
        - Energy
        - Utilities
        - Real Estate
        - Materials
        """
        import yfinance as yf
        import time
        
        # S&P 500 구성 종목 리스트 (Wikipedia에서 가져오거나 하드코딩)
        sp500_tickers = self._get_sp500_tickers()
        
        sectors_map: Dict[str, List[str]] = {}
        failed_tickers = []
        
        for ticker in sp500_tickers:
            try:
                # Rate Limiting 대응
                self._wait_for_rate_limit()
                
                # 종목 정보 조회
                stock = yf.Ticker(ticker)
                info = stock.info
                
                sector = info.get('sector', 'Unknown')
                if sector != 'Unknown':
                    if sector not in sectors_map:
                        sectors_map[sector] = []
                    sectors_map[sector].append(ticker)
                
                # Progress logging (매 50개마다)
                if len(sectors_map) % 50 == 0:
                    logger.info(f"[US Sectors] Processed {len(sectors_map)} tickers...")
                    
            except Exception as e:
                logger.warning(f"[US Sectors] Failed to fetch {ticker}: {e}")
                failed_tickers.append(ticker)
                continue
        
        if failed_tickers:
            logger.warning(f"[US Sectors] Failed tickers ({len(failed_tickers)}): {failed_tickers[:10]}...")
        
        return sectors_map
    
    def _get_sp500_tickers(self) -> List[str]:
        """
        S&P 500 구성 종목 리스트 반환
        
        Options:
        1. Wikipedia 크롤링 (실시간, 정확)
        2. pandas_datareader (편리)
        3. 하드코딩 (안정적, 주기적 업데이트 필요)
        """
        try:
            import pandas as pd
            # Wikipedia에서 S&P 500 리스트 가져오기
            url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
            tables = pd.read_html(url)
            df = tables[0]
            return df['Symbol'].str.replace('.', '-').tolist()
        except Exception as e:
            logger.error(f"[US Sectors] Failed to fetch S&P 500 list: {e}")
            # Fallback: 주요 종목만 반환
            return self._get_major_us_tickers()
    
    def _get_major_us_tickers(self) -> List[str]:
        """주요 미국 종목 리스트 (Fallback용)"""
        return [
            # Technology
            "AAPL", "MSFT", "GOOGL", "NVDA", "META", "TSLA", "AVGO", "ORCL", "AMD", "CRM",
            # Healthcare
            "UNH", "JNJ", "LLY", "ABBV", "MRK", "TMO", "ABT", "DHR", "PFE", "BMY",
            # Financials
            "BRK-B", "JPM", "V", "MA", "BAC", "WFC", "GS", "MS", "C", "AXP",
            # Consumer Discretionary
            "AMZN", "HD", "NKE", "MCD", "SBUX", "TGT", "LOW", "TJX",
            # Communication Services
            "GOOG", "META", "DIS", "NFLX", "T", "VZ", "CMCSA",
            # Industrials
            "UPS", "HON", "BA", "CAT", "GE", "MMM", "LMT", "RTX",
            # Consumer Staples
            "WMT", "PG", "KO", "PEP", "COST", "PM", "EL", "MO",
            # Energy
            "XOM", "CVX", "COP", "SLB", "EOG", "MPC", "PSX",
            # Utilities
            "NEE", "DUK", "SO", "D", "AEP", "EXC", "SRE",
            # Real Estate
            "AMT", "PLD", "CCI", "EQIX", "PSA", "SPG",
            # Materials
            "LIN", "APD", "ECL", "SHW", "FCX", "NEM"
        ]
    
    def _wait_for_rate_limit(self):
        """Yahoo Finance Rate Limiting 대응"""
        import time
        elapsed = (datetime.now() - self._last_yf_call).total_seconds()
        if elapsed < self._yf_delay:
            time.sleep(self._yf_delay - elapsed)
        self._last_yf_call = datetime.now()
    
    # ===== KR Market (FinanceDataReader) =====
    
    def _fetch_kr_sectors(self) -> Dict[str, List[str]]:
        """
        KRX 업종별 종목 조회
        
        Note: FinanceDataReader의 StockListing은 Sector 정보를 제공하지 않음
        따라서 KRX 공식 업종 분류 기반으로 하드코딩된 데이터 사용
        """
        # KRX 공식 업종 분류 기반 (시가총액 상위 종목 중심)
        return self._get_comprehensive_kr_sectors()
    
    def _get_comprehensive_kr_sectors(self) -> Dict[str, List[str]]:
        """KRX 업종별 주요 종목 (yfinance 호환 종목만)"""
        return {
            "반도체": [
                "005930.KS", "000660.KS", "042700.KS",  # 삼성전자, SK하이닉스, 한미반도체
            ],
            "2차전지": [
                "373220.KS", "006400.KS", "051910.KS", "003670.KS",  # LG에너지솔루션, 삼성SDI, LG화학, 포스코퓨처엠
            ],
            "자동차": [
                "005380.KS", "000270.KS", "012330.KS", "018880.KS",  # 현대차, 기아, 현대모비스, 한온시스템
            ],
            "바이오/제약": [
                "207940.KS", "068270.KS", "326030.KS", "128940.KS",  # 삼성바이오로직스, 셀트리온, SK바이오팜, 한미약품
            ],
            "금융": [
                "105560.KS", "055550.KS", "086790.KS", "316140.KS",  # KB금융, 신한지주, 하나금융지주, 우리금융지주
                "138040.KS", "024110.KS",  # 메리츠금융지주, 기업은행
            ],
            "IT/소프트웨어": [
                "035420.KS", "035720.KS", "036570.KS",  # NAVER, 카카오, NCsoft
            ],
            "전자/전기": [
                "066570.KS", "009150.KS", "011070.KS", "034220.KS",  # LG전자, 삼성전기, LG이노텍, LG디스플레이
            ],
            "철강/소재": [
                "005490.KS", "010130.KS", "004020.KS",  # POSCO홀딩스, 고려아연, 현대제철
            ],
            "화학": [
                "011170.KS", "009830.KS", "011780.KS",  # 롯데케미칼, 한화솔루션, 금호석유
            ],
            "조선/기계": [
                "009540.KS", "010140.KS", "042660.KS", "267250.KS",  # 한국조선해양, 삼성중공업, 한화오션, 현대중공업
            ],
            "건설": [
                "000720.KS", "006360.KS",  # 현대건설, GS건설
            ],
            "통신": [
                "017670.KS", "030200.KS", "032640.KS",  # SK텔레콤, KT, LG유플러스
            ],
            "유통/소비재": [
                "139480.KS", "004170.KS", "069960.KS",  # 이마트, 신세계, 현대백화점
            ],
            "식품/음료": [
                "097950.KS", "271560.KS", "033780.KS",  # CJ제일제당, 오리온, KT&G
            ],
            "항공/운송": [
                "003490.KS", "011200.KS",  # 대한항공, HMM
            ],
            "엔터테인먼트": [
                "035760.KS",  # CJ ENM
            ],
            "에너지": [
                "096770.KS", "010950.KS", "036460.KS",  # SK이노베이션, S-Oil, 한국가스공사
            ],
            "지주사": [
                "034730.KS", "003550.KS", "000880.KS", "001040.KS",  # SK, LG, 한화, CJ
            ],
        }
    
    def _get_fallback_kr_sectors(self) -> Dict[str, List[str]]:
        """한국 시장 Fallback (간소화 버전)"""
        return {
            "반도체": ["005930.KS", "000660.KS"],
            "2차전지": ["373220.KS", "006400.KS"],
            "바이오": ["207940.KS", "068270.KS"],
            "자동차": ["005380.KS", "000270.KS"],
            "금융": ["055550.KS", "105560.KS"],
        }
    
    # ===== Caching =====
    
    def _is_memory_cache_valid(self, market: str) -> bool:
        """메모리 캐시 유효성 검사"""
        if market not in self._memory_cache:
            return False
        _, timestamp = self._memory_cache[market]
        return (datetime.now() - timestamp).total_seconds() < self._cache_ttl
    
    def _load_from_file_cache(self, market: str) -> Optional[Dict[str, List[str]]]:
        """파일 캐시에서 로드"""
        cache_file = self._cache_dir / f"{market}_sectors.json"
        if not cache_file.exists():
            return None
        
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                cached = json.load(f)
            
            # 캐시 유효성 검사
            cached_time = datetime.fromisoformat(cached['timestamp'])
            if (datetime.now() - cached_time).total_seconds() > self._cache_ttl:
                logger.info(f"[SectorRepo] File cache expired for {market}")
                return None
            
            return cached['data']
        except Exception as e:
            logger.warning(f"[SectorRepo] Failed to load file cache for {market}: {e}")
            return None
    
    def _save_to_file_cache(self, market: str, data: Dict[str, List[str]]):
        """파일 캐시에 저장"""
        cache_file = self._cache_dir / f"{market}_sectors.json"
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'timestamp': datetime.now().isoformat(),
                    'data': data
                }, f, ensure_ascii=False, indent=2)
            logger.info(f"[SectorRepo] Saved file cache for {market}")
        except Exception as e:
            logger.error(f"[SectorRepo] Failed to save file cache for {market}: {e}")
    
    def _get_stale_cache(self, market: str) -> Dict[str, List[str]]:
        """
        Stale cache 반환 (Graceful Degradation)
        
        API 실패 시 오래된 캐시라도 반환하여 서비스 유지
        """
        # 1. 메모리 캐시 (TTL 무시)
        if market in self._memory_cache:
            logger.warning(f"[SectorRepo] Using stale memory cache for {market}")
            return self._memory_cache[market][0]
        
        # 2. 파일 캐시 (TTL 무시)
        cache_file = self._cache_dir / f"{market}_sectors.json"
        if cache_file.exists():
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cached = json.load(f)
                logger.warning(f"[SectorRepo] Using stale file cache for {market}")
                return cached['data']
            except Exception as e:
                logger.error(f"[SectorRepo] Failed to load stale cache: {e}")
        
        # 3. 최후의 수단: Fallback 하드코딩 데이터
        logger.error(f"[SectorRepo] All caches failed. Using fallback for {market}")
        if market == "KR":
            return self._get_fallback_kr_sectors()
        else:
            # US Fallback: Major tickers만 반환
            major_tickers = self._get_major_us_tickers()
            return {"Major Stocks": major_tickers}
