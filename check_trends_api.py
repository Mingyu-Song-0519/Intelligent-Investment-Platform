from pytrends.request import TrendReq
import pandas as pd
import time

def test_google_trends():
    print("🔍 Google Trends API 연결 상태 점검 중...")
    try:
        # 설정: 타임아웃만 설정 (retries 제거 - urllib3 호환성 문제)
        pytrend = TrendReq(hl='ko-KR', tz=-540, timeout=(10,25))
        
        keywords = ['삼성전자']
        print(f"📡 '{keywords[0]}' 키워드로 데이터 요청 중...")
        
        pytrend.build_payload(kw_list=keywords, timeframe='now 1-d')
        df = pytrend.interest_over_time()
        
        if not df.empty:
            print("\n✅ API 연결 성공! (데이터 수신됨)")
            print("-" * 30)
            print(df.tail(3))
            print("-" * 30)
            print("💡 대시보드에서도 정상 작동할 것입니다.")
        else:
            print("\n⚠️ API 연결은 성공했으나 데이터가 비어있습니다.")
            
    except Exception as e:
        print(f"\n❌ API 호출 실패: {e}")
        if "429" in str(e):
            print("\n🚨 [진단 결과]: Google 서버로부터 요청이 차단되었습니다 (429 Too Many Requests).")
            print("   - 원인: 짧은 시간 내에 너무 많은 요청 발생")
            print("   - 해결: 10~15분 대기 후 재시도하거나, VPN/테더링으로 IP를 변경하세요.")
        else:
            print(f"\n🚨 [진단 결과]: 알 수 없는 오류입니다.")

if __name__ == "__main__":
    test_google_trends()
