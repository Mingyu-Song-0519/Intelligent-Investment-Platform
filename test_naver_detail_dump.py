import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# 리스트 페이지 (수정된 URL)
url = 'https://finance.naver.com/item/news_news.naver?code=005930&page=1&sm=title_entity_id.basic&clusterId='
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Referer': 'https://finance.naver.com/item/news.naver?code=005930'
}

print(f"List URL: {url}")
res = requests.get(url, headers=headers)
soup = BeautifulSoup(res.content, 'html.parser')

items = soup.select('.tb_cont .title')
print(f"Items found: {len(items)}")

if items:
    # 링크 찾기
    item = items[0]
    link_tag = item if item.name == 'a' else item.find('a')
    
    if link_tag:
        link = link_tag.get('href')
        if link.startswith('/'):
            link = urljoin('https://finance.naver.com', link)
        
        print(f"Detail Link: {link}")
        
        # 상세 페이지 요청
        try:
            res_d = requests.get(link, headers=headers, timeout=10)
            print(f"Detail Status: {res_d.status_code}")
            print(f"Final URL: {res_d.url}") # 리디렉션 확인
            
            # HTML 저장
            with open('naver_detail_dump.html', 'wb') as f:
                f.write(res_d.content)
            print("Saved naver_detail_dump.html")
            
        except Exception as e:
            print(f"Error fetching detail: {e}")
    else:
        print("No link tag found")
else:
    print("No items found")
