"""
뉴스 수집 모듈 - 네이버 금융 뉴스 및 Google News RSS 피드 수집
"""
import requests
from bs4 import BeautifulSoup
import feedparser
import sqlite3
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from pathlib import Path
import sys
from urllib.parse import quote, urljoin
import re

# 프로젝트 루트 경로 설정
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config import DATABASE_PATH


class NewsCollector:
    """뉴스 수집 클래스 - 네이버 금융 뉴스 및 Google News RSS 피드 수집"""

    def __init__(self, db_path: Optional[Path] = None):
        """
        Args:
            db_path: SQLite 데이터베이스 경로 (기본값: config의 DATABASE_PATH)
        """
        self.db_path = db_path or DATABASE_PATH
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self._init_database()
        self.request_delay = 1.0  # Rate limiting: 1초 대기

    def _init_database(self):
        """데이터베이스 및 뉴스 테이블 초기화"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # 뉴스 테이블 생성
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS news (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticker TEXT NOT NULL,
                    title TEXT NOT NULL,
                    content TEXT,
                    url TEXT UNIQUE,
                    published_date TIMESTAMP,
                    sentiment_score REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    source TEXT
                )
            """)

            # 인덱스 생성
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_ticker_published
                ON news(ticker, published_date DESC)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_url
                ON news(url)
            """)

            conn.commit()

    def fetch_naver_finance_news(
        self,
        ticker: str,
        max_pages: int = 3
    ) -> List[Dict]:
        """
        네이버 금융 뉴스를 크롤링합니다.

        Args:
            ticker: 종목 코드 (예: '005930' - .KS 제외)
            max_pages: 수집할 최대 페이지 수

        Returns:
            뉴스 리스트 [{'title': ..., 'url': ..., 'date': ..., 'content': ...}, ...]
        """
        news_list = []

        # 종목 코드에서 .KS, .KQ 등 제거
        clean_ticker = ticker.split('.')[0]

        try:
            for page in range(1, max_pages + 1):
                # 네이버 금융 뉴스 URL (파라미터 추가)
                url = f"https://finance.naver.com/item/news_news.naver?code={clean_ticker}&page={page}&sm=title_entity_id.basic&clusterId="

                print(f"[INFO] 네이버 금융 뉴스 수집 중... (페이지 {page}/{max_pages})")

                # Referer 헤더 추가 (필수)
                headers = {
                    'Referer': f'https://finance.naver.com/item/news.naver?code={clean_ticker}'
                }
                response = self.session.get(url, headers=headers, timeout=10)
                response.raise_for_status()
                response.encoding = 'utf-8'  # 명시적 UTF-8 인코딩

                soup = BeautifulSoup(response.content, 'html.parser')

                # 뉴스 아이템 찾기
                news_items = soup.select('.tb_cont .title')

                if not news_items:
                    print(f"[INFO] {page}페이지에서 뉴스를 찾을 수 없습니다.")
                    # 디버깅: 왜 못 찾는지 HTML 확인
                    try:
                        with open(f"failed_page_{page}.html", "wb") as f:
                            f.write(response.content)
                        print(f"[DEBUG] failed_page_{page}.html 저장됨")
                    except:
                        pass
                    break

                # 제목 유사도 체크를 위한 기존 제목 세트
                collected_titles = [item['title'] for item in news_list]
                
                for item in news_items:
                    try:
                        # 링크 태그 찾기 (a 태그 자체이거나 자식 a 태그)
                        link_tag = item if item.name == 'a' else item.find('a')
                        
                        if not link_tag:
                            continue

                        link = link_tag.get('href', '')
                        if not link:
                            continue

                        # 절대 URL로 변환
                        if link.startswith('/'):
                            link = urljoin('https://finance.naver.com', link)

                        title = item.get_text(strip=True)
                        
                        # 중복 체크
                        is_duplicate = False
                        title_words = set(title.lower().split())
                        
                        for existing_title in collected_titles:
                            existing_words = set(existing_title.lower().split())
                            if not title_words or not existing_words:
                                continue
                            # Jaccard 유사도
                            intersection = len(title_words & existing_words)
                            union = len(title_words | existing_words)
                            similarity = intersection / union if union > 0 else 0
                            
                            if similarity >= 0.4:
                                is_duplicate = True
                                break
                        
                        if is_duplicate:
                            continue
                        
                        # 제목만 저장 (상세 페이지 접속 생략으로 속도 개선)
                        news_item = {
                            'title': title,
                            'url': link,
                            'date': None,  # 상세 수집 없이는 날짜 확인 불가
                            'content': '',  # 본문 없음
                            'source': 'naver_finance'
                        }

                        news_list.append(news_item)
                        collected_titles.append(title)

                    except Exception as e:
                        print(f"[ERROR] 뉴스 아이템 처리 실패: {e}")
                        continue

                # 페이지 간 Rate limiting (목록 요청만)
                time.sleep(0.5)

        except Exception as e:
            print(f"[ERROR] 네이버 금융 뉴스 수집 실패: {e}")

        print(f"[INFO] 네이버 금융에서 {len(news_list)}개 뉴스 수집 완료")
        return news_list

    def _fetch_naver_news_detail(self, url: str) -> Dict:
        """
        네이버 뉴스 상세 정보를 가져옵니다.

        Args:
            url: 뉴스 URL

        Returns:
            {'date': ..., 'content': ...}
        """
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # JS 리디렉션 감지 및 처리 (top.location.href)
            if "top.location.href" in str(soup):
                match = re.search(r"top\.location\.href='([^']+)'", str(soup))
                if match:
                    redirect_url = match.group(1)
                    # 리디렉션 URL로 재요청
                    response = self.session.get(redirect_url, timeout=10)
                    response.raise_for_status()
                    soup = BeautifulSoup(response.content, 'html.parser')

            # 날짜 추출 (여러 패턴 시도)
            date_str = None
            date_elem = soup.select_one('.article_info .date') # 금융 뉴스 구버전
            if not date_elem:
                date_elem = soup.select_one('.media_end_head_info_datestamp') # 네이버 뉴스 공통
            if not date_elem:
                date_elem = soup.select_one('.t11') # 옛날 네이버 뉴스
                
            if date_elem:
                date_text = date_elem.get_text(strip=True)
                # "2024.01.15 10:30" 형식에서 날짜 추출
                date_str = self._parse_date(date_text)

            # 본문 추출 (여러 패턴 시도)
            content = ''
            content_elem = soup.select_one('#articleBodyContents')
            if not content_elem:
                content_elem = soup.select_one('#dic_area') # 네이버 뉴스 공통
            if not content_elem:
                content_elem = soup.select_one('#newsEndContents') # 연예/스포츠 등
            if not content_elem:
                content_elem = soup.select_one('.article_body')
                
            if content_elem:
                # 불필요한 태그 제거
                for tag in content_elem.select('script, style, .link_news, .guide_txt'):
                    tag.decompose()
                content = content_elem.get_text(strip=True)
                # 공백 정리
                content = re.sub(r'\s+', ' ', content)

            return {
                'date': date_str,
                'content': content[:1000] if content else ''  # 최대 1000자
            }

        except Exception as e:
            print(f"[ERROR] 뉴스 상세 정보 수집 실패: {e}")
            return {'date': None, 'content': ''}

    def fetch_google_news_rss(
        self,
        query: str,
        max_items: int = 20
    ) -> List[Dict]:
        """
        Google News RSS 피드에서 뉴스를 수집합니다.

        Args:
            query: 검색 키워드 (예: 'Samsung Electronics' 또는 '삼성전자')
            max_items: 수집할 최대 뉴스 수

        Returns:
            뉴스 리스트
        """
        news_list = []

        try:
            # Google News RSS URL
            encoded_query = quote(query)
            rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=ko&gl=KR&ceid=KR:ko"

            print(f"[INFO] Google News RSS 피드 수집 중... (검색어: {query})")

            # RSS 피드 파싱
            feed = feedparser.parse(rss_url)

            if not feed.entries:
                print(f"[INFO] Google News에서 '{query}' 관련 뉴스를 찾을 수 없습니다.")
                return news_list

            for entry in feed.entries[:max_items]:
                try:
                    title = entry.get('title', '')
                    link = entry.get('link', '')
                    published = entry.get('published', '')
                    summary = entry.get('summary', '')

                    # 날짜 파싱
                    date_str = self._parse_rss_date(published)

                    news_item = {
                        'title': title,
                        'url': link,
                        'date': date_str,
                        'content': summary[:1000] if summary else '',
                        'source': 'google_news'
                    }

                    news_list.append(news_item)

                except Exception as e:
                    print(f"[ERROR] RSS 아이템 처리 실패: {e}")
                    continue

            print(f"[INFO] Google News에서 {len(news_list)}개 뉴스 수집 완료")

        except Exception as e:
            print(f"[ERROR] Google News RSS 수집 실패: {e}")

        return news_list

    def fetch_yahoo_finance_news_rss(
        self,
        ticker: str,
        max_items: int = 30
    ) -> List[Dict]:
        """
        Yahoo Finance RSS 피드에서 종목별 영문 뉴스를 수집합니다.

        Args:
            ticker: 종목 심볼 (예: 'AAPL', 'TSLA')
            max_items: 수집할 최대 뉴스 수

        Returns:
            뉴스 리스트
        """
        news_list = []

        try:
            # Yahoo Finance RSS URL
            rss_url = f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={ticker}&region=US&lang=en-US"

            print(f"[INFO] Yahoo Finance RSS 피드 수집 중... (종목: {ticker})")

            # RSS 피드 파싱
            feed = feedparser.parse(rss_url)

            if not feed.entries:
                print(f"[INFO] Yahoo Finance에서 '{ticker}' 관련 뉴스를 찾을 수 없습니다.")
                return news_list

            for entry in feed.entries[:max_items]:
                try:
                    title = entry.get('title', '')
                    link = entry.get('link', '')
                    published = entry.get('published', '')
                    summary = entry.get('summary', '')

                    # 날짜 파싱
                    date_str = self._parse_rss_date(published)

                    news_item = {
                        'title': title,
                        'url': link,
                        'date': date_str,
                        'content': summary[:1000] if summary else '',
                        'source': 'yahoo_finance'
                    }

                    news_list.append(news_item)

                except Exception as e:
                    print(f"[ERROR] Yahoo RSS 아이템 처리 실패: {e}")
                    continue

            print(f"[INFO] Yahoo Finance에서 {len(news_list)}개 뉴스 수집 완료")

        except Exception as e:
            print(f"[ERROR] Yahoo Finance RSS 수집 실패: {e}")

        return news_list

    def fetch_google_news_en_rss(
        self,
        query: str,
        max_items: int = 30
    ) -> List[Dict]:
        """
        Google News 영문 RSS 피드에서 뉴스를 수집합니다.

        Args:
            query: 검색 키워드 (예: 'Apple stock' 또는 'AAPL')
            max_items: 수집할 최대 뉴스 수

        Returns:
            뉴스 리스트
        """
        news_list = []

        try:
            # Google News 영문 RSS URL
            encoded_query = quote(query)
            rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-US&gl=US&ceid=US:en"

            print(f"[INFO] Google News (EN) RSS 피드 수집 중... (검색어: {query})")

            # RSS 피드 파싱
            feed = feedparser.parse(rss_url)

            if not feed.entries:
                print(f"[INFO] Google News (EN)에서 '{query}' 관련 뉴스를 찾을 수 없습니다.")
                return news_list

            for entry in feed.entries[:max_items]:
                try:
                    title = entry.get('title', '')
                    link = entry.get('link', '')
                    published = entry.get('published', '')
                    summary = entry.get('summary', '')

                    # 날짜 파싱
                    date_str = self._parse_rss_date(published)

                    news_item = {
                        'title': title,
                        'url': link,
                        'date': date_str,
                        'content': summary[:1000] if summary else '',
                        'source': 'google_news_en'
                    }

                    news_list.append(news_item)

                except Exception as e:
                    print(f"[ERROR] RSS 아이템 처리 실패: {e}")
                    continue

            print(f"[INFO] Google News (EN)에서 {len(news_list)}개 뉴스 수집 완료")

        except Exception as e:
            print(f"[ERROR] Google News (EN) RSS 수집 실패: {e}")

        return news_list

    def _parse_date(self, date_str: str) -> Optional[str]:
        """
        다양한 날짜 형식을 파싱하여 ISO 형식으로 변환합니다.

        Args:
            date_str: 날짜 문자열

        Returns:
            ISO 형식 날짜 문자열 또는 None
        """
        if not date_str:
            return None

        # 날짜 형식 패턴들
        patterns = [
            (r'(\d{4})\.(\d{1,2})\.(\d{1,2})\s+(\d{1,2}):(\d{2})', '%Y.%m.%d %H:%M'),
            (r'(\d{4})-(\d{2})-(\d{2})\s+(\d{2}):(\d{2})', '%Y-%m-%d %H:%M'),
            (r'(\d{4})\.(\d{1,2})\.(\d{1,2})', '%Y.%m.%d'),
            (r'(\d{4})-(\d{2})-(\d{2})', '%Y-%m-%d'),
        ]

        for pattern, date_format in patterns:
            match = re.search(pattern, date_str)
            if match:
                try:
                    # 숫자만 추출하여 날짜 파싱
                    clean_date = re.sub(r'[^\d\s:]', '-', match.group(0))
                    clean_date = re.sub(r'\s+', ' ', clean_date).strip()

                    # 날짜 파싱 시도
                    parsed_date = datetime.strptime(match.group(0), date_format)
                    return parsed_date.strftime('%Y-%m-%d %H:%M:%S')
                except:
                    continue

        # 파싱 실패 시 현재 시간 반환
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    def _parse_rss_date(self, date_str: str) -> Optional[str]:
        """
        RSS 날짜 형식을 파싱합니다.

        Args:
            date_str: RSS 날짜 문자열 (예: 'Mon, 15 Jan 2024 10:30:00 GMT')

        Returns:
            ISO 형식 날짜 문자열
        """
        if not date_str:
            return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        try:
            # feedparser의 parsed 값 사용
            from email.utils import parsedate_to_datetime
            dt = parsedate_to_datetime(date_str)
            return dt.strftime('%Y-%m-%d %H:%M:%S')
        except:
            return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    def save_news(self, ticker: str, news_list: List[Dict]) -> int:
        """
        수집된 뉴스를 데이터베이스에 저장합니다.

        Args:
            ticker: 종목 코드
            news_list: 뉴스 리스트

        Returns:
            저장된 뉴스 수
        """
        if not news_list:
            return 0

        saved_count = 0
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            for news in news_list:
                try:
                    cursor.execute("""
                        INSERT OR IGNORE INTO news
                        (ticker, title, content, url, published_date, source)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        ticker,
                        news.get('title', ''),
                        news.get('content', ''),
                        news.get('url', ''),
                        news.get('date'),
                        news.get('source', 'unknown')
                    ))

                    if cursor.rowcount > 0:
                        saved_count += 1

                except Exception as e:
                    print(f"[ERROR] 뉴스 저장 실패: {e}")
                    continue

            conn.commit()

        print(f"[INFO] {ticker}: {saved_count}개 뉴스 DB 저장 완료")
        return saved_count

    def collect_and_save(
        self,
        ticker: str,
        company_name: Optional[str] = None,
        use_naver: bool = True,
        use_google: bool = True,
        max_pages: int = 3,
        max_items: int = 20
    ) -> int:
        """
        뉴스를 수집하고 DB에 저장하는 통합 메서드

        Args:
            ticker: 종목 코드
            company_name: 회사명 (Google News 검색용)
            use_naver: 네이버 금융 뉴스 수집 여부
            use_google: Google News 수집 여부
            max_pages: 네이버 금융 최대 페이지 수
            max_items: Google News 최대 아이템 수

        Returns:
            총 저장된 뉴스 수
        """
        all_news = []

        # 네이버 금융 뉴스 수집
        if use_naver:
            naver_news = self.fetch_naver_finance_news(ticker, max_pages)
            all_news.extend(naver_news)

        # Google News 수집
        if use_google and company_name:
            google_news = self.fetch_google_news_rss(company_name, max_items)
            all_news.extend(google_news)

        # DB에 저장
        if all_news:
            return self.save_news(ticker, all_news)
        else:
            print(f"[INFO] {ticker}: 수집된 뉴스가 없습니다.")
            return 0

    def get_news(
        self,
        ticker: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict]:
        """
        DB에서 뉴스를 조회합니다.

        Args:
            ticker: 종목 코드
            start_date: 시작 날짜 (YYYY-MM-DD)
            end_date: 종료 날짜 (YYYY-MM-DD)
            limit: 최대 조회 수

        Returns:
            뉴스 리스트
        """
        query = "SELECT * FROM news WHERE ticker = ?"
        params = [ticker]

        if start_date:
            query += " AND published_date >= ?"
            params.append(start_date)

        if end_date:
            query += " AND published_date <= ?"
            params.append(end_date)

        query += " ORDER BY published_date DESC LIMIT ?"
        params.append(limit)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)

            columns = [desc[0] for desc in cursor.description]
            news_list = []

            for row in cursor.fetchall():
                news_dict = dict(zip(columns, row))
                news_list.append(news_dict)

        return news_list


# 사용 예시
if __name__ == "__main__":
    collector = NewsCollector()

    # 삼성전자 뉴스 수집 테스트
    print("=" * 80)
    print("삼성전자 뉴스 수집 테스트")
    print("=" * 80)

    total = collector.collect_and_save(
        ticker="005930.KS",
        company_name="삼성전자",
        use_naver=True,
        use_google=True,
        max_pages=2,
        max_items=10
    )

    print(f"\n총 {total}개 뉴스 저장됨")

    # DB에서 조회 테스트
    print("\n" + "=" * 80)
    print("DB 조회 테스트")
    print("=" * 80)

    news_list = collector.get_news("005930.KS", limit=5)
    for i, news in enumerate(news_list, 1):
        print(f"\n[{i}] {news['title']}")
        print(f"    URL: {news['url']}")
        print(f"    날짜: {news['published_date']}")
        print(f"    출처: {news['source']}")
