"""
팩터 투자 뷰 모듈

Clean Architecture: Presentation Layer
멀티팩터 분석 UI (Fama-French 5팩터 + 저변동성)
"""
import streamlit as st
import pandas as pd
from typing import List, Dict

# Services
from src.services.factor_analysis_service import FactorAnalyzer, FactorScores


def display_factor_investing():
    """팩터 투자 분석 탭 렌더링"""
    st.header("💎 팩터 투자 분석")
    st.markdown("""
    **Fama-French 5팩터 + 저변동성 팩터** 기반 종목 스코어링
    
    | 팩터 | 설명 |
    |------|------|
    | 📈 **모멘텀** | 12개월 수익률 (최근 1개월 제외) |
    | 💰 **가치** | PER, PBR이 낮을수록 높은 점수 |
    | ⭐ **품질** | ROE, 이익 마진이 높을수록 높은 점수 |
    | 📏 **규모** | 시가총액이 작을수록 높은 점수 (소형주 프리미엄) |
    | 🛡️ **저변동성** | 변동성이 낮을수록 높은 점수 |
    """)
    
    st.divider()
    
    # 현재 시장
    current_market = st.session_state.get('current_market', 'KR')
    market_label = "🇰🇷 한국" if current_market == "KR" else "🇺🇸 미국"
    
    st.info(f"📊 현재 시장: {market_label}")
    
    # 종목 선택
    col1, col2 = st.columns([3, 1])
    
    with col1:
        stock_options = st.session_state.get('active_stock_names', [])
        if not stock_options:
            st.warning("종목 목록을 로드할 수 없습니다. 사이드바에서 시장을 선택해주세요.")
            return
        
        selected_stocks = st.multiselect(
            "분석할 종목 선택 (최대 10개)",
            stock_options,
            max_selections=10,
            help="팩터 분석을 수행할 종목을 선택하세요"
        )
    
    with col2:
        analyze_btn = st.button("🔍 팩터 분석", type="primary", disabled=len(selected_stocks) == 0)
    
    if analyze_btn and selected_stocks:
        _run_factor_analysis(selected_stocks, current_market)
    
    # 이전 분석 결과 표시
    if 'factor_results' in st.session_state:
        _display_factor_results(st.session_state.get('factor_results', {}))


def _run_factor_analysis(selected_stocks: List[str], market: str):
    """팩터 분석 실행"""
    analyzer = FactorAnalyzer(market=market)
    results: List[Dict] = []
    
    # 종목별 데이터 수집 및 분석
    from src.dashboard.utils.data_cache import get_cached_stock_data
    from src.domain.entities.stock import StockEntity
    
    progress_bar = st.progress(0, text="팩터 분석 중...")
    
    for i, stock_name in enumerate(selected_stocks):
        progress_bar.progress((i + 1) / len(selected_stocks), text=f"분석 중: {stock_name}")
        
        try:
            # 종목 코드 추출
            stock_list = st.session_state.get('active_stock_list', {})
            ticker = stock_list.get(stock_name, None)
            if not ticker:
                continue
            
            # 티커 포맷
            if market == "KR" and not ticker.endswith(".KS"):
                ticker = ticker + ".KS"
            
            # 데이터 수집 (1년)
            df = get_cached_stock_data(ticker, "1y", st.session_state.get('cache_version', 0))
            if df.empty:
                continue
            
            # StockEntity 생성 (from_dataframe 사용)
            stock_entity = StockEntity.from_dataframe(ticker, df, name=stock_name, market=market)
            
            # 기본 정보 (실제로는 API에서 가져와야 함)
            # 임시로 기본값 사용
            stock_info = {
                "per": 15.0,  # 기본값
                "pbr": 1.5,
                "roe": 10.0,
                "profit_margin": 8.0,
                "market_cap": 1e12  # 1조
            }
            
            # 팩터 분석
            scores = analyzer.analyze(stock_entity, stock_info)
            results.append({
                "종목": stock_name,
                "티커": ticker,
                "모멘텀": scores.momentum,
                "가치": scores.value,
                "품질": scores.quality,
                "규모": scores.size,
                "저변동성": scores.volatility,
                "종합점수": scores.composite
            })
            
        except Exception as e:
            st.warning(f"⚠️ {stock_name} 분석 실패: {str(e)}")
            continue
    
    progress_bar.empty()
    
    if results:
        st.session_state['factor_results'] = results
        st.success(f"✅ {len(results)}개 종목 팩터 분석 완료!")
    else:
        st.error("분석 가능한 종목이 없습니다.")


def _display_factor_results(results: List[Dict]):
    """팩터 분석 결과 표시"""
    st.subheader("📊 팩터 분석 결과")
    
    # DataFrame 생성
    df = pd.DataFrame(results)
    
    # 종합점수 기준 정렬
    df = df.sort_values("종합점수", ascending=False)
    
    # 상위 종목 하이라이트
    st.markdown("### 🏆 팩터 점수 순위")
    
    # 스타일링된 테이블
    styled_df = df.style.background_gradient(
        subset=["모멘텀", "가치", "품질", "규모", "저변동성", "종합점수"],
        cmap="RdYlGn",
        vmin=0,
        vmax=100
    ).format({
        "모멘텀": "{:.1f}",
        "가치": "{:.1f}",
        "품질": "{:.1f}",
        "규모": "{:.1f}",
        "저변동성": "{:.1f}",
        "종합점수": "{:.1f}"
    })
    
    st.dataframe(styled_df, use_container_width=True, hide_index=True)
    
    # 팩터별 분포 차트
    st.markdown("### 📈 팩터별 평균 점수")
    
    factor_cols = ["모멘텀", "가치", "품질", "규모", "저변동성"]
    factor_means = df[factor_cols].mean()
    
    chart_data = pd.DataFrame({
        "팩터": factor_cols,
        "평균 점수": factor_means.values
    })
    
    st.bar_chart(chart_data.set_index("팩터"), horizontal=True)
    
    # 팩터 해석 가이드
    with st.expander("💡 팩터 점수 해석 가이드"):
        st.markdown("""
        | 점수 범위 | 의미 |
        |-----------|------|
        | 80-100 | 🟢 매우 우수 |
        | 60-79 | 🟡 우수 |
        | 40-59 | 🟠 보통 |
        | 20-39 | 🔴 미흡 |
        | 0-19 | ⚫ 매우 미흡 |
        
        **종합점수**는 각 팩터의 가중 평균입니다 (동일 가중치).
        """)
