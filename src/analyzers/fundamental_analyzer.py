"""
펀더멘털 분석 모듈 - PER, PBR, ROE, 배당수익률 등 기업 가치 지표
2024-2025 트렌드: 기술적 분석 + 펀더멘털 결합으로 투자 판단 정확도 향상
"""
import logging
import yfinance as yf
import pandas as pd
import numpy as np
from typing import Dict, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


class FundamentalAnalyzer:
    """펀더멘털(기업 가치) 분석 클래스"""
    
    def __init__(self, ticker: str):
        """
        Args:
            ticker: 종목 코드 (예: "005930.KS" 또는 "AAPL")
        """
        self.ticker = ticker
        self._stock = None
        self._info = None
        self._cache_timestamp = None
        self._cache_ttl = 3600  # 1시간 캐싱
    
    def _get_stock_info(self) -> Dict:
        """yfinance에서 종목 정보 가져오기 (캐싱)"""
        now = datetime.now()
        
        if (self._info is not None and
            self._cache_timestamp is not None and
            (now - self._cache_timestamp).total_seconds() < self._cache_ttl):
            return self._info
        
        try:
            self._stock = yf.Ticker(self.ticker)
            self._info = self._stock.info
            self._cache_timestamp = now
            return self._info
        except Exception as e:
            logger.error(f"종목 정보 수집 오류: {e}")
            return {}
    
    def get_valuation_metrics(self) -> Dict:
        """
        밸류에이션 지표 수집 (PER, PBR, EV/EBITDA)
        
        Returns:
            {
                "per": 주가수익비율,
                "forward_per": 선행 PER,
                "pbr": 주가순자산비율,
                "ev_ebitda": EV/EBITDA,
                "market_cap": 시가총액
            }
        """
        info = self._get_stock_info()
        
        return {
            "per": info.get("trailingPE"),
            "forward_per": info.get("forwardPE"),
            "pbr": info.get("priceToBook"),
            "ev_ebitda": info.get("enterpriseToEbitda"),
            "market_cap": info.get("marketCap"),
            "market_cap_formatted": self._format_number(info.get("marketCap"))
        }
    
    def get_profitability_metrics(self) -> Dict:
        """
        수익성 지표 수집 (ROE, ROA, 영업이익률)
        
        Returns:
            {
                "roe": 자기자본이익률,
                "roa": 총자산이익률,
                "profit_margin": 순이익률,
                "operating_margin": 영업이익률,
                "gross_margin": 매출총이익률
            }
        """
        info = self._get_stock_info()
        
        return {
            "roe": info.get("returnOnEquity"),
            "roa": info.get("returnOnAssets"),
            "profit_margin": info.get("profitMargins"),
            "operating_margin": info.get("operatingMargins"),
            "gross_margin": info.get("grossMargins")
        }
    
    def get_financial_health(self) -> Dict:
        """
        재무 건전성 지표 (부채비율, 유동비율)
        
        Returns:
            {
                "debt_to_equity": 부채비율,
                "current_ratio": 유동비율,
                "quick_ratio": 당좌비율,
                "total_debt": 총부채,
                "total_cash": 현금 및 현금성 자산
            }
        """
        info = self._get_stock_info()
        
        return {
            "debt_to_equity": info.get("debtToEquity"),
            "current_ratio": info.get("currentRatio"),
            "quick_ratio": info.get("quickRatio"),
            "total_debt": info.get("totalDebt"),
            "total_cash": info.get("totalCash"),
            "total_debt_formatted": self._format_number(info.get("totalDebt")),
            "total_cash_formatted": self._format_number(info.get("totalCash"))
        }
    
    def get_dividend_info(self) -> Dict:
        """
        배당 정보 수집
        
        Returns:
            {
                "dividend_yield": 배당수익률,
                "dividend_rate": 주당 배당금,
                "payout_ratio": 배당성향,
                "ex_dividend_date": 배당락일
            }
        """
        info = self._get_stock_info()
        
        ex_date = info.get("exDividendDate")
        if ex_date:
            ex_date = datetime.fromtimestamp(ex_date).strftime("%Y-%m-%d")
        
        return {
            "dividend_yield": info.get("dividendYield"),
            "dividend_rate": info.get("dividendRate"),
            "payout_ratio": info.get("payoutRatio"),
            "trailing_annual_yield": info.get("trailingAnnualDividendYield"),
            "ex_dividend_date": ex_date
        }
    
    def get_growth_metrics(self) -> Dict:
        """
        성장성 지표
        
        Returns:
            {
                "revenue_growth": 매출 성장률,
                "earnings_growth": 이익 성장률,
                "earnings_quarterly_growth": 분기별 이익 성장률
            }
        """
        info = self._get_stock_info()
        
        return {
            "revenue_growth": info.get("revenueGrowth"),
            "earnings_growth": info.get("earningsGrowth"),
            "earnings_quarterly_growth": info.get("earningsQuarterlyGrowth")
        }
    
    def get_company_info(self) -> Dict:
        """
        기업 기본 정보
        """
        info = self._get_stock_info()
        
        return {
            "name": info.get("shortName") or info.get("longName"),
            "sector": info.get("sector"),
            "industry": info.get("industry"),
            "country": info.get("country"),
            "website": info.get("website"),
            "employees": info.get("fullTimeEmployees")
        }
    
    def get_fundamental_summary(self) -> Dict:
        """전체 펀더멘털 요약"""
        valuation = self.get_valuation_metrics()
        profitability = self.get_profitability_metrics()
        health = self.get_financial_health()
        dividend = self.get_dividend_info()
        growth = self.get_growth_metrics()
        company = self.get_company_info()
        
        # 종합 점수 계산 (간이)
        score = 50  # 기본값
        
        # PER 평가 (10-20 이상적)
        per = valuation.get("per")
        if per:
            if per < 10:
                score += 10  # 저평가
            elif per > 30:
                score -= 10  # 고평가
        
        # ROE 평가 (15% 이상 우수)
        roe = profitability.get("roe")
        if roe:
            if roe > 0.15:
                score += 15
            elif roe < 0.05:
                score -= 10
        
        # 부채비율 평가 (100% 이하 안전)
        debt = health.get("debt_to_equity")
        if debt:
            if debt < 100:
                score += 10
            elif debt > 200:
                score -= 15
        
        # 배당수익률 (있으면 가점)
        div_yield = dividend.get("dividend_yield")
        if div_yield and div_yield > 0.02:
            score += 5
        
        score = max(0, min(100, score))
        
        # 등급 판정
        if score >= 70:
            grade = "🟢 우량"
        elif score >= 50:
            grade = "🟡 보통"
        else:
            grade = "🔴 주의"
        
        return {
            "company": company,
            "valuation": valuation,
            "profitability": profitability,
            "financial_health": health,
            "dividend": dividend,
            "growth": growth,
            "fundamental_score": score,
            "grade": grade
        }
    
    def get_fundamental_card_data(self) -> Dict:
        """UI 카드 표시용 간소화 데이터"""
        summary = self.get_fundamental_summary()
        
        val = summary["valuation"]
        prof = summary["profitability"]
        health = summary["financial_health"]
        div = summary["dividend"]
        
        # 색상 코드 결정 함수
        def get_per_color(per):
            if per is None:
                return "⚪"
            if per < 15:
                return "🟢"  # 저평가
            elif per < 25:
                return "🟡"
            else:
                return "🔴"  # 고평가
        
        def get_roe_color(roe):
            if roe is None:
                return "⚪"
            if roe > 0.15:
                return "🟢"  # 우수
            elif roe > 0.08:
                return "🟡"
            else:
                return "🔴"
        
        def get_debt_color(debt):
            if debt is None:
                return "⚪"
            if debt < 100:
                return "🟢"  # 안전
            elif debt < 200:
                return "🟡"
            else:
                return "🔴"
        
        return {
            "per": {
                "value": val.get("per"),
                "color": get_per_color(val.get("per")),
                "label": "PER (주가수익비율)"
            },
            "pbr": {
                "value": val.get("pbr"),
                "color": get_per_color(val.get("pbr") * 10 if val.get("pbr") else None),
                "label": "PBR (주가순자산비율)"
            },
            "roe": {
                "value": prof.get("roe"),
                "color": get_roe_color(prof.get("roe")),
                "label": "ROE (자기자본이익률)"
            },
            "debt_ratio": {
                "value": health.get("debt_to_equity"),
                "color": get_debt_color(health.get("debt_to_equity")),
                "label": "부채비율"
            },
            "dividend_yield": {
                "value": div.get("dividend_yield"),
                "color": "🟢" if div.get("dividend_yield") and div.get("dividend_yield") > 0.02 else "🟡",
                "label": "배당수익률"
            },
            "score": summary["fundamental_score"],
            "grade": summary["grade"]
        }
    
    def _format_number(self, num: Optional[float]) -> str:
        """큰 숫자를 읽기 쉽게 포맷"""
        if num is None:
            return "N/A"
        
        if num >= 1e12:
            return f"{num/1e12:.1f}조"
        elif num >= 1e8:
            return f"{num/1e8:.1f}억"
        elif num >= 1e4:
            return f"{num/1e4:.1f}만"
        else:
            return f"{num:,.0f}"


if __name__ == "__main__":
    # 테스트 - 삼성전자
    print("=== 삼성전자 펀더멘털 분석 ===")
    analyzer = FundamentalAnalyzer("005930.KS")
    summary = analyzer.get_fundamental_summary()
    
    print(f"\n회사: {summary['company']['name']}")
    print(f"업종: {summary['company']['sector']}")
    print(f"\n[밸류에이션]")
    print(f"PER: {summary['valuation']['per']}")
    print(f"PBR: {summary['valuation']['pbr']}")
    print(f"\n[수익성]")
    print(f"ROE: {summary['profitability']['roe']}")
    print(f"\n[배당]")
    print(f"배당수익률: {summary['dividend']['dividend_yield']}")
    print(f"\n종합 점수: {summary['fundamental_score']}")
    print(f"등급: {summary['grade']}")
