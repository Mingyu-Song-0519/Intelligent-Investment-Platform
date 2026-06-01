# Gemini API 마이그레이션 가이드

## 개요
2025년 12월 28일, 기존 `google-generativeai` 패키지에서 신규 `google-genai` 패키지로 마이그레이션을 완료하였습니다.

## 주요 변경사항
### 1. 패키지 의존성
- **제거**: `google-generativeai` (deprecated)
- **추가**: `google-genai` (recommended)

### 2. 코드 구조 변화
- **Client 중심 설계**: 모델 인스턴스를 유지하는 대신 `genai.Client`를 통해 모든 호출을 수행합니다.
- **설정 방식**: `genai.configure()` 대신 `genai.Client(api_key=...)`를 사용합니다.
- **시스템 지시**: `GenerateContentConfig`를 통해 명시적으로 전달합니다.

## 수정된 파일
- `src/infrastructure/external/gemini_client.py`: 핵심 클라이언트 로직 리팩토링
- `src/infrastructure/repositories/session_api_key_repository.py`: API 키 검증 로직 업데이트
- `src/dashboard/components/sidebar_chat.py`: 사이드바 연결 테스트 로직 업데이트
- `requirements.txt`: 의존성 라이브러리 교체

## 검증 결과
- **Unit Tests**: `tests/infrastructure/` 내 신규 테스트 케이스 통과
- **E2E Tests**: Playwright 기반 30개 테스트 100% 통과 확인
- **Baseline**: `e2e_baseline.txt` 대비 기능 회귀 없음 확인

## 롤백 방법 (필요 시)
1. `.bak` 파일로 복원 (작업 직후인 경우):
   ```bash
   cp src/infrastructure/external/gemini_client.py.bak src/infrastructure/external/gemini_client.py
   cp src/infrastructure/repositories/session_api_key_repository.py.bak src/infrastructure/repositories/session_api_key_repository.py
   cp src/dashboard/components/sidebar_chat.py.bak src/dashboard/components/sidebar_chat.py
   cp requirements.txt.bak requirements.txt
   ```
2. 패키지 재설치:
   ```bash
   pip uninstall google-genai -y
   pip install google-generativeai>=0.8.0
   ```
