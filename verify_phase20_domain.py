"""
Phase 20.1 Domain Layer Verification Script
Tests the Investment Profile domain entities, value objects, and repositories
"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

def test_risk_tolerance():
    """Test RiskTolerance Value Object"""
    from src.domain.investment_profile.value_objects.risk_tolerance import RiskTolerance, RiskLevel

    print("\n[TEST] RiskTolerance Value Object")

    # Test creation and validation
    rt_conservative = RiskTolerance(15)
    assert rt_conservative.level == RiskLevel.CONSERVATIVE
    assert rt_conservative.value == 15
    print("  PASS: Conservative risk tolerance creation")

    rt_aggressive = RiskTolerance(90)
    assert rt_aggressive.level == RiskLevel.AGGRESSIVE
    assert rt_aggressive.ideal_volatility_range == (0.40, 1.00)
    print("  PASS: Aggressive risk tolerance with volatility range")

    # Test immutability (adjust returns new instance)
    rt_adjusted = rt_conservative.adjust(30)
    assert rt_adjusted.value == 45
    assert rt_conservative.value == 15  # Original unchanged
    print("  PASS: Immutability pattern (adjust returns new instance)")

    # Test to_dict/from_dict
    rt_dict = rt_aggressive.to_dict()
    rt_restored = RiskTolerance.from_dict(rt_dict)
    assert rt_restored.value == rt_aggressive.value
    print("  PASS: Serialization/deserialization")

    return True

def test_investor_profile():
    """Test InvestorProfile Entity"""
    from src.domain.investment_profile.entities.investor_profile import InvestorProfile
    from src.domain.investment_profile.value_objects.risk_tolerance import RiskTolerance

    print("\n[TEST] InvestorProfile Entity")

    # Test creation
    profile = InvestorProfile(
        user_id="test_user_001",
        risk_tolerance=RiskTolerance(50),
        investment_horizon="medium",
        preferred_sectors=["Technology", "Healthcare"],
        style_scores={"value": 40.0, "growth": 50.0, "momentum": 10.0}
    )
    assert profile.profile_type == "균형형"
    print("  PASS: Profile creation with balanced risk")

    # Test business logic methods
    profile.add_preferred_sector("Financials")
    assert len(profile.preferred_sectors) == 3
    print("  PASS: Add preferred sector")

    match_score = profile.calculate_sector_match_score("Technology")
    assert match_score == 100.0
    print("  PASS: Sector matching score calculation")

    # Test create_default factory
    default_profile = InvestorProfile.create_default("default_user")
    assert default_profile.risk_tolerance.value == 50
    assert default_profile.investment_horizon == "medium"
    print("  PASS: Default profile factory method")

    # Test serialization
    profile_dict = profile.to_dict()
    restored = InvestorProfile.from_dict(profile_dict)
    assert restored.user_id == profile.user_id
    assert restored.risk_tolerance.value == profile.risk_tolerance.value
    print("  PASS: Profile serialization/deserialization")

    return True

def test_assessment_entities():
    """Test Question, Answer, AssessmentSession entities"""
    from src.domain.investment_profile.entities.assessment import (
        Question, QuestionOption, QuestionType, Answer, AssessmentSession
    )
    from datetime import datetime

    print("\n[TEST] Assessment Entities")

    # Test Question creation
    options = [
        QuestionOption(label="Option A", score=0.0),
        QuestionOption(label="Option B", score=50.0),
        QuestionOption(label="Option C", score=100.0)
    ]
    question = Question(
        question_id="Q001",
        category="risk_tolerance",
        question_text="Test question?",
        question_type=QuestionType.SCENARIO,
        options=options,
        weight=1.5
    )
    assert question.get_max_score() == 100.0
    assert question.get_score_for_option("Option B") == 50.0
    print("  PASS: Question entity creation and scoring")

    # Test Answer creation
    answer = Answer(
        question_id="Q001",
        selected_option="Option C",
        score=100.0
    )
    assert answer.score == 100.0
    print("  PASS: Answer entity creation")

    # Test AssessmentSession
    session = AssessmentSession(
        session_id="session_001",
        user_id="test_user"
    )
    session.add_answer(answer)
    assert len(session.answers) == 1
    assert session.get_answer("Q001").score == 100.0
    print("  PASS: Assessment session with answer tracking")

    # Test category score calculation
    questions_list = [question]
    category_score = session.calculate_category_score("risk_tolerance", questions_list)
    assert category_score == 100.0
    print("  PASS: Category score calculation with weights")

    return True

def test_repository_interfaces():
    """Test that repository interfaces are properly defined"""
    from src.domain.repositories.profile_interfaces import (
        IProfileRepository, IQuestionRepository
    )
    import inspect

    print("\n[TEST] Repository Interfaces (DIP Compliance)")

    # Test IProfileRepository interface
    profile_methods = [m for m in dir(IProfileRepository) if not m.startswith('_')]
    required_methods = ['save', 'load', 'delete', 'exists', 'list_all_users']
    for method in required_methods:
        assert method in profile_methods
    print("  PASS: IProfileRepository interface complete")

    # Test IQuestionRepository interface
    question_methods = [m for m in dir(IQuestionRepository) if not m.startswith('_')]
    required_methods = ['load_questions', 'get_question', 'get_questions_by_category']
    for method in required_methods:
        assert method in question_methods
    print("  PASS: IQuestionRepository interface complete")

    return True

def test_yaml_question_repository():
    """Test YAML Question Repository"""
    from src.infrastructure.repositories.question_repository import YAMLQuestionRepository

    print("\n[TEST] YAML Question Repository")

    repo = YAMLQuestionRepository("config/assessment_questions.yaml")

    # Test load_questions
    questions = repo.load_questions()
    assert len(questions) > 0
    print(f"  PASS: Loaded {len(questions)} questions from YAML")

    # Test get_question
    q1 = repo.get_question("Q001")
    assert q1 is not None
    assert q1.question_id == "Q001"
    print("  PASS: Get specific question by ID")

    # Test get_questions_by_category
    risk_questions = repo.get_questions_by_category("risk_tolerance")
    assert len(risk_questions) > 0
    print(f"  PASS: Get questions by category (found {len(risk_questions)} risk_tolerance questions)")

    # Test get_categories
    categories = repo.get_categories()
    assert len(categories) > 0
    print(f"  PASS: Get all categories (found {len(categories)} categories)")

    return True

def test_sqlite_profile_repository():
    """Test SQLite Profile Repository"""
    from src.infrastructure.repositories.profile_repository import SQLiteProfileRepository
    from src.domain.investment_profile.entities.investor_profile import InvestorProfile
    from src.domain.investment_profile.value_objects.risk_tolerance import RiskTolerance
    import tempfile
    import os

    print("\n[TEST] SQLite Profile Repository")

    # Use temporary database
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        tmp_path = tmp.name

    try:
        repo = SQLiteProfileRepository(tmp_path)

        # Test save
        profile = InvestorProfile(
            user_id="repo_test_user",
            risk_tolerance=RiskTolerance(60),
            investment_horizon="long",
            preferred_sectors=["Technology"],
            style_scores={"value": 30.0, "growth": 60.0, "momentum": 10.0}
        )
        result = repo.save(profile)
        assert result == True
        print("  PASS: Profile save operation")

        # Test exists
        assert repo.exists("repo_test_user") == True
        assert repo.exists("nonexistent_user") == False
        print("  PASS: Profile exists check")

        # Test load
        loaded = repo.load("repo_test_user")
        assert loaded is not None
        assert loaded.user_id == "repo_test_user"
        assert loaded.risk_tolerance.value == 60
        assert loaded.investment_horizon == "long"
        print("  PASS: Profile load operation")

        # Test list_all_users
        users = repo.list_all_users()
        assert "repo_test_user" in users
        print("  PASS: List all users")

        # Test delete
        deleted = repo.delete("repo_test_user")
        assert deleted == True
        assert repo.exists("repo_test_user") == False
        print("  PASS: Profile delete operation")

    finally:
        # Cleanup
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

    return True

def main():
    """Run all verification tests"""
    print("="*60)
    print("Phase 20.1 Domain Layer Verification")
    print("="*60)

    tests = [
        ("RiskTolerance Value Object", test_risk_tolerance),
        ("InvestorProfile Entity", test_investor_profile),
        ("Assessment Entities", test_assessment_entities),
        ("Repository Interfaces", test_repository_interfaces),
        ("YAML Question Repository", test_yaml_question_repository),
        ("SQLite Profile Repository", test_sqlite_profile_repository),
    ]

    passed = 0
    failed = 0

    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
        except Exception as e:
            failed += 1
            print(f"\n[FAIL] {test_name}")
            print(f"  Error: {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "="*60)
    print(f"VERIFICATION SUMMARY")
    print("="*60)
    print(f"Total Tests: {len(tests)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")

    if failed == 0:
        print("\n*** ALL TESTS PASSED ***")
        print("Phase 20.1 Domain Layer implementation verified successfully!")
        return 0
    else:
        print(f"\n*** {failed} TEST(S) FAILED ***")
        return 1

if __name__ == "__main__":
    sys.exit(main())
