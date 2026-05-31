"""
알림 시스템 모듈 - VIX 급등, MDD 초과, RSI 과매수/과매도 등 주요 이벤트 알림
2024-2025 트렌드: 실시간 리스크 모니터링 및 자동 알림
"""
import logging
import smtplib
import requests
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, List, Optional, Callable

logger = logging.getLogger(__name__)
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum


class AlertLevel(Enum):
    """알림 수준"""
    INFO = "info"       # 정보
    WARNING = "warning" # 경고
    CRITICAL = "critical"  # 위험


class AlertType(Enum):
    """알림 유형"""
    VIX_SPIKE = "vix_spike"           # VIX 급등
    MDD_THRESHOLD = "mdd_threshold"   # MDD 임계값 초과
    RSI_OVERBOUGHT = "rsi_overbought" # RSI 과매수
    RSI_OVERSOLD = "rsi_oversold"     # RSI 과매도
    PRICE_TARGET = "price_target"     # 목표가 도달
    VOLUME_SURGE = "volume_surge"     # 거래량 급증
    TREND_CHANGE = "trend_change"     # 추세 전환


@dataclass
class AlertConfig:
    """알림 설정"""
    # VIX 관련
    vix_spike_threshold: float = 25.0      # VIX 경고 임계값
    vix_critical_threshold: float = 35.0   # VIX 위험 임계값
    
    # MDD 관련
    mdd_warning_threshold: float = 10.0    # MDD 경고 % 
    mdd_critical_threshold: float = 20.0   # MDD 위험 %
    
    # RSI 관련
    rsi_overbought: float = 70.0
    rsi_oversold: float = 30.0
    
    # 거래량 관련
    volume_surge_multiplier: float = 3.0   # 평균 대비 N배
    
    # 알림 채널
    email_enabled: bool = False
    telegram_enabled: bool = False
    
    # Email 설정
    smtp_server: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    recipient_email: str = ""
    
    # Telegram 설정
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""


@dataclass
class Alert:
    """알림 객체"""
    alert_type: AlertType
    level: AlertLevel
    title: str
    message: str
    ticker: str = ""
    value: float = 0.0
    threshold: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict:
        return {
            "type": self.alert_type.value,
            "level": self.level.value,
            "title": self.title,
            "message": self.message,
            "ticker": self.ticker,
            "value": self.value,
            "threshold": self.threshold,
            "timestamp": self.timestamp.isoformat()
        }
    
    def to_html(self) -> str:
        """HTML 포맷 알림"""
        level_colors = {
            AlertLevel.INFO: "#3498db",
            AlertLevel.WARNING: "#f39c12",
            AlertLevel.CRITICAL: "#e74c3c"
        }
        level_emojis = {
            AlertLevel.INFO: "ℹ️",
            AlertLevel.WARNING: "⚠️",
            AlertLevel.CRITICAL: "🚨"
        }
        
        return f"""
        <div style="border-left: 4px solid {level_colors[self.level]}; padding: 10px; margin: 10px 0;">
            <h3>{level_emojis[self.level]} {self.title}</h3>
            <p>{self.message}</p>
            <p style="color: gray; font-size: 12px;">
                종목: {self.ticker} | 값: {self.value:.2f} | 임계값: {self.threshold:.2f}
            </p>
            <p style="color: gray; font-size: 10px;">{self.timestamp.strftime("%Y-%m-%d %H:%M:%S")}</p>
        </div>
        """
    
    def to_telegram(self) -> str:
        """Telegram 포맷 알림"""
        level_emojis = {
            AlertLevel.INFO: "ℹ️",
            AlertLevel.WARNING: "⚠️",
            AlertLevel.CRITICAL: "🚨"
        }
        
        return f"""{level_emojis[self.level]} *{self.title}*

{self.message}

📊 종목: `{self.ticker}`
📈 현재값: `{self.value:.2f}`
🎯 임계값: `{self.threshold:.2f}`

⏰ {self.timestamp.strftime("%Y-%m-%d %H:%M:%S")}
"""


class NotificationManager:
    """알림 관리 클래스"""
    
    def __init__(self, config: Optional[AlertConfig] = None):
        """
        Args:
            config: 알림 설정 (없으면 기본값 사용)
        """
        self.config = config or AlertConfig()
        self.alert_history: List[Alert] = []
        self.callbacks: List[Callable[[Alert], None]] = []
    
    def add_callback(self, callback: Callable[[Alert], None]):
        """알림 발생 시 호출할 콜백 등록"""
        self.callbacks.append(callback)
    
    def check_vix(self, current_vix: float) -> Optional[Alert]:
        """
        VIX 수준 체크 및 알림 생성
        
        Args:
            current_vix: 현재 VIX 값
            
        Returns:
            Alert 객체 (임계값 미달 시 None)
        """
        if current_vix >= self.config.vix_critical_threshold:
            alert = Alert(
                alert_type=AlertType.VIX_SPIKE,
                level=AlertLevel.CRITICAL,
                title="🚨 VIX 극고 - 시장 공포 확산",
                message=f"VIX가 {current_vix:.1f}로 급등했습니다. 극도의 변동성이 예상됩니다.",
                ticker="^VIX",
                value=current_vix,
                threshold=self.config.vix_critical_threshold
            )
            self._process_alert(alert)
            return alert
            
        elif current_vix >= self.config.vix_spike_threshold:
            alert = Alert(
                alert_type=AlertType.VIX_SPIKE,
                level=AlertLevel.WARNING,
                title="⚠️ VIX 상승 - 변동성 확대",
                message=f"VIX가 {current_vix:.1f}로 상승했습니다. 시장 불안이 증가하고 있습니다.",
                ticker="^VIX",
                value=current_vix,
                threshold=self.config.vix_spike_threshold
            )
            self._process_alert(alert)
            return alert
        
        return None
    
    def check_mdd(self, current_mdd: float, ticker: str = "") -> Optional[Alert]:
        """
        MDD (최대 낙폭) 체크 및 알림 생성
        
        Args:
            current_mdd: 현재 MDD (%)
            ticker: 종목 코드
        """
        if current_mdd >= self.config.mdd_critical_threshold:
            alert = Alert(
                alert_type=AlertType.MDD_THRESHOLD,
                level=AlertLevel.CRITICAL,
                title="🚨 MDD 위험 수준 초과",
                message=f"최대 낙폭이 {current_mdd:.1f}%로 위험 수준입니다. 손절 검토가 필요합니다.",
                ticker=ticker,
                value=current_mdd,
                threshold=self.config.mdd_critical_threshold
            )
            self._process_alert(alert)
            return alert
            
        elif current_mdd >= self.config.mdd_warning_threshold:
            alert = Alert(
                alert_type=AlertType.MDD_THRESHOLD,
                level=AlertLevel.WARNING,
                title="⚠️ MDD 경고 수준",
                message=f"최대 낙폭이 {current_mdd:.1f}%입니다. 포지션 점검을 권장합니다.",
                ticker=ticker,
                value=current_mdd,
                threshold=self.config.mdd_warning_threshold
            )
            self._process_alert(alert)
            return alert
        
        return None
    
    def check_rsi(self, current_rsi: float, ticker: str = "") -> Optional[Alert]:
        """
        RSI 과매수/과매도 체크 및 알림 생성
        """
        if current_rsi >= self.config.rsi_overbought:
            alert = Alert(
                alert_type=AlertType.RSI_OVERBOUGHT,
                level=AlertLevel.WARNING,
                title="⚠️ RSI 과매수 신호",
                message=f"RSI가 {current_rsi:.1f}로 과매수 구간입니다. 차익실현을 고려하세요.",
                ticker=ticker,
                value=current_rsi,
                threshold=self.config.rsi_overbought
            )
            self._process_alert(alert)
            return alert
            
        elif current_rsi <= self.config.rsi_oversold:
            alert = Alert(
                alert_type=AlertType.RSI_OVERSOLD,
                level=AlertLevel.INFO,
                title="ℹ️ RSI 과매도 신호",
                message=f"RSI가 {current_rsi:.1f}로 과매도 구간입니다. 반등 가능성을 검토하세요.",
                ticker=ticker,
                value=current_rsi,
                threshold=self.config.rsi_oversold
            )
            self._process_alert(alert)
            return alert
        
        return None
    
    def check_volume_surge(
        self, 
        current_volume: float, 
        average_volume: float, 
        ticker: str = ""
    ) -> Optional[Alert]:
        """거래량 급증 체크"""
        if average_volume <= 0:
            return None
            
        volume_ratio = current_volume / average_volume
        
        if volume_ratio >= self.config.volume_surge_multiplier:
            alert = Alert(
                alert_type=AlertType.VOLUME_SURGE,
                level=AlertLevel.INFO,
                title="ℹ️ 거래량 급증 감지",
                message=f"거래량이 평균 대비 {volume_ratio:.1f}배 증가했습니다. 관심 종목으로 체크하세요.",
                ticker=ticker,
                value=volume_ratio,
                threshold=self.config.volume_surge_multiplier
            )
            self._process_alert(alert)
            return alert
        
        return None
    
    def _process_alert(self, alert: Alert):
        """알림 처리 (저장, 콜백, 발송)"""
        # 기록
        self.alert_history.append(alert)
        
        # 콜백 실행
        for callback in self.callbacks:
            try:
                callback(alert)
            except Exception as e:
                logger.warning(f"Callback error: {e}")
        
        # 알림 발송
        if self.config.email_enabled:
            self._send_email(alert)
        
        if self.config.telegram_enabled:
            self._send_telegram(alert)
    
    def _send_email(self, alert: Alert) -> bool:
        """이메일 알림 발송"""
        if not all([
            self.config.smtp_server,
            self.config.smtp_user,
            self.config.smtp_password,
            self.config.recipient_email
        ]):
            logger.warning("Email configuration incomplete")
            return False
        
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = f"[Stock Alert] {alert.title}"
            msg["From"] = self.config.smtp_user
            msg["To"] = self.config.recipient_email
            
            # HTML 본문
            html_part = MIMEText(alert.to_html(), "html")
            msg.attach(html_part)
            
            with smtplib.SMTP(self.config.smtp_server, self.config.smtp_port) as server:
                server.starttls()
                server.login(self.config.smtp_user, self.config.smtp_password)
                server.sendmail(
                    self.config.smtp_user,
                    self.config.recipient_email,
                    msg.as_string()
                )
            
            logger.info(f"Email sent: {alert.title}")
            return True
            
        except Exception as e:
            logger.error(f"Email send failed: {e}")
            return False
    
    def _send_telegram(self, alert: Alert) -> bool:
        """텔레그램 알림 발송"""
        if not all([
            self.config.telegram_bot_token,
            self.config.telegram_chat_id
        ]):
            logger.warning("Telegram configuration incomplete")
            return False
        
        try:
            url = f"https://api.telegram.org/bot{self.config.telegram_bot_token}/sendMessage"
            
            payload = {
                "chat_id": self.config.telegram_chat_id,
                "text": alert.to_telegram(),
                "parse_mode": "Markdown"
            }
            
            response = requests.post(url, json=payload, timeout=10)
            
            if response.status_code == 200:
                logger.info(f"Telegram sent: {alert.title}")
                return True
            else:
                logger.error(f"Telegram API error: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Telegram send failed: {e}")
            return False
    
    def get_recent_alerts(self, count: int = 10) -> List[Alert]:
        """최근 알림 조회"""
        return self.alert_history[-count:]
    
    def clear_history(self):
        """알림 기록 초기화"""
        self.alert_history.clear()


# 편의 함수
def create_default_notification_manager() -> NotificationManager:
    """기본 설정의 알림 관리자 생성"""
    return NotificationManager(AlertConfig())


if __name__ == "__main__":
    # 테스트
    print("=== 알림 시스템 테스트 ===")
    
    manager = NotificationManager()
    
    # VIX 테스트
    alert1 = manager.check_vix(28.5)
    if alert1:
        print(f"VIX 알림: {alert1.title}")
    
    # MDD 테스트
    alert2 = manager.check_mdd(15.0, "005930.KS")
    if alert2:
        print(f"MDD 알림: {alert2.title}")
    
    # RSI 테스트
    alert3 = manager.check_rsi(75.0, "AAPL")
    if alert3:
        print(f"RSI 알림: {alert3.title}")
    
    # 기록 확인
    print(f"\n총 {len(manager.get_recent_alerts())}개 알림 발생")
