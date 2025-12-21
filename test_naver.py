import requests
from bs4 import BeautifulSoup

url = 'https://finance.naver.com/item/news_news.naver?code=005930&page=1&sm=title_entity_id.basic&clusterId='
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Referer': 'https://finance.naver.com/item/news.naver?code=005930'
}

print(f"URL: {url}")
res = requests.get(url, headers=headers)
print(f"Status: {res.status_code}")

soup = BeautifulSoup(res.content, 'html.parser')

items = soup.select('.tb_cont .title')
print(f"Items (.tb_cont .title): {len(items)}")

items2 = soup.select('.tit')
print(f"Items (.tit): {len(items2)}")

links = soup.select('a.tit')
print(f"Items (a.tit): {len(links)}")

# 테이블 확인
tables = soup.select('table')
print(f"Tables: {len(tables)}")
