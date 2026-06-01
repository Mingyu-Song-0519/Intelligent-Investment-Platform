# 🔧 AI 스크리너 화면 안 나오는 문제 해결 가이드

## ❌ 문제 상황
AI 스크리너 탭에 들어가도 아무것도 표시되지 않음

## ✅ 해결 완료
**원인**: app.py에 탭 렌더링 로직이 누락되어 있었음  
**수정**: `elif selected_tab == "🌅 AI 스크리너"` 블록 추가 완료

---

## 🔄 Streamlit 앱 재시작 방법

코드 변경 후 **반드시 앱을 재시작**해야 합니다!

### 방법 1: 터미널에서 재시작 (권장)

1. **현재 실행 중인 앱 중지**:
   ```
   Ctrl + C (터미널에서)
   ```

2. **다시 시작**:
   ```bash
   streamlit run src/dashboard/app.py
   ```

### 방법 2: 브라우저에서 재시작

1. 브라우저 우측 상단 **메뉴 (⋮)** 클릭
2. **"Rerun"** 또는 **"Clear cache"** 선택
3. 페이지 새로고침 (F5)

**주의**: 방법 2는 모든 변경사항을 반영하지 못할 수 있습니다.  
→ **방법 1 (터미널 재시작)을 권장합니다.**

---

## ✅ 수정 사항 확인

재시작 후 AI 스크리너 탭에 들어가면 다음이 표시되어야 합니다:

```
🌅 AI 모닝 픽
AI가 발굴한 오늘의 추천 종목입니다.

[시장 선택] [추천 개수] [🔍 종목 발굴]

👆 위에서 시장을 선택하고 '🔍 종목 발굴' 버튼을 클릭하여 AI 추천 종목을 확인하세요.

💡 사용 방법 (자동으로 펼쳐짐)
  - AI 스크리너 사용법
  - 필터 조건
  - 개인화 안내
```

---

## 🐛 여전히 문제가 있다면

### 1. Import 오류 확인

터미널에서 다음 명령 실행:
```bash
cd D:\Stock
python -c "from src.dashboard.views.screener_view import render_morning_picks; print('✅ Import OK')"
```

**예상 출력**:
```
✅ Import OK
```

**오류가 나면**: screener_view.py에 문법 오류가 있음

### 2. SCREENER_AVAILABLE 확인

app.py 상단 (60-66줄) 확인:
```python
# Phase C: AI 스크리너 뷰
try:
    from src.dashboard.views.screener_view import render_morning_picks
    SCREENER_AVAILABLE = True
except ImportError:
    SCREENER_AVAILABLE = False
```

이 블록이 있어야 함!

### 3. 탭 렌더링 로직 확인

app.py 하단 (2686-2690줄) 확인:
```python
elif selected_tab == "🌅 AI 스크리너":
    if SCREENER_AVAILABLE:
        render_morning_picks()
    else:
        st.warning("AI 스크리너 모듈을 불러올 수 없습니다.")
```

이 블록이 있어야 함!

---

## 🎯 테스트 순서

1. **터미널 재시작** (Ctrl+C → streamlit run ...)
2. **AI 스크리너 탭** 클릭
3. **안내 메시지 확인** (💡 사용 방법 expander)
4. **"🔍 종목 발굴"** 버튼 클릭
5. **30초~1분 대기**
6. **결과 확인**

---

## 📞 문제 지속 시

다음 정보를 함께 알려주세요:

1. Streamlit 재시작 여부 (예/아니오)
2. 터미널 오류 메시지 (있다면)
3. 브라우저 콘솔 오류 (F12 → Console 탭)
