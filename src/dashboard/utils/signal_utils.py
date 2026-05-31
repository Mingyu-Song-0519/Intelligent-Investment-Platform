"""
매매 시그널 표시 유틸리티 모듈

클린 아키텍처:
- Presentation Layer: 기술적 지표 기반 시그널 표시
"""
import streamlit as st
import pandas as pd


def display_signals(df: pd.DataFrame):
    """매매 시그널 표시"""
    st.subheader("📊 매매 시그널")
    
    # 지표 확인
    if 'rsi' not in df.columns or 'macd' not in df.columns:
        st.warning("기술적 지표가 계산되지 않았습니다.")
        return
    
    latest = df.iloc[-1]
    
    # 첫 번째 행: RSI, MACD, 볼린저밴드
    st.markdown("#### 기술적 지표 시그널")
    signal_cols = st.columns(3)

    with signal_cols[0]:
        rsi_val = latest.get('rsi', 50)
        if pd.notna(rsi_val):
            if rsi_val < 30:
                st.success(f"🟢 RSI 과매도 구간 ({rsi_val:.1f})")
                st.caption("💡 **매수 검토**: RSI 30 미만은 과매도 상태로, 반등 가능성이 높습니다.")
            elif rsi_val > 70:
                st.error(f"🔴 RSI 과매수 구간 ({rsi_val:.1f})")
                st.caption("💡 **매도 검토**: RSI 70 초과는 과매수 상태로, 조정 가능성이 있습니다.")
            else:
                st.info(f"⚪ RSI 중립 ({rsi_val:.1f})")
                st.caption("💡 **관망**: RSI 30~70 사이는 중립 구간으로, 다른 지표를 함께 확인하세요.")
        else:
            st.info("⚪ RSI 데이터 없음")

    with signal_cols[1]:
        macd_val = latest.get('macd', 0)
        macd_signal = latest.get('macd_signal', 0)
        if pd.notna(macd_val) and pd.notna(macd_signal):
            macd_diff = macd_val - macd_signal
            if macd_val > macd_signal:
                st.success(f"🟢 MACD 상승 추세 (+{macd_diff:.2f})")
                st.caption("💡 **매수 신호**: MACD가 시그널선 위에 있어 상승 모멘텀입니다.")
            else:
                st.error(f"🔴 MACD 하락 추세 ({macd_diff:.2f})")
                st.caption("💡 **매도 신호**: MACD가 시그널선 아래로 하락 모멘텀입니다.")
        else:
            st.info("⚪ MACD 데이터 없음")

    with signal_cols[2]:
        close = latest.get('close', 0)
        bb_lower = latest.get('bb_lower', 0)
        bb_upper = latest.get('bb_upper', 0)
        bb_middle = latest.get('bb_middle', 0)
        if pd.notna(bb_lower) and pd.notna(bb_upper) and bb_upper > bb_lower:
            bb_position = (close - bb_lower) / (bb_upper - bb_lower) * 100
            if close < bb_lower:
                st.success("🟢 볼린저밴드 하단 터치")
                st.caption("💡 **매수 검토**: 하단 밴드 터치는 과매도 신호로, 반등 가능성이 있습니다.")
            elif close > bb_upper:
                st.error("🔴 볼린저밴드 상단 터치")
                st.caption("💡 **매도 검토**: 상단 밴드 터치는 과매수 신호로, 조정 가능성이 있습니다.")
            else:
                st.info(f"⚪ 볼린저밴드 중립 ({bb_position:.0f}%)")
                st.caption("💡 **관망**: 밴드 내 중간 위치로, 추세 방향을 확인하세요.")
        else:
            st.info("⚪ 볼린저밴드 데이터 없음")
    
    # 두 번째 행: 이동평균 교차, 거래량 분석
    st.markdown("#### 추가 시그널")
    signal_cols2 = st.columns(3)
    
    with signal_cols2[0]:
        # 이동평균 교차 (골든크로스/데드크로스)
        ma5 = latest.get('ma5', None)
        ma20 = latest.get('ma20', None)
        if pd.notna(ma5) and pd.notna(ma20):
            if ma5 > ma20:
                # 이전 데이터와 비교하여 교차 여부 확인
                prev = df.iloc[-2] if len(df) > 1 else latest
                prev_ma5 = prev.get('ma5', 0)
                prev_ma20 = prev.get('ma20', 0)
                if pd.notna(prev_ma5) and pd.notna(prev_ma20) and prev_ma5 <= prev_ma20:
                    st.success("🟢 골든크로스 발생!")
                    st.caption("💡 **강력 매수 신호**: 단기 MA가 장기 MA를 상향 돌파했습니다.")
                else:
                    st.success("🟢 상승 추세 (MA5 > MA20)")
                    st.caption("💡 **매수 우위**: 단기 이동평균이 장기 이동평균 위에 있습니다.")
            else:
                prev = df.iloc[-2] if len(df) > 1 else latest
                prev_ma5 = prev.get('ma5', 0)
                prev_ma20 = prev.get('ma20', 0)
                if pd.notna(prev_ma5) and pd.notna(prev_ma20) and prev_ma5 >= prev_ma20:
                    st.error("🔴 데드크로스 발생!")
                    st.caption("💡 **강력 매도 신호**: 단기 MA가 장기 MA를 하향 돌파했습니다.")
                else:
                    st.error("🔴 하락 추세 (MA5 < MA20)")
                    st.caption("💡 **매도 우위**: 단기 이동평균이 장기 이동평균 아래에 있습니다.")
        else:
            st.info("⚪ 이동평균 데이터 없음")
            st.caption("💡 데이터 수집 후 이동평균이 계산됩니다 (최소 20일 필요)")
    
    with signal_cols2[1]:
        # 거래량 분석
        current_volume = latest.get('volume', 0)
        if pd.notna(current_volume) and 'volume' in df.columns:
            avg_volume = df['volume'].tail(20).mean()
            volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1
            if volume_ratio > 2.0:
                st.success(f"🟢 거래량 급증 ({volume_ratio:.1f}배)")
                st.caption("💡 **주목**: 평균 대비 2배 이상 거래량은 큰 움직임 신호입니다.")
            elif volume_ratio > 1.5:
                st.info(f"⚪ 거래량 증가 ({volume_ratio:.1f}배)")
                st.caption("💡 **관심**: 평균보다 높은 거래량으로 관심이 집중되고 있습니다.")
            elif volume_ratio < 0.5:
                st.warning(f"🟡 거래량 감소 ({volume_ratio:.1f}배)")
                st.caption("💡 **주의**: 낮은 거래량은 추세 지속력이 약할 수 있습니다.")
            else:
                st.info(f"⚪ 거래량 보통 ({volume_ratio:.1f}배)")
                st.caption("💡 **정상**: 평균 수준의 거래량입니다.")
        else:
            st.info("⚪ 거래량 데이터 없음")
    
    with signal_cols2[2]:
        # 종합 판단
        score = 0
        signals = []
        
        # RSI 점수
        if pd.notna(latest.get('rsi')):
            if latest['rsi'] < 30:
                score += 2
                signals.append("RSI 과매도")
            elif latest['rsi'] > 70:
                score -= 2
                signals.append("RSI 과매수")
        
        # MACD 점수
        if pd.notna(latest.get('macd')) and pd.notna(latest.get('macd_signal')):
            if latest['macd'] > latest['macd_signal']:
                score += 1
                signals.append("MACD 상승")
            else:
                score -= 1
                signals.append("MACD 하락")
        
        # 이동평균 점수
        if pd.notna(latest.get('ma5')) and pd.notna(latest.get('ma20')):
            if latest['ma5'] > latest['ma20']:
                score += 1
                signals.append("MA 상승추세")
            else:
                score -= 1
                signals.append("MA 하락추세")
        
        if score >= 3:
            st.success(f"📈 종합: 강력 매수 ({score}점)")
            st.caption(f"💡 {', '.join(signals)}")
        elif score >= 1:
            st.success(f"📈 종합: 매수 우위 ({score}점)")
            st.caption(f"💡 {', '.join(signals)}")
        elif score <= -3:
            st.error(f"📉 종합: 강력 매도 ({score}점)")
            st.caption(f"💡 {', '.join(signals)}")
        elif score <= -1:
            st.error(f"📉 종합: 매도 우위 ({score}점)")
            st.caption(f"💡 {', '.join(signals)}")
        else:
            st.info(f"⚖️ 종합: 중립 ({score}점)")
            st.caption(f"💡 {', '.join(signals) if signals else '시그널 없음'}")
