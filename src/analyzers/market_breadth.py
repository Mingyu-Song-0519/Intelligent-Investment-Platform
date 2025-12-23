"""
시장 폭(Market Breadth) 분석 모듈
"지수는 오르는데, 실제로 몇 종목이 오르고 있나?"를 분석
2024-2025 트렌드: 대형주 쏠림 장세 감지
"""
import yfinance as yf
import pandas as pd
import numpy as np
from typing import Dict, Tuple, Optional, List
from datetime import datetime, timedelta
import FinanceDataReader as fdr


class MarketBreadthAnalyzer:
    """시장 폭 분석 클래스"""
    
    def __init__(self, market: str = "KR"):
        """
        Args:
            market: 시장 코드 ("KR" 또는 "US")
        """
        self.market = market
        self._cache = {}
        self._cache_timestamp = None
        self._cache_ttl = 600  # 10분 캐싱
    
    def get_market_data(self, days: int = 5) -> pd.DataFrame:
        """
        시장 전체 종목의 최근 가격 데이터 수집
        
        Args:
            days: 수집 기간 (일)
            
        Returns:
            종목별 가격 데이터 DataFrame
        """
        now = datetime.now()
        cache_key = f"{self.market}_{days}"
        
        # 캐시 확인
        if (cache_key in self._cache and 
            self._cache_timestamp and
            (now - self._cache_timestamp).seconds < self._cache_ttl):
            return self._cache[cache_key]
        
        try:
            if self.market == "KR":
                # 한국: KOSPI 200 종목 사용 (대표성)
                df = fdr.StockListing('KOSPI')
                tickers = df['Code'].head(100).tolist()  # 상위 100개
            else:
                # 미국: S&P 500 ETF 구성종목 대신 주요 종목
                tickers = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA', 
                          'BRK-B', 'UNH', 'JNJ', 'XOM', 'JPM', 'V', 'PG', 'MA',
                          'HD', 'CVX', 'MRK', 'ABBV', 'LLY', 'PFE', 'KO', 'PEP',
                          'COST', 'WMT', 'DIS', 'CSCO', 'VZ', 'INTC', 'NFLX']
            
            # 가격 데이터 수집
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days + 5)  # 버퍼
            
            data = {}
            for ticker in tickers[:30]:  # 속도를 위해 30개로 제한
                try:
                    suffix = ".KS" if self.market == "KR" else ""
                    symbol = f"{ticker}{suffix}"
                    stock = yf.Ticker(symbol)
                    hist = stock.history(start=start_date, end=end_date)
                    if not hist.empty:
                        data[ticker] = hist['Close']
                except Exception:
                    continue
            
            result = pd.DataFrame(data)
            self._cache[cache_key] = result
            self._cache_timestamp = now
            
            return result
            
        except Exception as e:
            print(f"시장 데이터 수집 오류: {e}")
            return pd.DataFrame()
    
    def advance_decline_ratio(self) -> Dict:
        """
        상승/하락 종목 비율 계산
        
        Returns:
            {
                "advancing": 상승 종목 수,
                "declining": 하락 종목 수,
                "unchanged": 보합 종목 수,
                "ratio": 상승/하락 비율,
                "breadth_status": 상태 문자열
            }
        """
        df = self.get_market_data(days=2)
        
        if df.empty or len(df) < 2:
            return {"error": "데이터 부족"}
        
        # 일일 변화율 계산
        today = df.iloc[-1]
        yesterday = df.iloc[-2]
        changes = (today - yesterday) / yesterday * 100
        
        advancing = (changes > 0.5).sum()  # 0.5% 이상 상승
        declining = (changes < -0.5).sum()  # 0.5% 이상 하락
        unchanged = len(changes) - advancing - declining
        
        ratio = advancing / max(declining, 1)
        
        # 상태 판단
        if ratio > 2:
            status = "🟢 매우 건강 (강한 매수세)"
        elif ratio > 1:
            status = "🟢 건강 (상승 우위)"
        elif ratio > 0.5:
            status = "🟡 약세 (하락 우위)"
        else:
            status = "🔴 매우 약세 (강한 매도세)"
        
        return {
            "advancing": int(advancing),
            "declining": int(declining),
            "unchanged": int(unchanged),
            "ratio": round(ratio, 2),
            "breadth_status": status
        }
    
    def new_high_low_ratio(self) -> Dict:
        """
        52주 신고가/신저가 비율 계산
        
        Returns:
            {
                "new_highs": 신고가 종목 수,
                "new_lows": 신저가 종목 수,
                "ratio": 신고가/신저가 비율,
                "status": 상태 문자열
            }
        """
        # 1년치 데이터 필요
        df = self.get_market_data(days=260)
        
        if df.empty or len(df) < 252:
            return {"error": "데이터 부족 (1년치 필요)"}
        
        # 52주 고가/저가 계산
        high_52w = df.tail(252).max()
        low_52w = df.tail(252).min()
        current = df.iloc[-1]
        
        # 신고가: 현재가가 52주 고가의 98% 이상
        # 신저가: 현재가가 52주 저가의 102% 이하
        new_highs = ((current / high_52w) >= 0.98).sum()
        new_lows = ((current / low_52w) <= 1.02).sum()
        
        ratio = new_highs / max(new_lows, 1)
        
        if ratio > 3:
            status = "🟢 강세 (신고가 우위)"
        elif ratio > 1:
            status = "🟡 중립 (균형)"
        else:
            status = "🔴 약세 (신저가 우위)"
        
        return {
            "new_highs": int(new_highs),
            "new_lows": int(new_lows),
            "ratio": round(ratio, 2),
            "status": status
        }
    
    def market_concentration(self) -> Dict:
        """
        시장 집중도 분석 (상위 종목 쏠림도)
        
        Returns:
            {
                "top10_contribution": 상위 10종목 수익률 기여도,
                "market_return": 전체 시장 수익률,
                "concentration_warning": 경고 여부
            }
        """
        df = self.get_market_data(days=30)
        
        if df.empty or len(df) < 20:
            return {"error": "데이터 부족"}
        
        # 월간 수익률
        returns = (df.iloc[-1] - df.iloc[0]) / df.iloc[0] * 100
        returns = returns.dropna().sort_values(ascending=False)
        
        if len(returns) < 10:
            return {"error": "종목 수 부족"}
        
        # 상위 10개 평균 vs 전체 평균
        top10_return = returns.head(10).mean()
        market_return = returns.mean()
        
        # 상위 10개가 전체의 얼마나 많은 상승을 책임지는지
        concentration = top10_return / max(abs(market_return), 0.1)
        
        if concentration > 3:
            warning = "⚠️ 경고: 소수 종목 쏠림 (상위 10개가 지수 견인)"
        elif concentration > 2:
            warning = "🟡 주의: 중간 수준 집중"
        else:
            warning = "🟢 정상: 폭넓은 시장 참여"
        
        return {
            "top10_return": round(top10_return, 2),
            "market_return": round(market_return, 2),
            "concentration_ratio": round(concentration, 2),
            "warning": warning
        }
    
    def get_breadth_summary(self) -> Dict:
        """전체 시장 폭 요약"""
        ad = self.advance_decline_ratio()
        hl = self.new_high_low_ratio()
        conc = self.market_concentration()
        
        # 종합 점수 (0-100)
        score = 50  # 기본값
        
        if "ratio" in ad:
            if ad["ratio"] > 1.5:
                score += 20
            elif ad["ratio"] < 0.7:
                score -= 20
        
        if "ratio" in hl:
            if hl["ratio"] > 2:
                score += 15
            elif hl["ratio"] < 0.5:
                score -= 15
        
        if "concentration_ratio" in conc:
            if conc["concentration_ratio"] > 3:
                score -= 15  # 쏠림은 부정적
        
        score = max(0, min(100, score))
        
        if score >= 70:
            overall = "🟢 건강한 시장"
        elif score >= 40:
            overall = "🟡 중립 시장"
        else:
            overall = "🔴 취약한 시장"
        
        return {
            "advance_decline": ad,
            "new_high_low": hl,
            "concentration": conc,
            "breadth_score": score,
            "overall_status": overall
        }


if __name__ == "__main__":
    # 테스트
    analyzer = MarketBreadthAnalyzer(market="KR")
    
    print("=== 시장 폭 분석 ===")
    summary = analyzer.get_breadth_summary()
    
    print(f"\n상승/하락: {summary['advance_decline']}")
    print(f"신고가/신저가: {summary['new_high_low']}")
    print(f"집중도: {summary['concentration']}")
    print(f"\n종합 점수: {summary['breadth_score']}")
    print(f"종합 상태: {summary['overall_status']}")
