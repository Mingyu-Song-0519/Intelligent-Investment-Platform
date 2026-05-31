"""
LLM Client Infrastructure
Google Gemini API 클라이언트 및 인터페이스 정의
Clean Architecture: Infrastructure Layer
"""
from abc import ABC, abstractmethod
from typing import Optional
import logging
import time

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
    
    # 클래스 레벨 캐시: 모델 목록을 한 번만 조회
    _cached_models: Optional[list] = None
    
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
            
            # 모델 목록 로드 및 선정 (캐시 사용으로 API 호출 최소화)
            try:
                if GeminiClient._cached_models is not None:
                    available_models = GeminiClient._cached_models
                    logger.info(f"[GeminiClient] Using cached model list ({len(available_models)} models)")
                else:
                    available_models = []
                    for m in self.client.models.list():
                        # 신규/구버전 SDK 속성 대응
                        methods = getattr(m, 'supported_generation_methods', []) or getattr(m, 'supported_methods', [])
                        if 'generateContent' in methods or 'gemini' in m.name.lower():
                            available_models.append(m.name.split('/')[-1])
                    GeminiClient._cached_models = available_models
                    logger.info(f"[GeminiClient] Fetched and cached {len(available_models)} models")
                
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
                logger.warning(f"[GeminiClient] Model selection failed, using default: {e}", exc_info=True)
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
            except Exception as e:
                logger.debug(f"[GeminiClient] Session state model override failed: {e}")

            self._initialized = True
            logger.info(f"[GeminiClient] Initialized successfully with model: {self.selected_model_name}")
            
        except ImportError:
            logger.error("[GeminiClient] google-genai not installed")
        except Exception as e:
            logger.error(f"[GeminiClient] Init failed: {e}", exc_info=True)
            raise  # 에러를 상위로 전파하여 UI에서 보이게 함
    
    def _load_api_key(self) -> Optional[str]:
        """API 키 로드 (Streamlit Secrets 또는 환경변수)"""
        # 1. Streamlit Secrets
        try:
            import streamlit as st
            if hasattr(st, 'secrets') and 'GEMINI_API_KEY' in st.secrets:
                return st.secrets['GEMINI_API_KEY']
        except Exception as e:
            logger.debug(f"[GeminiClient] Streamlit secrets unavailable: {e}")
        
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
        
        # 429 RESOURCE_EXHAUSTED 에러 시 최대 3회 재시도 (exponential backoff)
        max_retries = 3
        for attempt in range(max_retries):
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
                
            except Exception as e:  # AI API가 다양한 예외를 던질 수 있음
                error_str = str(e)
                # 429 Rate Limit 에러 시 재시도
                if '429' in error_str or 'RESOURCE_EXHAUSTED' in error_str:
                    wait_time = (attempt + 1) * 5  # 5초, 10초, 15초
                    logger.warning(f"[GeminiClient] Rate limit hit (attempt {attempt + 1}/{max_retries}), waiting {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                
                logger.error(f"[GeminiClient] Generation failed: {e}")
                raise
        
        # 모든 재시도 실패
        raise RuntimeError("Gemini API 호출 한도를 초과했습니다. 잠시 후 다시 시도해주세요.")

    
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
            logger.warning(f"[GeminiClient] Failed to list models: {e}", exc_info=True)
            return []

    def set_model(self, model_name: str):
        """사용할 모델 설정"""
        self.selected_model_name = model_name


class MockLLMClient(ILLMClient):
    """
    데모 모드용 Mock LLM 클라이언트
    
    API 키 미설정시 사용자에게 유용한 데모 응답 제공
    """
    
    DEMO_RESPONSES = {
        # 기능 안내
        "삼성전자": "삼성전자(005930)는 반도체, 가전, 모바일 사업을 영위하는 대한민국 대표 기업입니다. 📊 상세 분석은 '단일 종목 분석' 탭에서 확인하세요.",
        "매수": "📈 매매 시그널을 확인하려면 '단일 종목 분석' 탭에서 기술적 지표(RSI, MACD, 볼린저밴드)를 확인해보세요.",
        "매도": "📉 매도 타이밍 분석은 '단일 종목 분석' 탭의 매매 시그널에서 확인할 수 있습니다.",
        "추천": "🌅 AI 종목 추천은 'AI 종목 추천' 탭에서 이용하실 수 있습니다. 전체 기능은 API 키 설정 후 사용 가능합니다.",
        "포트폴리오": "💼 포트폴리오 최적화는 '포트폴리오 최적화' 탭에서 확인하세요.",
        "리스크": "⚠️ 리스크 분석은 '리스크 관리' 탭에서 VaR, MDD 등을 확인할 수 있습니다.",
        "백테스트": "⏮️ 전략 백테스팅은 '백테스팅' 탭에서 이용하세요.",
        "뉴스": "📰 뉴스 감성 분석은 '뉴스 감성 분석' 탭에서 확인하세요.",
    }
    
    DEFAULT_RESPONSE = """💡 **데모 모드** 입니다.

현재 AI 기능을 체험 중입니다. 전체 기능을 사용하려면:

1. 사이드바 상단 **'🔑 AI API 설정'** 클릭
2. Gemini API 키 입력
3. 연결 테스트

🔗 무료 API 키는 [Google AI Studio](https://aistudio.google.com)에서 발급받을 수 있습니다.

---
💬 데모 모드에서도 다음 질문에 답변할 수 있어요:
- "삼성전자 분석해줘"
- "매수 타이밍 알려줘"
- "포트폴리오 최적화 방법"
"""
    
    def __init__(self, default_response: str = None):
        self.default_response = default_response or self.DEFAULT_RESPONSE
    
    def generate(self, prompt: str, system_instruction: Optional[str] = None) -> str:
        """키워드 매칭으로 데모 응답 반환"""
        prompt_lower = prompt.lower()
        
        # 키워드 매칭
        for keyword, response in self.DEMO_RESPONSES.items():
            if keyword.lower() in prompt_lower:
                return f"💡 **데모 응답** (API 키 설정 시 더 정확한 분석 제공)\n\n{response}"
        
        return self.default_response
    
    def is_available(self) -> bool:
        """항상 사용 가능"""
        return True

    def get_available_models(self) -> list[str]:
        """Mock 사용 가능 모델"""
        return ["gemini-2.0-flash", "gemini-1.5-pro", "gemini-1.5-flash"]

    def set_model(self, model_name: str):
        """모델 설정 (Mock)"""
        pass
