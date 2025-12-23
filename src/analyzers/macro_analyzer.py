"""
매크로 경제 지표 분석 모듈 - 금리, 달러 인덱스, 원자재 등
2024-2025 트렌드: 금리 정책, 달러 강세가 주식 시장에 미치는 영향 분석
"""
import yfinance as yf
import pandas as pd
import numpy as np
from typing import Dict, Optional, Tuple, List
from datetime import datetime, timedelta


class MacroAnalyzer:
    """매크로 경제 지표 분석 클래스"""
    
    # 주요 매크로 지표 티커
    MACRO_TICKERS = {
        # 금리
        "us_10y": "^TNX",       # 미국 10년물 국채 수익률
        "us_2y": "^IRX",        # 미국 2년물 국채 수익률 (근사)
        
        # 달러
        "dxy": "DX-Y.NYB",      # 달러 인덱스
        "usd_krw": "KRW=X",     # 달러/원
        "usd_jpy": "JPY=X",     # 달러/엔
        
        # 원자재
        "gold": "GC=F",         # 금 선물
        "oil": "CL=F",          # WTI 원유 선물
        "copper": "HG=F",       # 구리 선물 (경기 선행)
        
        # 지수
        "vix": "^VIX",          # 변동성 지수
        "sp500": "^GSPC",       # S&P 500
    }
    
    def __init__(self):
        """초기화"""
        self._cache = {}
        self._cache_timestamp = None
        self._cache_ttl = 300  # 5분 캐싱
    
    def get_indicator(self, indicator_key: str, period: str = "1mo") -> Dict:
        """
        단일 매크로 지표 조회
        
        Args:
            indicator_key: 지표 키 (예: "us_10y", "dxy")
            period: 데이터 기간
            
        Returns:
            {
                "current": 현재값,
                "change": 변화,
                "change_pct": 변화율,
                "high_52w": 52주 고가,
                "low_52w": 52주 저가
            }
        """
        if indicator_key not in self.MACRO_TICKERS:
            return {"error": f"Unknown indicator: {indicator_key}"}
        
        ticker = self.MACRO_TICKERS[indicator_key]
        
        # 캐시 확인
        cache_key = f"{ticker}_{period}"
        if cache_key in self._cache:
            cache_data = self._cache[cache_key]
            if (datetime.now() - cache_data['timestamp']).seconds < self._cache_ttl:
                return cache_data['data']
        
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period=period)
            
            if hist.empty:
                return {"error": "데이터 없음"}
            
            current = hist['Close'].iloc[-1]
            prev = hist['Close'].iloc[-2] if len(hist) > 1 else current
            
            change = current - prev
            change_pct = (change / prev * 100) if prev != 0 else 0
            
            # 52주 데이터
            hist_1y = stock.history(period="1y")
            high_52w = hist_1y['High'].max() if not hist_1y.empty else current
            low_52w = hist_1y['Low'].min() if not hist_1y.empty else current
            
            result = {
                "current": round(current, 4),
                "prev": round(prev, 4),
                "change": round(change, 4),
                "change_pct": round(change_pct, 2),
                "high_52w": round(high_52w, 4),
                "low_52w": round(low_52w, 4),
                "position_52w": round((current - low_52w) / (high_52w - low_52w) * 100, 1) if high_52w != low_52w else 50
            }
            
            # 캐시 저장
            self._cache[cache_key] = {
                'data': result,
                'timestamp': datetime.now()
            }
            
            return result
            
        except Exception as e:
            return {"error": str(e)}
    
    def get_treasury_yields(self) -> Dict:
        """미국 국채 수익률 조회"""
        us_10y = self.get_indicator("us_10y")
        
        # 수익률 곡선 해석
        yield_10y = us_10y.get("current", 0)
        
        if yield_10y > 5:
            interpretation = "🔴 고금리 (긴축 정책, 성장주 불리)"
        elif yield_10y > 4:
            interpretation = "🟡 중립~높음 (주의 필요)"
        elif yield_10y > 3:
            interpretation = "🟢 중립 (정상 수준)"
        else:
            interpretation = "🔵 저금리 (완화적, 성장주 유리)"
        
        return {
            "us_10y": us_10y,
            "interpretation": interpretation
        }
    
    def get_dollar_strength(self) -> Dict:
        """달러 강세 분석"""
        dxy = self.get_indicator("dxy")
        usd_krw = self.get_indicator("usd_krw")
        
        dxy_value = dxy.get("current", 100)
        
        if dxy_value > 105:
            interpretation = "🟢 달러 강세 (신흥국 통화 약세)"
        elif dxy_value > 100:
            interpretation = "🟡 달러 보통"
        else:
            interpretation = "🔴 달러 약세 (신흥국 통화 강세)"
        
        return {
            "dxy": dxy,
            "usd_krw": usd_krw,
            "interpretation": interpretation
        }
    
    def get_commodities(self) -> Dict:
        """원자재 가격 조회"""
        gold = self.get_indicator("gold")
        oil = self.get_indicator("oil")
        copper = self.get_indicator("copper")
        
        # 구리는 경기 선행 지표
        copper_change = copper.get("change_pct", 0)
        if copper_change > 5:
            copper_signal = "🟢 경기 확장 신호"
        elif copper_change < -5:
            copper_signal = "🔴 경기 수축 우려"
        else:
            copper_signal = "🟡 중립"
        
        return {
            "gold": gold,
            "oil": oil,
            "copper": copper,
            "copper_signal": copper_signal
        }
    
    def get_macro_summary(self) -> Dict:
        """매크로 환경 종합 요약"""
        yields = self.get_treasury_yields()
        dollar = self.get_dollar_strength()
        commodities = self.get_commodities()
        vix = self.get_indicator("vix")
        
        # 종합 점수 (시장 우호적일수록 높음)
        score = 50
        
        # VIX (낮을수록 좋음)
        vix_val = vix.get("current", 20)
        if vix_val < 15:
            score += 15
        elif vix_val > 25:
            score -= 15
        
        # 금리 (낮을수록 성장주에 유리)
        yield_10y = yields["us_10y"].get("current", 4)
        if yield_10y < 3.5:
            score += 10
        elif yield_10y > 5:
            score -= 10
        
        # 달러 (너무 강하면 신흥국 불리)
        dxy_val = dollar["dxy"].get("current", 100)
        if dxy_val > 105:
            score -= 5
        
        score = max(0, min(100, score))
        
        if score >= 65:
            environment = "🟢 시장 우호적"
        elif score >= 40:
            environment = "🟡 중립"
        else:
            environment = "🔴 시장 비우호적"
        
        return {
            "treasury_yields": yields,
            "dollar_strength": dollar,
            "commodities": commodities,
            "vix": vix,
            "macro_score": score,
            "environment": environment,
            "analysis_time": datetime.now().isoformat()
        }
    
    def get_sidebar_widget_data(self) -> Dict:
        """사이드바 위젯용 간소화 데이터"""
        try:
            us_10y = self.get_indicator("us_10y")
            dxy = self.get_indicator("dxy")
            vix = self.get_indicator("vix")
            usd_krw = self.get_indicator("usd_krw")
            
            return {
                "us_10y": {
                    "value": us_10y.get("current"),
                    "change": us_10y.get("change_pct"),
                    "label": "🇺🇸 미국 10년물"
                },
                "dxy": {
                    "value": dxy.get("current"),
                    "change": dxy.get("change_pct"),
                    "label": "💵 달러 인덱스"
                },
                "vix": {
                    "value": vix.get("current"),
                    "change": vix.get("change_pct"),
                    "label": "😱 VIX"
                },
                "usd_krw": {
                    "value": usd_krw.get("current"),
                    "change": usd_krw.get("change_pct"),
                    "label": "💱 USD/KRW"
                }
            }
        except Exception as e:
            return {"error": str(e)}


if __name__ == "__main__":
    # 테스트
    print("=== 매크로 경제 지표 분석 ===")
    
    analyzer = MacroAnalyzer()
    summary = analyzer.get_macro_summary()
    
    print(f"\n[금리]")
    yields = summary["treasury_yields"]
    print(f"  미국 10년물: {yields['us_10y'].get('current')}%")
    print(f"  해석: {yields['interpretation']}")
    
    print(f"\n[달러]")
    dollar = summary["dollar_strength"]
    print(f"  달러 인덱스: {dollar['dxy'].get('current')}")
    print(f"  USD/KRW: {dollar['usd_krw'].get('current')}")
    print(f"  해석: {dollar['interpretation']}")
    
    print(f"\n[VIX]")
    print(f"  현재: {summary['vix'].get('current')}")
    
    print(f"\n[종합]")
    print(f"  매크로 점수: {summary['macro_score']}/100")
    print(f"  환경: {summary['environment']}")
