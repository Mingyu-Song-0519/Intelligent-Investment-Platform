"""
분할 패널 모드용 미니 뷰 함수들

app.py에서 추출된 7개의 display_*_mini 함수를 제공합니다.
"""
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.dashboard.utils.data_cache import get_cached_stock_data, get_cached_multi_stock_data
from src.analyzers.technical_analyzer import TechnicalAnalyzer
from src.analyzers.risk_manager import RiskManager
from src.models.ensemble_predictor import EnsemblePredictor
from src.optimizers.portfolio_optimizer import PortfolioOptimizer
from src.backtest import Backtester, PerformanceMetrics
from src.backtest.strategies import RSIStrategy, MACDStrategy, MovingAverageStrategy
from src.dashboard.views.chart_utils import create_candlestick_chart, resample_ohlcv

# app.py 기준 프로젝트 루트 (src/dashboard/views -> 위로 3단계)
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent


def display_single_stock_analysis_mini(panel_id: str):
    """분할 모드용 간소화된 단일 종목 분석"""
    # 종목 선택
    stock_options = st.session_state.get('krx_stock_names', ["삼성전자 (005930)"])
    default_idx = stock_options.index("삼성전자 (005930)") if "삼성전자 (005930)" in stock_options else 0

    col1, col2 = st.columns([2, 1])
    with col1:
        selected = st.selectbox("종목 선택", stock_options, index=default_idx, key=f"mini_stock_{panel_id}")
    with col2:
        period = st.selectbox("기간", ["1mo", "3mo", "6mo", "1y"], index=2,
                             format_func=lambda x: {"1mo": "1개월", "3mo": "3개월", "6mo": "6개월", "1y": "1년"}.get(x),
                             key=f"mini_period_{panel_id}")

    ticker_code = st.session_state.get('krx_stock_list', {}).get(selected, "005930") + ".KS"
    ticker_name = selected.split(" (")[0] if "(" in selected else selected

    # 데이터 로드 버튼
    if st.button("📥 데이터 로드", key=f"mini_fetch_{panel_id}", type="primary"):
        with st.spinner(f'{ticker_name} 데이터 로드 중...'):
            try:
                df = get_cached_stock_data(ticker_code, period)
                if not df.empty:
                    analyzer = TechnicalAnalyzer(df)
                    analyzer.add_all_indicators()
                    df = analyzer.get_dataframe()
                    st.session_state[f'mini_data_{panel_id}'] = df
                    st.session_state[f'mini_name_{panel_id}'] = ticker_name
                    st.success(f"✅ {len(df)}개 데이터 로드 완료!")
            except Exception as e:
                logger.error("단일 종목 데이터 로드 오류: %s", e, exc_info=True)
                st.error(f"오류: {e}")

    # 차트 표시
    if f'mini_data_{panel_id}' in st.session_state:
        df = st.session_state.get(f'mini_data_{panel_id}', pd.DataFrame())
        name = st.session_state.get(f'mini_name_{panel_id}', ticker_name)

        if df.empty:
            st.warning("데이터가 없습니다.")
            return

        # 주요 지표
        latest = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else latest
        change = latest['close'] - prev['close']
        change_pct = (change / prev['close']) * 100

        m1, m2, m3 = st.columns(3)
        m1.metric("현재가", f"₩{latest['close']:,.0f}", f"{change:+,.0f} ({change_pct:+.2f}%)")
        m2.metric("RSI", f"{latest.get('rsi', 0):.1f}" if pd.notna(latest.get('rsi')) else "N/A")
        m3.metric("거래량", f"{latest['volume']:,.0f}")

        # 간소화된 차트
        fig = create_candlestick_chart(df, name)
        st.plotly_chart(fig, width='stretch', config={'scrollZoom': False})


def display_multi_stock_comparison_mini(panel_id: str):
    """분할 모드용 간소화된 다중 종목 비교"""
    stock_options = st.session_state.get('krx_stock_names', ["삼성전자 (005930)"])

    selected_stocks = st.multiselect(
        "종목 선택 (최대 5개)",
        stock_options,
        default=["삼성전자 (005930)"] if "삼성전자 (005930)" in stock_options else [],
        max_selections=5,
        key=f"multi_stocks_{panel_id}"
    )

    period = st.selectbox("기간", ["1mo", "3mo", "6mo", "1y"], index=2,
                         format_func=lambda x: {"1mo": "1개월", "3mo": "3개월", "6mo": "6개월", "1y": "1년"}.get(x),
                         key=f"multi_period_{panel_id}")

    if st.button("📥 비교 데이터 로드", key=f"multi_fetch_{panel_id}", type="primary"):
        if selected_stocks:
            data_dict = {}
            for stock in selected_stocks:
                ticker = st.session_state.get('krx_stock_list', {}).get(stock, "005930") + ".KS"
                name = stock.split(" (")[0]
                try:
                    df = get_cached_stock_data(ticker, period)
                    if not df.empty:
                        data_dict[name] = df
                except Exception as e:
                    logger.error("다중 종목 데이터 로드 오류 (%s): %s", ticker, e, exc_info=True)
            st.session_state[f'multi_data_{panel_id}'] = data_dict
            st.success(f"✅ {len(data_dict)}개 종목 로드 완료!")

    if f'multi_data_{panel_id}' in st.session_state:
        data_dict = st.session_state.get(f'multi_data_{panel_id}', {})
        if data_dict:
            # 수익률 비교 차트
            fig = go.Figure()
            for name, df in data_dict.items():
                if not df.empty:
                    returns = (df['close'] / df['close'].iloc[0] - 1) * 100
                    fig.add_trace(go.Scatter(x=df['date'], y=returns, name=name, mode='lines'))
            fig.update_layout(
                title="수익률 비교 (%)",
                template='plotly_dark',
                height=400,
                dragmode=False
            )
            fig.update_xaxes(tickformat="%Y년 %m월")
            st.plotly_chart(fig, width='stretch', config={'scrollZoom': False})


def display_news_sentiment_mini(panel_id: str):
    """분할 모드용 간소화된 뉴스 감성 분석"""
    current_market = st.session_state.get('current_market', 'KR')
    stock_options = st.session_state.get('active_stock_names', ["삼성전자 (005930)"])
    selected = st.selectbox("종목 선택", stock_options, key=f"news_stock_{panel_id}")

    # 종목 코드 추출 (시장별)
    stock_list = st.session_state.get('active_stock_list', {})
    if current_market == 'US':
        ticker = stock_list.get(selected, "AAPL")
    else:
        ticker = stock_list.get(selected, "005930")
    keyword = selected.split(" (")[0] if "(" in selected else selected

    if st.button("📰 뉴스 수집", key=f"news_fetch_{panel_id}", type="primary"):
        with st.spinner("뉴스 수집 중..."):
            try:
                from src.collectors.news_collector import NewsCollector
                collector = NewsCollector()

                if current_market == 'US':
                    # 미국: Yahoo Finance + Google EN
                    news_list = collector.fetch_yahoo_finance_news_rss(ticker, max_items=10)
                else:
                    # 한국: 네이버 금융
                    news_list = collector.fetch_naver_finance_news(ticker, max_pages=2)

                # DataFrame으로 변환
                news_df = pd.DataFrame(news_list) if news_list else pd.DataFrame()
                st.session_state[f'news_data_{panel_id}'] = news_df
                st.success(f"✅ {len(news_df)}개 뉴스 수집!")
            except Exception as e:
                logger.error("뉴스 수집 오류: %s", e, exc_info=True)
                st.error(f"오류: {e}")

    if f'news_data_{panel_id}' in st.session_state:
        news_df = st.session_state.get(f'news_data_{panel_id}', pd.DataFrame())
        if not news_df.empty:
            for _, row in news_df.head(5).iterrows():
                st.markdown(f"**{row.get('title', 'N/A')}**")
                st.caption(f"📅 {row.get('date', 'N/A')}")


def display_ai_prediction_mini(panel_id: str):
    """분할 모드용 AI 예측 (전체 화면과 동일)"""
    current_market = st.session_state.get('current_market', 'KR')
    stock_options = st.session_state.get('active_stock_names', ["삼성전자 (005930)"])
    selected = st.selectbox("종목 선택", stock_options, key=f"ai_stock_{panel_id}")

    stock_list = st.session_state.get('active_stock_list', {})
    if current_market == 'US':
        ticker_code = stock_list.get(selected, "AAPL")
    else:
        ticker_code = stock_list.get(selected, "005930") + ".KS"
    ticker_name = selected.split(" (")[0] if "(" in selected else selected

    col1, col2 = st.columns(2)
    with col1:
        strategy = st.selectbox(
            "앙상블 전략",
            ["weighted_average", "voting", "stacking"],
            format_func=lambda x: {
                "weighted_average": "가중평균",
                "voting": "투표",
                "stacking": "스태킹"
            }[x],
            key=f"ai_strategy_{panel_id}",
            help="가중평균: 비중 합산 / 투표: 다수결 / 스태킹: AI 재학습"
        )
    with col2:
        period = st.selectbox(
            "학습 기간",
            ["1y", "2y", "5y", "10y", "max"],
            index=2,
            key=f"ai_period_{panel_id}",
            help="데이터가 많을수록 정확도 향상"
        )

    # 저장된 모델 검색
    saved_models_dir = PROJECT_ROOT / "src" / "models" / "saved_models"
    use_saved_model = False

    if saved_models_dir.exists():
        safe_ticker = ticker_code.replace(":", "").replace("/", "")
        try:
            files = os.listdir(saved_models_dir)
            candidates = set()
            for f in files:
                if f.startswith(safe_ticker) and any(x in f for x in ["_lstm", "_xgboost", "_transformer"]):
                    parts = f.split('_')
                    if len(parts) >= 2:
                        candidates.add(f"{parts[0]}_{parts[1]}")

            sorted_candidates = sorted(list(candidates), key=lambda x: x.split('_')[1], reverse=True)

            if sorted_candidates:
                latest_date = sorted_candidates[0].split('_')[1]
                formatted_date = f"{latest_date[:4]}-{latest_date[4:6]}-{latest_date[6:]}"
                st.info(f"📅 저장된 모델: {formatted_date}")
                use_saved_model = st.checkbox(
                    "💾 저장된 모델 사용",
                    value=True,
                    key=f"ai_use_saved_{panel_id}",
                    help="재학습 없이 예측만 수행"
                )
        except OSError as e:
            logger.warning("저장된 모델 목록 조회 실패: %s", e)

    # Transformer 및 저장 옵션
    col_opt1, col_opt2, col_opt3 = st.columns(3)
    with col_opt1:
        use_transformer = st.checkbox(
            "🤖 Transformer",
            value=False,
            disabled=use_saved_model,
            key=f"ai_transformer_{panel_id}",
            help="딥러닝 Transformer 모델 포함"
        )
    with col_opt2:
        use_regime = st.checkbox(
            "🌍 Regime",
            value=True,
            disabled=use_saved_model,
            key=f"ai_regime_{panel_id}",
            help="시장 국면(Regime)에 따른 가중치 조절"
        )
    with col_opt3:
        save_model = st.checkbox(
            "💾 저장",
            value=True,
            disabled=use_saved_model,
            key=f"ai_save_{panel_id}",
            help="학습된 모델을 저장"
        )

    if st.button("🚀 예측 실행", key=f"ai_run_{panel_id}", type="primary"):
        with st.status("🚀 AI 예측 수행 중...", expanded=True) as status:
            status.write("🔄 데이터 분석 및 모델 로딩...")
            try:
                # 데이터 수집
                df = get_cached_stock_data(ticker_code, period)
                if df.empty:
                    st.error("데이터를 가져올 수 없습니다")
                    return

                # 기술적 지표 추가
                analyzer = TechnicalAnalyzer(df)
                analyzer.add_all_indicators()
                df = analyzer.get_dataframe()

                # 앙상블 예측
                predictor = EnsemblePredictor(include_transformer=use_transformer)
                result = predictor.train_and_predict(df, strategy=strategy)

                if use_regime:
                    from src.models.regime_predictor import RegimeAwarePredictor
                    regime_predictor = RegimeAwarePredictor(ensemble_predictor=predictor)
                    regime_result = regime_predictor.predict(df, use_regime_weights=True)

                    # 결과 갱신
                    last_close = df['close'].iloc[-1]
                    pred_close = regime_result['prediction']
                    result['direction'] = "상승" if pred_close and pred_close > last_close else "하락"
                    result['confidence'] = regime_result['confidence']
                    result['regime'] = regime_result['regime'].description
                else:
                    result['regime'] = "N/A"

                # 모델 저장
                if save_model and not use_saved_model:
                    try:
                        safe_ticker = ticker_code.replace(":", "").replace("/", "").replace(".KS", "")
                        predictor.save_models(safe_ticker)
                    except (OSError, IOError) as e:
                        logger.warning("모델 저장 실패: %s", e)

                st.session_state[f'ai_result_{panel_id}'] = result
                status.update(label="✅ 예측 완료!", state="complete", expanded=False)
                st.success("✅ 예측 완료!")
            except Exception as e:
                logger.error("AI 예측 오류: %s", e, exc_info=True)
                st.error(f"오류: {e}")

    if f'ai_result_{panel_id}' in st.session_state:
        result = st.session_state.get(f'ai_result_{panel_id}', None)
        if result:
            direction = result.get('direction', 'N/A')
            confidence = result.get('confidence', 0) * 100
            color = "🟢" if direction == "상승" else "🔴" if direction == "하락" else "⚪"
            st.markdown(f"### {color} 예측: **{direction}** (신뢰도: {confidence:.1f}%)")
            if 'regime' in result and result.get('regime') != "N/A":
                st.caption(f"🌍 시장 국면: {result['regime']}")


def display_backtest_mini(panel_id: str):
    """분할 모드용 백테스팅"""
    stock_options = st.session_state.get('krx_stock_names', ["삼성전자 (005930)"])
    selected = st.selectbox("종목 선택", stock_options, key=f"bt_stock_{panel_id}")
    ticker_code = st.session_state.get('krx_stock_list', {}).get(selected, "005930") + ".KS"

    col1, col2 = st.columns(2)
    with col1:
        strategy_type = st.selectbox("전략", ["RSI", "MACD", "이동평균"], key=f"bt_strategy_{panel_id}")
    with col2:
        period = st.selectbox("기간", ["1y", "2y", "5y"], index=1, key=f"bt_period_{panel_id}")

    initial_capital = st.number_input("초기 자본 (원)", value=10000000, step=1000000, key=f"bt_capital_{panel_id}")

    if st.button("▶️ 백테스트 실행", key=f"bt_run_{panel_id}", type="primary"):
        with st.spinner("백테스트 중..."):
            try:
                df = get_cached_stock_data(ticker_code, period)
                if df.empty:
                    st.error("데이터를 가져올 수 없습니다")
                    return

                analyzer = TechnicalAnalyzer(df)
                analyzer.add_all_indicators()
                df = analyzer.get_dataframe().set_index('date')

                # 전략 선택
                if strategy_type == "RSI":
                    strategy = RSIStrategy()
                elif strategy_type == "MACD":
                    strategy = MACDStrategy()
                else:
                    strategy = MovingAverageStrategy()

                backtester = Backtester(df, initial_capital=initial_capital)
                results = backtester.run(strategy)

                metrics = PerformanceMetrics(results['equity'], initial_capital)
                trades_df = backtester.get_trades_df()
                metrics_dict = metrics.get_all_metrics(trades_df)

                st.session_state[f'bt_result_{panel_id}'] = {
                    'results': results,
                    'metrics': metrics_dict,
                    'dates': backtester.df.index.tolist()
                }
                st.success(f"✅ 완료 (거래: {len(trades_df)}회)")
            except Exception as e:
                logger.error("백테스트 오류: %s", e, exc_info=True)
                st.error(f"오류: {e}")

    if f'bt_result_{panel_id}' in st.session_state:
        data = st.session_state.get(f'bt_result_{panel_id}', {})
        m = data['metrics']

        c1, c2 = st.columns(2)
        c1.metric("총 수익률", f"{m['total_return']*100:.2f}%")
        c2.metric("MDD", f"{m['max_drawdown']*100:.2f}%")


def display_portfolio_optimization_mini(panel_id: str):
    """분할 모드용 포트폴리오 최적화"""
    stock_options = st.session_state.get('krx_stock_names', ["삼성전자 (005930)"])

    selected_stocks = st.multiselect(
        "종목 선택 (최소 2개)",
        stock_options,
        default=["삼성전자 (005930)"] if "삼성전자 (005930)" in stock_options else [],
        max_selections=5,
        key=f"port_stocks_{panel_id}"
    )

    period = st.selectbox("분석 기간", ["1y", "2y", "5y"], index=1, key=f"port_period_{panel_id}")

    if len(selected_stocks) < 2:
        st.warning("최소 2개 종목을 선택해주세요.")
        return

    if st.button("🎯 최적화 실행", key=f"port_run_{panel_id}", type="primary"):
        with st.spinner("최적화 중..."):
            try:
                tickers = [st.session_state.get('krx_stock_list', {}).get(s, "005930") + ".KS" for s in selected_stocks]
                results = get_cached_multi_stock_data(tickers, period)

                if len(results) < 2:
                    st.error("최소 2개 종목의 데이터가 필요합니다.")
                    return

                returns_data = {}
                for ticker, df in results.items():
                    if not df.empty:
                        returns_data[ticker] = df.set_index('date')['close'].pct_change()

                returns_df = pd.DataFrame(returns_data).dropna()

                optimizer = PortfolioOptimizer(returns_df, risk_free_rate=0.035)
                max_sharpe = optimizer.optimize_max_sharpe()

                st.session_state[f'port_result_{panel_id}'] = max_sharpe
                st.success("✅ 최적화 완료!")
            except Exception as e:
                logger.error("포트폴리오 최적화 오류: %s", e, exc_info=True)
                st.error(f"오류: {e}")

    if f'port_result_{panel_id}' in st.session_state:
        result = st.session_state.get(f'port_result_{panel_id}', {})
        if result.get('success'):
            st.metric("기대 수익률", f"{result['return']*100:.2f}%")
            st.metric("샤프 비율", f"{result['sharpe']:.2f}")


def display_risk_management_mini(panel_id: str):
    """분할 모드용 리스크 관리"""
    stock_options = st.session_state.get('krx_stock_names', ["삼성전자 (005930)"])
    selected = st.selectbox("종목 선택", stock_options, key=f"risk_stock_{panel_id}")
    ticker_code = st.session_state.get('krx_stock_list', {}).get(selected, "005930") + ".KS"

    col1, col2 = st.columns(2)
    with col1:
        portfolio_value = st.number_input("포트폴리오 가치 (원)", value=100000000, step=10000000, key=f"risk_value_{panel_id}")
    with col2:
        confidence = st.slider("신뢰수준 (%)", 90, 99, 95, key=f"risk_conf_{panel_id}") / 100

    if st.button("📊 리스크 분석", key=f"risk_run_{panel_id}", type="primary"):
        with st.spinner("분석 중..."):
            try:
                df = get_cached_stock_data(ticker_code, "2y")
                if df.empty:
                    st.error("데이터를 가져올 수 없습니다")
                    return

                returns = df['close'].pct_change().dropna()
                rm = RiskManager(returns, portfolio_value)
                summary = rm.get_risk_summary(confidence, horizon=10)

                st.session_state[f'risk_result_{panel_id}'] = summary
                st.success("✅ 분석 완료!")
            except Exception as e:
                logger.error("리스크 분석 오류: %s", e, exc_info=True)
                st.error(f"오류: {e}")

    if f'risk_result_{panel_id}' in st.session_state:
        summary = st.session_state.get(f'risk_result_{panel_id}', {})
        st.markdown("### 📉 VaR")
        st.metric("Historical VaR", f"₩{summary['historical_var']['var_amount']:,.0f}")
        st.metric("CVaR", f"₩{summary['cvar']['cvar_amount']:,.0f}")


__all__ = [
    'display_single_stock_analysis_mini',
    'display_multi_stock_comparison_mini',
    'display_news_sentiment_mini',
    'display_ai_prediction_mini',
    'display_backtest_mini',
    'display_portfolio_optimization_mini',
    'display_risk_management_mini',
]
