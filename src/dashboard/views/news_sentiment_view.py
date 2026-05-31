"""
뉴스 및 감성 분석 뷰 모듈

클린 아키텍처:
- Presentation Layer: Streamlit UI 렌더링
- Application Layer: 뉴스/감성 분석 서비스 호출
"""
import streamlit as st
from src.collectors.news_collector import NewsCollector
from src.analyzers.sentiment_analyzer import SentimentAnalyzer


def display_news_sentiment():
    """뉴스 및 감성 분석 뷰"""
    st.header("📰 뉴스 분석 및 감성 평가")
    
    selected_ticker = st.session_state.get('selected_ticker')
    if not selected_ticker:
        st.warning("종목을 먼저 선택해주세요.")
        return
    
    with st.spinner("뉴스 수집 중..."):
        try:
            news_collector = NewsCollector()
            
            # 티커에서 .KS 제거 (네이버 금융용)
            clean_ticker = selected_ticker.replace(".KS", "")
            stock_name = st.session_state.get('selected_stock', clean_ticker)
            
            # 뉴스 수집 및 저장
            news_collector.collect_and_save(
                ticker=clean_ticker,
                company_name=stock_name,
                use_naver=False,  # 🔧 네이버 금융 잠시 비활성화
                use_google=True,
                max_pages=2,
                max_items=20
            )
            
            # DB에서 뉴스 조회 (naver_finance 제외)
            news_list = news_collector.get_news(
                clean_ticker, 
                limit=50,
                exclude_sources=['naver_finance']  # 🔧 네이버 금융 제외
            )
            
            if not news_list:
                st.info("최근 뉴스가 없습니다.")
                return
            
            # 리스트를 DataFrame으로 변환
            import pandas as pd
            news_df = pd.DataFrame(news_list)
            
            # 감성 분석
            sentiment_analyzer = SentimentAnalyzer()
            
            def get_sentiment_label(row):
                """감성 점수를 라벨로 변환 (제목 + 본문 결합)"""
                title = row.get('title', '') if isinstance(row, dict) else str(row)
                content = ''
                if isinstance(row, dict):
                    content = row.get('content', '') or ''
                
                # 제목과 본문을 결합하여 분석 (본문 있으면 더 정확)
                text = f"{title} {content}".strip()
                
                if not text:
                    return 'neutral'
                try:
                    result = sentiment_analyzer.analyze_text(text)
                    # analyze_text는 (score, details) 튜플 반환
                    if isinstance(result, tuple):
                        score = result[0]
                    else:
                        score = result
                    
                    # 🔧 임계값 낮춤: 0.2 -> 0.1 (더 민감하게 판정)
                    if score > 0.1:
                        return 'positive'
                    elif score < -0.1:
                        return 'negative'
                    else:
                        return 'neutral'
                except Exception:
                    return 'neutral'
            
            # 행 전체를 전달하여 title + content 모두 분석
            news_df['sentiment'] = news_df.apply(
                lambda row: get_sentiment_label(row.to_dict()), axis=1
            )
            
            # 감성 요약
            st.subheader("📊 감성 요약")
            col1, col2, col3 = st.columns(3)
            
            positive = (news_df['sentiment'] == 'positive').sum()
            negative = (news_df['sentiment'] == 'negative').sum()
            neutral = (news_df['sentiment'] == 'neutral').sum()
            total = len(news_df)
            
            with col1:
                st.metric("긍정적", f"{positive}건", f"{positive/total*100:.1f}%" if total > 0 else "0%")
            with col2:
                st.metric("부정적", f"{negative}건", f"{negative/total*100:.1f}%" if total > 0 else "0%")
            with col3:
                st.metric("중립", f"{neutral}건", f"{neutral/total*100:.1f}%" if total > 0 else "0%")
            
            # 뉴스 목록
            st.subheader(f"📰 최근 뉴스 ({total}건)")
            
            for _, row in news_df.iterrows():
                sentiment_val = row['sentiment']
                # sentiment가 문자열인지 확인
                if isinstance(sentiment_val, tuple):
                    sentiment_val = 'neutral'
                sentiment_emoji = {
                    'positive': '🟢',
                    'negative': '🔴',
                    'neutral': '⚪'
                }.get(sentiment_val, '⚪')
                
                title = row.get('title', '제목 없음')
                with st.expander(f"{sentiment_emoji} {title}"):
                    st.write(f"**출처**: {row.get('source', 'Unknown')}")
                    st.write(f"**날짜**: {row.get('published_date', 'N/A')}")
                    content = row.get('content', '')
                    if content:
                        st.write(content[:300] + "..." if len(content) > 300 else content)
                    url = row.get('url', '')
                    if url:
                        st.markdown(f"[전체 기사 보기]({url})")
                        
        except Exception as e:
            st.error(f"뉴스 수집 오류: {e}")
            import traceback
            st.code(traceback.format_exc())
