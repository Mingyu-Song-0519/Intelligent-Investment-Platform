# 🔑 Gemini API 키 설정 가이드

## 현재 상태 확인

현재 **API 키 없이도** AI 분석이 작동하는 이유는 자동으로 `MockLLMClient`가 사용되기 때문입니다.

### MockLLMClient란?
- 테스트용 가짜 LLM 클라이언트
- 실제 API 호출 없이 고정된 응답 반환
- API 키가 없거나 오류 발생 시 자동으로 활성화됨

### 실제 AI vs Mock AI 비교

| 항목 | Mock AI (현재) | Gemini AI (키 설정 후) |
|------|---------------|----------------------|
| 비용 | 무료 | 무료 (일 1,500회) |
| 응답 | 고정된 템플릿 | 실제 AI 분석 |
| 정확도 | 없음 | 높음 |
| 종목별 차이 | 없음 | 있음 |

---

## 🚀 Gemini API 키 발급 방법

### 1단계: Google AI Studio 접속

1. 웹 브라우저에서 접속: https://makersuite.google.com/app/apikey
2. Google 계정으로 로그인

### 2단계: API 키 생성

1. **"Create API Key"** 버튼 클릭
2. 프로젝트 선택 또는 새 프로젝트 생성
3. **API 키 복사** (예: `AIzaSyD...`)

⚠️ **주의**: API 키는 한 번만 표시되므로 반드시 복사하세요!

---

## 📝 API 키 설정 방법

### 방법 1: Streamlit Secrets (권장)

#### 1. secrets.toml 파일 생성

프로젝트 루트에서:
```bash
# .streamlit 폴더로 이동
cd .streamlit

# secrets.toml.example을 복사
copy secrets.toml.example secrets.toml
```

#### 2. API 키 입력

`D:\Stock\.streamlit\secrets.toml` 파일을 열고:

```toml
GEMINI_API_KEY = "AIzaSyD...여기에_실제_키_붙여넣기"
```

#### 3. 앱 재시작

Streamlit 앱을 재시작하면 자동으로 Gemini API가 활성화됩니다.

---

### 방법 2: 환경변수 (대안)

#### Windows (PowerShell)
```powershell
$env:GEMINI_API_KEY = "AIzaSyD...여기에_실제_키_붙여넣기"
```

#### Linux/Mac (bash)
```bash
export GEMINI_API_KEY="AIzaSyD...여기에_실제_키_붙여넣기"
```

---

## ✅ API 키 작동 확인

### 1. 로그 확인

앱 실행 시 콘솔에서 다음 메시지를 확인:

```
[GeminiClient] Initialized successfully  ← Gemini API 사용 중
```

또는

```
[GeminiClient] API key not found  ← MockLLM 사용 중
```

### 2. AI 분석 실행

1. **단일 종목 분석** 탭 이동
2. 종목 선택 (예: 삼성전자)
3. **"🤖 AI 투자 분석"** expander 클릭
4. **"🤖 AI 분석"** 버튼 클릭

**Gemini API 사용 시**:
- 5-10초 소요
- 종목별로 다른 분석 제공
- 상세하고 논리적인 리포트

**MockLLM 사용 시**:
- 즉시 응답
- 모든 종목에 동일한 응답
- 간단한 템플릿 응답

---

## 🔒 보안 주의사항

### secrets.toml 관리

1. **절대 Git에 올리지 마세요**
   - `.gitignore`에 이미 포함되어 있음
   - 확인: `git status`에 `secrets.toml`이 나오면 안 됨

2. **API 키 공유 금지**
   - API 키는 개인 정보처럼 관리
   - 팀원과 공유 시 각자 발급받기

3. **키 노출 시 조치**
   - Google AI Studio에서 해당 키 삭제
   - 새 키 즉시 발급

---

## 💡 무료 티어 제한

### Gemini 1.5 Flash (무료)

| 제한 | 값 |
|------|-----|
| 분당 요청 (RPM) | 60회 |
| 일 요청 (RPD) | 1,500회 |
| 입력 토큰 | 1M tokens/min |

### 제한 초과 시

```
Error: Rate limit exceeded
```

**해결책**:
1. 요청 간격 늘리기 (1초 이상)
2. AI 스크리너 실행 횟수 줄이기 (하루 2-3회 권장)
3. 유료 플랜 검토 (필요시)

---

## 🆘 문제 해결

### "API key not found" 오류

**원인**: secrets.toml 파일이 없거나 키가 잘못됨

**해결**:
1. `.streamlit/secrets.toml` 파일 존재 확인
2. 파일 내용 확인: `GEMINI_API_KEY = "..."`
3. 키에 따옴표 있는지 확인
4. 앱 재시작

### "Invalid API key" 오류

**원인**: 잘못된 API 키

**해결**:
1. Google AI Studio에서 키 재확인
2. 복사 시 공백이나 줄바꿈 제거
3. 키 재발급 시도

### Mock 응답이 계속 나올 때

**확인 사항**:
1. `secrets.toml` 파일 위치: `D:\Stock\.streamlit\secrets.toml`
2. 키 형식: `GEMINI_API_KEY = "AIzaSy..."`
3. 앱 재시작 여부
4. 콘솔 로그 확인

---

## 📚 추가 리소스

- [Google AI Studio](https://makersuite.google.com/)
- [Gemini API 문서](https://ai.google.dev/docs)
- [Streamlit Secrets 관리](https://docs.streamlit.io/library/advanced-features/secrets-management)

---

## ❓ FAQ

### Q: API 키가 꼭 필요한가요?
A: 아니요, MockLLM으로도 테스트 가능합니다. 하지만 실제 AI 분석을 받으려면 필수입니다.

### Q: 무료로 얼마나 사용할 수 있나요?
A: 하루 1,500회 요청까지 무료입니다. 일반 사용자는 충분합니다.

### Q: API 키가 유출되면 어떻게 되나요?
A: 타인이 당신의 할당량을 사용할 수 있습니다. 즉시 키를 삭제하고 재발급하세요.

### Q: 여러 PC에서 사용하려면?
A: 각 PC의 `.streamlit/secrets.toml`에 동일한 키를 설정하면 됩니다.
