"""
Sidebar Chat Component
Clean Architecture: Presentation Layer
Phase E: AI Agentic Control Integration
"""
import streamlit as st
import logging
from typing import Optional

from src.domain.chat.entities import ContextData
from src.domain.chat.actions import ActionExecutionResult
from src.services.chat.chat_service import ChatService
from src.services.chat.action_executor import ActionExecutor
from src.infrastructure.external.gemini_client import GeminiClient, MockLLMClient

logger = logging.getLogger(__name__)


def _get_stock_listing() -> dict:
    """종목 목록 가져오기 (ActionExecutor용)"""
    # session_state에서 가져오거나 빈 딕셔너리 반환
    stock_list = st.session_state.get('active_stock_list', {})
    
    # 역매핑도 추가 (종목명 -> 종목코드)
    if not stock_list:
        # 기본 종목 (없으면 빈 딕셔너리)
        return {}
    
    # {종목명: 종목코드} -> {종목코드: 종목명}으로 변환
    return {v: k for k, v in stock_list.items()}


def _get_available_tabs() -> list:
    """사용 가능한 탭 목록"""
    market = st.session_state.get('current_market', 'KR')
    
    if market == "US":
        return [
            "🎯 투자 컨트롤 센터",
            "📊 단일 종목 분석",
            "🔀 다중 종목 비교",
            "⭐ 관심 종목",
            "📰 뉴스 감성 분석",
            "🤖 AI 예측",
            "⏮️ 백테스팅",
            "💼 포트폴리오 최적화",
            "⚠️ 리스크 관리",
            "🏥 시장 체력 진단",
            "🔥 Market Buzz",
            "💎 팩터 투자",
            "👤 투자 성향",
            "🌅 AI 스크리너"
        ]
    else:
        return [
            "🎯 투자 컨트롤 센터",
            "🔴 실시간 시세",
            "📊 단일 종목 분석",
            "🔀 다중 종목 비교",
            "⭐ 관심 종목",
            "📰 뉴스 감성 분석",
            "🤖 AI 예측",
            "⏮️ 백테스팅",
            "💼 포트폴리오 최적화",
            "⚠️ 리스크 관리",
            "🏥 시장 체력 진단",
            "🔥 Market Buzz",
            "💎 팩터 투자",
            "👤 투자 성향",
            "🌅 AI 스크리너"
        ]


def _get_chat_service() -> ChatService:
    """ChatService 인스턴스 생성 및 세션 로드"""
    
    # session_state에서 API 키 확인 (사용자가 UI에서 입력한 키)
    user_api_key = st.session_state.get('gemini_api_key', None)
    
    # API 키가 변경되었거나 서비스가 없으면 재생성
    if 'chat_service' not in st.session_state or \
       st.session_state.get('_last_api_key') != user_api_key:
        
        # LLM 클라이언트 초기화 (사용자 입력 키 우선)
        llm_client = GeminiClient(api_key=user_api_key)
        
        if not llm_client.is_available():
            logger.warning("[ChatService] Gemini unavailable, using Mock")
            llm_client = MockLLMClient()
        
        # Phase E: ActionExecutor 생성
        stock_listing = _get_stock_listing()
        available_tabs = _get_available_tabs()
        
        action_executor = ActionExecutor(
            stock_listing=stock_listing,
            available_tabs=available_tabs
        )
        
        service = ChatService(llm_client, action_executor=action_executor)
        service.start_session()
        st.session_state.chat_service = service
        st.session_state._last_api_key = user_api_key
        
    return st.session_state.chat_service


def _extract_context() -> ContextData:
    """
    현재 Session State에서 ContextData 추출
    """
    market = st.session_state.get('current_market', 'KR')
    selected_tab = st.session_state.get('active_tab_name', "알 수 없음")
    available_tabs = _get_available_tabs()
    
    context = ContextData(
        tab_name=selected_tab,
        market=market,
        available_tabs=available_tabs,
        user_id=st.session_state.get('user_id', 'default_user')
    )
    
    # 단일 종목 분석 데이터
    if selected_tab == "📊 단일 종목 분석":
        if 'ticker_code' in st.session_state:
            context.active_ticker = st.session_state.ticker_code
            context.active_stock_name = st.session_state.get('stock_name')
            
            # AI 리포트 요약
            if 'ai_report' in st.session_state:
                report = st.session_state.ai_report
                if hasattr(report, 'summary'):
                     context.ai_report_summary = report.summary
    
    # 스크리너 결과
    elif selected_tab == "🌅 AI 스크리너":
        if 'screener_picks' in st.session_state:
            picks = st.session_state.screener_picks
            context.screener_results = [
                {
                    "stock_name": p.stock_name,
                    "ticker": p.ticker,
                    "ai_score": p.ai_score,
                    "reason": p.reason,
                    "current_price": p.current_price
                }
                for p in picks
            ]
            
    # 포트폴리오
    elif selected_tab == "💼 포트폴리오 최적화":
        if 'portfolio_data' in st.session_state:
            context.portfolio_summary = st.session_state.portfolio_data
            
    return context


def _handle_action_result(result: Optional[ActionExecutionResult]):
    """
    Phase E: ActionExecutionResult를 처리하여 UI 상태 업데이트
    Clean Architecture: Presentation Layer에서만 UI 조작
    """
    if not result or not result.success or not result.redirect_needed:
        return
    
    action_type = result.action.action_type
    data = result.data or {}
    
    if action_type == 'switch_tab':
        tab_name = data.get('tab_name')
        if tab_name:
            st.session_state.pending_tab = tab_name
            logger.info(f"[ActionHandler] Set pending_tab: {tab_name}")
    
    elif action_type == 'select_stock':
        ticker = data.get('ticker')
        name = data.get('name')
        target_tab = data.get('target_tab', '📊 단일 종목 분석')
        
        if ticker:
            st.session_state.ticker_code = ticker
            st.session_state.stock_name = name
            st.session_state.pending_tab = target_tab
            logger.info(f"[ActionHandler] Select stock: {name}({ticker})")
    
    elif action_type == 'run_screener':
        tab_name = data.get('tab_name', '🌅 AI 스크리너')
        st.session_state.pending_tab = tab_name
        # 스크리너 결과가 있으면 저장
        if 'picks' in data:
            st.session_state.pending_screener_picks = data['picks']
        logger.info(f"[ActionHandler] Run screener, switch to: {tab_name}")


def _test_api_key(api_key: str) -> tuple[bool, str]:
    """
    API 키 연결 테스트
    
    Returns:
        (success: bool, message: str)
    """
    if not api_key or len(api_key) < 20:
        return False, "API 키가 너무 짧습니다"
    
    try:
        import google.generativeai as genai
        
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.0-flash')
        response = model.generate_content("Test")
        
        if response and response.text:
            return True, "연결 성공! (gemini-2.0-flash 사용)"
        else:
            return False, "API 응답 없음"
            
    except ImportError:
        return False, "google-generativeai 미설치"
    except Exception as e:
        error_msg = str(e)
        
        if "404" in error_msg and "models/" in error_msg:
            fallbacks = ['gemini-2.0-flash', 'gemini-2.0-flash-lite', 'gemini-flash-latest', 'gemini-2.5-flash']
            for model_name in fallbacks:
                try:
                    m = genai.GenerativeModel(model_name)
                    res = m.generate_content("Test")
                    if res and res.text:
                        return True, f"연결 성공! ({model_name} 사용)"
                except:
                    continue

            try:
                available = list(genai.list_models())
                model_list = ", ".join([m.name.split('/')[-1] for m in available if 'generateContent' in m.supported_generation_methods])
                if not model_list:
                    model_list = "없음"
                return False, f"모델 404. 사용 가능: {model_list[:100]}"
            except Exception as list_err:
                return False, f"모델 404 & 목록 조회 실패"
        
        if "API_KEY_INVALID" in error_msg or "invalid" in error_msg.lower():
            return False, "유효하지 않은 API 키"
        elif "quota" in error_msg.lower():
            return False, "API 할당량 초과"
        elif "permission" in error_msg.lower():
            return False, "권한 오류"
        else:
            logger.error(f"API key test failed: {e}")
            return False, f"오류: {error_msg[:100]}"


def render_sidebar_chat():
    """사이드바 챗봇 렌더링"""
    
    st.sidebar.markdown("---")
    st.sidebar.subheader("🤖 AI 투자 비서")
    
    # 0-1. 현재 API 상태 표시
    current_client = GeminiClient(api_key=st.session_state.get('gemini_api_key'))
    
    if current_client.is_available():
        st.sidebar.success("✅ Gemini API 연결됨")
    else:
        st.sidebar.info("💡 위 설정 탭에서 Gemini API 키를 입력하면 AI 챗봇이 활성화됩니다.")
    
    # 0-2. API 키 설정 UI (Gemini가 사용 불가능할 때만 표시)
    temp_client = GeminiClient(api_key=st.session_state.get('gemini_api_key'))
    
    if not temp_client.is_available():
        with st.sidebar.expander("⚙️ API 키 설정", expanded=True):
            st.warning("⚠️ **보안 주의**: 개인 사용만 권장")
            st.caption("🔐 API 키는 브라우저 세션에만 저장됩니다 (임시)")
            
            api_key_input = st.text_input(
                "API Key",
                type="password",
                value=st.session_state.get('gemini_api_key', ''),
                key="api_key_input",
                placeholder="AIzaSy...",
                help="Google AI Studio에서 발급받은 API 키"
            )
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("적용 및 테스트", type="primary", use_container_width=True, key="apply_api_key"):
                    if not api_key_input or len(api_key_input) < 10:
                        st.error("❌ 유효하지 않은 API 키")
                    else:
                        with st.spinner("연결 테스트 중..."):
                            success, message = _test_api_key(api_key_input)
                            
                        if success:
                            st.session_state.gemini_api_key = api_key_input
                            st.success(f"✅ {message}")
                            st.rerun()
                        else:
                            st.error(f"❌ {message}")
                            st.caption("API 키를 확인하세요")
            
            with col2:
                if st.button("초기화", use_container_width=True):
                    if 'gemini_api_key' in st.session_state:
                        del st.session_state.gemini_api_key
                    st.info("🔄 MockLLM 사용")
                    st.rerun()
            
            st.markdown("---")
            st.caption("💡 [API 키 발급](https://makersuite.google.com/app/apikey)")
            
            with st.expander("🔒 보안 권장사항"):
                st.markdown("""
                **배포 환경에서는 다음 방법을 권장합니다:**
                
                1. **Streamlit Cloud**: Settings → Secrets
                2. **Docker**: 환경변수 (`-e GEMINI_API_KEY=...`)
                3. **로컬 개발**: `.streamlit/secrets.toml`
                
                **UI 입력의 제한사항**:
                - 브라우저 닫으면 키가 사라짐
                - 공용 컴퓨터에서 사용 위험
                - 개인/로컬 사용에만 적합
                """)

    # 0-3. 채팅 세션 초기화 버튼
    if st.sidebar.button("💬 대화 초기화", use_container_width=True, help="대화 기록을 지우고 서비스를 재시작합니다"):
        if 'chat_service' in st.session_state:
            del st.session_state.chat_service
        if 'chat_history' in st.session_state:
            del st.session_state.chat_history
        st.rerun()
    
    # 1. 서비스 & 컨텍스트 준비
    service = _get_chat_service()
    context = _extract_context()
    
    # 2. 대화 기록 표시
    messages_container = st.sidebar.container(height=400)
    
    with messages_container:
        for msg in service.current_session.messages:
            with st.chat_message(msg.role):
                st.markdown(msg.content)
    
    # 3. 입력창
    if prompt := st.sidebar.chat_input("질문을 입력하세요...", key="sidebar_chat_input"):
        # 3.1 사용자 메시지 즉시 표시 (UI 반응성)
        with messages_container:
            with st.chat_message("user"):
                st.markdown(prompt)
                
        # 3.2 응답 생성 (Phase E: Tuple 반환)
        with messages_container:
            with st.chat_message("ai"):
                with st.spinner("분석 중..."):
                    response, action_result = service.send_message(prompt, context)
                    st.markdown(response)
        
        # 3.3 Phase E: Action 결과 처리 (UI 상태 업데이트)
        _handle_action_result(action_result)
                    
        # 3.4 리렌더링 (히스토리 업데이트를 위해)
        st.rerun()

