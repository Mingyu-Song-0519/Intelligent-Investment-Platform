"""
LLM Client Factory - Infrastructure Layer
Clean Architecture: 중앙화된 LLM 클라이언트 생성

Phase 2: API 키 중앙화 구현
"""
from typing import Optional
import logging

from src.infrastructure.external.gemini_client import ILLMClient, GeminiClient, MockLLMClient

logger = logging.getLogger(__name__)


class LLMClientFactory:
    """
    LLM 클라이언트 생성 Factory
    
    중앙화된 API 키를 사용하여 LLM 클라이언트를 생성합니다.
    API 키가 없거나 유효하지 않으면 MockLLMClient를 반환합니다.
    
    사용법:
        # 1. 세션에서 자동으로 API 키 가져오기
        client = LLMClientFactory.create_gemini_client()
        
        # 2. API 키 직접 전달
        client = LLMClientFactory.create_gemini_client(api_key="AIza...")
    """
    
    @staticmethod
    def create_gemini_client(api_key: Optional[str] = None) -> ILLMClient:
        """
        Gemini 클라이언트 생성
        
        Args:
            api_key: API 키 (None이면 session_state에서 조회)
            
        Returns:
            ILLMClient (GeminiClient 또는 MockLLMClient)
        """
        # 1. API 키 결정
        resolved_key = api_key
        
        if not resolved_key:
            # session_state에서 조회
            try:
                import streamlit as st
                resolved_key = st.session_state.get('gemini_api_key')
            except Exception:
                pass
        
        # 2. 클라이언트 생성 시도
        if resolved_key:
            try:
                client = GeminiClient(api_key=resolved_key)
                if client.is_available():
                    logger.info("[LLMClientFactory] Created GeminiClient with provided key")
                    return client
                else:
                    logger.warning("[LLMClientFactory] GeminiClient not available, using Mock")
            except Exception as e:
                logger.warning(f"[LLMClientFactory] GeminiClient creation failed: {e}")
        
        # 3. 폴백: Mock 클라이언트
        logger.info("[LLMClientFactory] Using MockLLMClient")
        return MockLLMClient()
    
    @staticmethod
    def create_gemini_client_from_service() -> ILLMClient:
        """
        APIKeyService를 통해 Gemini 클라이언트 생성
        
        Clean Architecture 준수 방식 (권장)
        """
        try:
            from src.services.api_key_service import APIKeyService
            from src.infrastructure.repositories.session_api_key_repository import SessionAPIKeyRepository
            
            repo = SessionAPIKeyRepository()
            service = APIKeyService(repository=repo)
            
            api_key = service.get_gemini_key()
            return LLMClientFactory.create_gemini_client(api_key=api_key)
            
        except Exception as e:
            logger.warning(f"[LLMClientFactory] Service-based creation failed: {e}")
            return MockLLMClient()
    
    @staticmethod
    def is_gemini_available(api_key: Optional[str] = None) -> bool:
        """
        Gemini 사용 가능 여부 확인
        
        Args:
            api_key: API 키 (None이면 session_state에서 조회)
            
        Returns:
            사용 가능 여부
        """
        client = LLMClientFactory.create_gemini_client(api_key)
        return isinstance(client, GeminiClient) and client.is_available()
