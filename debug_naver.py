import sys
import os
sys.path.insert(0, os.getcwd())

from src.collectors.news_collector import NewsCollector

print("=== Naver News Collector Debug ===")
collector = NewsCollector()
try:
    news = collector.fetch_naver_finance_news("005930")
    print(f"\nResult: {len(news)} items fetched.")
    if news:
        print(f"First item: {news[0].get('title', 'No Title')} / Date: {news[0].get('date', 'No Date')}")
        print(f"Content length: {len(news[0].get('content', ''))}")
except Exception as e:
    print(f"\nException occurred: {e}")
    import traceback
    traceback.print_exc()
