"""
뉴스 수집 및 감성 분석 테스트 스크립트
"""
import sys
from pathlib import Path

# 프로젝트 루트 경로 설정
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.collectors.news_collector import NewsCollector
from src.analyzers.sentiment_analyzer import SentimentAnalyzer


def test_sentiment_analyzer():
    """감성 분석기 테스트"""
    print("=" * 80)
    print("1. 감성 분석기 테스트")
    print("=" * 80)

    analyzer = SentimentAnalyzer()

    # 한국어 테스트
    test_cases_korean = [
        ("삼성전자 주가가 급등하며 신고가를 돌파했다. 실적 호조에 투자자들의 기대감이 높아지고 있다.", "긍정"),
        ("실적 부진으로 주가가 급락했다. 투자자들의 우려가 커지고 있으며 전망이 어둡다.", "부정"),
        ("삼성전자가 오늘 주주총회를 개최했다.", "중립"),
    ]

    print("\n[한국어 감성 분석]")
    for text, expected in test_cases_korean:
        score, details = analyzer.analyze_text(text, language='korean')
        print(f"\n텍스트: {text[:50]}...")
        print(f"예상: {expected} | 점수: {score:.3f} | 긍정: {details['positive_count']} | 부정: {details['negative_count']}")

    # 영어 테스트
    test_cases_english = [
        ("Stock prices surge to record high as company beats earnings expectations.", "긍정"),
        ("Stock plunges on disappointing earnings and weak guidance.", "부정"),
        ("The company announced quarterly results today.", "중립"),
    ]

    print("\n[영어 감성 분석]")
    for text, expected in test_cases_english:
        score, details = analyzer.analyze_text(text, language='english')
        print(f"\n텍스트: {text[:50]}...")
        print(f"예상: {expected} | 점수: {score:.3f} | 긍정: {details['positive_count']} | 부정: {details['negative_count']}")


def test_news_collector():
    """뉴스 수집기 테스트"""
    print("\n\n" + "=" * 80)
    print("2. 뉴스 수집기 테스트")
    print("=" * 80)

    collector = NewsCollector()

    # 구글 뉴스 RSS 테스트 (더 안정적)
    print("\n[Google News RSS 테스트]")
    print("삼성전자 관련 뉴스 수집 중...")

    try:
        google_news = collector.fetch_google_news_rss("삼성전자", max_items=5)
        print(f"\n수집된 뉴스: {len(google_news)}개")

        for i, news in enumerate(google_news[:3], 1):
            print(f"\n[{i}] {news['title'][:60]}...")
            print(f"    날짜: {news['date']}")
            print(f"    URL: {news['url'][:80]}...")
    except Exception as e:
        print(f"Google News 수집 실패: {e}")

    # 네이버 금융 뉴스 테스트 (선택적)
    print("\n[네이버 금융 뉴스 테스트]")
    print("삼성전자(005930) 관련 뉴스 수집 중...")

    try:
        naver_news = collector.fetch_naver_finance_news("005930", max_pages=1)
        print(f"\n수집된 뉴스: {len(naver_news)}개")

        for i, news in enumerate(naver_news[:3], 1):
            print(f"\n[{i}] {news['title'][:60]}...")
            print(f"    날짜: {news['date']}")
    except Exception as e:
        print(f"네이버 금융 뉴스 수집 실패 (정상적일 수 있음): {e}")


def test_integration():
    """통합 테스트 - 뉴스 수집 및 감성 분석"""
    print("\n\n" + "=" * 80)
    print("3. 통합 테스트 - 뉴스 수집 및 감성 분석")
    print("=" * 80)

    collector = NewsCollector()
    analyzer = SentimentAnalyzer()

    # 뉴스 수집 및 저장
    print("\n[뉴스 수집 및 DB 저장]")
    try:
        saved_count = collector.collect_and_save(
            ticker="005930.KS",
            company_name="삼성전자",
            use_naver=False,  # 네이버는 선택적으로 비활성화
            use_google=True,
            max_pages=1,
            max_items=10
        )
        print(f"저장된 뉴스: {saved_count}개")
    except Exception as e:
        print(f"뉴스 수집 실패: {e}")
        saved_count = 0

    # 감성 분석
    if saved_count > 0:
        print("\n[감성 분석 수행]")
        analyzed_count = analyzer.analyze_all_news(ticker="005930.KS")
        print(f"분석된 뉴스: {analyzed_count}개")

        # 감성 요약
        print("\n[감성 분석 요약]")
        summary = analyzer.get_sentiment_summary("005930.KS", days=30)
        if summary['total_news'] > 0:
            print(f"\n종목: {summary['ticker']}")
            print(f"전체 뉴스: {summary['total_news']}개")
            print(f"평균 감성: {summary['avg_sentiment']:.3f}")
            print(f"감성 레이블: {summary['sentiment_label']}")
            print(f"긍정 뉴스: {summary['positive_news']}개")
            print(f"부정 뉴스: {summary['negative_news']}개")
            print(f"중립 뉴스: {summary['neutral_news']}개")

            # 최근 뉴스 조회
            print("\n[최근 뉴스 샘플]")
            recent_news = collector.get_news("005930.KS", limit=3)
            for i, news in enumerate(recent_news, 1):
                sentiment = news.get('sentiment_score', 0)
                sentiment_label = analyzer._get_sentiment_label(sentiment) if sentiment else 'N/A'
                print(f"\n[{i}] {news['title'][:60]}...")
                print(f"    날짜: {news['published_date']}")
                print(f"    감성: {sentiment:.3f if sentiment else 'N/A'} ({sentiment_label})")
                print(f"    출처: {news['source']}")
        else:
            print("분석된 뉴스가 없습니다.")
    else:
        print("\n저장된 뉴스가 없어 감성 분석을 건너뜁니다.")


def main():
    """메인 테스트 실행"""
    print("\n")
    print("=" * 80)
    print("뉴스 수집 및 감성 분석 모듈 테스트")
    print("=" * 80)

    try:
        # 1. 감성 분석기 테스트
        test_sentiment_analyzer()

        # 2. 뉴스 수집기 테스트
        test_news_collector()

        # 3. 통합 테스트
        test_integration()

        print("\n\n" + "=" * 80)
        print("테스트 완료!")
        print("=" * 80)

    except Exception as e:
        print(f"\n[ERROR] 테스트 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
