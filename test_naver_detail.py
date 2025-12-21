import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin

url = 'https://finance.naver.com/item/news_news.naver?code=005930&page=1&sm=title_entity_id.basic&clusterId='
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Referer': 'https://finance.naver.com/item/news.naver?code=005930'
}

print(f"Main URL: {url}")
res = requests.get(url, headers=headers)
soup = BeautifulSoup(res.content, 'html.parser')

items = soup.select('.tb_cont .title')
print(f"List items: {len(items)}")

if items:
    link_tag = items[0].find('a')
    if not link_tag:
        # .title 자체가 a 태그일 수도
        if items[0].name == 'a':
            link_tag = items[0]
    
    if link_tag:
        link = link_tag.get('href')
        full_link = urljoin('https://finance.naver.com', link)
        print(f"Detail URL: {full_link}")
        
        res_d = requests.get(full_link, headers=headers)
        soup_d = BeautifulSoup(res_d.content, 'html.parser')
        
        # 1. 기존 셀렉터
        date1 = soup_d.select_one('.article_info .date')
        content1 = soup_d.select_one('#articleBodyContents')
        print(f"Method 1 (Old Finance): Date={'Found' if date1 else 'None'}, Content={'Found' if content1 else 'None'}")
        
        # 2. n.news.naver.com 스타일
        date2 = soup_d.select_one('.media_end_head_info_datestamp')
        content2 = soup_d.select_one('#dic_area')
        print(f"Method 2 (n.news): Date={'Found' if date2 else 'None'}, Content={'Found' if content2 else 'None'}")
        
        # 3. title 확인
        print(f"Title: {soup_d.title.string.strip() if soup_d.title else 'No Title'}")

    else:
        print("Link tag not found in item")
else:
    print("No items found")
