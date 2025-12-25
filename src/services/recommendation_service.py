"""
RecommendationService
맞춤 종목 추천 및 피드백 처리 서비스

Clean Architecture: Application Layer (Service)
"""
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import uuid
import numpy as np

from src.domain.investment_profile.entities.investor_profile import InvestorProfile
from src.domain.investment_profile.entities.recommendation import (
    Recommendation, RecommendationFeedback, RankedStock, RecommendationStatus
)
from src.domain.investment_profile.value_objects.risk_tolerance import RiskTolerance
from src.domain.repositories.profile_interfaces import IProfileRepository


class RecommendationService:
    """
    맞춤 종목 추천 서비스
    
    책임:
    - 성향 기반 종목 추천 생성
    - 피드백 처리 및 프로필 업데이트
    - 추천 이력 관리
    """
    
    # 한국 주요 종목 (실제 환경에서는 DB에서 로드)
    KOREAN_STOCKS = {
        "005930.KS": {"name": "삼성전자", "sector": "Technology"},
        "000660.KS": {"name": "SK하이닉스", "sector": "Technology"},
        "035420.KS": {"name": "NAVER", "sector": "Communication"},
        "035720.KS": {"name": "카카오", "sector": "Communication"},
        "051910.KS": {"name": "LG화학", "sector": "Materials"},
        "207940.KS": {"name": "삼성바이오로직스", "sector": "Healthcare"},
        "006400.KS": {"name": "삼성SDI", "sector": "Technology"},
        "068270.KS": {"name": "셀트리온", "sector": "Healthcare"},
        "105560.KS": {"name": "KB금융", "sector": "Financials"},
        "055550.KS": {"name": "신한지주", "sector": "Financials"},
        "096770.KS": {"name": "SK이노베이션", "sector": "Energy"},
        "034730.KS": {"name": "SK", "sector": "Industrials"},
        "003550.KS": {"name": "LG", "sector": "Industrials"},
        "000270.KS": {"name": "기아", "sector": "Consumer"},
        "005380.KS": {"name": "현대차", "sector": "Consumer"},
        "066570.KS": {"name": "LG전자", "sector": "Technology"},
        "028260.KS": {"name": "삼성물산", "sector": "Industrials"},
        "017670.KS": {"name": "SK텔레콤", "sector": "Communication"},
        "032830.KS": {"name": "삼성생명", "sector": "Financials"},
        "086790.KS": {"name": "하나금융지주", "sector": "Financials"},
    }
    
    # 섹터별 특성 (변동성, 스타일)
    SECTOR_CHARACTERISTICS = {
        "Technology": {"volatility": 0.35, "style": {"value": 30, "growth": 50, "momentum": 20}},
        "Healthcare": {"volatility": 0.40, "style": {"value": 20, "growth": 60, "momentum": 20}},
        "Financials": {"volatility": 0.25, "style": {"value": 60, "growth": 20, "momentum": 20}},
        "Consumer": {"volatility": 0.30, "style": {"value": 40, "growth": 35, "momentum": 25}},
        "Energy": {"volatility": 0.45, "style": {"value": 35, "growth": 30, "momentum": 35}},
        "Communication": {"volatility": 0.32, "style": {"value": 35, "growth": 45, "momentum": 20}},
        "Industrials": {"volatility": 0.28, "style": {"value": 50, "growth": 30, "momentum": 20}},
        "Materials": {"volatility": 0.35, "style": {"value": 40, "growth": 35, "momentum": 25}},
        "Utilities": {"volatility": 0.15, "style": {"value": 70, "growth": 15, "momentum": 15}},
    }
    
    def __init__(self, profile_repo: IProfileRepository, use_ai_model: bool = True):
        self.profile_repo = profile_repo
        self.use_ai_model = use_ai_model
        self._recommendations: Dict[str, List[Recommendation]] = {}  # user_id -> recommendations
        self._feedbacks: List[RecommendationFeedback] = []
        
        # StockRankingService 인스턴스 (AI 예측 위임)
        self._stock_ranking_service = None
    
    def _get_stock_ranking_service(self):
        """StockRankingService 지연 로딩"""
        if self._stock_ranking_service is None:
            from src.services.stock_ranking_service import StockRankingService
            self._stock_ranking_service = StockRankingService(
                self.profile_repo,
                use_ai_model=self.use_ai_model
            )
        return self._stock_ranking_service
    
    def generate_recommendations(
        self,
        profile: InvestorProfile,
        top_n: int = 10
    ) -> List[Recommendation]:
        """
        프로필 기반 종목 추천 생성
        
        점수 = (성향 적합도 * 0.4) + (트렌드 점수 * 0.3) + (AI 예측 * 0.3)
        """
        recommendations = []
        
        for ticker, stock_info in self.KOREAN_STOCKS.items():
            stock_name = stock_info["name"]
            sector = stock_info["sector"]
            
            # 1. 성향 적합도 계산
            profile_fit = self._calculate_profile_fit(profile, sector)
            
            # 2. 트렌드 점수 (시뮬레이션)
            trend_score = self._simulate_trend_score(ticker)
            
            # 3. AI 예측 점수 (시뮬레이션, 실제로는 EnsemblePredictor 사용)
            ai_score, ai_prediction, confidence = self._simulate_ai_prediction(ticker)
            
            # 종합 점수
            composite_score = (profile_fit * 0.4) + (trend_score * 0.3) + (ai_score * 0.3)
            
            # 추천 사유 생성
            reason = self._generate_reason(profile, sector, profile_fit, ai_prediction)
            
            rec = Recommendation(
                recommendation_id=str(uuid.uuid4())[:8],
                user_id=profile.user_id,
                ticker=ticker,
                stock_name=stock_name,
                sector=sector,
                fit_score=profile_fit,
                trend_score=trend_score,
                ai_score=ai_score,
                composite_score=composite_score,
                ai_prediction=ai_prediction,
                confidence=confidence,
                recommendation_reason=reason
            )
            recommendations.append(rec)
        
        # 점수순 정렬
        recommendations.sort(key=lambda x: x.composite_score, reverse=True)
        
        # 상위 N개 저장 및 반환
        top_recommendations = recommendations[:top_n]
        self._recommendations[profile.user_id] = top_recommendations
        
        return top_recommendations
    
    def _calculate_profile_fit(self, profile: InvestorProfile, sector: str) -> float:
        """성향 적합도 계산"""
        sector_info = self.SECTOR_CHARACTERISTICS.get(sector, {})
        sector_volatility = sector_info.get("volatility", 0.30)
        sector_style = sector_info.get("style", {"value": 33, "growth": 33, "momentum": 34})
        
        # 1. 변동성 적합도 (40%)
        ideal_vol_min, ideal_vol_max = profile.get_ideal_volatility_range()
        if ideal_vol_min <= sector_volatility <= ideal_vol_max:
            vol_fit = 100.0
        else:
            ideal_mid = (ideal_vol_min + ideal_vol_max) / 2
            vol_fit = max(0, 100 - abs(sector_volatility - ideal_mid) * 200)
        
        # 2. 섹터 적합도 (30%)
        sector_fit = profile.calculate_sector_match_score(sector)
        
        # 3. 스타일 적합도 (30%)
        style_fit = profile.calculate_style_similarity(sector_style)
        
        return (vol_fit * 0.4) + (sector_fit * 0.3) + (style_fit * 0.3)
    
    def _simulate_trend_score(self, ticker: str) -> float:
        """트렌드 점수 시뮬레이션 (실제로는 TechnicalAnalyzer 사용)"""
        # 간단한 랜덤 시뮬레이션
        np.random.seed(hash(ticker) % 2**32)
        return np.random.uniform(40, 90)
    
    def _simulate_ai_prediction(self, ticker: str) -> Tuple[float, str, float]:
        """AI 예측 시뮬레이션 (실제로는 EnsemblePredictor 사용)"""
        np.random.seed(hash(ticker + "ai") % 2**32)
        score = np.random.uniform(30, 95)
        confidence = np.random.uniform(0.5, 0.9)
        
        if score >= 70:
            prediction = "상승"
        elif score >= 40:
            prediction = "보합"
        else:
            prediction = "하락"
        
        return score, prediction, confidence
    
    def _generate_reason(
        self,
        profile: InvestorProfile,
        sector: str,
        fit_score: float,
        ai_prediction: str
    ) -> str:
        """추천 사유 생성"""
        reasons = []
        
        if sector in profile.preferred_sectors:
            reasons.append(f"선호 섹터 ({sector})")
        
        if fit_score >= 80:
            reasons.append("높은 성향 적합도")
        elif fit_score >= 60:
            reasons.append("양호한 성향 적합도")
        
        if ai_prediction == "상승":
            reasons.append("AI 상승 예측")
        
        return ", ".join(reasons) if reasons else "종합 점수 기반 추천"
    
    # ===== 피드백 처리 =====
    
    def process_feedback(
        self,
        user_id: str,
        recommendation_id: str,
        action: str,
        reason: str = ""
    ) -> bool:
        """
        피드백 처리 및 프로필 업데이트
        
        수락: 해당 섹터/스타일 강화
        거절: 사유 분석 후 프로필 조정
        """
        # 추천 찾기
        user_recs = self._recommendations.get(user_id, [])
        rec = None
        for r in user_recs:
            if r.recommendation_id == recommendation_id:
                rec = r
                break
        
        if not rec:
            return False
        
        # 피드백 저장
        feedback = RecommendationFeedback(
            feedback_id=str(uuid.uuid4())[:8],
            recommendation_id=recommendation_id,
            user_id=user_id,
            action=action,
            reason=reason,
            ticker=rec.ticker,
            sector=rec.sector
        )
        self._feedbacks.append(feedback)
        
        # 추천 상태 업데이트
        if action == "accept":
            rec.accept()
        else:
            rec.reject()
        
        # 프로필 업데이트
        profile = self.profile_repo.load(user_id)
        if profile:
            self._update_profile_from_feedback(profile, feedback, rec)
            self.profile_repo.save(profile)
        
        return True
    
    def _update_profile_from_feedback(
        self,
        profile: InvestorProfile,
        feedback: RecommendationFeedback,
        rec: Recommendation
    ) -> None:
        """피드백 기반 프로필 업데이트"""
        if feedback.is_accept:
            # 수락: 섹터 선호도 강화
            profile.add_preferred_sector(rec.sector)
            
            # 변동성 높은 종목 수락 시 위험 감수 증가
            sector_vol = self.SECTOR_CHARACTERISTICS.get(rec.sector, {}).get("volatility", 0.30)
            if sector_vol > 0.35:
                profile.adjust_risk_tolerance(3)
        
        elif feedback.is_reject:
            # 거절: 사유 분석
            reason_lower = feedback.reason.lower()
            
            if "변동" in reason_lower or "위험" in reason_lower:
                # 변동성/위험 관련 거절 → 위험 감수 감소
                profile.adjust_risk_tolerance(-5)
            
            if "섹터" in reason_lower or "관심" in reason_lower:
                # 섹터 관련 거절 → 선호 섹터에서 제거
                profile.remove_preferred_sector(rec.sector)
    
    # ===== 순위 조회 =====
    
    def get_ranked_stocks(
        self,
        profile: InvestorProfile,
        top_n: int = 10
    ) -> List[RankedStock]:
        """순위가 매겨진 종목 리스트 반환 (StockRankingService 위임)"""
        ranking_service = self._get_stock_ranking_service()
        return ranking_service.get_personalized_ranking(profile.user_id, top_n)
    
    def get_user_recommendations(self, user_id: str) -> List[Recommendation]:
        """사용자 추천 이력 조회"""
        return self._recommendations.get(user_id, [])
    
    def get_pending_recommendations(self, user_id: str) -> List[Recommendation]:
        """대기 중인 추천 조회"""
        recs = self._recommendations.get(user_id, [])
        return [r for r in recs if r.status == RecommendationStatus.PENDING]
    
    def get_feedback_history(self, user_id: str) -> List[RecommendationFeedback]:
        """피드백 이력 조회"""
        return [f for f in self._feedbacks if f.user_id == user_id]
