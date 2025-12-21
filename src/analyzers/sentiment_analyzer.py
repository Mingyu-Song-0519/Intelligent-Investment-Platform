"""
감성 분석 모듈 - 한국어 및 영어 뉴스 감성 분석
"""
import re
import sqlite3
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import sys

# 프로젝트 루트 경로 설정
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config import DATABASE_PATH


class SentimentAnalyzer:
    """뉴스 감성 분석 클래스 - 한국어 및 영어 감성 분석 (키워드 기반 + 딥러닝)"""

    def __init__(self, db_path: Optional[Path] = None, use_deep_learning: bool = False):
        """
        Args:
            db_path: SQLite 데이터베이스 경로 (기본값: config의 DATABASE_PATH)
            use_deep_learning: 딥러닝 모델 사용 여부 (기본값: False)
        """
        self.db_path = db_path or DATABASE_PATH
        self.use_deep_learning = use_deep_learning
        
        # 키워드 기반 사전 초기화
        self._init_korean_lexicon()
        self._init_english_lexicon()
        
        # 딥러닝 모델 (lazy loading)
        self._dl_model = None
        self._dl_tokenizer = None
        self._dl_device = None
    
    def _load_deep_learning_model(self):
        """딥러닝 모델 로드 (필요 시에만 로드) - PyTorch 백엔드"""
        if self._dl_model is not None:
            return
        
        try:
            import torch
            from transformers import AutoTokenizer, AutoModelForSequenceClassification
            
            print("[INFO] 딥러닝 감성 분석 모델 로딩 중...")
            
            # GPU 사용 여부 확인
            if torch.cuda.is_available():
                self._dl_device = "cuda"
                print(f"[INFO] GPU 사용: {torch.cuda.get_device_name(0)}")
            else:
                self._dl_device = "cpu"
                print("[INFO] CPU 모드로 실행")
            
            # 한국어 금융 감성 분석 모델 (snunlp/KR-FinBert-SC)
            model_name = "snunlp/KR-FinBert-SC"
            
            self._dl_tokenizer = AutoTokenizer.from_pretrained(model_name)
            self._dl_model = AutoModelForSequenceClassification.from_pretrained(model_name)
            self._dl_model.to(self._dl_device)
            self._dl_model.eval()
            
            print("[INFO] 딥러닝 모델 로드 완료!")
            
        except Exception as e:
            print(f"[ERROR] 딥러닝 모델 로드 실패: {e}")
            print("[INFO] 키워드 기반 분석으로 대체합니다.")
            self.use_deep_learning = False
    
    def analyze_text_deep(self, text: str) -> Tuple[float, Dict]:
        """
        딥러닝 모델을 사용한 감성 분석 (PyTorch 백엔드)
        
        Args:
            text: 분석할 텍스트
            
        Returns:
            (감성 점수, 상세 정보)
            감성 점수: -1.0 (매우 부정) ~ 1.0 (매우 긍정)
        """
        if not text or not text.strip():
            return 0.0, {'method': 'deep_learning', 'error': 'empty_text'}
        
        # 모델 로드 (lazy loading)
        self._load_deep_learning_model()
        
        if self._dl_model is None:
            # 모델 로드 실패 시 키워드 기반으로 대체
            return self.analyze_korean_text(text)
        
        try:
            import torch
            
            # 텍스트 토큰화
            inputs = self._dl_tokenizer(
                text,
                return_tensors="pt",
                truncation=True,
                max_length=512,
                padding=True
            )
            inputs = {k: v.to(self._dl_device) for k, v in inputs.items()}
            
            # 추론
            with torch.no_grad():
                outputs = self._dl_model(**inputs)
                logits = outputs.logits
                
                # Softmax로 확률 변환
                probs = torch.softmax(logits, dim=-1).cpu().numpy()[0]
            
            # KR-FinBert-SC: [부정, 중립, 긍정] 순서
            # 점수 계산: -1 * 부정 + 0 * 중립 + 1 * 긍정
            score = float(-1 * probs[0] + 0 * probs[1] + 1 * probs[2])
            
            return score, {
                'method': 'deep_learning',
                'model': 'KR-FinBert-SC',
                'device': self._dl_device,
                'probabilities': {
                    'negative': float(probs[0]),
                    'neutral': float(probs[1]),
                    'positive': float(probs[2])
                }
            }
            
        except Exception as e:
            print(f"[ERROR] 딥러닝 분석 실패: {e}")
            return self.analyze_korean_text(text)


    def _init_korean_lexicon(self):
        """한국어 감성 사전 초기화 (간단한 키워드 기반)"""

        # 긍정 키워드
        self.korean_positive = {
            # 상승 관련
            '상승', '급등', '강세', '호조', '성장', '증가', '개선', '회복',
            '확대', '신고가', '최고', '돌파', '상승세', '오름', '플러스',

            # 긍정적 실적
            '흑자', '이익', '수익', '실적호조', '호실적', '선방', '양호',
            '기대이상', '초과달성', '목표달성', '사상최대', '사상최고',

            # 긍정적 전망
            '낙관', '긍정', '기대', '유망', '전망밝', '희망', '청신호',
            '호재', '모멘텀', '활기', '탄력', '훈풍', '순풍',

            # 투자 관련
            '투자증가', '투자확대', '신규투자', '인수', '합병', '제휴',
            '협력', '파트너십', '계약체결', '수주', '수출증가',

            # 기타
            '혁신', '개발성공', '신제품', '점유율확대', '시장선도',
            '경쟁력강화', '수주증가', '매출증가', '주가상승'
        }

        # 부정 키워드
        self.korean_negative = {
            # 하락 관련
            '하락', '급락', '폭락', '약세', '부진', '감소', '악화', '위축',
            '축소', '신저가', '최저', '붕괴', '하락세', '내림', '마이너스',

            # 부정적 실적
            '적자', '손실', '실적부진', '악성적', '부진', '미달', '저조',
            '기대이하', '목표미달', '부진지속', '사상최저', '최악',

            # 부정적 전망
            '비관', '부정', '우려', '불안', '전망어둡', '위기', '적신호',
            '악재', '리스크', '위험', '침체', '불황', '역풍', '찬바람',

            # 투자 관련
            '투자감소', '투자축소', '투자중단', '철수', '구조조정',
            '감원', '정리해고', '부도', '파산', '수출감소',

            # 기타
            '실패', '개발실패', '리콜', '점유율하락', '경쟁심화',
            '경쟁력약화', '수주감소', '매출감소', '주가하락', '규제',
            '제재', '소송', '분쟁', '스캔들', '논란'
        }

        # 중립 키워드 (분석에서 제외)
        self.korean_neutral = {
            '발표', '공시', '예정', '계획', '검토', '진행', '지속',
            '유지', '보합', '변동없음', '동결'
        }

    def _init_english_lexicon(self):
        """영어 감성 사전 초기화 (VADER 간소화 버전)"""

        # 긍정 키워드
        self.english_positive = {
            # Market movements
            'surge', 'soar', 'rally', 'gain', 'rise', 'jump', 'climb',
            'advance', 'high', 'peak', 'breakthrough', 'bullish', 'upturn',

            # Performance
            'profit', 'revenue', 'earnings', 'outperform', 'beat',
            'exceed', 'record', 'best', 'strong', 'robust', 'solid',

            # Outlook
            'optimistic', 'positive', 'hopeful', 'promising', 'bright',
            'upbeat', 'confident', 'favorable', 'opportunity', 'momentum',

            # Investment
            'acquisition', 'merger', 'partnership', 'deal', 'contract',
            'expansion', 'growth', 'innovation', 'breakthrough',

            # Others
            'success', 'improve', 'upgrade', 'launch', 'win', 'leader',
            'dominant', 'competitive', 'advantage', 'increase'
        }

        # 부정 키워드
        self.english_negative = {
            # Market movements
            'plunge', 'tumble', 'crash', 'fall', 'drop', 'decline',
            'slump', 'sink', 'low', 'bottom', 'bearish', 'downturn',

            # Performance
            'loss', 'deficit', 'miss', 'underperform', 'disappoint',
            'worst', 'weak', 'poor', 'dismal', 'sluggish',

            # Outlook
            'pessimistic', 'negative', 'concern', 'worry', 'fear',
            'uncertain', 'risk', 'threat', 'challenge', 'pressure',

            # Investment
            'bankruptcy', 'default', 'layoff', 'cut', 'reduction',
            'closure', 'shutdown', 'restructure', 'downsizing',

            # Others
            'failure', 'decline', 'downgrade', 'recall', 'lawsuit',
            'investigation', 'scandal', 'fraud', 'crisis', 'decrease',
            'regulation', 'penalty', 'violation', 'dispute'
        }

        # 강도 수식어
        self.intensity_boosters = {
            'very': 1.5, 'extremely': 2.0, 'highly': 1.5, 'strongly': 1.5,
            'significantly': 1.5, 'considerably': 1.5, 'substantially': 1.5,
            '매우': 1.5, '극도로': 2.0, '상당히': 1.5, '크게': 1.5,
            '대폭': 2.0, '급격히': 2.0, '급': 2.0
        }

    def analyze_korean_text(self, text: str) -> Tuple[float, Dict]:
        """
        한국어 텍스트의 감성을 분석합니다.

        Args:
            text: 분석할 텍스트

        Returns:
            (감성 점수, 상세 정보)
            감성 점수: -1.0 (매우 부정) ~ 1.0 (매우 긍정)
            상세 정보: {'positive_count': ..., 'negative_count': ..., 'keywords': [...]}
        """
        if not text:
            return 0.0, {'positive_count': 0, 'negative_count': 0, 'keywords': []}

        # 텍스트 정규화
        text = text.lower()
        text = re.sub(r'[^\w\s]', ' ', text)

        positive_count = 0
        negative_count = 0
        found_keywords = []

        # 강도 수식어 체크
        intensity_multiplier = 1.0
        for booster, multiplier in self.intensity_boosters.items():
            if booster in text:
                intensity_multiplier = max(intensity_multiplier, multiplier)

        # 긍정 키워드 카운트
        for keyword in self.korean_positive:
            count = text.count(keyword)
            if count > 0:
                positive_count += count
                found_keywords.append(('positive', keyword, count))

        # 부정 키워드 카운트
        for keyword in self.korean_negative:
            count = text.count(keyword)
            if count > 0:
                negative_count += count
                found_keywords.append(('negative', keyword, count))

        # 감성 점수 계산
        total = positive_count + negative_count
        if total == 0:
            score = 0.0
        else:
            # -1.0 ~ 1.0 범위로 정규화
            raw_score = (positive_count - negative_count) / total
            score = raw_score * intensity_multiplier

            # 범위 제한
            score = max(-1.0, min(1.0, score))

        details = {
            'positive_count': positive_count,
            'negative_count': negative_count,
            'total_keywords': total,
            'intensity_multiplier': intensity_multiplier,
            'keywords': found_keywords
        }

        return score, details

    def analyze_english_text(self, text: str) -> Tuple[float, Dict]:
        """
        영어 텍스트의 감성을 분석합니다.

        Args:
            text: 분석할 텍스트

        Returns:
            (감성 점수, 상세 정보)
            감성 점수: -1.0 (매우 부정) ~ 1.0 (매우 긍정)
        """
        if not text:
            return 0.0, {'positive_count': 0, 'negative_count': 0, 'keywords': []}

        # 텍스트 정규화
        text = text.lower()
        text = re.sub(r'[^\w\s]', ' ', text)

        positive_count = 0
        negative_count = 0
        found_keywords = []

        # 강도 수식어 체크
        intensity_multiplier = 1.0
        for booster, multiplier in self.intensity_boosters.items():
            if booster in text:
                intensity_multiplier = max(intensity_multiplier, multiplier)

        # 부정어 체크 (not, no 등)
        negation_words = ['not', 'no', 'never', 'neither', 'nobody', 'nothing']
        has_negation = any(word in text for word in negation_words)

        # 긍정 키워드 카운트
        for keyword in self.english_positive:
            count = text.count(keyword)
            if count > 0:
                positive_count += count
                found_keywords.append(('positive', keyword, count))

        # 부정 키워드 카운트
        for keyword in self.english_negative:
            count = text.count(keyword)
            if count > 0:
                negative_count += count
                found_keywords.append(('negative', keyword, count))

        # 부정어가 있으면 감성 반전
        if has_negation:
            positive_count, negative_count = negative_count, positive_count

        # 감성 점수 계산
        total = positive_count + negative_count
        if total == 0:
            score = 0.0
        else:
            raw_score = (positive_count - negative_count) / total
            score = raw_score * intensity_multiplier
            score = max(-1.0, min(1.0, score))

        details = {
            'positive_count': positive_count,
            'negative_count': negative_count,
            'total_keywords': total,
            'has_negation': has_negation,
            'intensity_multiplier': intensity_multiplier,
            'keywords': found_keywords
        }

        return score, details

    def analyze_text(self, text: str, language: str = 'auto') -> Tuple[float, Dict]:
        """
        텍스트의 감성을 분석합니다 (언어 자동 감지).

        Args:
            text: 분석할 텍스트
            language: 'auto', 'korean', 'english'

        Returns:
            (감성 점수, 상세 정보)
        """
        if not text:
            return 0.0, {}

        # 언어 자동 감지
        if language == 'auto':
            # 한글이 있으면 한국어로 판단
            if re.search(r'[가-힣]', text):
                language = 'korean'
            else:
                language = 'english'

        # 언어별 분석
        if language == 'korean':
            return self.analyze_korean_text(text)
        else:
            return self.analyze_english_text(text)

    def analyze_news(self, news_id: int) -> Optional[float]:
        """
        DB에 저장된 뉴스의 감성을 분석하고 점수를 업데이트합니다.

        Args:
            news_id: 뉴스 ID

        Returns:
            감성 점수 또는 None
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # 뉴스 조회
            cursor.execute("""
                SELECT title, content FROM news WHERE id = ?
            """, (news_id,))

            result = cursor.fetchone()
            if not result:
                return None

            title, content = result

            # 제목과 본문 결합 (제목에 가중치 부여)
            combined_text = f"{title} {title} {content}"

            # 감성 분석
            score, details = self.analyze_text(combined_text)

            # 점수 업데이트
            cursor.execute("""
                UPDATE news SET sentiment_score = ? WHERE id = ?
            """, (score, news_id))

            conn.commit()

            return score

    def analyze_all_news(self, ticker: Optional[str] = None) -> int:
        """
        DB의 모든 뉴스 또는 특정 종목의 뉴스를 분석합니다.

        Args:
            ticker: 종목 코드 (None이면 전체)

        Returns:
            분석된 뉴스 수
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # 미분석 뉴스 조회
            if ticker:
                cursor.execute("""
                    SELECT id FROM news
                    WHERE ticker = ? AND sentiment_score IS NULL
                """, (ticker,))
            else:
                cursor.execute("""
                    SELECT id FROM news WHERE sentiment_score IS NULL
                """)

            news_ids = [row[0] for row in cursor.fetchall()]

        print(f"[INFO] {len(news_ids)}개 뉴스 감성 분석 시작")

        analyzed_count = 0
        for news_id in news_ids:
            try:
                score = self.analyze_news(news_id)
                if score is not None:
                    analyzed_count += 1

                    if analyzed_count % 10 == 0:
                        print(f"[INFO] {analyzed_count}/{len(news_ids)} 뉴스 분석 완료")

            except Exception as e:
                print(f"[ERROR] 뉴스 ID {news_id} 분석 실패: {e}")
                continue

        print(f"[INFO] 총 {analyzed_count}개 뉴스 감성 분석 완료")
        return analyzed_count

    def get_sentiment_summary(
        self,
        ticker: str,
        days: int = 7
    ) -> Dict:
        """
        특정 기간 동안의 감성 분석 요약을 제공합니다.

        Args:
            ticker: 종목 코드
            days: 분석 기간 (일)

        Returns:
            요약 정보 딕셔너리
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT
                    COUNT(*) as total_news,
                    AVG(sentiment_score) as avg_sentiment,
                    SUM(CASE WHEN sentiment_score > 0.2 THEN 1 ELSE 0 END) as positive_news,
                    SUM(CASE WHEN sentiment_score < -0.2 THEN 1 ELSE 0 END) as negative_news,
                    SUM(CASE WHEN sentiment_score BETWEEN -0.2 AND 0.2 THEN 1 ELSE 0 END) as neutral_news
                FROM news
                WHERE ticker = ?
                    AND sentiment_score IS NOT NULL
                    AND published_date >= datetime('now', '-' || ? || ' days')
            """, (ticker, days))

            result = cursor.fetchone()

            if result and result[0] > 0:
                return {
                    'ticker': ticker,
                    'total_news': result[0],
                    'avg_sentiment': round(result[1], 3) if result[1] else 0.0,
                    'positive_news': result[2] or 0,
                    'negative_news': result[3] or 0,
                    'neutral_news': result[4] or 0,
                    'days': days,
                    'sentiment_label': self._get_sentiment_label(result[1] if result[1] else 0.0)
                }
            else:
                return {
                    'ticker': ticker,
                    'total_news': 0,
                    'avg_sentiment': 0.0,
                    'positive_news': 0,
                    'negative_news': 0,
                    'neutral_news': 0,
                    'days': days,
                    'sentiment_label': 'NEUTRAL'
                }

    def _get_sentiment_label(self, score: float) -> str:
        """
        감성 점수를 레이블로 변환합니다.

        Args:
            score: 감성 점수

        Returns:
            감성 레이블
        """
        if score > 0.5:
            return 'VERY_POSITIVE'
        elif score > 0.2:
            return 'POSITIVE'
        elif score < -0.5:
            return 'VERY_NEGATIVE'
        elif score < -0.2:
            return 'NEGATIVE'
        else:
            return 'NEUTRAL'


# 사용 예시
if __name__ == "__main__":
    analyzer = SentimentAnalyzer()

    # 테스트 텍스트
    print("=" * 80)
    print("감성 분석 테스트")
    print("=" * 80)

    # 한국어 긍정 텍스트
    korean_positive = "삼성전자 주가가 급등하며 신고가를 돌파했다. 실적 호조에 투자자들의 기대감이 높아지고 있다."
    score, details = analyzer.analyze_text(korean_positive)
    print(f"\n[한국어 긍정] 점수: {score:.3f}")
    print(f"긍정 키워드: {details['positive_count']}, 부정 키워드: {details['negative_count']}")

    # 한국어 부정 텍스트
    korean_negative = "실적 부진으로 주가가 급락했다. 투자자들의 우려가 커지고 있으며 전망이 어둡다."
    score, details = analyzer.analyze_text(korean_negative)
    print(f"\n[한국어 부정] 점수: {score:.3f}")
    print(f"긍정 키워드: {details['positive_count']}, 부정 키워드: {details['negative_count']}")

    # 영어 긍정 텍스트
    english_positive = "Stock prices surge to record high as company beats earnings expectations. Investors are optimistic about future growth."
    score, details = analyzer.analyze_text(english_positive)
    print(f"\n[영어 긍정] 점수: {score:.3f}")
    print(f"긍정 키워드: {details['positive_count']}, 부정 키워드: {details['negative_count']}")

    # 영어 부정 텍스트
    english_negative = "Stock plunges on disappointing earnings. Investors worry about the company's future amid weak performance."
    score, details = analyzer.analyze_text(english_negative)
    print(f"\n[영어 부정] 점수: {score:.3f}")
    print(f"긍정 키워드: {details['positive_count']}, 부정 키워드: {details['negative_count']}")

    # DB의 뉴스 분석 (뉴스가 있는 경우)
    print("\n" + "=" * 80)
    print("DB 뉴스 감성 분석")
    print("=" * 80)

    analyzed_count = analyzer.analyze_all_news()
    print(f"\n총 {analyzed_count}개 뉴스 분석 완료")

    # 감성 요약 (삼성전자)
    summary = analyzer.get_sentiment_summary("005930.KS", days=7)
    if summary['total_news'] > 0:
        print("\n" + "=" * 80)
        print("감성 분석 요약 (최근 7일)")
        print("=" * 80)
        print(f"종목: {summary['ticker']}")
        print(f"전체 뉴스: {summary['total_news']}개")
        print(f"평균 감성: {summary['avg_sentiment']:.3f} ({summary['sentiment_label']})")
        print(f"긍정 뉴스: {summary['positive_news']}개")
        print(f"부정 뉴스: {summary['negative_news']}개")
        print(f"중립 뉴스: {summary['neutral_news']}개")
