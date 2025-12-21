# 뉴스 수집 및 감성 분석 모듈 사용 가이드

## 개요

이 모듈은 주식 관련 뉴스를 수집하고 감성 분석을 수행하여 투자 의사결정에 도움을 제공합니다.

## 주요 기능

### 1. NewsCollector (뉴스 수집)
- 네이버 금융 뉴스 크롤링
- Google News RSS 피드 수집
- SQLite 데이터베이스 저장
- Rate limiting 및 robots.txt 준수

### 2. SentimentAnalyzer (감성 분석)
- 한국어 감성 분석 (키워드 기반)
- 영어 감성 분석 (VADER 스타일)
- 감성 점수: -1.0 (매우 부정) ~ 1.0 (매우 긍정)
- 감성 요약 및 통계

## 설치

```bash
pip install -r requirements.txt
```

필요한 패키지:
- requests
- beautifulsoup4
- feedparser

## 사용 예시

### 1. 뉴스 수집

```python
from src.collectors.news_collector import NewsCollector

# NewsCollector 초기화
collector = NewsCollector()

# 삼성전자 뉴스 수집 및 저장
saved_count = collector.collect_and_save(
    ticker="005930.KS",
    company_name="삼성전자",
    use_naver=True,      # 네이버 금융 뉴스 사용
    use_google=True,     # Google News 사용
    max_pages=3,         # 네이버 금융 최대 페이지
    max_items=20         # Google News 최대 아이템
)

print(f"저장된 뉴스: {saved_count}개")

# 저장된 뉴스 조회
news_list = collector.get_news("005930.KS", limit=10)
for news in news_list:
    print(f"제목: {news['title']}")
    print(f"날짜: {news['published_date']}")
    print(f"URL: {news['url']}\n")
```

### 2. 감성 분석

```python
from src.analyzers.sentiment_analyzer import SentimentAnalyzer

# SentimentAnalyzer 초기화
analyzer = SentimentAnalyzer()

# 텍스트 감성 분석
text = "삼성전자 주가가 급등하며 신고가를 돌파했다."
score, details = analyzer.analyze_text(text)

print(f"감성 점수: {score:.3f}")
print(f"긍정 키워드: {details['positive_count']}")
print(f"부정 키워드: {details['negative_count']}")

# DB에 저장된 모든 뉴스 감성 분석
analyzed_count = analyzer.analyze_all_news(ticker="005930.KS")
print(f"분석된 뉴스: {analyzed_count}개")

# 감성 분석 요약 (최근 7일)
summary = analyzer.get_sentiment_summary("005930.KS", days=7)
print(f"평균 감성: {summary['avg_sentiment']:.3f}")
print(f"감성 레이블: {summary['sentiment_label']}")
print(f"긍정 뉴스: {summary['positive_news']}개")
print(f"부정 뉴스: {summary['negative_news']}개")
```

### 3. 통합 사용 (뉴스 수집 + 감성 분석)

```python
from src.collectors.news_collector import NewsCollector
from src.analyzers.sentiment_analyzer import SentimentAnalyzer

# 초기화
collector = NewsCollector()
analyzer = SentimentAnalyzer()

# 1. 뉴스 수집
saved_count = collector.collect_and_save(
    ticker="005930.KS",
    company_name="삼성전자",
    max_pages=2,
    max_items=15
)

# 2. 감성 분석
if saved_count > 0:
    analyzed_count = analyzer.analyze_all_news(ticker="005930.KS")

    # 3. 결과 확인
    summary = analyzer.get_sentiment_summary("005930.KS", days=7)

    print("=" * 60)
    print(f"종목: {summary['ticker']}")
    print(f"전체 뉴스: {summary['total_news']}개")
    print(f"평균 감성: {summary['avg_sentiment']:.3f}")
    print(f"감성 레이블: {summary['sentiment_label']}")
    print("=" * 60)
```

## 데이터베이스 스키마

### news 테이블

| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| id | INTEGER | 기본키 (자동증가) |
| ticker | TEXT | 종목 코드 (예: '005930.KS') |
| title | TEXT | 뉴스 제목 |
| content | TEXT | 뉴스 본문 |
| url | TEXT | 뉴스 URL (UNIQUE) |
| published_date | TIMESTAMP | 뉴스 게시일 |
| sentiment_score | REAL | 감성 점수 (-1.0 ~ 1.0) |
| created_at | TIMESTAMP | 수집 일시 |
| source | TEXT | 출처 ('naver_finance' 또는 'google_news') |

## 감성 점수 해석

- **1.0 ~ 0.5**: VERY_POSITIVE (매우 긍정적)
- **0.5 ~ 0.2**: POSITIVE (긍정적)
- **0.2 ~ -0.2**: NEUTRAL (중립)
- **-0.2 ~ -0.5**: NEGATIVE (부정적)
- **-0.5 ~ -1.0**: VERY_NEGATIVE (매우 부정적)

## 테스트

```bash
# 전체 테스트 실행
python test_news_sentiment.py
```

## 주의사항

1. **Rate Limiting**: 네이버 금융 크롤링 시 1초 간격으로 요청합니다.
2. **robots.txt**: 웹사이트의 크롤링 정책을 준수합니다.
3. **중복 방지**: URL 기준으로 중복 뉴스는 자동으로 필터링됩니다.
4. **오류 처리**: 뉴스를 찾지 못하거나 네트워크 오류 시 빈 결과를 반환합니다.

## 감성 분석 키워드

### 한국어 긍정 키워드 (예시)
- 상승, 급등, 강세, 호조, 성장, 증가, 개선, 회복
- 흑자, 이익, 수익, 호실적, 기대이상
- 낙관, 긍정, 기대, 호재
- 투자증가, 제휴, 수주

### 한국어 부정 키워드 (예시)
- 하락, 급락, 폭락, 약세, 부진, 감소, 악화
- 적자, 손실, 실적부진, 기대이하
- 비관, 우려, 위기, 악재
- 구조조정, 감원, 수출감소

### 영어 긍정/부정 키워드
- 파일 참조: `src/analyzers/sentiment_analyzer.py`

## 확장 가능성

### KoBERT 통합 (선택사항)

더 정교한 한국어 감성 분석을 위해 KoBERT를 통합할 수 있습니다:

```python
# requirements.txt에 추가
# transformers>=4.30.0
# torch>=2.0.0

# sentiment_analyzer.py에 KoBERT 모델 추가
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch

class SentimentAnalyzer:
    def __init__(self):
        # KoBERT 모델 로드 (선택사항)
        self.kobert_tokenizer = AutoTokenizer.from_pretrained("monologg/kobert")
        self.kobert_model = AutoModelForSequenceClassification.from_pretrained(
            "monologg/kobert-sentiment"
        )

    def analyze_korean_text_with_kobert(self, text):
        inputs = self.kobert_tokenizer(text, return_tensors="pt", truncation=True)
        outputs = self.kobert_model(**inputs)
        # ... 감성 점수 계산
```

## 문제 해결

### 네이버 금융 뉴스 수집 실패
- 네이버 금융 웹사이트 구조가 변경되었을 수 있습니다.
- `use_naver=False`로 설정하고 Google News만 사용하세요.

### Google News RSS 수집 실패
- 인터�트 연결을 확인하세요.
- VPN 사용 시 비활성화해보세요.

### 감성 분석 점수가 항상 0
- 뉴스 본문이 비어있거나 키워드가 없을 수 있습니다.
- 뉴스 수집 시 본문도 함께 수집되는지 확인하세요.

## 참고 문서

- [BeautifulSoup Documentation](https://www.crummy.com/software/BeautifulSoup/bs4/doc/)
- [feedparser Documentation](https://feedparser.readthedocs.io/)
- [VADER Sentiment Analysis](https://github.com/cjhutto/vaderSentiment)
