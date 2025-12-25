"""
Profile-Aware Buzz Service - Phase 20 투자 성향 연동

투자자 프로필 기반 맞춤 Buzz 분석 서비스
- 사용자 위험 감수 성향에 따른 필터링
- 선호 섹터 보너스 점수
- 개인화된 관심 종목 추천
"""
import logging
from typing import List, Optional
from datetime import datetime

from src.services.market_buzz_service import MarketBuzzService
from src.domain.market_buzz.entities.buzz_score import BuzzScore
from src.infrastructure.repositories.profile_repository import SQLiteProfileRepository

logger = logging.getLogger(__name__)


class ProfileAwareBuzzService:
    """
    투자 성향 기반 맞춤 Buzz 분석 서비스 (Phase 20/21 Integration)
    
    Features:
    - 위험 감수 성향에 따른 변동성 필터링
    - 선호 섹터 우선 순위 부여
    - 프로필 적합도 점수 (0~100) 계산
    """
    
    def __init__(
        self,
        market_buzz_service: MarketBuzzService,
        profile_repo: Optional[SQLiteProfileRepository] = None
    ):
        """
        Args:
            market_buzz_service: 기본 Buzz 서비스
            profile_repo: 프로필 저장소 (Optional, None이면 기본 생성)
        """
        self.buzz_service = market_buzz_service
        self.profile_repo = profile_repo or SQLiteProfileRepository()
        
        # 섹터 정보 캐시 {ticker: sector}
        self._sector_cache = {}
    
    def get_personalized_buzz_stocks(
        self,
        user_id: str,
        market: str = "KR",
        top_n: int = 10,
        force_refresh: bool = False
    ) -> List[BuzzScore]:
        """
        사용자 성향에 맞는 관심 종목 필터링
        
        로직:
        1. MarketBuzzService에서 전체 Buzz 종목 조회 (상위 50개)
        2. 사용자 프로필 로드
        3. 프로필 기반 필터링:
           - 안정형/안정추구형: 변동성 높은 종목 제외
           - 성장추구형/공격투자형: HOT 종목 우선
           - 선호 섹터: 해당 섹터 보너스 점수 부여
        4. profile_fit_score 계산 및 최종 점수 산정
        
        Args:
            user_id: 사용자 ID (이메일)
            market: "US" 또는 "KR"
            top_n: 상위 N개
            force_refresh: 캐시 무시
        
        Returns:
            BuzzScore 리스트 (final_score 높은 순)
        """
        # 1. 전체 Buzz 종목 조회
        try:
            all_buzz = self.buzz_service.get_top_buzz_stocks(
                market=market,
                top_n=50,  # 넉넉하게 50개 가져오기
                force_refresh=force_refresh
            )
        except Exception as e:
            logger.error(f"[ProfileBuzz] Failed to get buzz stocks: {e}")
            return []
        
        # 2. 프로필 로드
        try:
            profile = self.profile_repo.load(user_id)
        except Exception as e:
            logger.warning(f"[ProfileBuzz] Failed to load profile for {user_id}: {e}")
            profile = None
        
        if not profile:
            # 프로필 없으면 전체 반환 (profile_fit_score 없음)
            logger.info(f"[ProfileBuzz] No profile found for {user_id}, returning all buzz")
            return all_buzz[:top_n]
        
        # 3. 성향 기반 필터링 및 점수 부여
        logger.info(f"[ProfileBuzz] Applying profile filter for {user_id} (risk: {profile.risk_tolerance.value})")
        
        personalized = []
        for buzz in all_buzz:
            # 변동성 필터링 (안정형/안정추구형만)
            if profile.risk_tolerance.value <= 40:  # 안정형/안정추구형
                if buzz.volatility_ratio > 2.0:
                    logger.debug(f"[ProfileBuzz] Filtering out {buzz.ticker} due to high volatility ({buzz.volatility_ratio:.2f})")
                    continue  # 변동성 높은 종목 제외
            
            # Profile Fit Score 계산
            profile_fit_score = self._calculate_profile_fit(buzz, profile)
            
            # BuzzScore에 profile_fit_score 추가
            buzz.profile_fit_score = profile_fit_score
            
            # 섹터 정보 추가 (캐싱)
            buzz.sector = self._get_stock_sector(buzz.ticker)
            
            personalized.append(buzz)
        
        # 4. final_score 기준 정렬 (base_score * 0.6 + profile_fit * 0.4)
        personalized.sort(reverse=True)  # BuzzScore.__lt__ 사용
        
        logger.info(f"[ProfileBuzz] Personalized {len(personalized)} stocks for {user_id}")
        return personalized[:top_n]
    
    def _calculate_profile_fit(self, buzz: BuzzScore, profile) -> float:
        """
        프로필 적합도 점수 계산 (0~100)
        
        계산 요소:
        1. 섹터 선호도 (50점)
        2. 변동성 적합도 (30점)
        3. 위험 감수 레벨 매칭 (20점)
        """
        score = 0.0
        
        # 1. 섹터 선호도 (50점)
        sector = self._get_stock_sector(buzz.ticker)
        if sector and sector in profile.preferred_sectors:
            score += 50
            logger.debug(f"[ProfileFit] {buzz.ticker} sector bonus: {sector}")
        else:
            score += 20  # 기본 점수
        
        # 2. 변동성 적합도 (30점)
        # 안정형(0-20): volatility_ratio < 1.5 → 30점
        # 안정추구형(21-40): volatility_ratio < 2.0 → 30점
        # 균형형(41-60): volatility_ratio < 2.5 → 30점
        # 성장추구형(61-80): volatility_ratio < 3.0 → 30점
        # 공격투자형(81-100): volatility_ratio 무관 → 30점
        
        risk_value = profile.risk_tolerance.value
        
        if risk_value <= 20:  # 안정형
            if buzz.volatility_ratio < 1.5:
                score += 30
            elif buzz.volatility_ratio < 2.0:
                score += 15
        elif risk_value <= 40:  # 안정추구형
            if buzz.volatility_ratio < 2.0:
                score += 30
            elif buzz.volatility_ratio < 2.5:
                score += 15
        elif risk_value <= 60:  # 균형형
            if buzz.volatility_ratio < 2.5:
                score += 30
            else:
                score += 20
        elif risk_value <= 80:  # 성장추구형
            if buzz.volatility_ratio < 3.0:
                score += 30
            else:
                score += 25
        else:  # 공격투자형
            score += 30  # 변동성 무관
        
        # 3. Heat Level 매칭 (20점)
        # 안정형/안정추구형: COLD/WARM 선호
        # 균형형: WARM 선호
        # 성장추구형/공격투자형: HOT 선호
        
        if risk_value <= 40:  # 안정형/안정추구형
            if buzz.heat_level in ["COLD", "WARM"]:
                score += 20
            else:
                score += 5
        elif risk_value <= 60:  # 균형형
            if buzz.heat_level == "WARM":
                score += 20
            else:
                score += 10
        else:  # 성장추구형/공격투자형
            if buzz.heat_level == "HOT":
                score += 20
            else:
                score += 10
        
        return min(100, score)
    
    def _get_stock_sector(self, ticker: str) -> Optional[str]:
        """
        종목의 섹터 조회 (캐싱)
        
        Args:
            ticker: 종목 코드
        
        Returns:
            섹터명 또는 None
        """
        # 캐시 확인
        if ticker in self._sector_cache:
            return self._sector_cache[ticker]
        
        # yfinance로 섹터 정보 조회
        try:
            import yfinance as yf
            stock = yf.Ticker(ticker)
            info = stock.info
            sector = info.get('sector', None)
            
            # 캐싱
            self._sector_cache[ticker] = sector
            return sector
            
        except Exception as e:
            logger.warning(f"[Sector] Failed to fetch sector for {ticker}: {e}")
            return None
    
    def get_profile_summary(self, user_id: str) -> Optional[dict]:
        """
        사용자 프로필 요약 정보 반환 (UI 표시용)
        
        Returns:
            {
                'risk_tolerance': 'MODERATE',
                'risk_value': 50,
                'preferred_sectors': ['Technology', 'Healthcare'],
                'last_updated': '2025-12-25'
            }
        """
        try:
            profile = self.profile_repo.load(user_id)
            if not profile:
                return None
            
            return {
                'risk_tolerance': profile.risk_tolerance.name,
                'risk_value': profile.risk_tolerance.value,
                'preferred_sectors': profile.preferred_sectors,
                'last_updated': profile.last_assessment.strftime('%Y-%m-%d') if profile.last_assessment else None
            }
        except Exception as e:
            logger.error(f"[ProfileSummary] Failed for {user_id}: {e}")
            return None
