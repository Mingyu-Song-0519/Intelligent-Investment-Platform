"""
뉴스 및 텍스트 감성 분석 모듈
Phase F: LLMSentimentAnalyzer (Gemini) 통합
"""
from typing import List, Dict, Optional
import re

try:
    from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification
    import torch
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False

try:
    from textblob import TextBlob
    TEXTBLOB_AVAILABLE = True
except ImportError:
    TEXTBLOB_AVAILABLE = False

try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer as VaderAnalyzer
    VADER_AVAILABLE = True
except ImportError:
    VADER_AVAILABLE = False

# Phase F: LLM Sentiment Analyzer (Gemini)
try:
    from src.infrastructure.sentiment.llm_sentiment_analyzer import LLMSentimentAnalyzer
    LLM_SENTIMENT_AVAILABLE = True
except ImportError:
    LLM_SENTIMENT_AVAILABLE = False

class SentimentAnalyzer:
    """
    텍스트 감성 분석기
    
    지원 모드:
    - 기본: 키워드 + TextBlob
    - 딥러닝: KR-FinBert-SC
    - LLM: Gemini API (Phase F)
    """
    
    def __init__(self, use_deep_learning: bool = False, use_llm: bool = False):
        """
        초기화
        Args:
            use_deep_learning: 딥러닝 모델(FinBERT) 사용 여부
            use_llm: Gemini LLM 감성 분석 사용 여부 (Phase F)
        """
        self.use_deep_learning = use_deep_learning
        self.use_llm = use_llm
        self.dl_model = None
        self.dl_tokenizer = None
        self.dl_pipeline = None
        self.vader_analyzer = None
        self.llm_analyzer = None
        
        # VADER 분석기 초기화 (영문용)
        if VADER_AVAILABLE:
            self.vader_analyzer = VaderAnalyzer()
        
        # LLM 분석기 초기화 (Gemini) - 중앙화된 API 키 사용
        if use_llm and LLM_SENTIMENT_AVAILABLE:
            try:
                # Phase F: 중앙화된 API 키 사용 (LLMClientFactory)
                from src.infrastructure.external.llm_client_factory import LLMClientFactory
                gemini_client = LLMClientFactory.create_gemini_client()
                
                # GeminiClient인지 확인 (MockLLMClient가 아닌지)
                from src.infrastructure.external.gemini_client import GeminiClient
                if isinstance(gemini_client, GeminiClient) and gemini_client.is_available():
                    self.llm_analyzer = LLMSentimentAnalyzer(llm_client=gemini_client)
                    print("[INFO] Gemini LLM 감성 분석기 초기화 완료")
                else:
                    print("[WARNING] Gemini API 키가 설정되지 않았습니다. 사이드바 '🔑 AI API 설정'에서 입력해주세요.")
                    self.use_llm = False
            except Exception as e:
                print(f"[WARNING] LLM 분석기 초기화 실패: {e}. 기본 분석 사용.")
                self.use_llm = False
        elif use_llm and not LLM_SENTIMENT_AVAILABLE:
            print("[WARNING] LLMSentimentAnalyzer를 불러올 수 없습니다. 기본 분석 사용.")
            self.use_llm = False
        
        if use_deep_learning:
            self._load_dl_model()
        
    def _load_dl_model(self):
        """딥러닝 모델 로드 (KR-FinBert-SC)"""
        if not TRANSFORMERS_AVAILABLE:
            print("[WARNING] transformers 라이브러리가 설치되지 않았습니다. 기본 분석을 사용합니다.")
            self.use_deep_learning = False
            return

        try:
            print("[INFO] 딥러닝 감성 분석 모델 로드 중... (snunlp/KR-FinBert-SC)")
            # GPU 사용 가능 여부 확인
            device = 0 if torch.cuda.is_available() else -1
            
            # 파이프라인 생성
            self.dl_pipeline = pipeline(
                "sentiment-analysis",
                model="snunlp/KR-FinBert-SC",
                tokenizer="snunlp/KR-FinBert-SC",
                device=device
            )
            print(f"[INFO] 모델 로드 완료 (Device: {'GPU' if device==0 else 'CPU'})")
        except Exception as e:
            print(f"[ERROR] 모델 로드 실패: {e}")
            self.use_deep_learning = False

    def analyze_text_llm(self, text: str) -> tuple:
        """
        LLM(Gemini) 기반 감성 분석
        
        Returns:
            tuple: (점수, 상세정보 dict)
        """
        if not self.llm_analyzer:
            return self.analyze_text(text)
        
        try:
            result = self.llm_analyzer.analyze(text)
            # SentimentResult 속성: score, confidence, source, keywords
            return result.score, {
                'keywords': result.keywords,
                'confidence': result.confidence,
                'source': result.source
            }
        except Exception as e:
            print(f"[WARNING] LLM 감성 분석 실패: {e}. 기본 분석 사용.")
            return self.analyze_text(text)

    def analyze_text(self, text: str) -> tuple:
        """기본 감성 분석 (키워드/TextBlob) - 한국어용"""
        score = self.analyze_sentiment(text)
        return score, {}

    def analyze_text_en(self, text: str) -> tuple:
        """영문 텍스트 감성 분석 (VADER 기반)"""
        if not text:
            return 0.0, {}
        
        try:
            # VADER 분석기 사용 (영문에 최적화)
            if self.vader_analyzer:
                scores = self.vader_analyzer.polarity_scores(text)
                # compound 점수: -1.0 ~ 1.0
                compound = scores['compound']
                
                # 레이블 결정
                if compound >= 0.05:
                    label = 'positive'
                elif compound <= -0.05:
                    label = 'negative'
                else:
                    label = 'neutral'
                
                return compound, {
                    'label': label,
                    'positive': scores['pos'],
                    'negative': scores['neg'],
                    'neutral': scores['neu']
                }
            
            # VADER 사용 불가 시 TextBlob 폴백
            elif TEXTBLOB_AVAILABLE:
                blob = TextBlob(text)
                polarity = blob.sentiment.polarity
                
                if polarity > 0.1:
                    label = 'positive'
                elif polarity < -0.1:
                    label = 'negative'
                else:
                    label = 'neutral'
                    
                return polarity, {'label': label}
            
            # 둘 다 없으면 0 반환
            return 0.0, {'label': 'neutral'}
            
        except Exception as e:
            print(f"[ERROR] 영문 감성 분석 중 오류: {e}")
            return 0.0, {'label': 'neutral'}

    def analyze_text_deep(self, text: str) -> tuple:
        """딥러닝 감성 분석"""
        if not self.use_deep_learning or not self.dl_pipeline:
            return self.analyze_text(text)
            
        try:
            # 텍스트 길이 제한 (FinBERT는 512 토큰 제한)
            # 대략적인 문자 수로 자름 (토크나이저 속도 최적화)
            if len(text) > 1000:
                text = text[:1000]
                
            result = self.dl_pipeline(text)[0]
            # result 예시: {'label': 'positive', 'score': 0.99}
            # KR-FinBert-SC labels: positive, negative, neutral
            
            label = result['label']
            confidence = result['score']
            
            # 점수 변환 (-1.0 ~ 1.0)
            score = 0.0
            if label == 'positive':
                score = confidence
            elif label == 'negative':
                score = -confidence
            else: # neutral
                score = 0.0
                
            return score, {'label': label, 'confidence': confidence}
            
        except Exception as e:
            print(f"[ERROR] 딥러닝 분석 중 오류: {e}")
            return self.analyze_text(text)
        
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
            except Exception:
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