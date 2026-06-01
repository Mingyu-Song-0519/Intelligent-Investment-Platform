"""
AI 예측 뷰 (Phase 2 완전 모듈화 버전)
앙상블 전략, 뉴스 감성 분석, Gemini LLM, 시장 국면 등 전체 옵션 포함
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
from pathlib import Path

# 모델 및 분석 관련
from src.models.ensemble_predictor import EnsemblePredictor
from src.models.predictor import TENSORFLOW_AVAILABLE, XGBOOST_AVAILABLE
from src.collectors.stock_collector import StockDataCollector
from src.analyzers.technical_analyzer import TechnicalAnalyzer
from config import ENSEMBLE_CONFIG

# 캐시된 데이터 로드 (순환 import 방지: app.py 대신 data_cache.py에서 import)
from src.dashboard.utils.data_cache import get_cached_stock_data

# 서비스 레이어
try:
    from src.infrastructure.repositories.model_repository import ModelRepository
    from src.services.incremental_learning_service import IncrementalLearningService
    SERVICE_AVAILABLE = True
except ImportError:
    SERVICE_AVAILABLE = False

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent


def display_ai_prediction():
    """AI 가격 예측 뷰 (완전한 옵션 포함)"""
    st.header("🔮 AI 가격 예측")

    # 모델 가용성 안내
    if not TENSORFLOW_AVAILABLE or not XGBOOST_AVAILABLE:
        unavailable = []
        if not TENSORFLOW_AVAILABLE:
            unavailable.append("LSTM (TensorFlow/Keras 미설치)")
        if not XGBOOST_AVAILABLE:
            unavailable.append("XGBoost (xgboost 미설치)")
        st.info(
            f"ℹ️ 현재 환경에서 사용 불가능한 모델: **{', '.join(unavailable)}**\n\n"
            "로컬에서 `pip install -e '.[ml-boost,ml-tf]'` 설치 시 모든 모델을 사용할 수 있습니다."
        )

    selected_ticker = st.session_state.get('selected_ticker')
    selected_stock = st.session_state.get('selected_stock', '삼성전자')
    
    if not selected_ticker:
        st.warning("👈 사이드바에서 예측할 종목을 선택하세요.")
        return
    
    ticker_code = selected_ticker
    ticker_name = selected_stock
    
    # ========== 전략 및 기간 설정 ==========
    st.markdown("### ⚙️ 예측 설정")
    col1, col2 = st.columns(2)
    
    with col1:
        strategy = st.selectbox(
            "앙상블 전략",
            ["weighted_average", "voting", "stacking"],
            format_func=lambda x: {
                "weighted_average": "🎯 가중평균 (Weighted Average)",
                "voting": "🗳️ 투표 (Voting)",
                "stacking": "📚 스태킹 (Stacking)"
            }[x],
            help="""
            🤖 앙상블 전략 설명:
            
            1. 가중평균: 각 모델의 예측값에 비중을 두어 합산합니다.
            2. 투표: 모델들의 다수결로 상승/하락을 결정합니다.
            3. 스태킹: 모델들의 예측 결과를 AI가 다시 학습하여 최종 판단합니다.
            """
        )
        
        # 전략 설명
        strategy_desc = {
            "weighted_average": "💡 성과가 좋은 모델에 더 높은 비중을 주어 예측 오차를 줄입니다.",
            "voting": "💡 여러 전문가의 의견을 듣고 다수결로 결정하는 것과 같습니다.",
            "stacking": "💡 여러 모델의 장점을 결합해 시너지를 내는 고도화된 방식입니다."
        }
        st.caption(strategy_desc[strategy])
    
    with col2:
        period = st.selectbox(
            "학습 기간",
            ["1y", "2y", "5y", "10y", "max"],
            index=2,
            help="Transformer 등 딥러닝 모델은 데이터가 많을수록(기간이 길수록) 성능이 좋아집니다."
        )
    
    # ========== 저장된 모델 확인 ==========
    import os
    saved_models_dir = PROJECT_ROOT / "src" / "models" / "saved_models"
    use_saved_model = False
    use_incremental = False
    latest_model_prefix = None
    
    if saved_models_dir.exists():
        safe_ticker = ticker_code.replace(":", "").replace("/", "").replace(".KS", "")
        try:
            files = os.listdir(saved_models_dir)
            candidates = set()
            for f in files:
                if f.startswith(safe_ticker) and any(x in f for x in ["_lstm", "_xgboost", "_transformer"]):
                    for suffix in ["_lstm", "_xgboost", "_transformer"]:
                        if suffix in f:
                            prefix = f.split(suffix)[0]
                            candidates.add(prefix)
                            break
            
            sorted_candidates = sorted(list(candidates), reverse=True)
            
            if sorted_candidates:
                latest_model_prefix = sorted_candidates[0]
                parts = latest_model_prefix.split('_')
                latest_date = parts[-1] if parts[-1].isdigit() and len(parts[-1]) == 8 else "Unknown"
                formatted_date = f"{latest_date[:4]}-{latest_date[4:6]}-{latest_date[6:]}" if latest_date != "Unknown" else latest_date
                
                st.info(f"📅 최근 학습된 모델이 있습니다 ({formatted_date})")
                use_saved_model = st.checkbox(
                    "💾 저장된 모델 불러오기 (재학습 건너뛰기)",
                    value=True,
                    help=f"체크하면 '{formatted_date}'에 학습된 모델을 불러와서 예측만 수행합니다."
                )
        except Exception as e:
            st.warning(f"모델 검색 중 오류: {e}")
    
    # ========== 고급 설정 ==========
    st.markdown("### ⚡ 고급 설정")
    col_opt1, col_opt2, col_opt3, col_opt4 = st.columns(4)
    
    with col_opt1:
        use_transformer = st.checkbox(
            "🤖 Transformer 포함",
            value=False,
            disabled=use_saved_model,
            help="Transformer(Attention) 모델을 포함하여 예측합니다. (시간이 더 소요됨)"
        )
    
    with col_opt2:
        use_regime = st.checkbox(
            "🌍 시장 국면 반영",
            value=True,
            help="현재 시장 상황(강세/약세/횡보)을 감지하고, 이에 맞춰 AI 모델 가중치를 자동으로 조절합니다."
        )
    
    with col_opt3:
        use_sentiment = st.checkbox(
            "📰 감성 분석 포함",
            value=False,
            help="뉴스 감성 점수를 AI 모델 입력으로 추가합니다."
        )
    
    with col_opt4:
        save_model = st.checkbox(
            "💾 학습된 모델 저장",
            value=True,
            disabled=use_saved_model,
            help="새로 학습한 모델을 저장하여 나중에 재사용합니다."
        )
    
    # Gemini LLM 옵션 (감성 분석 활성화 시에만 표시)
    use_llm_sentiment = False
    if use_sentiment:
        use_llm_sentiment = st.checkbox(
            "🧠 Gemini LLM 감성 분석",
            value=False,
            help="Gemini AI를 활용한 고급 감성 분석을 사용합니다. API 키 필요."
        )
    
    # ========== 예측 실행 ==========
    if st.button("🚀 예측 실행", type="primary"):
        with st.status("🚀 AI 심층 분석 진행 중...", expanded=True) as status:
            try:
                status.write("📊 시장 데이터 수집 중...")
                df = get_cached_stock_data(ticker_code, period)
                
                if df.empty:
                    st.error("데이터를 가져올 수 없습니다.")
                    return
                
                # 기술적 지표 추가
                analyzer = TechnicalAnalyzer(df)
                analyzer.add_all_indicators()
                df = analyzer.get_dataframe()
                
                # 감성 분석 피처 통합 (옵션)
                feature_cols = None
                if use_sentiment:
                    llm_msg = " (🧠 Gemini LLM)" if use_llm_sentiment else ""
                    status.write(f"📰 뉴스 감성 분석 중...{llm_msg}")
                    try:
                        from src.models.sentiment_feature_integrator import create_enhanced_features
                        current_market = st.session_state.get('current_market', 'KR')
                        df, feature_cols = create_enhanced_features(
                            df, ticker_code, ticker_name, current_market,
                            include_sentiment=True,
                            use_llm=use_llm_sentiment
                        )
                        from src.services.sentiment_analysis_service import SentimentAnalysisService
                        sentiment_feature_count = len(SentimentAnalysisService.get_sentiment_feature_columns())
                        st.success(f"✅ 감성 피처 {sentiment_feature_count}개 추가됨{llm_msg}")
                    except Exception as e:
                        st.warning(f"감성 분석 생략: {str(e)}")
                
                # 앙상블 예측기 초기화
                ensemble = EnsemblePredictor(strategy=strategy)
                
                # 모델 로드 또는 학습
                if use_saved_model and latest_model_prefix:
                    status.write(f"💾 저장된 모델 불러오는 중... ({latest_model_prefix})")
                    try:
                        load_path = saved_models_dir / latest_model_prefix
                        ensemble.load_models(str(load_path))
                        st.success("✅ 모델 로드 완료!")
                    except Exception as e:
                        st.error(f"모델 로드 실패: {str(e)}")
                        st.warning("⚠️ '저장된 모델 불러오기' 체크를 해제하고 다시 시도해주세요.")
                        return
                else:
                    # 모델 학습
                    train_size = int(len(df) * 0.8)
                    train_df = df.iloc[:train_size].copy()
                    
                    model_name = "LSTM + XGBoost" + (" + Transformer" if use_transformer else "")
                    status.write(f"🧠 새 모델 학습 중... ({model_name})")
                    
                    ensemble.train_models(
                        train_df,
                        train_lstm=True,
                        train_xgboost=True,
                        train_transformer=use_transformer,
                        verbose=0
                    )
                    
                    # 모델 저장
                    if save_model:
                        save_dir = (PROJECT_ROOT / "src" / "models" / "saved_models").resolve()
                        os.makedirs(save_dir, exist_ok=True)
                        
                        safe_ticker = ticker_code.replace(":", "").replace("/", "").replace(".KS", "")
                        today = datetime.now().strftime("%Y%m%d")
                        save_path = save_dir / f"{safe_ticker}_{today}"
                        
                        save_metadata = {
                            'last_train_date': datetime.now().isoformat(),
                            'data_end_date': df['date'].max().isoformat(),
                            'total_samples': len(df),
                            'ticker': ticker_code
                        }
                        
                        ensemble.save_models(str(save_path), metadata=save_metadata)
                        st.success(f"💾 모델 저장 완료!")
                
                # 예측 실행
                current_price = df['close'].iloc[-1]
                
                if use_regime:
                    # 시장 국면 기반 예측
                    try:
                        from src.models.regime_predictor import RegimeAwarePredictor
                        status.write("🌍 시장 국면 분석 중...")
                        regime_predictor = RegimeAwarePredictor(ensemble_predictor=ensemble)
                        regime_result = regime_predictor.predict(df, use_regime_weights=True)
                        
                        predicted_price = regime_result['prediction']
                        final_confidence = regime_result['confidence']
                        regime_info = regime_result['regime']
                        
                        price_pred = {'ensemble_prediction': predicted_price, 'individual_predictions': {}}
                        direction_pred = {
                            'ensemble_prediction': 'up' if predicted_price and predicted_price > current_price else 'down',
                            'confidence_score': final_confidence,
                            'individual_predictions': {}
                        }
                        
                        st.success(f"✅ 시장 국면: {regime_info.description} (신뢰도 {regime_info.confidence:.0%})")
                        st.info(f"💡 투자 권고: {regime_result['recommendation']}")
                        
                        with st.expander("🔍 상세 가중치 및 설명"):
                            st.write(f"VIX 수준: {regime_info.vix_level:.2f}")
                            st.write(f"추세 강도: {regime_info.trend}")
                            st.json(regime_result['model_weights'])
                    except Exception as e:
                        st.warning(f"시장 국면 분석 실패: {e}, 기본 예측 수행")
                        use_regime = False
                
                if not use_regime:
                    status.write("🔮 예측 수행 중...")
                    price_pred = ensemble.predict_price(df)
                    direction_pred = ensemble.predict_direction(df)
                
                status.update(label="✅ 예측 완료!", state="complete", expanded=False)
                
                # ========== 결과 표시 ==========
                st.markdown("---")
                st.subheader("📊 예측 결과")
                
                # 예측 대상 날짜 계산
                last_date = pd.to_datetime(df['date'].iloc[-1])
                next_date = last_date + pd.Timedelta(days=1)
                while next_date.weekday() > 4:
                    next_date += pd.Timedelta(days=1)
                prediction_date_str = next_date.strftime("%m/%d")
                
                # 가격 및 방향
                predicted_price = price_pred.get('ensemble_prediction')
                if predicted_price:
                    price_based_direction = 'up' if predicted_price > current_price else 'down'
                    price_change_pct = ((predicted_price - current_price) / current_price) * 100
                else:
                    price_based_direction = direction_pred.get('ensemble_prediction', 'neutral')
                    price_change_pct = 0
                
                confidence = direction_pred.get('confidence_score', 0)
                
                # 메트릭 표시
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("현재가", f"₩{current_price:,.0f}", f"{last_date.strftime('%Y-%m-%d')}")
                
                with col2:
                    if predicted_price:
                        st.metric(
                            f"예측 종가 ({prediction_date_str})",
                            f"₩{predicted_price:,.0f}",
                            f"{price_change_pct:+.2f}%"
                        )
                    else:
                        st.metric("예측 종가", "모델 학습 필요")
                
                with col3:
                    direction_emoji = "📈" if price_based_direction == 'up' else "📉"
                    direction_label = "상승" if price_based_direction == 'up' else "하락"
                    st.metric(
                        f"예측 방향 {direction_emoji}",
                        direction_label,
                        f"신뢰도: {confidence:.1%}"
                    )
                
                # 차트 표시
                st.subheader("📈 가격 차트")
                fig = go.Figure()
                
                fig.add_trace(go.Scatter(
                    x=df['date'].tail(60),
                    y=df['close'].tail(60),
                    mode='lines',
                    name='실제 가격',
                    line=dict(color='#00d775', width=2)
                ))
                
                if predicted_price:
                    fig.add_trace(go.Scatter(
                        x=[last_date, next_date],
                        y=[current_price, predicted_price],
                        mode='lines+markers',
                        name='예측 가격',
                        line=dict(color='#ff4b4b', width=2, dash='dash'),
                        marker=dict(size=10)
                    ))
                
                fig.update_layout(
                    title=f"{ticker_name} - AI 가격 예측",
                    xaxis_title="날짜",
                    yaxis_title="가격",
                    template='plotly_dark',
                    height=400,
                    hovermode='x unified'
                )
                
                st.plotly_chart(fig, use_container_width=True)
                
                # 개별 모델 예측
                st.subheader("🔍 개별 모델 예측")
                model_data = []
                if price_pred.get('individual_predictions'):
                    for k, v in price_pred['individual_predictions'].items():
                        model_data.append({
                            '모델': k.upper(),
                            '예측값': f"₩{v:,.0f}" if isinstance(v, (int, float)) else str(v)
                        })
                
                if model_data:
                    st.dataframe(pd.DataFrame(model_data), use_container_width=True)
                else:
                    st.info("개별 모델 예측 데이터가 없습니다. 모델 학습이 필요합니다.")
                
                # 신뢰도 분석
                st.subheader("📊 신뢰도 분석")
                confidence_level = "높음" if confidence > ENSEMBLE_CONFIG['confidence_threshold']['high'] else \
                                  "중간" if confidence > ENSEMBLE_CONFIG['confidence_threshold']['medium'] else "낮음"
                st.info(f"**신뢰도 수준:** {confidence_level} ({confidence:.1%})")
                st.caption(f"모델 가중치: {ensemble.weights}")
                
                # 경고
                st.warning("⚠️ AI 예측은 참고용이며, 실제 투자 결정에는 종합적인 분석이 필요합니다.")
                
            except Exception as e:
                st.error(f"예측 중 오류 발생: {str(e)}")
                import traceback
                st.code(traceback.format_exc())
