"""
Technical Analysis Service - Application Layer
기술적 분석을 위한 Application Service

Clean Architecture:
- Repository에서 데이터 조회
- TechnicalAnalyzer로 지표 계산
- 결과를 Entity로 반환
"""
from typing import Dict, Optional
import pandas as pd

from src.domain.repositories.interfaces import IStockRepository
from src.domain.entities.stock import StockEntity, SignalEntity


class TechnicalAnalysisService:
    """
    기술적 분석 Service
    
    DI: IStockRepository를 주입받아 사용
    """
    
    def __init__(self, stock_repo: IStockRepository):
        """
        Args:
            stock_repo: IStockRepository 구현체
        """
        self.stock_repo = stock_repo
    
    def analyze(self, ticker: str, period: str = "1mo") -> Optional[Dict]:
        """
        종목의 기술적 지표 분석
        
        Args:
            ticker: 종목 코드
            period: 데이터 기간
            
        Returns:
            {
                'rsi': float,
                'macd': float,
                'macd_signal': float,
                'bb_upper': float,
                'bb_lower': float,
                'adx': float,
                'vwap': float,
                'obv': float
            }
        """
        try:
            # Repository에서 데이터 조회
            stock = self.stock_repo.get_stock_data(ticker, period=period)
            
            if not stock:
                return None
            
            # StockEntity → DataFrame
            df = stock.to_dataframe()
            
            if df.empty:
                return None
            
            # TechnicalAnalyzer 사용
            from src.analyzers.technical_analyzer import TechnicalAnalyzer
            
            analyzer = TechnicalAnalyzer(df)
            analyzer.add_all_indicators()
            result_df = analyzer.get_dataframe()
            
            # 최신 지표값 추출
            if result_df.empty:
                return None
            
            latest = result_df.iloc[-1]
            
            return {
                'rsi': latest.get('rsi'),
                'macd': latest.get('macd'),
                'macd_signal': latest.get('macd_signal'),
                'bb_upper': latest.get('bb_upper'),
                'bb_lower': latest.get('bb_lower'),
                'adx': latest.get('adx'),
                'vwap': latest.get('vwap'),
                'obv': latest.get('obv')
            }
            
        except Exception as e:
            print(f"[ERROR] TechnicalAnalysisService.analyze: {e}")
            return None
    
    def get_signal(self, ticker: str, period: str = "1mo") -> Optional[SignalEntity]:
        """
        기술적 분석 기반 매매 신호 생성
        
        Args:
            ticker: 종목 코드
            period: 데이터 기간
            
        Returns:
            SignalEntity (BUY/SELL/HOLD)
        """
        try:
            indicators = self.analyze(ticker, period)
            
            if not indicators:
                return None
            
            # 간단한 규칙 기반 신호
            rsi = indicators.get('rsi', 50)
            macd = indicators.get('macd', 0)
            macd_signal = indicators.get('macd_signal', 0)
            
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
                ticker=ticker,
                signal_type=signal_type,
                confidence=confidence,
                reason=reason,
                source="TECHNICAL"
            )
            
        except Exception as e:
            print(f"[ERROR] TechnicalAnalysisService.get_signal: {e}")
            return None
