"""
Action Executor Service
Clean Architecture: Application Layer
Phase E: AI Agentic Control

역할:
- UI Action 실행 비즈니스 로직 (순수 Application Layer)
- Streamlit 의존성 없음 (Clean Architecture 준수)
- 검증, 데이터 조회, 결과 반환만 담당
- 실제 UI 조작은 Presentation Layer의 ActionHandler가 수행
"""
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from src.domain.chat.actions import UIAction, ActionExecutionResult, ALLOWED_ACTIONS

logger = logging.getLogger(__name__)


class ActionExecutor:
    """
    Action 실행 Application Service
    
    Responsibilities:
    - Action 유효성 검증
    - 비즈니스 로직 실행 (데이터 조회 등)
    - 실행 결과 반환 (UI 조작은 하지 않음)
    """
    
    # 타임아웃 설정 (초)
    ACTION_TIMEOUT = {
        'switch_tab': 1,
        'select_stock': 2,
        'run_screener': 60,
        'run_analysis': 30,
        'search_stock': 5,
    }
    
    def __init__(
        self,
        stock_listing: Optional[Dict[str, str]] = None,  # {ticker: name}
        available_tabs: Optional[List[str]] = None,
        screener_service = None,  # Optional[ScreenerService]
        investment_report_service = None,  # Optional[InvestmentReportService]
    ):
        """
        Args:
            stock_listing: 종목코드 -> 종목명 매핑 딕셔너리
            available_tabs: 이동 가능한 탭 이름 목록
            screener_service: Phase C 스크리너 서비스 (선택)
            investment_report_service: Phase A AI 리포트 서비스 (선택)
        """
        self.stock_listing = stock_listing or {}
        self.available_tabs = available_tabs or []
        self.screener_service = screener_service
        self.report_service = investment_report_service
        
        # 종목명 -> 종목코드 역매핑 생성
        self.name_to_ticker: Dict[str, str] = {}
        for ticker, name in self.stock_listing.items():
            self.name_to_ticker[name] = ticker
            # 종목명에서 괄호 제거한 버전도 추가 (검색 용이성)
            clean_name = name.split('(')[0].strip() if '(' in name else name
            self.name_to_ticker[clean_name] = ticker
    
    def execute(self, action: UIAction, user_id: str = "default") -> ActionExecutionResult:
        """
        Action 실행
        
        Args:
            action: 실행할 UIAction
            user_id: 사용자 ID (Phase 20 프로필 연동용)
            
        Returns:
            ActionExecutionResult
        """
        # 1. 화이트리스트 검증
        if action.action_type not in ALLOWED_ACTIONS:
            return ActionExecutionResult.failure(
                f"허용되지 않은 작업: {action.action_type}",
                action
            )
        
        # 2. 액션 타입별 실행
        try:
            if action.action_type == 'switch_tab':
                return self._execute_switch_tab(action)
            elif action.action_type == 'select_stock':
                return self._execute_select_stock(action)
            elif action.action_type == 'run_screener':
                return self._execute_run_screener(action, user_id)
            elif action.action_type == 'run_analysis':
                return self._execute_run_analysis(action)
            elif action.action_type == 'search_stock':
                return self._execute_search_stock(action)
            else:
                return ActionExecutionResult.failure(
                    f"구현되지 않은 작업: {action.action_type}",
                    action
                )
        except Exception as e:
            logger.error(f"[ActionExecutor] Execution failed: {e}")
            return ActionExecutionResult.failure(
                f"작업 실행 중 오류 발생: {str(e)[:50]}",
                action
            )
    
    def _execute_switch_tab(self, action: UIAction) -> ActionExecutionResult:
        """탭 전환 액션 실행"""
        tab_name = action.params.get('tab_name')
        
        if not tab_name:
            return ActionExecutionResult.failure(
                "탭 이름이 지정되지 않았습니다",
                action
            )
        
        # 탭 이름 검증 (available_tabs가 설정된 경우)
        if self.available_tabs and tab_name not in self.available_tabs:
            # 부분 매칭 시도
            matched_tab = None
            for available in self.available_tabs:
                if tab_name in available or available in tab_name:
                    matched_tab = available
                    break
            
            if not matched_tab:
                return ActionExecutionResult.failure(
                    f"탭을 찾을 수 없습니다: {tab_name}",
                    action
                )
            tab_name = matched_tab
        
        return ActionExecutionResult.success_with_redirect(
            f"'{tab_name}' 탭으로 이동합니다",
            action,
            data={'tab_name': tab_name}
        )
    
    def _execute_select_stock(self, action: UIAction) -> ActionExecutionResult:
        """종목 선택 액션 실행"""
        ticker = action.params.get('ticker')
        name = action.params.get('name')
        
        # 종목명으로 검색 시 ticker 조회
        if not ticker and name:
            ticker = self.name_to_ticker.get(name)
            if not ticker:
                # 부분 매칭 시도
                for stock_name, stock_ticker in self.name_to_ticker.items():
                    if name in stock_name:
                        ticker = stock_ticker
                        name = stock_name
                        break
        
        if not ticker:
            return ActionExecutionResult.failure(
                f"종목을 찾을 수 없습니다: {name or ticker}",
                action
            )
        
        # ticker로 name 조회
        if not name:
            name = self.stock_listing.get(ticker, ticker)
        
        return ActionExecutionResult.success_with_redirect(
            f"{name}({ticker})을(를) 선택했습니다",
            action,
            data={
                'ticker': ticker,
                'name': name,
                'target_tab': '📊 단일 종목 분석'
            }
        )
    
    def _execute_run_screener(self, action: UIAction, user_id: str) -> ActionExecutionResult:
        """스크리너 실행 액션"""
        market = action.params.get('market', 'KR')
        
        if not self.screener_service:
            return ActionExecutionResult.success_with_redirect(
                "AI 종목 추천 탭으로 이동합니다. 수동으로 실행해주세요.",
                action,
                data={'tab_name': '🌅 AI 종목 추천', 'market': market}
            )
        
        try:
            # Phase C 스크리너 서비스 호출
            picks = self.screener_service.run_daily_screen(
                user_id=user_id,
                market=market,
                top_n=5
            )
            
            # 결과 요약
            pick_summaries = []
            for i, pick in enumerate(picks[:5], 1):
                pick_summaries.append({
                    'rank': i,
                    'name': getattr(pick, 'stock_name', 'Unknown'),
                    'ticker': getattr(pick, 'ticker', ''),
                    'score': getattr(pick, 'ai_score', 0),
                    'reason': getattr(pick, 'reason', '')
                })
            
            return ActionExecutionResult.success_with_redirect(
                f"AI 종목 추천 실행 완료: {len(picks)}개 종목 추천",
                action,
                data={
                    'tab_name': '🌅 AI 종목 추천',
                    'market': market,
                    'picks': pick_summaries
                }
            )
        except Exception as e:
            logger.error(f"[ActionExecutor] Screener failed: {e}")
            return ActionExecutionResult.failure(
                f"스크리너 실행 실패: {str(e)[:50]}",
                action
            )
    
    def _execute_run_analysis(self, action: UIAction) -> ActionExecutionResult:
        """AI 분석 실행 액션"""
        ticker = action.params.get('ticker')
        
        if not ticker:
            # 현재 선택된 종목이 없음
            return ActionExecutionResult.failure(
                "분석할 종목이 선택되지 않았습니다. 먼저 종목을 선택해주세요.",
                action
            )
        
        if not self.report_service:
            return ActionExecutionResult(
                success=True,
                message=f"{ticker} 종목의 AI 분석을 수동으로 실행해주세요.",
                action=action,
                redirect_needed=False,
                data={'ticker': ticker}
            )
        
        # Phase A AI 리포트 서비스 호출은 무거우므로 여기서는 안내만
        return ActionExecutionResult(
            success=True,
            message=f"{ticker} 종목의 AI 분석 버튼을 클릭하여 분석을 시작하세요.",
            action=action,
            redirect_needed=False,
            data={'ticker': ticker, 'action_hint': 'click_ai_analysis_button'}
        )
    
    def _execute_search_stock(self, action: UIAction) -> ActionExecutionResult:
        """종목 검색 액션"""
        query = action.params.get('query', '')
        
        if not query:
            return ActionExecutionResult.failure(
                "검색어가 지정되지 않았습니다",
                action
            )
        
        # 종목명 검색
        matches = []
        query_lower = query.lower()
        
        for name, ticker in self.name_to_ticker.items():
            if query_lower in name.lower():
                matches.append({'name': name, 'ticker': ticker})
        
        # ticker로도 검색
        for ticker, name in self.stock_listing.items():
            if query_lower in ticker.lower():
                if not any(m['ticker'] == ticker for m in matches):
                    matches.append({'name': name, 'ticker': ticker})
        
        if not matches:
            return ActionExecutionResult.failure(
                f"'{query}'에 해당하는 종목을 찾을 수 없습니다",
                action
            )
        
        # 최대 10개까지 반환
        matches = matches[:10]
        
        return ActionExecutionResult(
            success=True,
            message=f"{len(matches)}개의 종목을 찾았습니다",
            action=action,
            redirect_needed=False,
            data={'matches': matches, 'query': query}
        )
