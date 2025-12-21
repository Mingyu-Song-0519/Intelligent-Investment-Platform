"""
뉴스 수집 및 감성 분석 사용 예제
"""
import sys
from pathlib import Path

# 프로젝트 루트 경로 설정
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.collectors import NewsCollector
from src.analyzers import SentimentAnalyzer


def example_basic_usage():
    """기본 사용 예제"""
    print("=" * 80)
    print("기본 사용 예제 - 삼성전자 뉴스 수집 및 감성 분석")
    print("=" * 80)

    # 1. 객체 초기화
    collector = NewsCollector()
    analyzer = SentimentAnalyzer()

    # 2. 뉴스 수집
    print("\n[1단계] 뉴스 수집 중...")
    saved_count = collector.collect_and_save(
        ticker="005930.KS",
        company_name="삼성전자",
        use_naver=False,  # 네이버 금융 (선택적)
        use_google=True,  # Google News
        max_pages=2,
        max_items=15
    )
    print(f"수집 완료: {saved_count}개 뉴스 저장됨")

    # 3. 감성 분석
    if saved_count > 0:
        print("\n[2단계] 감성 분석 수행 중...")
        analyzed_count = analyzer.analyze_all_news(ticker="005930.KS")
        print(f"분석 완료: {analyzed_count}개 뉴스 분석됨")

        # 4. 결과 확인
        print("\n[3단계] 결과 확인")
        summary = analyzer.get_sentiment_summary("005930.KS", days=30)

        print("\n" + "-" * 60)
        print(f"종목: {summary['ticker']}")
        print(f"전체 뉴스: {summary['total_news']}개")
        print(f"평균 감성 점수: {summary['avg_sentiment']:.3f}")
        print(f"감성 레이블: {summary['sentiment_label']}")
        print("-" * 60)
        print(f"긍정 뉴스: {summary['positive_news']}개")
        print(f"부정 뉴스: {summary['negative_news']}개")
        print(f"중립 뉴스: {summary['neutral_news']}개")
        print("-" * 60)

        # 5. 최근 뉴스 샘플
        print("\n[최근 뉴스 샘플]")
        recent_news = collector.get_news("005930.KS", limit=5)

        for i, news in enumerate(recent_news, 1):
            sentiment = news.get('sentiment_score')
            if sentiment is not None:
                sentiment_label = analyzer._get_sentiment_label(sentiment)
                sentiment_str = f"{sentiment:.3f} ({sentiment_label})"
            else:
                sentiment_str = "N/A"

            print(f"\n[{i}] {news['title'][:70]}...")
            print(f"    날짜: {news['published_date']}")
            print(f"    감성: {sentiment_str}")
            print(f"    출처: {news['source']}")
    else:
        print("\n수집된 뉴스가 없습니다.")


def example_text_sentiment():
    """텍스트 감성 분석 예제"""
    print("\n\n" + "=" * 80)
    print("텍스트 감성 분석 예제")
    print("=" * 80)

    analyzer = SentimentAnalyzer()

    # 한국어 텍스트 예제
    korean_texts = [
        "삼성전자 주가가 급등하며 신고가를 돌파했다. 실적 호조에 투자자들의 기대감이 높아지고 있다.",
        "실적 부진으로 주가가 급락했다. 투자자들의 우려가 커지고 있으며 전망이 어둡다.",
        "삼성전자가 오늘 주주총회를 개최하고 신제품을 발표했다.",
    ]

    print("\n[한국어 감성 분석]")
    for i, text in enumerate(korean_texts, 1):
        score, details = analyzer.analyze_text(text, language='korean')
        label = analyzer._get_sentiment_label(score)

        print(f"\n[{i}] {text[:60]}...")
        print(f"    감성 점수: {score:.3f} ({label})")
        print(f"    긍정 키워드: {details['positive_count']}개")
        print(f"    부정 키워드: {details['negative_count']}개")

    # 영어 텍스트 예제
    english_texts = [
        "Stock prices surge to record high as company beats earnings expectations. Investors are optimistic.",
        "Stock plunges on disappointing earnings and weak guidance. Concerns grow among investors.",
        "The company announced quarterly results today and held a shareholder meeting.",
    ]

    print("\n[영어 감성 분석]")
    for i, text in enumerate(english_texts, 1):
        score, details = analyzer.analyze_text(text, language='english')
        label = analyzer._get_sentiment_label(score)

        print(f"\n[{i}] {text[:60]}...")
        print(f"    감성 점수: {score:.3f} ({label})")
        print(f"    긍정 키워드: {details['positive_count']}개")
        print(f"    부정 키워드: {details['negative_count']}개")


def example_multiple_tickers():
    """여러 종목 뉴스 수집 예제"""
    print("\n\n" + "=" * 80)
    print("여러 종목 뉴스 수집 및 분석 예제")
    print("=" * 80)

    collector = NewsCollector()
    analyzer = SentimentAnalyzer()

    # 분석할 종목 리스트
    stocks = [
        ("005930.KS", "삼성전자"),
        ("000660.KS", "SK하이닉스"),
        ("035420.KS", "NAVER"),
    ]

    results = []

    for ticker, name in stocks:
        print(f"\n[{name} ({ticker})] 뉴스 수집 중...")

        # 뉴스 수집
        saved_count = collector.collect_and_save(
            ticker=ticker,
            company_name=name,
            use_google=True,
            max_items=10
        )

        if saved_count > 0:
            # 감성 분석
            analyzer.analyze_all_news(ticker=ticker)

            # 요약
            summary = analyzer.get_sentiment_summary(ticker, days=7)
            results.append(summary)

            print(f"  수집: {saved_count}개 | 평균 감성: {summary['avg_sentiment']:.3f} ({summary['sentiment_label']})")

    # 종합 결과
    if results:
        print("\n" + "=" * 80)
        print("종합 결과 (최근 7일)")
        print("=" * 80)

        for summary in results:
            ticker_name = dict(stocks).get(summary['ticker'], summary['ticker'])
            print(f"\n{ticker_name} ({summary['ticker']})")
            print(f"  뉴스 수: {summary['total_news']}개")
            print(f"  평균 감성: {summary['avg_sentiment']:.3f} ({summary['sentiment_label']})")
            print(f"  긍정: {summary['positive_news']}개 | 부정: {summary['negative_news']}개 | 중립: {summary['neutral_news']}개")


def main():
    """메인 함수"""
    print("\n뉴스 수집 및 감성 분석 모듈 사용 예제\n")

    try:
        # 1. 기본 사용 예제
        example_basic_usage()

        # 2. 텍스트 감성 분석 예제
        example_text_sentiment()

        # 3. 여러 종목 예제 (선택적 - 시간이 오래 걸림)
        # example_multiple_tickers()

        print("\n\n" + "=" * 80)
        print("모든 예제 실행 완료!")
        print("=" * 80)
        print("\n자세한 사용법은 NEWS_SENTIMENT_USAGE.md 파일을 참고하세요.")

    except Exception as e:
        print(f"\n[ERROR] 예제 실행 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
