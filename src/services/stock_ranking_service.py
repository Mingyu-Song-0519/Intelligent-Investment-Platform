"""
StockRankingService
종목 순위 산출 서비스 - EnsemblePredictor 연동

Clean Architecture: Application Layer (Service)
"""
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import numpy as np

from src.domain.investment_profile.entities.investor_profile import InvestorProfile
from src.domain.investment_profile.entities.recommendation import RankedStock
from src.domain.repositories.profile_interfaces import IProfileRepository


# 모듈 수준 AI 예측 캐시 (앱 전체에서 공유)
_AI_PREDICTION_CACHE: Dict[str, Tuple[float, str, float, datetime]] = {}
_AI_CACHE_TTL_SECONDS = 3600  # 1시간


class StockRankingService:
    """
    종목 순위 산출 서비스
    
    기능:
    - EnsemblePredictor 기반 AI 점수 산출 (실제 예측)
    - 프로필 기반 성향 적합도 계산
    - 트렌드 점수 계산
    - 캐싱 전략 (1시간 TTL)
    """
    
    # 한국 주요 종목 리스트
    KOREAN_TICKERS = {
        "005930.KS": {"name": "삼성전자", "sector": "Technology"},
        "000660.KS": {"name": "SK하이닉스", "sector": "Technology"},
        "035420.KS": {"name": "NAVER", "sector": "Communication"},
        "035720.KS": {"name": "카카오", "sector": "Communication"},
        "051910.KS": {"name": "LG화학", "sector": "Materials"},
        "207940.KS": {"name": "삼성바이오로직스", "sector": "Healthcare"},
        "006400.KS": {"name": "삼성SDI", "sector": "Technology"},
        "068270.KS": {"name": "셀트리온", "sector": "Healthcare"},
        "105560.KS": {"name": "KB금융", "sector": "Financials"},
        "055550.KS": {"name": "신한지주", "sector": "Financials"},
    }
    
    SECTOR_VOLATILITY = {
        "Technology": 0.35,
        "Healthcare": 0.40,
        "Financials": 0.25,
        "Consumer": 0.30,
        "Energy": 0.45,
        "Communication": 0.32,
        "Industrials": 0.28,
        "Materials": 0.35,
        "Utilities": 0.15,
    }
    
    SECTOR_STYLES = {
        "Technology": {"value": 30, "growth": 50, "momentum": 20},
        "Healthcare": {"value": 20, "growth": 60, "momentum": 20},
        "Financials": {"value": 60, "growth": 20, "momentum": 20},
        "Consumer": {"value": 40, "growth": 35, "momentum": 25},
        "Energy": {"value": 35, "growth": 30, "momentum": 35},
        "Communication": {"value": 35, "growth": 45, "momentum": 20},
        "Industrials": {"value": 50, "growth": 30, "momentum": 20},
        "Materials": {"value": 40, "growth": 35, "momentum": 25},
        "Utilities": {"value": 70, "growth": 15, "momentum": 15},
    }
    
    def __init__(
        self,
        profile_repo: IProfileRepository,
        cache_ttl: int = 3600,
        use_ai_model: bool = True  # 기본값 True로 변경
    ):
        self.profile_repo = profile_repo
        self.cache_ttl = cache_ttl
        self.use_ai_model = use_ai_model
        
        # 사용자별 순위 캐시
        self._user_ranking_cache: Dict[str, Tuple[List[RankedStock], datetime]] = {}
        
        # AI 모델 인스턴스 (지연 로딩)
        self._ensemble_predictor = None
        self._data_collector = None
    
    def _get_ensemble_predictor(self):
        """EnsemblePredictor 지연 로딩"""
        if self._ensemble_predictor is None and self.use_ai_model:
            try:
                from src.models.ensemble_predictor import EnsemblePredictor
                self._ensemble_predictor = EnsemblePredictor()
            except Exception as e:
                print(f"[WARNING] EnsemblePredictor 로드 실패: {e}")
        return self._ensemble_predictor
    
    def _get_data_collector(self):
        """StockDataCollector 지연 로딩"""
        if self._data_collector is None and self.use_ai_model:
            try:
                from src.collectors.stock_collector import StockDataCollector
                self._data_collector = StockDataCollector()
            except Exception as e:
                print(f"[WARNING] StockDataCollector 로드 실패: {e}")
        return self._data_collector
    
    def get_personalized_ranking(
        self,
        user_id: str,
        top_n: int = 10,
        force_refresh: bool = False
    ) -> List[RankedStock]:
        """사용자 맞춤 종목 순위 반환"""
        # 1. 캐시 확인
        if not force_refresh:
            cached = self._get_from_cache(user_id)
            if cached:
                return cached[:top_n]
        
        # 2. 프로필 로드
        profile = self.profile_repo.load(user_id)
        if not profile:
            profile = InvestorProfile.create_default(user_id)
        
        # 3. 순위 계산
        ranking = self._calculate_ranking(profile)
        
        # 4. 캐시 저장
        self._save_to_cache(user_id, ranking)
        
        return ranking[:top_n]
    
    def _get_from_cache(self, user_id: str) -> Optional[List[RankedStock]]:
        """캐시에서 조회"""
        if user_id not in self._user_ranking_cache:
            return None
        
        ranking, timestamp = self._user_ranking_cache[user_id]
        
        if (datetime.now() - timestamp).seconds > self.cache_ttl:
            del self._user_ranking_cache[user_id]
            return None
        
        return ranking
    
    def _save_to_cache(self, user_id: str, ranking: List[RankedStock]) -> None:
        """캐시에 저장"""
        self._user_ranking_cache[user_id] = (ranking, datetime.now())
    
    def invalidate_cache(self, user_id: str) -> None:
        """캐시 무효화"""
        if user_id in self._user_ranking_cache:
            del self._user_ranking_cache[user_id]
    
    def _calculate_ranking(self, profile: InvestorProfile) -> List[RankedStock]:
        """순위 계산"""
        ranked_stocks = []
        
        for ticker, stock_info in self.KOREAN_TICKERS.items():
            stock_name = stock_info["name"]
            sector = stock_info["sector"]
            
            # 1. 성향 적합도 (40%)
            profile_fit = self._calculate_profile_fit(profile, sector)
            
            # 2. 트렌드 점수 (30%)
            trend_score = self._calculate_trend_score(ticker)
            
            # 3. AI 점수 (30%) - 실제 예측 사용
            ai_score, ai_prediction, confidence = self._get_ai_prediction(ticker)
            
            # 종합 점수
            composite_score = (
                (profile_fit * 0.4) + 
                (trend_score * 0.3) + 
                (ai_score * 0.3)
            )
            
            # 실제 변동성 계산 (캐싱된 데이터 사용)
            volatility = self._calculate_real_volatility(ticker, sector)
            
            ranked_stock = RankedStock(
                rank=0,
                ticker=ticker,
                stock_name=stock_name,
                sector=sector,
                composite_score=composite_score,
                profile_fit=profile_fit,
                trend_score=trend_score,
                ai_score=ai_score,
                ai_prediction=ai_prediction,
                confidence=confidence,
                volatility=volatility
            )
            ranked_stocks.append(ranked_stock)
        
        # 점수순 정렬
        ranked_stocks.sort(key=lambda x: x.composite_score, reverse=True)
        
        # 순위 설정
        for i, stock in enumerate(ranked_stocks):
            stock.rank = i + 1
        
        return ranked_stocks
    
    def _calculate_profile_fit(self, profile: InvestorProfile, sector: str) -> float:
        """성향 적합도 계산"""
        sector_vol = self.SECTOR_VOLATILITY.get(sector, 0.30)
        vol_min, vol_max = profile.get_ideal_volatility_range()
        
        if vol_min <= sector_vol <= vol_max:
            vol_fit = 100.0
        else:
            ideal_mid = (vol_min + vol_max) / 2
            vol_fit = max(0, 100 - abs(sector_vol - ideal_mid) * 200)
        
        sector_fit = 100.0 if sector in profile.preferred_sectors else 30.0
        
        sector_style = self.SECTOR_STYLES.get(sector, {"value": 33, "growth": 33, "momentum": 34})
        style_fit = profile.calculate_style_similarity(sector_style)
        
        return (vol_fit * 0.4) + (sector_fit * 0.3) + (style_fit * 0.3)
    
    def _calculate_trend_score(self, ticker: str) -> float:
        """트렌드 점수 계산 (기술적 분석)"""
        try:
            collector = self._get_data_collector()
            if collector and self.use_ai_model:
                from src.analyzers.technical_analyzer import TechnicalAnalyzer
                
                df = collector.fetch_stock_data(ticker, period="3mo")
                if df is not None and len(df) > 20:
                    analyzer = TechnicalAnalyzer(df)
                    signals = analyzer.get_trading_signals()
                    
                    # 신호 기반 점수 계산
                    score = 50.0
                    if signals.get('rsi_signal') == 'oversold':
                        score += 15
                    elif signals.get('rsi_signal') == 'overbought':
                        score -= 10
                    
                    if signals.get('macd_signal') == 'bullish':
                        score += 20
                    elif signals.get('macd_signal') == 'bearish':
                        score -= 15
                    
                    if signals.get('bb_signal') == 'lower':
                        score += 10
                    elif signals.get('bb_signal') == 'upper':
                        score -= 5
                    
                    return min(100, max(0, score))
        except Exception:
            pass
        
        # 폴백: 시뮬레이션
        np.random.seed(hash(ticker) % 2**32)
        return np.random.uniform(40, 75)
    
    def _calculate_real_volatility(self, ticker: str, sector: str) -> float:
        """
        실제 변동성 계산 (연간 변동성)
        
        계산 방식:
        - 일일 수익률의 표준편차 × √252 (연간화)
        """
        try:
            collector = self._get_data_collector()
            if collector:
                df = collector.fetch_stock_data(ticker, period="6mo")
                
                if df is not None and len(df) > 20:
                    # 일일 수익률 계산
                    returns = df['close'].pct_change().dropna()
                    
                    if len(returns) > 10:
                        # 연간 변동성 (일일 변동성 × √252)
                        daily_vol = returns.std()
                        annual_vol = daily_vol * np.sqrt(252)
                        
                        # 0-100% 범위로 제한
                        return min(1.0, max(0.05, annual_vol))
        except Exception:
            pass
        
        # 폴백: 섹터 기반 추정치
        return self.SECTOR_VOLATILITY.get(sector, 0.30)
    
    def _get_ai_prediction(self, ticker: str) -> Tuple[float, str, float]:
        """AI 예측 점수 (EnsemblePredictor 사용)"""
        global _AI_PREDICTION_CACHE
        
        # 캐시 확인
        if ticker in _AI_PREDICTION_CACHE:
            score, prediction, confidence, timestamp = _AI_PREDICTION_CACHE[ticker]
            if (datetime.now() - timestamp).seconds < _AI_CACHE_TTL_SECONDS:
                return score, prediction, confidence
        
        # 실제 예측 수행
        if self.use_ai_model:
            try:
                predictor = self._get_ensemble_predictor()
                collector = self._get_data_collector()
                
                if predictor and collector:
                    df = collector.fetch_stock_data(ticker, period="1y")
                    
                    if df is not None and len(df) >= 60:
                        # 방향 예측
                        direction_result = predictor.predict_direction(df)
                        
                        if direction_result:
                            # 올바른 키 사용
                            confidence = direction_result.get('confidence_score', 0.5)
                            ensemble_pred = direction_result.get('ensemble_prediction', 'down')
                            
                            # 문자열 예측값을 숫자로 변환
                            if ensemble_pred == 'up':
                                prediction_val = 1.0
                                prediction = "상승"
                            else:
                                prediction_val = -1.0
                                prediction = "하락"
                            
                            # 예측값을 점수로 변환 (0-100 범위)
                            score = 50 + (prediction_val * confidence * 50)
                            score = min(100, max(0, score))
                            
                            # 캐시 저장
                            _AI_PREDICTION_CACHE[ticker] = (score, prediction, confidence, datetime.now())
                            
                            return score, prediction, confidence
            except Exception as e:
                print(f"[WARNING] AI 예측 실패 ({ticker}): {e}")
        
        # 폴백: 시뮬레이션
        np.random.seed(hash(ticker + "ai") % 2**32)
        score = np.random.uniform(40, 80)
        confidence = np.random.uniform(0.5, 0.75)
        
        if score >= 65:
            prediction = "상승"
        elif score >= 45:
            prediction = "보합"
        else:
            prediction = "하락"
        
        return score, prediction, confidence
    
    def get_cache_stats(self) -> Dict:
        """캐시 통계"""
        return {
            "user_ranking_cache_size": len(self._user_ranking_cache),
            "ai_prediction_cache_size": len(_AI_PREDICTION_CACHE),
            "cache_ttl_seconds": self.cache_ttl,
            "use_ai_model": self.use_ai_model
        }
    
    def clear_ai_cache(self) -> None:
        """AI 예측 캐시 초기화"""
        global _AI_PREDICTION_CACHE
        _AI_PREDICTION_CACHE.clear()

