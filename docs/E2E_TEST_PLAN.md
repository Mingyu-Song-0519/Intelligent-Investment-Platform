# 주식 분석 대시보드 E2E 테스트 계획서

**작성일**: 2025-12-27
**테스트 프레임워크**: Playwright + Streamlit Testing
**대상 애플리케이션**: Streamlit 기반 주식 분석 대시보드

---

## 📋 테스트 개요

### 목적
- 주요 사용자 시나리오의 End-to-End 동작 검증
- 사이드바 최적화 후 UI/UX 정상 작동 확인
- 탭 전환 및 데이터 로딩 흐름 검증

### 테스트 환경
- **로컬 환경**: `streamlit run src/dashboard/app.py`
- **기본 URL**: `http://localhost:8501`
- **브라우저**: Chromium, Firefox, WebKit (Playwright)

---

## 🎯 테스트 대상 주요 기능

### 1. 사이드바 (Sidebar) - 최근 최적화 적용
- ✅ Phase 1: 탭별 설정 최상단 배치
- ✅ Phase 2: 시장 선택 토글 버튼
- ✅ Phase 3: 설정 통합 (Expander + Tabs)
- ✅ Phase 4: 경제 지표 위젯 제거

### 2. 메인 탭 (Main Tabs)
한국 시장 (KR):
- 🎯 투자 컨트롤 센터
- 🔴 실시간 시세
- 📊 단일 종목 분석
- 🔀 다중 종목 비교
- ⭐ 관심 종목
- 📰 뉴스 감성 분석
- 🤖 AI 예측
- ⏮️ 백테스팅
- 💼 포트폴리오 최적화
- ⚠️ 리스크 관리
- 🏥 시장 체력 진단
- 🔥 Market Buzz
- 💎 팩터 투자
- 👤 투자 성향
- 🌅 AI 스크리너

미국 시장 (US):
- 동일 (실시간 시세 제외)

### 3. AI 챗봇
- 사이드바 하단 고정
- 질문 입력 및 응답

---

## 🧪 E2E 테스트 시나리오

### **테스트 그룹 1: 사이드바 기본 기능**

#### **TS-001: 페이지 초기 로딩**
**목적**: 앱이 정상적으로 로딩되고 기본 요소가 표시되는지 확인

**테스트 단계**:
1. 브라우저에서 `http://localhost:8501` 접속
2. 페이지 로딩 대기 (최대 10초)
3. 다음 요소 존재 확인:
   - [ ] 페이지 타이틀 표시
   - [ ] 사이드바 표시
   - [ ] 메인 탭 메뉴 표시
   - [ ] 기본 탭("📊 단일 종목 분석") 선택됨

**예상 결과**: 모든 요소가 5초 이내 로딩 완료

**Playwright 선택자**:
```javascript
// 사이드바
await page.locator('[data-testid="stSidebar"]').isVisible()

// 탭 메뉴
await page.locator('text=분석 메뉴').isVisible()

// 기본 탭
await page.locator('text=📊 단일 종목 분석').isVisible()
```

---

#### **TS-002: 시장 선택 토글 버튼 (Phase 2)**
**목적**: 한국/미국 시장 전환이 정상 작동하는지 확인

**테스트 단계**:
1. 사이드바에서 "🌍 시장 선택" 섹션 확인
2. 초기 상태: "🇰🇷 한국" 버튼이 primary 타입 (강조 표시)
3. "🇺🇸 미국" 버튼 클릭
4. 페이지 리로드 대기
5. 다음 확인:
   - [ ] "🇺🇸 미국" 버튼이 primary 타입으로 변경
   - [ ] "🇰🇷 한국" 버튼이 secondary 타입으로 변경
   - [ ] 캡션에 "선택: 🇺🇸 미국 (NYSE/NASDAQ)" 표시
   - [ ] 탭 메뉴에서 "🔴 실시간 시세" 탭 사라짐
6. "🇰🇷 한국" 버튼 클릭하여 원래대로 복원

**예상 결과**: 시장 전환 시 2초 이내 리로드 및 UI 업데이트

**Playwright 선택자**:
```javascript
// 한국 버튼
const krButton = page.locator('button:has-text("🇰🇷 한국")')

// 미국 버튼
const usButton = page.locator('button:has-text("🇺🇸 미국")')

// primary 타입 확인
await expect(krButton).toHaveAttribute('type', 'primary')

// 버튼 클릭
await usButton.click()

// 캡션 확인
await page.locator('text=선택: 🇺🇸 미국 (NYSE/NASDAQ)').isVisible()
```

---

#### **TS-003: 통합 설정 Expander (Phase 3)**
**목적**: 사용자/API/알림 설정이 하나의 Expander에 통합되었는지 확인

**테스트 단계**:
1. 사이드바에서 "⚙️ 설정" Expander 찾기
2. Expander 클릭하여 확장
3. 3개 탭 확인:
   - [ ] "👤 사용자" 탭
   - [ ] "🔑 API" 탭
   - [ ] "🔔 알림" 탭
4. "👤 사용자" 탭 클릭
   - [ ] "유저 ID" 입력 필드 표시
5. "🔑 API" 탭 클릭
   - [ ] "Gemini API Key" 입력 필드 표시 (type="password")
6. "🔔 알림" 탭 클릭
   - [ ] "알림 활성화" 토글 표시
   - [ ] 토글 활성화 시 "VIX 임계값" 슬라이더 표시

**예상 결과**: Expander 확장/축소 및 탭 전환이 즉시 반영됨

**Playwright 선택자**:
```javascript
// Expander
const settingsExpander = page.locator('[data-testid="stExpander"]:has-text("⚙️ 설정")')
await settingsExpander.click()

// 탭들
const userTab = page.locator('button:has-text("👤 사용자")')
const apiTab = page.locator('button:has-text("🔑 API")')
const alertTab = page.locator('button:has-text("🔔 알림")')

// 사용자 탭 내용
await userTab.click()
await page.locator('input[aria-label="유저 ID"]').isVisible()

// API 탭 내용
await apiTab.click()
await page.locator('input[type="password"][aria-label="Gemini API Key"]').isVisible()
```

---

#### **TS-004: 탭별 설정 최상단 배치 (Phase 1)**
**목적**: 실시간 시세/단일 종목 분석 탭에서 설정이 사이드바 최상단에 표시되는지 확인

**테스트 단계**:
1. 메인 탭에서 "🔴 실시간 시세" 선택
2. 사이드바 확인:
   - [ ] 최상단에 "⚙️ 실시간 설정" 헤더 표시
   - [ ] "종목 검색" 드롭다운 표시
   - [ ] "갱신 주기 (초)" 슬라이더 표시
   - [ ] "▶️ 실시간 조회 시작" 버튼 표시
3. 메인 탭에서 "📊 단일 종목 분석" 선택
4. 사이드바 확인:
   - [ ] 최상단에 "⚙️ 설정" 헤더 표시
   - [ ] "종목 검색" 드롭다운 표시
   - [ ] "조회 기간" 드롭다운 표시
   - [ ] "📥 데이터 수집" 버튼 표시
5. "🌍 시장 현황" 탭 선택
6. 사이드바 확인:
   - [ ] "현재 시장: 🇰🇷 한국" 메시지만 표시 (설정 섹션 없음)

**예상 결과**: 탭 전환 시 사이드바 최상단 내용이 즉시 변경됨

**Playwright 선택자**:
```javascript
// 실시간 시세 탭 선택
await page.locator('text=🔴 실시간 시세').click()

// 사이드바 최상단 헤더 확인
await page.locator('[data-testid="stSidebar"] >> text=⚙️ 실시간 설정').first().isVisible()

// 종목 검색 드롭다운
await page.locator('[data-testid="stSidebar"] >> [data-testid="stSelectbox"]:has-text("종목 검색")').isVisible()

// 단일 종목 분석 탭 선택
await page.locator('text=📊 단일 종목 분석').click()

// 데이터 수집 버튼
await page.locator('button:has-text("📥 데이터 수집")').isVisible()
```

---

#### **TS-005: AI 챗봇 하단 고정**
**목적**: AI 챗봇이 사이드바 하단에 고정되어 있는지 확인 (중복 없음)

**테스트 단계**:
1. 사이드바 스크롤 하단으로 이동
2. "🤖 AI 투자 비서" 또는 챗봇 입력 필드 확인
3. 다른 탭으로 전환 (예: "📰 뉴스 감성 분석")
4. 사이드바 하단 다시 확인
5. 검증:
   - [ ] AI 챗봇이 하단에 1개만 표시됨 (중복 없음)
   - [ ] 모든 탭에서 동일하게 표시됨

**예상 결과**: AI 챗봇이 사이드바 하단에 1개만 고정 표시

**Playwright 선택자**:
```javascript
// 사이드바 내 챗봇 요소 개수 확인
const chatbotCount = await page.locator('[data-testid="stSidebar"] >> text=AI 투자 비서').count()
expect(chatbotCount).toBe(1)

// 또는 챗봇 입력 필드 확인
await page.locator('[data-testid="stSidebar"] >> textarea').last().isVisible()
```

---

### **테스트 그룹 2: 메인 탭 기능**

#### **TS-101: 단일 종목 분석 - 데이터 수집**
**목적**: 종목 선택 및 데이터 수집 기능이 정상 작동하는지 확인

**테스트 단계**:
1. "📊 단일 종목 분석" 탭 선택
2. 사이드바에서 종목 선택:
   - [ ] "종목 검색" 드롭다운 클릭
   - [ ] "삼성전자 (005930)" 선택 (또는 다른 종목)
3. "조회 기간" 드롭다운에서 "1년" 선택
4. "📥 데이터 수집" 버튼 클릭
5. 로딩 대기 (최대 30초)
6. 메인 화면 확인:
   - [ ] 주가 차트 표시
   - [ ] 기술적 지표 테이블 표시
   - [ ] "종목코드: 005930.KS" 또는 유사 정보 표시
   - [ ] 에러 메시지 없음

**예상 결과**: 데이터 수집 후 30초 이내 차트 및 지표 표시

**Playwright 선택자**:
```javascript
// 탭 선택
await page.locator('text=📊 단일 종목 분석').click()

// 종목 드롭다운
const stockSelect = page.locator('[data-testid="stSelectbox"]:has-text("종목 검색")')
await stockSelect.click()
await page.locator('text=삼성전자 (005930)').click()

// 기간 선택
const periodSelect = page.locator('[data-testid="stSelectbox"]:has-text("조회 기간")')
await periodSelect.click()
await page.locator('text=1년').click()

// 데이터 수집 버튼
await page.locator('button:has-text("📥 데이터 수집")').click()

// 차트 로딩 대기
await page.locator('[data-testid="stPlotlyChart"]').waitFor({ timeout: 30000 })
```

---

#### **TS-102: 실시간 시세 - 시작/중지**
**목적**: 실시간 시세 조회 시작/중지가 정상 작동하는지 확인 (한국 시장만)

**테스트 단계**:
1. 시장을 "🇰🇷 한국"으로 설정 (이미 설정되어 있으면 스킵)
2. "🔴 실시간 시세" 탭 선택
3. 사이드바에서:
   - [ ] 종목 선택 (예: "삼성전자 (005930)")
   - [ ] 갱신 주기 슬라이더 조정 (예: 2초)
4. "▶️ 실시간 조회 시작" 버튼 클릭
5. 확인:
   - [ ] 버튼이 "⏹️ 중지"로 변경
   - [ ] "🟢 실시간 조회 중..." 메시지 표시
   - [ ] 메인 화면에 실시간 데이터 표시 (2초마다 갱신)
6. 5초 대기
7. "⏹️ 중지" 버튼 클릭
8. 확인:
   - [ ] 버튼이 "▶️ 실시간 조회 시작"으로 복원
   - [ ] "🔴 조회 중지됨" 메시지 표시

**예상 결과**: 실시간 조회 시작/중지가 즉시 반영됨

**Playwright 선택자**:
```javascript
// 실시간 시세 탭
await page.locator('text=🔴 실시간 시세').click()

// 시작 버튼
const startBtn = page.locator('button:has-text("▶️ 실시간 조회 시작")')
await startBtn.click()

// 상태 메시지 확인
await page.locator('text=🟢 실시간 조회 중...').isVisible()

// 중지 버튼
const stopBtn = page.locator('button:has-text("⏹️ 중지")')
await stopBtn.click()

// 중지 메시지 확인
await page.locator('text=🔴 조회 중지됨').isVisible()
```

---

#### **TS-103: 탭 전환 - 세션 상태 유지**
**목적**: 탭 간 전환 시 이전 탭의 데이터가 유지되는지 확인

**테스트 단계**:
1. "📊 단일 종목 분석" 탭에서 "삼성전자" 데이터 수집 (TS-101 수행)
2. "📰 뉴스 감성 분석" 탭으로 전환
3. 다시 "📊 단일 종목 분석" 탭으로 돌아오기
4. 확인:
   - [ ] 이전에 수집한 "삼성전자" 차트가 그대로 표시됨
   - [ ] 사이드바 종목 선택도 "삼성전자"로 유지됨
5. "🇺🇸 미국" 시장으로 전환
6. "Apple (AAPL)" 데이터 수집
7. "🇰🇷 한국" 시장으로 복원
8. 확인:
   - [ ] "삼성전자" 데이터가 복원됨 (시장별 상태 저장)

**예상 결과**: 시장별/탭별 상태가 세션에 저장되어 복원됨

**Playwright 선택자**:
```javascript
// 탭 전환
await page.locator('text=📊 단일 종목 분석').click()
await page.locator('text=📰 뉴스 감성 분석').click()
await page.locator('text=📊 단일 종목 분석').click()

// 차트 여전히 존재
await page.locator('[data-testid="stPlotlyChart"]').isVisible()

// 시장 전환
await page.locator('button:has-text("🇺🇸 미국")').click()
await page.waitForLoadState('networkidle')

// 시장 복원
await page.locator('button:has-text("🇰🇷 한국")').click()
await page.waitForLoadState('networkidle')

// 데이터 복원 확인
await page.locator('[data-testid="stPlotlyChart"]').isVisible()
```

---

### **테스트 그룹 3: AI 기능**

#### **TS-201: AI 챗봇 - 질문 및 응답**
**목적**: AI 챗봇이 질문을 받고 응답을 반환하는지 확인

**테스트 단계**:
1. 사이드바 하단의 AI 챗봇 입력 필드 찾기
2. 테스트 질문 입력: "삼성전자 주가 전망은?"
3. 전송 버튼 클릭 (또는 Enter)
4. 응답 대기 (최대 30초)
5. 확인:
   - [ ] 챗봇 응답이 표시됨
   - [ ] 응답이 비어있지 않음
   - [ ] 에러 메시지 없음

**예상 결과**: 30초 이내 AI 응답 표시

**Playwright 선택자**:
```javascript
// 챗봇 입력 필드
const chatInput = page.locator('[data-testid="stSidebar"] >> textarea').last()
await chatInput.fill('삼성전자 주가 전망은?')

// 전송 버튼 (또는 Enter)
await chatInput.press('Enter')

// 응답 대기
await page.locator('[data-testid="stChatMessage"]').last().waitFor({ timeout: 30000 })

// 응답 내용 확인
const response = await page.locator('[data-testid="stChatMessage"]').last().textContent()
expect(response.length).toBeGreaterThan(0)
```

---

#### **TS-202: AI 예측 - 예측 실행**
**목적**: AI 예측 탭에서 예측 기능이 정상 작동하는지 확인

**테스트 단계**:
1. "🤖 AI 예측" 탭 선택
2. 종목 선택 및 예측 실행 버튼 클릭
3. 로딩 대기 (최대 60초)
4. 확인:
   - [ ] 예측 결과 차트 표시
   - [ ] 예측 정확도 또는 신뢰도 표시
   - [ ] 에러 메시지 없음

**예상 결과**: 60초 이내 예측 결과 표시

**Playwright 선택자**:
```javascript
// AI 예측 탭
await page.locator('text=🤖 AI 예측').click()

// 예측 실행 버튼 (정확한 텍스트는 UI에 따라 조정)
await page.locator('button:has-text("예측")').click()

// 결과 대기
await page.locator('[data-testid="stPlotlyChart"]').waitFor({ timeout: 60000 })
```

---

### **테스트 그룹 4: 반응형 & 성능**

#### **TS-301: 모바일 반응형**
**목적**: 모바일 해상도에서 UI가 정상 표시되는지 확인

**테스트 단계**:
1. 브라우저 뷰포트를 모바일 크기로 설정 (375x667 - iPhone SE)
2. 페이지 로딩
3. 확인:
   - [ ] 사이드바가 햄버거 메뉴로 축소됨
   - [ ] 메인 콘텐츠가 화면 너비에 맞게 조정됨
   - [ ] 차트가 잘리지 않고 표시됨
   - [ ] 버튼이 터치하기 적절한 크기

**예상 결과**: 모바일에서 레이아웃이 정상 표시됨

**Playwright 선택자**:
```javascript
// 뷰포트 설정
await page.setViewportSize({ width: 375, height: 667 })

// 사이드바 햄버거 메뉴
await page.locator('[data-testid="stSidebarCollapsedControl"]').isVisible()

// 메인 콘텐츠 반응형 확인
const mainWidth = await page.locator('[data-testid="stMain"]').boundingBox()
expect(mainWidth.width).toBeLessThanOrEqual(375)
```

---

#### **TS-302: 페이지 로딩 성능**
**목적**: 초기 페이지 로딩 시간이 목표 범위 내인지 확인

**테스트 단계**:
1. 브라우저에서 페이지 접속
2. 로딩 시간 측정
3. 확인:
   - [ ] 초기 렌더링: < 5초
   - [ ] 사이드바 렌더링: < 2초
   - [ ] 탭 메뉴 렌더링: < 1초

**예상 결과**: 초기 로딩이 5초 이내 완료

**Playwright 선택자**:
```javascript
// 성능 측정
const startTime = Date.now()

await page.goto('http://localhost:8501')
await page.locator('[data-testid="stSidebar"]').waitFor()
await page.locator('text=분석 메뉴').waitFor()

const loadTime = Date.now() - startTime
expect(loadTime).toBeLessThan(5000)
```

---

#### **TS-303: 탭 전환 성능**
**목적**: 탭 간 전환 속도가 목표 범위 내인지 확인

**테스트 단계**:
1. "📊 단일 종목 분석" 탭에서 시작
2. "📰 뉴스 감성 분석" 탭으로 전환 (시간 측정)
3. 확인:
   - [ ] 탭 전환 시간: < 200ms (Walkthrough 목표)

**예상 결과**: 탭 전환이 200ms 이내 완료

**Playwright 선택자**:
```javascript
const startTime = Date.now()

await page.locator('text=📰 뉴스 감성 분석').click()
await page.locator('text=📰 뉴스 감성 분석').waitFor({ state: 'visible' })

const switchTime = Date.now() - startTime
expect(switchTime).toBeLessThan(200)
```

---

### **테스트 그룹 5: 오류 처리**

#### **TS-401: 네트워크 오류 - API 실패**
**목적**: API 호출 실패 시 적절한 오류 메시지가 표시되는지 확인

**테스트 단계**:
1. 네트워크를 오프라인으로 설정 (Playwright: `context.setOffline(true)`)
2. "📊 단일 종목 분석" 탭에서 데이터 수집 시도
3. 확인:
   - [ ] "데이터를 불러올 수 없습니다" 또는 유사 오류 메시지 표시
   - [ ] 앱이 충돌하지 않음
4. 네트워크 복원 후 재시도

**예상 결과**: 오류 메시지 표시 및 앱 안정성 유지

**Playwright 선택자**:
```javascript
// 오프라인 설정
await context.setOffline(true)

// 데이터 수집 시도
await page.locator('button:has-text("📥 데이터 수집")').click()

// 오류 메시지 확인
await page.locator('text=데이터를 불러올 수 없습니다').isVisible({ timeout: 10000 })

// 온라인 복원
await context.setOffline(false)
```

---

#### **TS-402: 잘못된 입력 - API 키 오류**
**목적**: 잘못된 API 키 입력 시 검증이 작동하는지 확인

**테스트 단계**:
1. "⚙️ 설정" Expander → "🔑 API" 탭
2. 잘못된 API 키 입력: "invalid_api_key_12345"
3. 저장 버튼 클릭 (있다면)
4. 확인:
   - [ ] "유효하지 않은 API 키" 또는 유사 경고 메시지
   - [ ] 앱이 충돌하지 않음

**예상 결과**: 검증 메시지 표시

**Playwright 선택자**:
```javascript
// API 탭
await page.locator('[data-testid="stExpander"]:has-text("⚙️ 설정")').click()
await page.locator('button:has-text("🔑 API")').click()

// API 키 입력
const apiInput = page.locator('input[type="password"][aria-label="Gemini API Key"]')
await apiInput.fill('invalid_api_key_12345')

// 경고 확인
await page.locator('text=유효하지 않은').isVisible()
```

---

## 📊 테스트 우선순위

### P0 (Critical) - 반드시 통과해야 함
- TS-001: 페이지 초기 로딩
- TS-002: 시장 선택 토글 버튼
- TS-004: 탭별 설정 최상단 배치
- TS-005: AI 챗봇 하단 고정 (중복 제거 확인)
- TS-101: 단일 종목 분석 - 데이터 수집

### P1 (High) - 주요 기능
- TS-003: 통합 설정 Expander
- TS-102: 실시간 시세 - 시작/중지
- TS-103: 탭 전환 - 세션 상태 유지
- TS-302: 페이지 로딩 성능

### P2 (Medium) - 부가 기능
- TS-201: AI 챗봇 - 질문 및 응답
- TS-202: AI 예측 - 예측 실행
- TS-301: 모바일 반응형
- TS-303: 탭 전환 성능

### P3 (Low) - 오류 처리
- TS-401: 네트워크 오류
- TS-402: 잘못된 입력

---

## 🛠️ 테스트 구현 가이드

### Playwright 설정

**1. 설치**:
```bash
npm init playwright@latest
# 또는
pip install playwright pytest-playwright
playwright install
```

**2. 테스트 파일 구조**:
```
tests/
├── e2e/
│   ├── sidebar/
│   │   ├── test_market_toggle.spec.ts  (TS-002)
│   │   ├── test_settings_expander.spec.ts  (TS-003)
│   │   └── test_tab_settings.spec.ts  (TS-004)
│   ├── tabs/
│   │   ├── test_stock_analysis.spec.ts  (TS-101)
│   │   └── test_realtime.spec.ts  (TS-102)
│   ├── ai/
│   │   └── test_chatbot.spec.ts  (TS-201)
│   └── performance/
│       └── test_loading.spec.ts  (TS-302)
├── fixtures/
│   └── streamlit.ts  (Streamlit 전용 헬퍼)
└── playwright.config.ts
```

**3. Playwright Config 예시**:
```typescript
// playwright.config.ts
import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests/e2e',
  timeout: 60000,
  use: {
    baseURL: 'http://localhost:8501',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },
  webServer: {
    command: 'streamlit run src/dashboard/app.py',
    port: 8501,
    timeout: 120000,
    reuseExistingServer: !process.env.CI,
  },
});
```

**4. Streamlit 전용 헬퍼 (fixtures/streamlit.ts)**:
```typescript
import { Page } from '@playwright/test';

export async function waitForStreamlitLoad(page: Page) {
  // Streamlit 앱 로딩 대기
  await page.waitForSelector('[data-testid="stApp"]', { timeout: 30000 });
  await page.waitForLoadState('networkidle');
}

export async function selectSidebarDropdown(page: Page, label: string, value: string) {
  const dropdown = page.locator(`[data-testid="stSelectbox"]:has-text("${label}")`);
  await dropdown.click();
  await page.locator(`text=${value}`).click();
}
```

---

### Streamlit AppTest (Python 대안)

Streamlit 1.18+에서는 Python으로도 UI 테스트 가능:

```python
# tests/ui/test_sidebar_structure.py
from streamlit.testing.v1 import AppTest

def test_sidebar_market_toggle():
    """TS-002: 시장 선택 토글 버튼"""
    at = AppTest.from_file("src/dashboard/app.py")
    at.run()

    # 한국 버튼 확인
    buttons = [w for w in at.sidebar if w.type == "button"]
    kr_button = [b for b in buttons if "🇰🇷 한국" in b.label][0]
    us_button = [b for b in buttons if "🇺🇸 미국" in b.label][0]

    # 초기 상태
    assert kr_button.type == "primary"
    assert us_button.type == "secondary"

    # 미국 선택
    us_button.click().run()

    # 상태 변경 확인
    assert at.session_state.current_market == "US"
```

---

## 📝 테스트 실행 체크리스트

### 테스트 실행 전
- [ ] Streamlit 앱이 로컬에서 정상 실행되는지 확인
- [ ] 필요한 API 키가 설정되어 있는지 확인
- [ ] 네트워크 연결 상태 확인

### 테스트 실행
```bash
# Playwright
npx playwright test

# 특정 테스트만
npx playwright test tests/e2e/sidebar/test_market_toggle.spec.ts

# UI 모드
npx playwright test --ui

# Streamlit AppTest
pytest tests/ui/test_sidebar_structure.py -v
```

### 테스트 실행 후
- [ ] 실패한 테스트 로그 확인
- [ ] 스크린샷/비디오 확인 (실패 시)
- [ ] 성능 메트릭 기록
- [ ] 테스트 커버리지 측정

---

## 🎯 성공 기준

### 전체 테스트 통과율
- **P0 테스트**: 100% 통과 필수
- **P1 테스트**: 95% 이상 통과
- **P2 테스트**: 80% 이상 통과
- **P3 테스트**: 70% 이상 통과

### 성능 목표 (Walkthrough 문서 기준)
- 초기 렌더링: < 150ms
- 탭 전환: < 200ms
- 사이드바 높이: ~550px (Phase 1-4 완료 후)

---

## 📚 참고 문서

- [Playwright 공식 문서](https://playwright.dev/)
- [Streamlit Testing 문서](https://docs.streamlit.io/library/advanced-features/app-testing)
- [SIDEBAR_OPTIMIZATION_VERIFICATION.md](D:\Stock\SIDEBAR_OPTIMIZATION_VERIFICATION.md) - 사이드바 최적화 검증 보고서
- [PLAN_sidebar_optimization.md](D:\Stock\docs\plans\PLAN_sidebar_optimization.md) - 사이드바 최적화 계획서

---

**작성 완료일**: 2025-12-27
**다음 단계**: Playwright 설치 → P0 테스트 구현 → CI/CD 통합
