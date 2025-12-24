"""
Alert Orchestrator Service - Application Layer
알림 발송 오케스트레이션 (Phase 9-5 NotificationManager 연동)
"""
from typing import List, Dict, Optional
from datetime import datetime

from src.domain.entities.stock import StockEntity, SignalEntity
from src.domain.repositories.interfaces import IStockRepository


class AlertOrchestratorService:
    """
    알림 발송 오케스트레이션 서비스
    
    Phase 9-5 NotificationManager와 연동하여
    - VIX 급등 알림
    - MDD 초과 알림
    - 매매 신호 알림
    """
    
    def __init__(
        self,
        stock_repo: IStockRepository,
        notification_manager=None
    ):
        """
        Args:
            stock_repo: IStockRepository 구현체
            notification_manager: NotificationManager 인스턴스 (Phase 9-5)
        """
        self.stock_repo = stock_repo
        self.notification_manager = notification_manager
    
    def check_and_alert_vix(self) -> Optional[Dict]:
        """
        VIX 수준 체크 및 알림
        
        Returns:
            Alert 정보 또는 None
        """
        if not self.notification_manager:
            return None
        
        try:
            # VIX 데이터 조회
            from src.analyzers.volatility_analyzer import VolatilityAnalyzer
            
            analyzer = VolatilityAnalyzer()
            vix = analyzer.get_current_vix()
            
            if vix:
                # NotificationManager로 체크
                alert = self.notification_manager.check_vix(vix)
                
                if alert:
                    return alert.to_dict()
                    
        except Exception as e:
            print(f"[ERROR] AlertOrchestratorService.check_and_alert_vix: {e}")
        
        return None
    
    def check_and_alert_portfolio_mdd(
        self,
        ticker: str,
        threshold: float = 10.0
    ) -> Optional[Dict]:
        """
        종목 MDD 체크 및 알림
        
        Args:
            ticker: 종목 코드
            threshold: 알림 임계값 (%)
        """
        if not self.notification_manager:
            return None
        
        try:
            # 종목 데이터 조회
            stock = self.stock_repo.get_stock_data(ticker, period="1mo")
            
            if not stock:
                return None
            
            # MDD 계산
            mdd = stock.get_max_drawdown()
            
            if mdd >= threshold:
                alert = self.notification_manager.check_mdd(mdd, ticker)
                
                if alert:
                    return alert.to_dict()
                    
        except Exception as e:
            print(f"[ERROR] AlertOrchestratorService.check_and_alert_portfolio_mdd: {e}")
        
        return None
    
    def check_and_alert_trading_signal(
        self,
        signal: SignalEntity
    ) -> bool:
        """
        매매 신호 알림
        
        Args:
            signal: SignalEntity
            
        Returns:
            알림 발송 성공 여부
        """
        if not self.notification_manager:
            return False
        
        try:
            # 강한 신호만 알림 (STRONG_BUY, STRONG_SELL)
            if signal.signal_type in [
                SignalEntity.SignalType.STRONG_BUY,
                SignalEntity.SignalType.STRONG_SELL
            ]:
                # Custom Alert 생성
                from src.utils.notification_manager import Alert, AlertLevel, AlertType
                
                level = AlertLevel.INFO if signal.is_bullish else AlertLevel.WARNING
                
                alert = Alert(
                    alert_type=AlertType.PRICE_TARGET,
                    level=level,
                    title=f"{signal.to_emoji()} {signal.ticker} 매매 신호",
                    message=f"{signal.signal_type}: {signal.reason}",
                    ticker=signal.ticker,
                    value=signal.confidence,
                    threshold=0.7
                )
                
                # 알림 발송 (NotificationManager 내부 로직)
                self.notification_manager._process_alert(alert)
                
                return True
                
        except Exception as e:
            print(f"[ERROR] AlertOrchestratorService.check_and_alert_trading_signal: {e}")
        
        return False
    
    def batch_check_watchlist(
        self,
        tickers: List[str],
        check_vix: bool = True,
        check_mdd: bool = True
    ) -> Dict:
        """
        관심 종목 일괄 체크
        
        Args:
            tickers: 종목 코드 리스트
            check_vix: VIX 체크 여부
            check_mdd: MDD 체크 여부
            
        Returns:
            {
                "vix_alert": VIX 알림,
                "mdd_alerts": [{ticker: "AAPL", alert: {...}}, ...],
                "timestamp": ISO 시간
            }
        """
        result = {
            "vix_alert": None,
            "mdd_alerts": [],
            "timestamp": datetime.now().isoformat()
        }
        
        # VIX 체크
        if check_vix:
            vix_alert = self.check_and_alert_vix()
            if vix_alert:
                result["vix_alert"] = vix_alert
        
        # MDD 체크
        if check_mdd:
            for ticker in tickers:
                mdd_alert = self.check_and_alert_portfolio_mdd(ticker)
                if mdd_alert:
                    result["mdd_alerts"].append({
                        "ticker": ticker,
                        "alert": mdd_alert
                    })
        
        return result
