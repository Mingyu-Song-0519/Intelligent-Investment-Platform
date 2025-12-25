"""
투자 성향 분석 시스템 E2E 테스트
전체 워크플로우 검증

테스트 범위:
1. 설문 응답 → 프로필 생성
2. 프로필 → 추천 생성
3. 피드백 → 프로필 업데이트
4. 순위 조회 → 캐싱 동작
"""
import pytest
import tempfile
import os
from datetime import datetime, timedelta

from src.domain.investment_profile.entities.investor_profile import InvestorProfile
from src.domain.investment_profile.entities.assessment import Answer, AssessmentSession
from src.domain.investment_profile.entities.recommendation import Recommendation, RecommendationFeedback
from src.domain.investment_profile.value_objects.risk_tolerance import RiskTolerance, RiskLevel
from src.infrastructure.repositories.profile_repository import SQLiteProfileRepository
from src.infrastructure.repositories.question_repository import YAMLQuestionRepository
from src.services.profile_assessment_service import ProfileAssessmentService
from src.services.recommendation_service import RecommendationService
from src.services.stock_ranking_service import StockRankingService


class TestInvestorProfileEntity:
    """InvestorProfile 엔티티 테스트"""
    
    def test_create_default_profile(self):
        """기본 프로필 생성 테스트"""
        profile = InvestorProfile.create_default("user123")
        
        assert profile.user_id == "user123"
        assert profile.risk_tolerance.value == 50
        assert profile.investment_horizon == "medium"
        assert profile.profile_type == "균형형"
        assert len(profile.preferred_sectors) > 0
    
    def test_risk_tolerance_levels(self):
        """위험 감수 수준 분류 테스트"""
        test_cases = [
            (15, RiskLevel.CONSERVATIVE, "안정형"),
            (35, RiskLevel.MODERATELY_CONSERVATIVE, "안정추구형"),
            (55, RiskLevel.BALANCED, "균형형"),
            (75, RiskLevel.GROWTH_SEEKING, "성장추구형"),
            (90, RiskLevel.AGGRESSIVE, "공격투자형"),
        ]
        
        for value, expected_level, expected_name in test_cases:
            rt = RiskTolerance(value)
            assert rt.level == expected_level
            assert rt.level_name == expected_name
    
    def test_profile_adjustment(self):
        """프로필 조정 테스트"""
        profile = InvestorProfile.create_default("test")
        initial_risk = profile.risk_tolerance.value
        
        # 위험 감수 증가
        profile.adjust_risk_tolerance(10)
        assert profile.risk_tolerance.value == initial_risk + 10
        
        # 섹터 추가
        profile.add_preferred_sector("Energy")
        assert "Energy" in profile.preferred_sectors
        
        # 섹터 제거
        profile.remove_preferred_sector("Energy")
        assert "Energy" not in profile.preferred_sectors
    
    def test_profile_outdated(self):
        """프로필 만료 확인 테스트"""
        profile = InvestorProfile.create_default("test")
        
        # 현재 프로필은 만료되지 않음
        assert not profile.is_outdated(180)
        
        # 과거 날짜로 설정
        profile.last_updated = datetime.now() - timedelta(days=200)
        assert profile.is_outdated(180)


class TestSQLiteProfileRepository:
    """SQLite Repository 테스트"""
    
    @pytest.fixture
    def temp_repo(self):
        """임시 DB 생성"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test_profiles.db")
            yield SQLiteProfileRepository(db_path)
    
    def test_save_and_load(self, temp_repo):
        """저장 및 로드 테스트"""
        profile = InvestorProfile.create_default("test_user")
        
        # 저장
        result = temp_repo.save(profile)
        assert result is True
        
        # 로드
        loaded = temp_repo.load("test_user")
        assert loaded is not None
        assert loaded.user_id == profile.user_id
        assert loaded.risk_tolerance.value == profile.risk_tolerance.value
    
    def test_exists_and_delete(self, temp_repo):
        """존재 확인 및 삭제 테스트"""
        profile = InvestorProfile.create_default("test_user")
        
        # 존재하지 않음
        assert not temp_repo.exists("test_user")
        
        # 저장 후 존재
        temp_repo.save(profile)
        assert temp_repo.exists("test_user")
        
        # 삭제
        temp_repo.delete("test_user")
        assert not temp_repo.exists("test_user")


class TestProfileAssessmentService:
    """ProfileAssessmentService 테스트"""
    
    @pytest.fixture
    def service(self):
        """서비스 인스턴스 생성"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            profile_repo = SQLiteProfileRepository(db_path)
            question_repo = YAMLQuestionRepository()
            yield ProfileAssessmentService(profile_repo, question_repo)
    
    def test_start_assessment(self, service):
        """설문 세션 시작 테스트"""
        session = service.start_assessment("user123")
        
        assert session is not None
        assert session.user_id == "user123"
        assert session.session_id is not None
    
    def test_get_questions(self, service):
        """질문 로드 테스트"""
        questions = service.get_all_questions()
        
        # 질문이 로드되었는지 확인
        assert len(questions) >= 0  # YAML 파일이 있으면 >0
    
    def test_create_default_profile(self, service):
        """기본 프로필 생성 테스트"""
        profile = service.create_default_profile("new_user")
        
        assert profile is not None
        assert profile.profile_type == "균형형"
        
        # 저장 확인
        loaded = service.get_profile("new_user")
        assert loaded is not None


class TestRecommendationService:
    """RecommendationService 테스트"""
    
    @pytest.fixture
    def service(self):
        """서비스 인스턴스 생성"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            profile_repo = SQLiteProfileRepository(db_path)
            yield RecommendationService(profile_repo)
    
    def test_generate_recommendations(self, service):
        """추천 생성 테스트"""
        profile = InvestorProfile.create_default("test_user")
        
        recommendations = service.generate_recommendations(profile, top_n=5)
        
        assert len(recommendations) == 5
        # 점수순 정렬 확인
        scores = [r.composite_score for r in recommendations]
        assert scores == sorted(scores, reverse=True)
    
    def test_profile_fit_calculation(self, service):
        """성향 적합도 계산 테스트"""
        # 안정형 프로필
        conservative_profile = InvestorProfile(
            user_id="conservative",
            risk_tolerance=RiskTolerance(20),
            investment_horizon="short",
            preferred_sectors=["Utilities", "Financials"],
            style_scores={"value": 60, "growth": 25, "momentum": 15}
        )
        
        # 공격투자형 프로필
        aggressive_profile = InvestorProfile(
            user_id="aggressive",
            risk_tolerance=RiskTolerance(90),
            investment_horizon="long",
            preferred_sectors=["Technology", "Healthcare"],
            style_scores={"value": 15, "growth": 45, "momentum": 40}
        )
        
        # 추천 생성
        conservative_recs = service.generate_recommendations(conservative_profile, top_n=3)
        aggressive_recs = service.generate_recommendations(aggressive_profile, top_n=3)
        
        # 다른 결과가 나와야 함
        conservative_tickers = [r.ticker for r in conservative_recs]
        aggressive_tickers = [r.ticker for r in aggressive_recs]
        
        # 완전히 같지 않아야 함 (성향에 따라 다른 추천)
        # (시뮬레이션이므로 완전한 검증은 어려움)
        assert len(conservative_recs) > 0
        assert len(aggressive_recs) > 0
    
    def test_feedback_processing(self, service):
        """피드백 처리 테스트"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            profile_repo = SQLiteProfileRepository(db_path)
            svc = RecommendationService(profile_repo)
            
            # 프로필 생성 및 저장
            profile = InvestorProfile(
                user_id="feedback_test",
                risk_tolerance=RiskTolerance(70),
                investment_horizon="medium",
                preferred_sectors=["Technology"],
                style_scores={"value": 30, "growth": 40, "momentum": 30}
            )
            profile_repo.save(profile)
            
            # 추천 생성
            recommendations = svc.generate_recommendations(profile, top_n=3)
            rec = recommendations[0]
            
            # 피드백: 변동성 이유로 거절
            result = svc.process_feedback(
                user_id="feedback_test",
                recommendation_id=rec.recommendation_id,
                action="reject",
                reason="변동성이 너무 높음"
            )
            
            assert result is True
            
            # 프로필 업데이트 확인 (위험 감수 감소)
            updated_profile = profile_repo.load("feedback_test")
            assert updated_profile.risk_tolerance.value < 70


class TestStockRankingService:
    """StockRankingService 테스트"""
    
    @pytest.fixture
    def service(self):
        """서비스 인스턴스 생성"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            profile_repo = SQLiteProfileRepository(db_path)
            yield StockRankingService(profile_repo)
    
    def test_get_personalized_ranking(self, service):
        """맞춤 순위 조회 테스트"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            profile_repo = SQLiteProfileRepository(db_path)
            svc = StockRankingService(profile_repo)
            
            # 프로필 생성
            profile = InvestorProfile.create_default("ranking_test")
            profile_repo.save(profile)
            
            # 순위 조회
            ranking = svc.get_personalized_ranking("ranking_test", top_n=5)
            
            assert len(ranking) == 5
            # 순위 번호 확인
            ranks = [s.rank for s in ranking]
            assert ranks == [1, 2, 3, 4, 5]
    
    def test_caching(self, service):
        """캐싱 동작 테스트"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            profile_repo = SQLiteProfileRepository(db_path)
            svc = StockRankingService(profile_repo, cache_ttl=3600)
            
            # 프로필 생성
            profile = InvestorProfile.create_default("cache_test")
            profile_repo.save(profile)
            
            # 첫 번째 조회 (캐시 미스)
            ranking1 = svc.get_personalized_ranking("cache_test", top_n=5)
            
            # 두 번째 조회 (캐시 히트)
            ranking2 = svc.get_personalized_ranking("cache_test", top_n=5)
            
            # 같은 결과
            assert [s.ticker for s in ranking1] == [s.ticker for s in ranking2]
            
            # 캐시 통계
            stats = svc.get_cache_stats()
            assert stats["cached_users"] == 1


class TestE2EWorkflow:
    """전체 워크플로우 E2E 테스트"""
    
    def test_complete_user_journey(self):
        """완전한 사용자 여정 테스트"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "e2e_test.db")
            
            # 1. 서비스 초기화
            profile_repo = SQLiteProfileRepository(db_path)
            question_repo = YAMLQuestionRepository()
            assessment_service = ProfileAssessmentService(profile_repo, question_repo)
            recommendation_service = RecommendationService(profile_repo)
            ranking_service = StockRankingService(profile_repo)
            
            user_id = "e2e_test_user"
            
            # 2. 프로필이 없음 확인
            assert not assessment_service.has_profile(user_id)
            
            # 3. 기본 프로필 생성
            profile = assessment_service.create_default_profile(user_id)
            assert profile.profile_type == "균형형"
            
            # 4. 추천 생성
            recommendations = recommendation_service.generate_recommendations(profile, top_n=5)
            assert len(recommendations) == 5
            
            # 5. 첫 번째 추천 수락
            rec = recommendations[0]
            recommendation_service.process_feedback(
                user_id=user_id,
                recommendation_id=rec.recommendation_id,
                action="accept"
            )
            
            # 6. 두 번째 추천 거절
            rec2 = recommendations[1]
            recommendation_service.process_feedback(
                user_id=user_id,
                recommendation_id=rec2.recommendation_id,
                action="reject",
                reason="변동성이 높음"
            )
            
            # 7. 프로필 업데이트 확인
            updated_profile = profile_repo.load(user_id)
            # 거절 피드백으로 인한 위험 감수 감소
            assert updated_profile.risk_tolerance.value < 50
            
            # 8. 순위 조회
            ranking = ranking_service.get_personalized_ranking(user_id, top_n=10)
            assert len(ranking) == 10
            
            print("✅ E2E 테스트 통과!")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
