"""
Legacy Adapter - Strangler Fig Pattern
기존 collectors/, analyzers/ 모듈을 새 인터페이스로 래핑
점진적 마이그레이션을 위한 어댑터
"""
import sys
from pathlib import Path
from typing import List, Optional, Dict

# 기존 코드 경로 추가
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.domain.repositories.interfaces import IStockRepository, INewsRepository
from src.domain.entities.stock import StockEntity, SignalEntity


class LegacyCollectorAdapter(IStockRepository):
    """
    기존 StockDataCollector를 IStockRepository로 래핑
    
    Strangler Fig Pattern:
    - 기존 코드 수정 없이 새 인터페이스 적용
    - 점진적으로 YFinanceStockRepository로 대체 예정
    """
    
    def __init__(self):
        from src.collectors.stock_collector import StockDataCollector
        self._legacy_collector = StockDataCollector()
    
    def get_stock_data(
        self, 
        ticker: str, 
        period: str = "1mo",
        interval: str = "1d"
    ) -> Optional[StockEntity]:
        """기존 collector로 데이터 조회 후 Entity 변환"""
        
        try:
            # 기존 메서드 호출
            df = self._legacy_collector.fetch_stock_data(ticker, period=period)
            
            if df is None or df.empty:
                return None
            
            # DataFrame → StockEntity 변환
            market = "KR" if ticker.endswith(".KS") else "US"
            
            return StockEntity.from_dataframe(
                ticker=ticker,
                df=df,
                name=ticker.split(".")[0],
                market=market
            )
            
        except Exception as e:
            print(f"[ERROR] LegacyCollectorAdapter.get_stock_data: {e}")
            return None
    
    def get_multiple_stocks(
        self, 
        tickers: List[str], 
        period: str = "1mo"
    ) -> Dict[str, StockEntity]:
        """여러 종목 조회"""
        
        result = {}
        for ticker in tickers:
            stock = self.get_stock_data(ticker, period)
            if stock:
                result[ticker] = stock
        
        return result
    
    def get_stock_info(self, ticker: str) -> Optional[Dict]:
        """종목 정보 조회 (yfinance 직접 사용)"""
        
        import yfinance as yf
        
        try:
            ticker_obj = yf.Ticker(ticker)
            info = ticker_obj.info
            
            return {
                "name": info.get("shortName") or info.get("longName"),
                "sector": info.get("sector"),
                "industry": info.get("industry"),
                "market_cap": info.get("marketCap")
            }
        except Exception as e:
            print(f"[ERROR] LegacyCollectorAdapter.get_stock_info: {e}")
            return None


class LegacyNewsAdapter(INewsRepository):
    """
    기존 NewsCollector를 INewsRepository로 래핑
    """
    
    def __init__(self):
        from src.collectors.news_collector import NewsCollector
        self._legacy_collector = NewsCollector()
    
    def get_news(
        self, 
        keyword: str, 
        max_results: int = 10,
        language: str = "ko"
    ) -> List[Dict]:
        """뉴스 검색"""
        
        try:
            if language == "ko":
                # 네이버 금융 뉴스
                articles = self._legacy_collector.fetch_naver_finance_news(
                    keyword, max_pages=2
                )
            else:
                # Google News 영문
                articles = self._legacy_collector.fetch_google_news_en_rss(
                    keyword, max_results=max_results
                )
            
            return articles[:max_results]
            
        except Exception as e:
            print(f"[ERROR] LegacyNewsAdapter.get_news: {e}")
            return []
    
    def get_stock_news(
        self, 
        ticker: str, 
        max_results: int = 10
    ) -> List[Dict]:
        """종목 관련 뉴스 검색"""
        
        # 티커에서 종목명 유추
        stock_name = ticker.replace(".KS", "").replace(".KQ", "")
        
        return self.get_news(stock_name, max_results)


class LegacyAnalyzerAdapter:
    """
    기존 TechnicalAnalyzer를 래핑
    """
    
    def __init__(self):
        from src.analyzers.technical_analyzer import TechnicalAnalyzer
        self._analyzer_class = TechnicalAnalyzer
    
    def analyze(self, stock: StockEntity) -> Dict:
        """기술적 분석 실행"""
        
        try:
            # Entity → DataFrame
            df = stock.to_dataframe()
            
            # 기존 Analyzer 사용
            analyzer = self._analyzer_class(df)
            analyzer.add_all_indicators()
            result_df = analyzer.get_dataframe()
            
            # 최신 지표값 추출
            latest = result_df.iloc[-1] if not result_df.empty else {}
            
            return {
                "rsi": latest.get("rsi"),
                "macd": latest.get("macd"),
                "macd_signal": latest.get("macd_signal"),
                "bb_upper": latest.get("bb_upper"),
                "bb_lower": latest.get("bb_lower"),
                "adx": latest.get("adx"),
                "vwap": latest.get("vwap"),
                "obv": latest.get("obv")
            }
            
        except Exception as e:
            print(f"[ERROR] LegacyAnalyzerAdapter.analyze: {e}")
            return {}
    
    def get_signal(self, stock: StockEntity) -> SignalEntity:
        """기술적 분석 기반 매매 신호 생성"""
        
        indicators = self.analyze(stock)
        
        # 간단한 규칙 기반 신호
        rsi = indicators.get("rsi", 50)
        macd = indicators.get("macd", 0)
        macd_signal = indicators.get("macd_signal", 0)
        
        signal_type = SignalEntity.SignalType.HOLD
        confidence = 0.5
        reason = ""
        
        if rsi and rsi < 30:
            signal_type = SignalEntity.SignalType.BUY
            confidence = 0.7
            reason = f"RSI 과매도 ({rsi:.1f})"
        elif rsi and rsi > 70:
            signal_type = SignalEntity.SignalType.SELL
            confidence = 0.7
            reason = f"RSI 과매수 ({rsi:.1f})"
        elif macd and macd_signal and macd > macd_signal:
            signal_type = SignalEntity.SignalType.BUY
            confidence = 0.6
            reason = "MACD 골든크로스"
        elif macd and macd_signal and macd < macd_signal:
            signal_type = SignalEntity.SignalType.SELL
            confidence = 0.6
            reason = "MACD 데드크로스"
        
        return SignalEntity(
            ticker=stock.ticker,
            signal_type=signal_type,
            confidence=confidence,
            reason=reason,
            source="TECHNICAL"
        )
