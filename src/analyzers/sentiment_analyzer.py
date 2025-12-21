"""
뉴스 및 텍스트 감성 분석 모듈
"""
from typing import List, Dict, Optional
import re

try:
    from textblob import TextBlob
    TEXTBLOB_AVAILABLE = True
except ImportError:
    TEXTBLOB_AVAILABLE = False

class SentimentAnalyzer:
    """텍스트 감성 분석기"""
    
    def __init__(self):
        """초기화"""
        pass
        
    def analyze_sentiment(self, text: str) -> float:
        """
        텍스트의 감성 점수를 계산합니다.
        
        Args:
            text: 분석할 텍스트
            
        Returns:
            -1.0 (부정) ~ 1.0 (긍정) 사이의 실수
        """
        if not text:
            return 0.0
            
        # 1. 텍스트 정제
        clean_text = self._clean_text(text)
        
        # 2. TextBlob을 이용한 기초 분석 (영어에 강함)
        score = 0.0
        if TEXTBLOB_AVAILABLE:
            try:
                blob = TextBlob(clean_text)
                score = blob.sentiment.polarity
            except:
                pass
        
        # 3. 한국어 금융 키워드 보정 (간단한 규칙)
        # TextBlob은 한국어 지원이 약하므로, 명시적인 키워드로 점수 보정
        korean_score = self._analyze_korean_keywords(clean_text)
        
        # 영어 분석 결과와 한국어 키워드 분석 결과 결합
        # 한국어 키워드가 발견되면 우선순위를 둠
        if korean_score != 0:
            final_score = (score + korean_score) / 2
            # 범위 제한
            return max(-1.0, min(1.0, final_score))
            
        return score
    
    def _clean_text(self, text: str) -> str:
        """텍스트 정제"""
        # HTML 태그 제거
        text = re.sub(r'<[^>]+>', '', text)
        # 특수문자 제거 (일부 보존)
        text = re.sub(r'[^\w\s\.\,\%\-\+]', ' ', text)
        return text.strip()
        
    def _analyze_korean_keywords(self, text: str) -> float:
        """한국어 금융 키워드 기반 감성 분석"""
        positive_keywords = [
            '상승', '급등', '최고가', '호재', '성장', '이익', '수익', '개선', '돌파', 
            '매수', '긍정', '기대', '확대', '회복', '강세', '체결', '수주', '배당'
        ]
        negative_keywords = [
            '하락', '급락', '최저가', '악재', '손실', '적자', '감소', '이탈', 
            '매도', '부정', '우려', '축소', '둔화', '약세', '해지', '취소', '불확실'
        ]
        
        score = 0.0
        for word in positive_keywords:
            if word in text:
                score += 0.3
        
        for word in negative_keywords:
            if word in text:
                score -= 0.3
                
        return max(-1.0, min(1.0, score))

    def analyze_news_list(self, news_list: List[Dict]) -> List[Dict]:
        """
        뉴스 리스트의 감성을 분석하여 점수를 추가합니다.
        
        Args:
            news_list: 뉴스 딕셔너리 리스트
            
        Returns:
            감성 점수가 추가된 뉴스 리스트
        """
        for news in news_list:
            # 제목과 본문을 합쳐서 분석 가중치 조절
            title = news.get('title', '')
            content = news.get('content', '')
            
            # 제목에 가중치 2배
            full_text = f"{title} {title} {content}"
            sentiment = self.analyze_sentiment(full_text)
            
            news['sentiment_score'] = sentiment
            news['sentiment_label'] = 'positive' if sentiment > 0.1 else ('negative' if sentiment < -0.1 else 'neutral')
            
        return news_list