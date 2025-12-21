# 주식 시장 동향 분석 및 주가 예측 프로그램
# Stock Market Analysis & Prediction System

## 프로젝트 개요
국내외 주식 시장 데이터를 수집·분석하고, AI 모델을 통해 주가를 예측하며, 
Streamlit 웹 대시보드로 시각화하는 종합 금융 분석 시스템

## 프로젝트 구조
```
D:\Stock\
├── data/              # 원시 데이터 저장
├── processed/         # 가공된 데이터
├── models/            # 학습된 모델 파일
├── notebooks/         # 탐색적 분석 노트북
├── src/
│   ├── collectors/    # 데이터 수집 모듈
│   ├── analyzers/     # 기술적 분석 모듈
│   ├── models/        # AI 예측 모델
│   └── dashboard/     # Streamlit UI
├── config.py          # 설정 파일
├── requirements.txt   # 의존성 패키지
└── app.py             # 메인 진입점
```

## 설치 방법
```bash
pip install -r requirements.txt
```

## 실행 방법
```bash
streamlit run app.py
```

## 주요 기능
- 📊 실시간 주가 데이터 수집 (Yahoo Finance)
- 📈 기술적 지표 자동 계산 (RSI, MACD, 볼린저밴드)
- 🤖 AI 주가 예측 (LSTM, XGBoost)
- 📰 뉴스 수집 및 감성 분석 (네이버 금융, Google News)
- 💬 한국어/영어 감성 분석 (키워드 기반)
- 📱 웹 대시보드 시각화 (Streamlit)

## 새로운 기능: 뉴스 감성 분석

### 뉴스 수집
- 네이버 금융 뉴스 크롤링 (BeautifulSoup)
- Google News RSS 피드 수집 (feedparser)
- 종목별 뉴스 자동 분류 및 저장

### 감성 분석
- 한국어 감성 분석 (긍정/부정 키워드 사전 기반)
- 영어 감성 분석 (VADER 스타일)
- 감성 점수: -1.0 (매우 부정) ~ 1.0 (매우 긍정)
- 감성 요약 통계 제공

### 사용 예제
```python
from src.collectors import NewsCollector
from src.analyzers import SentimentAnalyzer

# 뉴스 수집
collector = NewsCollector()
collector.collect_and_save(ticker="005930.KS", company_name="삼성전자")

# 감성 분석
analyzer = SentimentAnalyzer()
analyzer.analyze_all_news(ticker="005930.KS")

# 결과 확인
summary = analyzer.get_sentiment_summary("005930.KS", days=7)
print(f"평균 감성: {summary['avg_sentiment']:.3f}")
```

자세한 사용법은 [NEWS_SENTIMENT_USAGE.md](NEWS_SENTIMENT_USAGE.md) 파일을 참고하세요.
