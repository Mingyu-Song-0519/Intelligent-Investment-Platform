"""
Chat Service
Application Service: 대화 관리 및 응답 생성
Clean Architecture: Application Layer
Phase E: AI Agentic Control 통합
Phase F: ChatHistoryRepository 통합
"""
import logging
import re
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime

from src.domain.chat.entities import ChatSession, ContextData, ChatMessage
from src.domain.chat.actions import UIAction, ActionExecutionResult
from src.services.chat.context_assembler import ContextAssembler
from src.services.chat.action_executor import ActionExecutor
from src.infrastructure.external.gemini_client import ILLMClient

# Phase F: Optional ChatHistory import
try:
    from src.infrastructure.repositories.chat_history_repository import (
        IChatHistoryRepository,
        SQLiteChatHistoryRepository
    )
    CHAT_HISTORY_AVAILABLE = True
except ImportError:
    CHAT_HISTORY_AVAILABLE = False
    IChatHistoryRepository = None

logger = logging.getLogger(__name__)


class ChatService:
    """
    AI 챗봇 서비스
    
    역할:
    1. 세션 관리 (메시지 저장)
    2. 컨텍스트 조립
    3. LLM 호출
    4. Phase E: Action 파싱 및 실행
    5. Phase F: 대화 이력 저장 및 활용
    """
    
    # Rate Limiting (Gemini Free: 15 RPM, 여유 있게 설정)
    MAX_CALLS_PER_MINUTE = 12
    
    def __init__(
        self, 
        llm_client: ILLMClient,
        action_executor: Optional[ActionExecutor] = None,
        history_repo: Optional['IChatHistoryRepository'] = None
    ):
        self.llm_client = llm_client
        self.history_repo = history_repo
        self.context_assembler = ContextAssembler(history_repo=history_repo)
        self.action_executor = action_executor
        self.current_session: Optional[ChatSession] = None
        self.call_history: List[datetime] = []
        
        # Phase E: 최근 실행된 액션 결과 저장 (UI Handler에서 사용)
        self.last_action_result: Optional[ActionExecutionResult] = None
    
    def start_session(self, session_id: str = "default"):
        """새 세션 시작 또는 기존 세션 로드"""
        self.current_session = ChatSession(session_id)
        logger.info(f"[ChatService] Session started: {session_id}")
    
    def restore_session(self, session: ChatSession):
        """기존 세션 복원 (Streamlit state에서)"""
        self.current_session = session
    
    def send_message(
        self, 
        user_input: str, 
        context: ContextData
    ) -> Tuple[str, Optional[ActionExecutionResult]]:
        """
        사용자 메시지 처리 및 응답 생성
        
        Args:
            user_input: 사용자 질문
            context: 현재 화면의 ContextData
            
        Returns:
            (AI 응답 텍스트, ActionExecutionResult or None)
        """
        if not self.current_session:
            self.start_session()
        
        # Rate Limiting 체크
        if not self._check_rate_limit():
            error_msg = "⚠️ API 호출 제한 초과. 잠시 후 다시 시도하세요."
            self.current_session.add_user_message(user_input)
            self.current_session.add_model_message(error_msg)
            return error_msg, None
            
        # 1. 사용자 메시지 저장
        self.current_session.add_user_message(user_input)
        
        # 2. 시스템 프롬프트 조립 (Context + Tools 설명 포함)
        system_prompt = self.context_assembler.assemble_system_prompt(context)
        
        # 3. 대화 히스토리 포맷팅
        full_history_prompt = self._build_full_prompt(user_input)
        
        # 4. LLM 호출 (1차)
        try:
            response_text = self.llm_client.generate(
                prompt=full_history_prompt, 
                system_instruction=system_prompt
            )
        except Exception as e:
            logger.error(f"[ChatService] LLM generation failed: {e}")
            error_msg = f"죄송합니다. AI 서비스 연결에 문제가 발생했습니다. (상세: {str(e)[:100]})"
            self.current_session.add_model_message(error_msg)
            return error_msg, None
        
        # 5. Phase E: Action 파싱 시도
        action = self._parse_action(response_text)
        action_result = None
        
        if action and self.action_executor:
            # Action 실행
            action_result = self.action_executor.execute(
                action, 
                user_id=context.user_id
            )
            self.last_action_result = action_result
            
            # 실행 결과를 포함한 2차 응답 생성
            if action_result.success:
                # Action 블록을 제거하고 결과 메시지 추가
                clean_response = self._remove_action_block(response_text)
                final_response = f"{clean_response}\n\n✅ {action_result.message}"
                
                # 추가 데이터가 있으면 표시
                if action_result.data and 'picks' in action_result.data:
                    picks = action_result.data['picks']
                    pick_lines = ["\n**추천 종목:**"]
                    for p in picks[:5]:
                        pick_lines.append(f"- {p['rank']}위: {p['name']} ({p['ticker']}) - AI점수: {p['score']}")
                    final_response += "\n".join(pick_lines)
            else:
                clean_response = self._remove_action_block(response_text)
                final_response = f"{clean_response}\n\n⚠️ {action_result.message}"
            
            response_text = final_response
        
        # 6. AI 응답 저장
        self.current_session.add_model_message(response_text)
        
        return response_text, action_result
    
    def _check_rate_limit(self) -> bool:
        """Rate Limiting 체크"""
        now = datetime.now()
        # 1분 이내 호출 기록만 유지
        self.call_history = [t for t in self.call_history if (now - t).total_seconds() < 60]
        
        if len(self.call_history) >= self.MAX_CALLS_PER_MINUTE:
            logger.warning(f"[ChatService] Rate limit exceeded: {len(self.call_history)} calls/min")
            return False
        
        self.call_history.append(now)
        return True
    
    def _parse_action(self, response: str) -> Optional[UIAction]:
        """
        LLM 응답에서 Action JSON 추출
        
        Format: ```action {"action": "...", "params": {...}} ```
        """
        # ```action ... ``` 블록 찾기
        pattern = r'```action\s*\n?\s*(\{.*?\})\s*\n?\s*```'
        match = re.search(pattern, response, re.DOTALL | re.IGNORECASE)
        
        if not match:
            return None
        
        json_str = match.group(1).strip()
        action = UIAction.from_json(json_str)
        
        if action:
            logger.info(f"[ChatService] Parsed action: {action.action_type}")
        
        return action
    
    def _remove_action_block(self, response: str) -> str:
        """응답에서 action 블록 제거"""
        pattern = r'```action\s*\n?\s*\{.*?\}\s*\n?\s*```'
        return re.sub(pattern, '', response, flags=re.DOTALL | re.IGNORECASE).strip()
    
    def _build_full_prompt(self, current_input: str) -> str:
        """
        대화 히스토리를 포함한 전체 프롬프트 생성
        (Stateless API 호출을 위해 전체 기록을 보냄)
        """
        prompt_parts = []
        
        # 최근 10개 대화만 유지 (토큰 제한 방지)
        recent_messages = self.current_session.messages[-11:-1]
        
        for msg in recent_messages:
            role = "User" if msg.role == 'user' else "AI Assistant"
            prompt_parts.append(f"{role}: {msg.content}")
            
        # 현재 질문
        prompt_parts.append(f"User: {current_input}")
        prompt_parts.append("AI Assistant:")
        
        return "\n".join(prompt_parts)

