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
        self.client = None
        self.selected_model_name = 'gemini-2.0-flash'
        self._initialized = False
        
        self._init_client()
    
    def _init_client(self):
        """클라이언트 초기화"""
        try:
            from google import genai
            
            # API 키 로드 순서: 인자 > Streamlit Secrets > 환경변수
            if self.api_key is None:
                self.api_key = self._load_api_key()
            
            if self.api_key is None:
                logger.warning("[GeminiClient] API key not found")
                return
            
            # 신규 API: Client 생성
            self.client = genai.Client(api_key=self.api_key)
            
            # 모델 목록 로드 및 선정
            try:
                available_models = []
                for m in self.client.models.list():
                    # 신규/구버전 SDK 속성 대응
                    methods = getattr(m, 'supported_generation_methods', []) or getattr(m, 'supported_methods', [])
                    if 'generateContent' in methods or 'gemini' in m.name.lower():
                        available_models.append(m.name.split('/')[-1])
                
                if 'gemini-2.0-flash' in available_models:
                    self.selected_model_name = 'gemini-2.0-flash'
                elif 'gemini-1.5-flash' in available_models:
                    self.selected_model_name = 'gemini-1.5-flash'
                elif available_models:
                    self.selected_model_name = available_models[0]
                else:
                    self.selected_model_name = 'gemini-2.0-flash'
                
                logger.info(f"[GeminiClient] Selected model: {self.selected_model_name}")
            except Exception as e:
                logger.warning(f"[GeminiClient] Model selection failed, using default: {e}")
                self.selected_model_name = 'gemini-2.0-flash'
            
            # 사용자 설정 모델 확인 (Streamlit Session State)
            try:
                import streamlit as st
                if hasattr(st, 'session_state') and 'gemini_model_name' in st.session_state:
                    preferred = st.session_state['gemini_model_name']
                    # 모델이 유효한지 확인하지 않고 설정 (새로운 모델일 수 있음)
                    if preferred:
                        self.selected_model_name = preferred
                        logger.info(f"[GeminiClient] Overridden by session state: {self.selected_model_name}")
            except:
                pass
                
            self._initialized = True
            logger.info(f"[GeminiClient] Initialized successfully with model: {self.selected_model_name}")
            
        except ImportError:
            logger.error("[GeminiClient] google-genai not installed")
        except Exception as e:
            logger.error(f"[GeminiClient] Init failed: {e}")
            raise # 에러를 상위로 전파하여 UI에서 보이게 함
    
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
        if not self._initialized or self.client is None:
            raise RuntimeError("GeminiClient not initialized. Check API key.")
        
        try:
            from google import genai
            
            # 신규 API: GenerateContentConfig 사용
            if system_instruction:
                config = genai.types.GenerateContentConfig(
                    system_instruction=system_instruction
                )
                response = self.client.models.generate_content(
                    model=self.selected_model_name,
                    contents=prompt,
                    config=config
                )
            else:
                response = self.client.models.generate_content(
                    model=self.selected_model_name,
                    contents=prompt
                )
            
            # 응답이 비어있거나 차단된 경우 처리
            if not response or not hasattr(response, 'text'):
                # candidate 피드백 확인
                if response.candidates and response.candidates[0].finish_reason:
                    reason = response.candidates[0].finish_reason
                    logger.warning(f"[GeminiClient] Blocked: {reason}")
                    return f"죄송합니다. 서비스 정책상 답변을 드릴 수 없습니다. (사유: {reason})"
                return "AI가 응답을 생성하지 못했습니다."
                
            return response.text
            
        except Exception as e:
            logger.error(f"[GeminiClient] Generation failed: {e}")
            raise

    
    def is_available(self) -> bool:
        """서비스 사용 가능 여부 확인"""
        return self._initialized and self.client is not None

    def get_available_models(self) -> list[str]:
        """사용 가능한 모델 목록 반환"""
        if not self._initialized or self.client is None:
            return []
        
        try:
            available = []
            for m in self.client.models.list():
                # 신규/구버전 SDK 속성 대응
                methods = getattr(m, 'supported_generation_methods', []) or getattr(m, 'supported_methods', [])
                # 'generateContent' 권한이 있거나, 이름에 'gemini'가 포함된 모델만 추출
                if 'generateContent' in methods or 'gemini' in m.name.lower():
                    name = m.name.split('/')[-1]
                    if name not in available:
                        available.append(name)
            
            # 정렬 (최신 모델이 위로 오게 하거나 알파벳순)
            available.sort()
            return available
        except Exception as e:
            logger.warning(f"[GeminiClient] Failed to list models: {e}")
            return []

    def set_model(self, model_name: str):
        """사용할 모델 설정"""
        self.selected_model_name = model_name


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

    def get_available_models(self) -> list[str]:
        """Mock 사용 가능 모델"""
        return ["gemini-2.0-flash", "gemini-1.5-pro", "gemini-1.5-flash"]

    def set_model(self, model_name: str):
        """모델 설정 (Mock)"""
        pass
