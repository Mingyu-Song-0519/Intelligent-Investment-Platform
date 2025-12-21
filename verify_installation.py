"""
뉴스 수집 및 감성 분석 모듈 설치 검증 스크립트
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))


def verify_imports():
    """모듈 import 검증"""
    print("=" * 80)
    print("모듈 Import 검증")
    print("=" * 80)

    modules_to_test = [
        ("src.collectors", "NewsCollector"),
        ("src.analyzers", "SentimentAnalyzer"),
    ]

    all_success = True

    for module_name, class_name in modules_to_test:
        try:
            module = __import__(module_name, fromlist=[class_name])
            cls = getattr(module, class_name)
            print(f"✓ {module_name}.{class_name} - OK")

            # 인스턴스 생성 테스트
            instance = cls()
            print(f"  └─ 인스턴스 생성 성공")

        except Exception as e:
            print(f"✗ {module_name}.{class_name} - FAIL: {e}")
            all_success = False

    return all_success


def verify_dependencies():
    """필수 패키지 검증"""
    print("\n" + "=" * 80)
    print("필수 패키지 검증")
    print("=" * 80)

    required_packages = [
        "requests",
        "bs4",  # BeautifulSoup4
        "feedparser",
        "sqlite3",
    ]

    all_success = True

    for package in required_packages:
        try:
            __import__(package)
            print(f"✓ {package} - OK")
        except ImportError as e:
            print(f"✗ {package} - FAIL: {e}")
            all_success = False

    return all_success


def verify_database():
    """데이터베이스 테이블 검증"""
    print("\n" + "=" * 80)
    print("데이터베이스 테이블 검증")
    print("=" * 80)

    try:
        import sqlite3
        from config import DATABASE_PATH

        with sqlite3.connect(DATABASE_PATH) as conn:
            cursor = conn.cursor()

            # news 테이블 존재 확인
            cursor.execute("""
                SELECT name FROM sqlite_master
                WHERE type='table' AND name='news'
            """)

            if cursor.fetchone():
                print("✓ news 테이블 - OK")

                # 테이블 스키마 확인
                cursor.execute("PRAGMA table_info(news)")
                columns = cursor.fetchall()

                expected_columns = [
                    'id', 'ticker', 'title', 'content', 'url',
                    'published_date', 'sentiment_score', 'created_at', 'source'
                ]

                actual_columns = [col[1] for col in columns]

                for col in expected_columns:
                    if col in actual_columns:
                        print(f"  ✓ 컬럼 '{col}' - OK")
                    else:
                        print(f"  ✗ 컬럼 '{col}' - MISSING")

                return True
            else:
                print("✗ news 테이블 - MISSING")
                return False

    except Exception as e:
        print(f"✗ 데이터베이스 검증 실패: {e}")
        return False


def verify_sentiment_analysis():
    """감성 분석 기능 검증"""
    print("\n" + "=" * 80)
    print("감성 분석 기능 검증")
    print("=" * 80)

    try:
        from src.analyzers import SentimentAnalyzer

        analyzer = SentimentAnalyzer()

        # 테스트 케이스
        test_cases = [
            ("주가가 급등했다", "korean", "positive"),
            ("실적이 부진했다", "korean", "negative"),
            ("Stock prices surge", "english", "positive"),
            ("Stock plunges", "english", "negative"),
        ]

        all_success = True

        for text, lang, expected_type in test_cases:
            score, details = analyzer.analyze_text(text, language=lang)

            # 예상 결과 확인
            is_correct = (
                (expected_type == "positive" and score > 0) or
                (expected_type == "negative" and score < 0)
            )

            status = "✓" if is_correct else "✗"
            print(f"{status} [{lang}] '{text[:30]}...' - 점수: {score:.3f} (예상: {expected_type})")

            if not is_correct:
                all_success = False

        return all_success

    except Exception as e:
        print(f"✗ 감성 분석 검증 실패: {e}")
        return False


def main():
    """메인 검증 함수"""
    print("\n")
    print("=" * 80)
    print("뉴스 수집 및 감성 분석 모듈 설치 검증")
    print("=" * 80)
    print()

    results = []

    # 1. 모듈 import 검증
    results.append(("모듈 Import", verify_imports()))

    # 2. 필수 패키지 검증
    results.append(("필수 패키지", verify_dependencies()))

    # 3. 데이터베이스 검증
    results.append(("데이터베이스", verify_database()))

    # 4. 감성 분석 기능 검증
    results.append(("감성 분석", verify_sentiment_analysis()))

    # 최종 결과
    print("\n" + "=" * 80)
    print("검증 결과 요약")
    print("=" * 80)

    all_passed = True
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{name}: {status}")
        if not passed:
            all_passed = False

    print("=" * 80)

    if all_passed:
        print("\n✓ 모든 검증 통과! 뉴스 수집 및 감성 분석 모듈이 정상적으로 설치되었습니다.")
        print("\n다음 명령으로 테스트를 실행할 수 있습니다:")
        print("  python test_news_sentiment.py")
        print("  python example_news_sentiment.py")
    else:
        print("\n✗ 일부 검증 실패. 위의 오류 메시지를 확인하세요.")

    print()


if __name__ == "__main__":
    main()
