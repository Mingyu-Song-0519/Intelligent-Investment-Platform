"""
LLM Sentiment Analyzer
Clean Architecture: Infrastructure Layer

Gemini LLM을 활용한 고급 감성 분석
"""
import logging
import json
import re
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

from src.infrastructure.external.gemini_client import ILLMClient

logger = logging.getLogger(__name__)


@dataclass
class SentimentResult:
    """감성 분석 결과"""
    score: float  # -1.0 (부정) ~ 1.0 (긍정)
    confidence: float  # 0.0 ~ 1.0
    source: str  # 'llm', 'vader', 'keyword'
    keywords: list = None  # 감성 관련 키워드
    
    def __post_init__(self):
        if self.keywords is None:
            self.keywords = []
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'score': self.score,
            'confidence': self.confidence,
            'source': self.source,
            'keywords': self.keywords
        }


class LLMSentimentAnalyzer:
    """
    LLM 기반 감성 분석기
    
    Gemini를 사용하여 금융 뉴스/텍스트의 감성을 분석합니다.
    """
    
    SENTIMENT_PROMPT_TEMPLATE = """
JSON만 응답하세요. 다른 텍스트는 포함하지 마세요.
"""

    BATCH_TICKER_PROMPT_TEMPLATE = """
다음은 여러 주식 종목들의 최신 뉴스 헤드라인 목록입니다.
각 종목별로 뉴스 맥락을 분석하여 향후 주가에 미칠 영향(감성 점수)을 산출하세요.

점수 기준:
- 1.0: 매우 긍정 (강력한 호재, 어닝 서프라이즈, 대규모 수주 등)
- 0.5: 긍정 (일반적 호재, 양호한 실적 등)
- 0.0: 중립 (단순 사실 보도, 영향 미미)
- -0.5: 부정 (일반적 악재, 실적 하회 등)
- -1.0: 매우 부정 (강력한 악재, 횡령, 부도 위험 등)

분석 대상 프로젝트 데이터:
{ticker_data}

반드시 아래 JSON 형식으로만 답변하세요. 다른 설명은 생략하세요:
{{
  "TICKER_CODE_1": {{"score": 0.5, "reason": "핵심 긍정 요인 요약"}},
  "TICKER_CODE_2": {{"score": -0.3, "reason": "핵심 부정 요인 요약"}}
}}
"""
    
    def __init__(self, llm_client: ILLMClient):
        """
        Args:
            llm_client: ILLMClient 구현체 (GeminiClient 등)
        """
        self.llm_client = llm_client
    
    def analyze(self, text: str) -> SentimentResult:
        """
        텍스트 감성 분석
        
        Args:
            text: 분석할 텍스트
            
        Returns:
            SentimentResult
            
        Raises:
            Exception: LLM 호출 실패 시
        """
        if not text or len(text.strip()) < 10:
            return SentimentResult(score=0.0, confidence=0.0, source='llm')
        
        try:
            prompt = self.SENTIMENT_PROMPT_TEMPLATE.format(text=text[:1000])  # 길이 제한
            response = self.llm_client.generate(prompt)
            
            return self._parse_response(response)
            
        except Exception as e:
            logger.error(f"[LLMSentiment] Analysis failed: {e}")
            raise
    
    def analyze_batch(self, texts: list) -> list:
        """
        배치 감성 분석 (Rate Limiting 주의)
        
        Args:
            texts: 분석할 텍스트 리스트
            
        Returns:
            SentimentResult 리스트
        """
        results = []
        for text in texts:
            try:
                result = self.analyze(text)
                results.append(result)
            except Exception as e:
                logger.warning(f"[LLMSentiment] Batch item failed: {e}")
                results.append(SentimentResult(score=0.0, confidence=0.0, source='error'))
        
        return results

    def analyze_tickers_batch(self, ticker_headlines: Dict[str, List[str]]) -> Dict[str, Dict[str, Any]]:
        """
        여러 종목의 뉴스 헤드라인을 한 번에 분석 (Gemini Batch)
        
        Args:
            ticker_headlines: { '005930': ['뉴스1', '뉴스2'], ... }
            
        Returns:
            { '005930': {'score': 0.5, 'reason': '...'}, ... }
        """
        if not ticker_headlines:
            return {}
            
        try:
            # 텍스트 데이터 구성
            formatted_data = ""
            for ticker, headlines in ticker_headlines.items():
                headlines_str = "\n".join([f"- {h}" for h in headlines[:5]]) # 종목당 최대 5개 뉴스
                formatted_data += f"\n[{ticker}]\n{headlines_str}\n"

            prompt = self.BATCH_TICKER_PROMPT_TEMPLATE.format(ticker_data=formatted_data)
            response = self.llm_client.generate(prompt)
            
            # JSON 추출 및 파싱
            json_str = response.strip()
            if '```' in json_str:
                match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', json_str, re.DOTALL)
                if match:
                    json_str = match.group(1)
            
            result_data = json.loads(json_str)
            return result_data
            
        except Exception as e:
            logger.error(f"[LLMSentiment] Batch ticker analysis failed: {e}")
            return {}
    
    def _parse_response(self, response: str) -> SentimentResult:
        """LLM 응답 파싱"""
        try:
            # JSON 추출 (```json 블록 제거)
            json_str = response.strip()
            if '```' in json_str:
                match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', json_str, re.DOTALL)
                if match:
                    json_str = match.group(1)
            
            # JSON 파싱
            data = json.loads(json_str)
            
            score = float(data.get('score', 0))
            score = max(-1.0, min(1.0, score))  # 범위 제한
            
            confidence = float(data.get('confidence', 0.5))
            confidence = max(0.0, min(1.0, confidence))
            
            keywords = data.get('keywords', [])
            if not isinstance(keywords, list):
                keywords = []
            
            return SentimentResult(
                score=score,
                confidence=confidence,
                source='llm',
                keywords=keywords[:5]  # 최대 5개
            )
            
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"[LLMSentiment] Parse failed: {e}, response: {response[:100]}")
            return SentimentResult(score=0.0, confidence=0.0, source='llm_parse_error')


class VaderSentimentAnalyzer:
    """
    VADER 기반 감성 분석기 (Fallback용)
    
    영문 텍스트에 최적화되어 있으나, 한국어도 간단히 처리 가능
    """
    
    def __init__(self):
        try:
            from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
            self.analyzer = SentimentIntensityAnalyzer()
            self.available = True
        except ImportError:
            self.analyzer = None
            self.available = False
            logger.warning("[VaderSentiment] vaderSentiment not installed")
    
    def analyze(self, text: str) -> SentimentResult:
        """VADER 감성 분석"""
        if not self.available or not self.analyzer:
            return self._keyword_fallback(text)
        
        try:
            scores = self.analyzer.polarity_scores(text)
            compound = scores.get('compound', 0)
            
            return SentimentResult(
                score=compound,
                confidence=abs(compound),  # 절대값을 신뢰도로 사용
                source='vader'
            )
        except Exception as e:
            logger.warning(f"[VaderSentiment] Failed: {e}")
            return self._keyword_fallback(text)
    
    def _keyword_fallback(self, text: str) -> SentimentResult:
        """한국어 키워드 기반 감성 분석 (최종 Fallback)"""
        positive_keywords = [
            '상승', '호재', '증가', '성장', '개선', '호조', '수주', '상향',
            '긍정', '반등', '돌파', '신고가', '매수', '추천', '긍정적'
        ]
        negative_keywords = [
            '하락', '악재', '감소', '하향', '부진', '적자', '손실', '하락세',
            '부정', '폭락', '매도', '우려', '리스크', '위험', '부정적'
        ]
        
        text_lower = text.lower()
        positive_count = sum(1 for kw in positive_keywords if kw in text_lower)
        negative_count = sum(1 for kw in negative_keywords if kw in text_lower)
        
        total = positive_count + negative_count
        if total == 0:
            return SentimentResult(score=0.0, confidence=0.0, source='keyword')
        
        score = (positive_count - negative_count) / total
        confidence = min(total / 5, 1.0)  # 키워드가 많을수록 신뢰도 증가
        
        return SentimentResult(score=score, confidence=confidence, source='keyword')
