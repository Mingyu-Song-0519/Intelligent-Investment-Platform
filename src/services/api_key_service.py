"""
API Key Service - Application Layer
Clean Architecture: API 키 관리 서비스

Phase 1: API 키 중앙화 구현
"""
from typing import Optional, Tuple
from abc import ABC, abstractmethod
import logging

logger = logging.getLogger(__name__)


class IAPIKeyRepository(ABC):
    """API 키 저장소 인터페이스 (DIP)"""
    
    @abstractmethod
    def get_key(self, key_type: str, user_id: str) -> Optional[str]:
        """API 키 조회"""
        pass
    
    @abstractmethod
    def set_key(self, key_type: str, user_id: str, key_value: str) -> bool:
        """API 키 저장"""
        pass
    
    @abstractmethod
    def delete_key(self, key_type: str, user_id: str) -> bool:
        """API 키 삭제"""
        pass
    
    @abstractmethod
    def validate_key(self, key_type: str, key_value: str) -> Tuple[bool, str]:
        """API 키 유효성 검증"""
        pass


class APIKeyService:
    """
    API 키 관리 서비스 (Application Layer)
    
    책임:
    - API 키 저장/조회/삭제
    - 유효성 검증
    - 다중 API 키 유형 지원 (gemini, openai 등)
    """
    
    SUPPORTED_KEY_TYPES = ['gemini_api_key', 'openai_api_key']
    
    def __init__(self, repository: IAPIKeyRepository):
        """
        Args:
            repository: API 키 저장소 (DI)
        """
        self.repository = repository
    
    def get_gemini_key(self, user_id: str = "default_user") -> Optional[str]:
        """
        Gemini API 키 조회
        
        Args:
            user_id: 사용자 ID
            
        Returns:
            API 키 또는 None
        """
        return self.repository.get_key('gemini_api_key', user_id)
    
    def set_gemini_key(
        self, 
        user_id: str, 
        key_value: str,
        validate: bool = True
    ) -> Tuple[bool, str]:
        """
        Gemini API 키 저장
        
        Args:
            user_id: 사용자 ID
            key_value: API 키 값
            validate: 유효성 검증 여부
            
        Returns:
            (성공 여부, 메시지)
        """
        if not key_value or not key_value.strip():
            return False, "API 키를 입력해주세요."
        
        key_value = key_value.strip()
        
        # 기본 형식 검증
        if not key_value.startswith('AIza'):
            logger.warning(f"[APIKeyService] Invalid key format for user {user_id}")
            return False, "유효하지 않은 Gemini API 키 형식입니다. (AIza...로 시작해야 함)"
        
        # 선택적 실제 연결 검증
        if validate:
            is_valid, validation_msg = self.repository.validate_key('gemini_api_key', key_value)
            if not is_valid:
                return False, validation_msg
        
        # 저장
        saved = self.repository.set_key('gemini_api_key', user_id, key_value)
        if saved:
            logger.info(f"[APIKeyService] Gemini key saved for user {user_id}")
            return True, "✅ API 키가 저장되었습니다!"
        else:
            return False, "API 키 저장에 실패했습니다."
    
    def delete_gemini_key(self, user_id: str = "default_user") -> Tuple[bool, str]:
        """
        Gemini API 키 삭제
        
        Args:
            user_id: 사용자 ID
            
        Returns:
            (성공 여부, 메시지)
        """
        deleted = self.repository.delete_key('gemini_api_key', user_id)
        if deleted:
            logger.info(f"[APIKeyService] Gemini key deleted for user {user_id}")
            return True, "🗑️ API 키가 삭제되었습니다."
        else:
            return False, "삭제할 API 키가 없습니다."
    
    def has_gemini_key(self, user_id: str = "default_user") -> bool:
        """Gemini API 키 존재 여부 확인"""
        key = self.get_gemini_key(user_id)
        return bool(key and len(key) > 0)
