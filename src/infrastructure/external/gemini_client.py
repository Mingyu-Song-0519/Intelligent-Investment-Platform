"""
LLM Client Infrastructure
Google Gemini API 클라이언트 및 인터페이스 정의
Clean Architecture: Infrastructure Layer
"""
from abc import ABC, abstractmethod
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class ILLMClient(ABC):
    """
    LLM 클라이언트 인터페이스 (DIP 준수)
    
    추후 Local LLM (Ollama, LLaMA) 전환 시 이 인터페이스만 구현하면 됨
    """
    
    @abstractmethod
    def generate(self, prompt: str, system_instruction: Optional[str] = None) -> str:
        """
        텍스트 생성
        
        Args:
            prompt: 사용자 프롬프트
            system_instruction: 시스템 지시 (선택)
            
        Returns:
            생성된 텍스트
        """
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """서비스 사용 가능 여부 확인"""
        pass


class GeminiClient(ILLMClient):
    """
    Google Gemini API 클라이언트
    
    무료 티어 사용:
    - 분당 60회 요청 (RPM)
    - 일 1,500회 요청 (RPD)
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Args:
            api_key: Gemini API 키 (None이면 환경변수/Secrets에서 로드)
        """
        self.api_key = api_key
        self.model = None
        self._initialized = False
        
        self._init_client()
    
    def _init_client(self):
        """클라이언트 초기화"""
        try:
            import google.generativeai as genai
            
            # API 키 로드 순서: 인자 > Streamlit Secrets > 환경변수
            if self.api_key is None:
                self.api_key = self._load_api_key()
            
            if self.api_key is None:
                logger.warning("[GeminiClient] API key not found")
                return
            
            genai.configure(api_key=self.api_key)
            
            # gemini-1.5-flash 사용 (무료, 빠름)
            self.model = genai.GenerativeModel('gemini-1.5-flash')
            self._initialized = True
            logger.info("[GeminiClient] Initialized successfully")
            
        except ImportError:
            logger.error("[GeminiClient] google-generativeai not installed")
        except Exception as e:
            logger.error(f"[GeminiClient] Init failed: {e}")
    
    def _load_api_key(self) -> Optional[str]:
        """API 키 로드 (Streamlit Secrets 또는 환경변수)"""
        # 1. Streamlit Secrets
        try:
            import streamlit as st
            if hasattr(st, 'secrets') and 'GEMINI_API_KEY' in st.secrets:
                return st.secrets['GEMINI_API_KEY']
        except:
            pass
        
        # 2. 환경변수
        import os
        return os.environ.get('GEMINI_API_KEY')
    
    def generate(self, prompt: str, system_instruction: Optional[str] = None) -> str:
        """
        텍스트 생성
        
        Args:
            prompt: 사용자 프롬프트
            system_instruction: 시스템 지시 (선택)
            
        Returns:
            생성된 텍스트
        """
        if not self._initialized or self.model is None:
            raise RuntimeError("GeminiClient not initialized. Check API key.")
        
        try:
            # 시스템 지시가 있으면 프롬프트 앞에 추가
            full_prompt = prompt
            if system_instruction:
                full_prompt = f"{system_instruction}\n\n---\n\n{prompt}"
            
            response = self.model.generate_content(full_prompt)
            
            return response.text
            
        except Exception as e:
            logger.error(f"[GeminiClient] Generation failed: {e}")
            raise
    
    def is_available(self) -> bool:
        """서비스 사용 가능 여부 확인"""
        return self._initialized and self.model is not None


class MockLLMClient(ILLMClient):
    """
    테스트용 Mock LLM 클라이언트
    
    개발/테스트 시 API 호출 없이 사용
    """
    
    def __init__(self, default_response: str = "Mock response"):
        self.default_response = default_response
    
    def generate(self, prompt: str, system_instruction: Optional[str] = None) -> str:
        """Mock 응답 반환"""
        return f"""신호: BUY
신뢰도: 75
요약: 이 종목은 기술적으로 상승 추세에 있으며, 감성 분석 결과도 긍정적입니다.
논리: RSI가 과매도 구간을 벗어나 상승 중이며, 최근 뉴스 감성이 긍정적입니다. 거래량도 증가 추세입니다.
"""
    
    def is_available(self) -> bool:
        """항상 사용 가능"""
        return True
