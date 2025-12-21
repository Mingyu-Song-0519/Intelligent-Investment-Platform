# 한국투자증권 API 설정 가이드

## 1. KIS Developers 가입

1. 한국투자증권 계좌 개설
2. [KIS Developers](https://apiportal.koreainvestment.com/) 접속
3. Open API 서비스 신청

## 2. API 키 발급

- **모의투자**: 테스트용 계좌 (무료)
- **실전투자**: 실제 거래 계좌

발급받을 정보:
- App Key
- App Secret  
- 계좌번호

## 3. 환경변수 설정

### Windows (PowerShell)
```powershell
$env:KIS_APP_KEY="your_app_key"
$env:KIS_APP_SECRET="your_app_secret"
$env:KIS_ACCOUNT_NO="your_account_number"
```

### 또는 `.env` 파일 생성

`D:\Stock\.env` 파일:
```
KIS_APP_KEY=your_app_key
KIS_APP_SECRET=your_app_secret
KIS_ACCOUNT_NO=your_account_number
KIS_IS_VIRTUAL=True  # False면 실전투자
```

## 4. python-kis 설치

```bash
cd D:\Stock
.\venv_tf\Scripts\activate
pip install python-kis
```

## 5. 테스트

```bash
python src\collectors\kis_realtime_collector.py
```

## 주의사항

- 모의투자는 **평일 09:00-15:30** 운영
- API 초당 20회 호출 제한
- WebSocket은 최대 40개 종목 동시 구독 가능
