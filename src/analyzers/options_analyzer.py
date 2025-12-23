"""
옵션 분석 모듈 - Put/Call Ratio, 내재변동성(IV) 등 옵션 데이터 분석
2024-2025 트렌드: 0DTE 옵션, 감마 노출 등 옵션 시장 영향력 증가
"""
import yfinance as yf
import pandas as pd
import numpy as np
from typing import Dict, Optional, Tuple, List
from datetime import datetime, timedelta


class OptionsAnalyzer:
    """옵션 데이터 분석 클래스"""
    
    def __init__(self, ticker: str):
        """
        Args:
            ticker: 종목 코드 (예: "AAPL", "SPY")
        """
        self.ticker = ticker
        self._stock = None
        self._options_cache = {}
        self._cache_timestamp = None
        self._cache_ttl = 300  # 5분 캐싱
    
    def _get_stock(self) -> yf.Ticker:
        """yfinance Ticker 객체 반환"""
        if self._stock is None:
            self._stock = yf.Ticker(self.ticker)
        return self._stock
    
    def get_available_expirations(self) -> List[str]:
        """
        사용 가능한 만기일 목록 반환
        
        Returns:
            만기일 리스트 (YYYY-MM-DD 형식)
        """
        try:
            stock = self._get_stock()
            return list(stock.options)
        except Exception as e:
            print(f"만기일 조회 오류: {e}")
            return []
    
    def get_options_chain(self, expiration: Optional[str] = None) -> Dict:
        """
        옵션 체인 데이터 조회
        
        Args:
            expiration: 만기일 (없으면 가장 가까운 만기)
            
        Returns:
            {"calls": DataFrame, "puts": DataFrame}
        """
        try:
            stock = self._get_stock()
            expirations = stock.options
            
            if not expirations:
                return {"calls": pd.DataFrame(), "puts": pd.DataFrame(), "error": "옵션 데이터 없음"}
            
            # 만기일 선택
            if expiration is None or expiration not in expirations:
                expiration = expirations[0]
            
            # 캐시 확인
            cache_key = f"{self.ticker}_{expiration}"
            if cache_key in self._options_cache:
                cache_data = self._options_cache[cache_key]
                if (datetime.now() - cache_data['timestamp']).seconds < self._cache_ttl:
                    return cache_data['data']
            
            # 옵션 체인 조회
            opt_chain = stock.option_chain(expiration)
            
            result = {
                "calls": opt_chain.calls,
                "puts": opt_chain.puts,
                "expiration": expiration
            }
            
            # 캐시 저장
            self._options_cache[cache_key] = {
                'data': result,
                'timestamp': datetime.now()
            }
            
            return result
            
        except Exception as e:
            print(f"옵션 체인 조회 오류: {e}")
            return {"calls": pd.DataFrame(), "puts": pd.DataFrame(), "error": str(e)}
    
    def calculate_put_call_ratio(self, expiration: Optional[str] = None) -> Dict:
        """
        Put/Call Ratio 계산
        
        Put/Call Ratio 해석:
        - < 0.7: 강세 (콜 옵션 거래량 높음)
        - 0.7 ~ 1.0: 중립
        - > 1.0: 약세 (풋 옵션 거래량 높음)
        - > 1.5: 극단적 약세 (역발상 매수 신호 가능)
        
        Returns:
            {
                "volume_ratio": 거래량 기준 P/C 비율,
                "oi_ratio": 미결제약정 기준 P/C 비율,
                "interpretation": 해석
            }
        """
        chain = self.get_options_chain(expiration)
        
        if chain.get("error") or chain["calls"].empty or chain["puts"].empty:
            return {
                "volume_ratio": None,
                "oi_ratio": None,
                "interpretation": "데이터 없음",
                "error": chain.get("error", "데이터 부족")
            }
        
        calls = chain["calls"]
        puts = chain["puts"]
        
        # 거래량 기준 P/C Ratio
        call_volume = calls["volume"].sum() if "volume" in calls.columns else 0
        put_volume = puts["volume"].sum() if "volume" in puts.columns else 0
        
        volume_ratio = put_volume / max(call_volume, 1)
        
        # 미결제약정 기준 P/C Ratio
        call_oi = calls["openInterest"].sum() if "openInterest" in calls.columns else 0
        put_oi = puts["openInterest"].sum() if "openInterest" in puts.columns else 0
        
        oi_ratio = put_oi / max(call_oi, 1)
        
        # 해석
        if volume_ratio < 0.7:
            interpretation = "🟢 강세 신호 (콜 옵션 우위)"
        elif volume_ratio < 1.0:
            interpretation = "🟡 중립"
        elif volume_ratio < 1.5:
            interpretation = "🔴 약세 신호 (풋 옵션 우위)"
        else:
            interpretation = "🟣 극단적 약세 (역발상 매수 검토)"
        
        return {
            "volume_ratio": round(volume_ratio, 3),
            "oi_ratio": round(oi_ratio, 3),
            "call_volume": int(call_volume),
            "put_volume": int(put_volume),
            "expiration": chain.get("expiration"),
            "interpretation": interpretation
        }
    
    def get_iv_percentile(self, lookback_days: int = 252) -> Dict:
        """
        내재변동성(IV) 백분위수 계산
        
        현재 IV가 과거 N일 대비 몇 번째 %인지
        - 90% 이상: IV 매우 높음 (옵션 프리미엄 비쌈)
        - 50% 근처: 평균 수준
        - 10% 이하: IV 매우 낮음 (옵션 프리미엄 쌈)
        
        Returns:
            {
                "current_iv": 현재 평균 IV,
                "iv_percentile": IV 백분위수,
                "interpretation": 해석
            }
        """
        chain = self.get_options_chain()
        
        if chain.get("error") or chain["calls"].empty:
            return {
                "current_iv": None,
                "iv_percentile": None,
                "interpretation": "데이터 없음"
            }
        
        calls = chain["calls"]
        
        # ATM (At-The-Money) 옵션의 IV 추출
        if "impliedVolatility" not in calls.columns:
            return {
                "current_iv": None,
                "iv_percentile": None,
                "interpretation": "IV 데이터 없음"
            }
        
        # 현재 IV (평균)
        current_iv = calls["impliedVolatility"].mean()
        
        # 역사적 변동성과 비교 (간이 계산)
        # 정확한 IV 백분위수는 과거 IV 데이터가 필요하지만,
        # yfinance에서 제공하지 않으므로 현재 IV만 표시
        
        # VIX 레벨과 비교 (간이 해석)
        iv_percent = current_iv * 100
        
        if iv_percent > 50:
            interpretation = "🔴 IV 매우 높음 (옵션 프리미엄 비쌈)"
            percentile_estimate = 90
        elif iv_percent > 30:
            interpretation = "🟡 IV 보통~높음"
            percentile_estimate = 60
        elif iv_percent > 20:
            interpretation = "🟢 IV 보통"
            percentile_estimate = 50
        else:
            interpretation = "🟢 IV 낮음 (옵션 프리미엄 쌈)"
            percentile_estimate = 20
        
        return {
            "current_iv": round(iv_percent, 2),
            "iv_percentile_estimate": percentile_estimate,
            "interpretation": interpretation
        }
    
    def get_max_pain(self, expiration: Optional[str] = None) -> Dict:
        """
        Max Pain 가격 계산
        
        Max Pain: 옵션 매도자에게 가장 유리한 만기 가격
        (풋 + 콜 매수자의 손실이 최대가 되는 가격)
        
        Returns:
            {
                "max_pain_price": Max Pain 가격,
                "current_price": 현재 주가,
                "distance_pct": 현재가 대비 괴리율
            }
        """
        chain = self.get_options_chain(expiration)
        
        if chain.get("error") or chain["calls"].empty or chain["puts"].empty:
            return {"error": "데이터 없음"}
        
        calls = chain["calls"]
        puts = chain["puts"]
        
        # 현재 주가
        stock = self._get_stock()
        try:
            current_price = stock.info.get("regularMarketPrice") or stock.info.get("previousClose", 0)
        except:
            current_price = 0
        
        # 행사가 목록
        strikes = sorted(set(calls["strike"].tolist()))
        
        # 각 행사가에서 총 손실 계산
        pain_values = {}
        for strike in strikes:
            call_pain = 0
            put_pain = 0
            
            # 콜 옵션 손실 (행사가 < strike이면 손실)
            for _, row in calls.iterrows():
                if strike > row["strike"]:
                    oi = row.get("openInterest", 0) or 0
                    call_pain += (strike - row["strike"]) * oi
            
            # 풋 옵션 손실 (행사가 > strike이면 손실)
            for _, row in puts.iterrows():
                if strike < row["strike"]:
                    oi = row.get("openInterest", 0) or 0
                    put_pain += (row["strike"] - strike) * oi
            
            pain_values[strike] = call_pain + put_pain
        
        if not pain_values:
            return {"error": "계산 불가"}
        
        # Max Pain = 손실 합계가 최대인 행사가
        max_pain_price = max(pain_values, key=pain_values.get)
        
        distance_pct = ((max_pain_price - current_price) / current_price * 100) if current_price > 0 else 0
        
        return {
            "max_pain_price": max_pain_price,
            "current_price": current_price,
            "distance_pct": round(distance_pct, 2),
            "expiration": chain.get("expiration")
        }
    
    def get_options_summary(self) -> Dict:
        """옵션 분석 종합 요약"""
        pc_ratio = self.calculate_put_call_ratio()
        iv_data = self.get_iv_percentile()
        max_pain = self.get_max_pain()
        expirations = self.get_available_expirations()
        
        return {
            "ticker": self.ticker,
            "put_call_ratio": pc_ratio,
            "implied_volatility": iv_data,
            "max_pain": max_pain,
            "available_expirations": expirations[:5],  # 최근 5개만
            "analysis_time": datetime.now().isoformat()
        }


if __name__ == "__main__":
    # 테스트 - SPY (S&P 500 ETF)
    print("=== SPY 옵션 분석 ===")
    
    analyzer = OptionsAnalyzer("SPY")
    summary = analyzer.get_options_summary()
    
    print(f"\n[Put/Call Ratio]")
    pc = summary["put_call_ratio"]
    print(f"  거래량 기준: {pc.get('volume_ratio')}")
    print(f"  해석: {pc.get('interpretation')}")
    
    print(f"\n[내재변동성]")
    iv = summary["implied_volatility"]
    print(f"  현재 IV: {iv.get('current_iv')}%")
    print(f"  해석: {iv.get('interpretation')}")
    
    print(f"\n[Max Pain]")
    mp = summary["max_pain"]
    print(f"  Max Pain 가격: ${mp.get('max_pain_price')}")
    print(f"  현재가: ${mp.get('current_price')}")
    print(f"  괴리율: {mp.get('distance_pct')}%")
