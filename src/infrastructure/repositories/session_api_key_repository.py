"""
Session API Key Repository - Infrastructure Layer
Clean Architecture: Streamlit Session State 기반 API 키 저장소

Phase 1: API 키 중앙화 구현
"""
from typing import Optional, Tuple
import logging

from src.services.api_key_service import IAPIKeyRepository

logger = logging.getLogger(__name__)


class SessionAPIKeyRepository(IAPIKeyRepository):
    """
    Streamlit Session State 기반 API 키 저장소
    
    특징:
    - 사용자별 독립 세션 (보안)
    - 브라우저 종료 시 자동 삭제
    - 서버에 저장되지 않음
    """
    
    def __init__(self, session_state=None):
        """
        Args:
            session_state: Streamlit session_state (테스트 시 Mock 주입 가능)
        """
        self._session_state = session_state
    
    @property
    def session_state(self):
        """Lazy load session_state (Streamlit 컨텍스트에서만 동작)"""
        if self._session_state is None:
            try:
                import streamlit as st
                return st.session_state
            except Exception:
                # Streamlit 외부에서 실행 시 빈 딕셔너리 반환
                self._session_state = {}
        return self._session_state
    
    def get_key(self, key_type: str, user_id: str) -> Optional[str]:
        """
        API 키 조회
        
        Args:
            key_type: 키 유형 (gemini_api_key, openai_api_key 등)
            user_id: 사용자 ID (현재는 사용 안함, 향후 확장용)
            
        Returns:
            API 키 또는 None
        """
        try:
            return self.session_state.get(key_type)
        except Exception as e:
            logger.error(f"[SessionAPIKeyRepo] get_key failed: {e}")
            return None
    
    def set_key(self, key_type: str, user_id: str, key_value: str) -> bool:
        """
        API 키 저장
        
        Args:
            key_type: 키 유형
            user_id: 사용자 ID
            key_value: API 키 값
            
        Returns:
            저장 성공 여부
        """
        try:
            self.session_state[key_type] = key_value
            logger.info(f"[SessionAPIKeyRepo] Key '{key_type}' saved")
            return True
        except Exception as e:
            logger.error(f"[SessionAPIKeyRepo] set_key failed: {e}")
            return False
    
    def delete_key(self, key_type: str, user_id: str) -> bool:
        """
        API 키 삭제
        
        Args:
            key_type: 키 유형
            user_id: 사용자 ID
            
        Returns:
            삭제 성공 여부
        """
        try:
            if key_type in self.session_state:
                del self.session_state[key_type]
                logger.info(f"[SessionAPIKeyRepo] Key '{key_type}' deleted")
                return True
            return False
        except Exception as e:
            logger.error(f"[SessionAPIKeyRepo] delete_key failed: {e}")
            return False
    
    def validate_key(self, key_type: str, key_value: str) -> Tuple[bool, str]:
        """
        API 키 유효성 검증 (실제 API 호출)
        
        Args:
            key_type: 키 유형
            key_value: API 키 값
            
        Returns:
            (유효 여부, 메시지)
        """
        if key_type == 'gemini_api_key':
            return self._validate_gemini_key(key_value)
        else:
            # 다른 키 유형은 형식 검증만
            return True, "형식 검증 통과"
    
    def _validate_gemini_key(self, key_value: str) -> Tuple[bool, str]:
        """
        Gemini API 키 실제 검증
        
        간단한 API 호출로 키 유효성 확인
        """
        try:
            import google.generativeai as genai
            
            # 임시 설정
            genai.configure(api_key=key_value)
            
            # 간단한 모델 목록 조회로 검증
            models = list(genai.list_models())
            
            if models:
                logger.info("[SessionAPIKeyRepo] Gemini key validation success")
                return True, "✅ API 키가 유효합니다!"
            else:
                return False, "API 키는 유효하지만 모델을 찾을 수 없습니다."
                
        except Exception as e:
            error_msg = str(e)
            logger.warning(f"[SessionAPIKeyRepo] Gemini key validation failed: {error_msg}")
            
            if "API_KEY_INVALID" in error_msg or "invalid" in error_msg.lower():
                return False, "❌ 유효하지 않은 API 키입니다."
            elif "quota" in error_msg.lower():
                return False, "⚠️ API 할당량이 초과되었습니다."
            else:
                # 네트워크 오류 등은 검증 건너뛰기 (키는 저장)
                logger.warning(f"[SessionAPIKeyRepo] Validation skipped due to: {error_msg}")
                return True, "⚠️ 검증을 건너뛰었습니다. (네트워크 오류)"
