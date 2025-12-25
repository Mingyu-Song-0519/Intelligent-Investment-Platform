"""
News Repository - Infrastructure Layer
INewsRepository 인터페이스의 구현체
"""
import requests
from bs4 import BeautifulSoup
import feedparser
from typing import List, Dict, Optional
from datetime import datetime
import time
from urllib.parse import quote, urljoin

from src.domain.repositories.interfaces import INewsRepository


class NaverNewsRepository(INewsRepository):
    """
    네이버 금융 뉴스 Repository 구현체
    
    기존 NewsCollector의 네이버 크롤링 로직 이관
    """
    
    def __init__(self, request_delay: float = 1.0):
        """
        Args:
            request_delay: 요청 간 대기 시간 (초)
        """
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.request_delay = request_delay
    
    def get_news(
        self, 
        keyword: str, 
        max_results: int = 10,
        language: str = "ko"
    ) -> List[Dict]:
        """네이버 금융 뉴스 검색"""
        
        if language != "ko":
            # 한국어가 아니면 빈 리스트 반환
            return []
        
        news_list = []
        max_pages = max(1, max_results // 10)
        
        try:
            # 종목 코드 정리 (.KS 등 제거)
            clean_keyword = keyword.split('.')[0]
            
            for page in range(1, max_pages + 1):
                url = f"https://finance.naver.com/item/news_news.naver?code={clean_keyword}&page={page}"
                
                headers = {
                    'Referer': f'https://finance.naver.com/item/news.naver?code={clean_keyword}'
                }
                
                response = self.session.get(url, headers=headers, timeout=10)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.content, 'html.parser')
                news_items = soup.select('.tb_cont .title')
                
                if not news_items:
                    break
                
                for item in news_items:
                    try:
                        link_tag = item if item.name == 'a' else item.find('a')
                        if not link_tag:
                            continue
                        
                        link = link_tag.get('href', '')
                        if not link:
                            continue
                        
                        if link.startswith('/'):
                            link = urljoin('https://finance.naver.com', link)
                        
                        title = item.get_text(strip=True)
                        
                        news_list.append({
                            'title': title,
                            'url': link,
                            'date': datetime.now().isoformat(),
                            'content': '',
                            'source': 'naver'
                        })
                        
                        if len(news_list) >= max_results:
                            break
                            
                    except Exception as e:
                        print(f"[ERROR] 뉴스 파싱 실패: {e}")
                        continue
                
                if len(news_list) >= max_results:
                    break
                
                # Rate limiting
                time.sleep(self.request_delay)
            
            return news_list[:max_results]
            
        except Exception as e:
            print(f"[ERROR] NaverNewsRepository.get_news: {e}")
            return []
    
    def get_stock_news(
        self, 
        ticker: str, 
        max_results: int = 10
    ) -> List[Dict]:
        """종목 관련 뉴스 검색"""
        return self.get_news(ticker, max_results, language="ko")


class GoogleNewsRepository(INewsRepository):
    """
    Google News RSS Repository 구현체
    """
    
    def __init__(self):
        """Google News RSS 초기화"""
        pass
    
    def get_news(
        self, 
        keyword: str, 
        max_results: int = 10,
        language: str = "ko"
    ) -> List[Dict]:
        """Google News RSS로 뉴스 검색"""
        
        try:
            # 언어별 RSS URL
            if language == "ko":
                base_url = "https://news.google.com/rss/search?q="
                encoded_keyword = quote(keyword)
                url = f"{base_url}{encoded_keyword}&hl=ko&gl=KR&ceid=KR:ko"
            else:
                base_url = "https://news.google.com/rss/search?q="
                encoded_keyword = quote(keyword)
                url = f"{base_url}{encoded_keyword}&hl=en-US&gl=US&ceid=US:en"
            
            # RSS 파싱
            feed = feedparser.parse(url)
            
            news_list = []
            for entry in feed.entries[:max_results]:
                news_list.append({
                    'title': entry.get('title', ''),
                    'url': entry.get('link', ''),
                    'date': entry.get('published', datetime.now().isoformat()),
                    'content': entry.get('summary', ''),
                    'source': 'google'
                })
            
            return news_list
            
        except Exception as e:
            print(f"[ERROR] GoogleNewsRepository.get_news: {e}")
            return []
    
    def get_stock_news(
        self, 
        ticker: str, 
        max_results: int = 10
    ) -> List[Dict]:
        """종목 관련 뉴스 검색"""
        # 티커를 종목명으로 변환하거나 그대로 사용
        return self.get_news(ticker, max_results, language="en")
