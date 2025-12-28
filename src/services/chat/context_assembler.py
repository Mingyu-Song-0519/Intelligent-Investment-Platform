"""
Context Assembler
Domain Service: ContextData -> System Prompt 변환 로직
Clean Architecture: Application Layer
"""
import logging
from typing import Dict, Any, List, Optional

from src.domain.chat.entities import ContextData

logger = logging.getLogger(__name__)


# Phase F: ChatHistory Repository Interface (Optional DI)
try:
    from src.infrastructure.repositories.chat_history_repository import (
        IChatHistoryRepository,
        SQLiteChatHistoryRepository
    )
    CHAT_HISTORY_AVAILABLE = True
except ImportError:
    CHAT_HISTORY_AVAILABLE = False
    IChatHistoryRepository = None


class ContextAssembler:
    """
    ContextData를 LLM 시스템 프롬프트로 변환하는 조립기
    
    Phase F: ChatHistoryRepository 통합으로 과거 분석 이력 활용
    """
    
    def __init__(self, history_repo: Optional['IChatHistoryRepository'] = None):
        """
        Args:
            history_repo: 대화 이력 저장소 (None이면 과거 이력 미표시)
        """
        self.history_repo = history_repo
    
    def assemble_system_prompt(self, context: ContextData) -> str:
        """
        ContextData를 기반으로 전체 시스템 프롬프트를 생성합니다.
        """
        parts = [
            "당신은 '스마트 투자 분석 플랫폼'의 AI 투자 비서입니다.",
            "사용자의 투자 질문에 친절하고 전문적으로 답변해야 합니다.",
            "사용자가 현재 보고 있는 화면의 정보(Context)가 아래에 제공됩니다.",
            "이 정보를 바탕으로 구체적이고 실질적인 조언을 제공하세요.",
            "",
            "--- [Current Context] ---",
            f"현재 보고 있는 탭: {context.tab_name}",
            f"시장: {'한국(KR)' if context.market == 'KR' else '미국(US)'}"
        ]
        
        # Phase F: 과거 분석 이력 추가
        if self.history_repo and context.user_id:
            history_section = self._format_recent_history(context.user_id)
            if history_section:
                parts.append(history_section)
        
        # 탭별 상세 정보 추가
        if context.active_ticker:
            parts.append(self._format_stock_context(context))
        
        if context.screener_results:
            parts.append(self._format_screener_context(context))
            
        if context.portfolio_summary:
            parts.append(self._format_portfolio_context(context))
            
        parts.append("---------------------------")
        parts.append("")
        
        # Phase E: 사용 가능한 도구(Tools) 설명 추가
        parts.append(self._format_tools_description(context))
        
        parts.append("")
        parts.append("답변 가이드라인:")
        parts.append("1. 제공된 Context 정보를 우선적으로 활용하세요.")
        parts.append("2. 종목에 대한 매수/매도 추천을 할 때는 근거(RSI, 수급, AI 점수 등)를 명시하세요.")
        parts.append("3. 사용자가 묻지 않은 과도한 정보는 피하고 핵심만 답변하세요.")
        parts.append("4. 한국어로 답변하세요.")
        parts.append("5. 사용자가 탭 이동, 종목 선택, 분석 실행을 요청하면 적절한 도구를 사용하세요.")
        parts.append("6. 과거 분석 이력이 있다면 일관된 투자 조언을 유지하세요.")
        
        # Few-shot 예시 추가 (P1-2)
        parts.append("")
        parts.append(self._format_few_shot_examples())
        
        return "\n".join(parts)
    
    def _format_recent_history(self, user_id: str) -> str:
        """
        Phase F: 최근 분석 이력 포맷팅
        """
        try:
            reports = self.history_repo.get_recent_reports(user_id, limit=3)
            if not reports:
                return ""
            
            lines = ["\n[최근 분석 이력]"]
            for r in reports:
                date_str = r.created_at.strftime('%m/%d')
                lines.append(f"- {date_str} {r.stock_name}: {r.signal_type} (신뢰도 {r.confidence_score:.0%})")
            
            return "\n".join(lines)
        except Exception as e:
            logger.warning(f"[ContextAssembler] Failed to get history: {e}")
            return ""
    
    def _format_few_shot_examples(self) -> str:
        """
        P1-2: Few-shot 예시 (분석가 스타일)
        """
        return """--- [응답 예시] ---
Q: "삼성전자 지금 살까요?"
A: "현재 RSI가 28로 과매도 구간입니다. 기관이 3일 연속 순매수 중이며, PBR 1.2는 역사적 저점 대비 매력적입니다. 단기 반등 가능성이 높으나, 반도체 업황 둔화 리스크가 있어 분할 매수를 권장합니다."

Q: "오늘 시장 어때?"
A: "KOSPI가 -1.2% 하락한 가운데, 외국인 5,000억 순매도가 부담입니다. 반도체/자동차 약세, 방산/조선 강세입니다. 현금 비중 확대를 고려할 시점입니다."
--------------------"""
        
    def _format_stock_context(self, context: ContextData) -> str:
        """단일 종목 분석 컨텍스트 포맷팅"""
        lines = [
            f"\n[선택된 종목 정보]",
            f"종목명: {context.active_stock_name}",
            f"종목코드: {context.active_ticker}",
            f"현재가: {context.current_price:,.0f}" if context.current_price else "현재가: 정보 없음"
        ]
        
        if context.technical_indicators:
            tech = context.technical_indicators
            lines.append(f"RSI: {tech.get('rsi', 'N/A')}")
            lines.append(f"PBR: {tech.get('pbr', 'N/A')}")
            lines.append(f"거래량: {tech.get('volume', 'N/A')}")
            
        if context.ai_report_summary:
            lines.append(f"\n[AI 분석 리포트 요약]")
            lines.append(context.ai_report_summary)
            
        return "\n".join(lines)
    
    def _format_screener_context(self, context: ContextData) -> str:
        """스크리너 결과 컨텍스트 포맷팅"""
        if not context.screener_results:
            return ""
            
        lines = ["\n[AI 종목 추천 결과 (Top 추천주)]"]
        
        for i, item in enumerate(context.screener_results, 1):
            name = item.get('stock_name', 'Unknown')
            ticker = item.get('ticker', '')
            score = item.get('ai_score', 0)
            reason = item.get('reason', '')
            price = item.get('current_price', 0)
            
            lines.append(f"{i}위: {name} ({ticker}) - AI점수: {score:.0f}")
            lines.append(f"   현재가: {price:,.0f}")
            lines.append(f"   추천이유: {reason}")
            
        return "\n".join(lines)

    def _format_portfolio_context(self, context: ContextData) -> str:
        """포트폴리오 컨텍스트 포맷팅"""
        if not context.portfolio_summary:
            return ""
            
        summary = context.portfolio_summary
        lines = [
            "\n[포트폴리오 현황]",
            f"총 자산: {summary.get('total_value', 0):,.0f}",
            f"수익률: {summary.get('return_pct', 0):+.2f}%",
            f"보유 종목 수: {summary.get('stock_count', 0)}"
        ]
        return "\n".join(lines)
    
    def _format_tools_description(self, context: ContextData) -> str:
        """
        Phase E: 사용 가능한 도구(Tools) 설명 생성
        
        LLM이 action 블록을 생성할 수 있도록 포맷과 예시를 제공합니다.
        """
        # 이동 가능한 탭 목록 (context에서 가져오거나 기본값 사용)
        available_tabs = context.available_tabs if context.available_tabs else [
            "📊 단일 종목 분석",
            "🌅 AI 종목 추천", 
            "🔴 실시간 시세",
            "⭐ 관심 종목",
            "📰 뉴스 감성 분석",
            "🤖 AI 예측",
            "⏮️ 백테스팅",
            "💼 포트폴리오 최적화",
            "⚠️ 리스크 관리",
            "👤 투자 성향"
        ]
        
        lines = [
            "--- [사용 가능한 도구 (Tools)] ---",
            "",
            "사용자가 특정 작업을 요청하면 아래 도구를 사용할 수 있습니다.",
            "도구를 사용하려면 응답에 ```action ... ``` 코드 블록을 포함하세요.",
            "",
            "**1. switch_tab**: 다른 탭으로 이동",
            f"   - 이동 가능한 탭: {', '.join(available_tabs)}",
            "   - 예시:",
            '   ```action',
            '   {"action": "switch_tab", "params": {"tab_name": "🌅 AI 종목 추천"}}',
            '   ```',
            "",
            "**2. select_stock**: 종목 선택 및 분석 탭으로 이동",
            "   - 종목코드 또는 종목명으로 선택 가능",
            "   - 예시:",
            '   ```action',
            '   {"action": "select_stock", "params": {"ticker": "005930", "name": "삼성전자"}}',
            '   ```',
            "",
            "**3. run_screener**: AI 종목 추천 실행 (추천 종목 찾기)",
            "   - market: KR(한국) 또는 US(미국)",
            "   - 예시:",
            '   ```action',
            '   {"action": "run_screener", "params": {"market": "KR"}}',
            '   ```',
            "",
            "**4. run_analysis**: 현재 선택된 종목 AI 분석 실행",
            "   - 예시:",
            '   ```action',
            '   {"action": "run_analysis", "params": {}}',
            '   ```',
            "",
            "**5. search_stock**: 종목명으로 종목코드 검색",
            "   - 예시:",
            '   ```action',
            '   {"action": "search_stock", "params": {"query": "현대차"}}',
            '   ```',
            "",
            "도구 실행 후 결과가 제공되면 그 결과를 바탕으로 자연스럽게 답변하세요.",
            "-----------------------------------"
        ]
        
        return "\n".join(lines)

