# Dockerfile for Google Cloud Run
# Intelligent Investment Platform v3.1

# Python 3.11 슬림 이미지 사용 (경량화)
FROM python:3.11-slim

# 시스템 의존성 설치
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# 작업 디렉토리 설정
WORKDIR /app

# 의존성 파일 먼저 복사 (캐시 활용)
COPY requirements.txt .

# Python 패키지 설치
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 복사
COPY . .

# Streamlit 설정 파일 생성
RUN mkdir -p ~/.streamlit
RUN echo '\
    [server]\n\
    port = 8080\n\
    address = "0.0.0.0"\n\
    headless = true\n\
    enableCORS = false\n\
    enableXsrfProtection = false\n\
    \n\
    [browser]\n\
    gatherUsageStats = false\n\
    ' > ~/.streamlit/config.toml

# Cloud Run에서 사용하는 포트
EXPOSE 8080

# 환경 변수 설정
ENV PORT=8080
ENV PYTHONUNBUFFERED=1

# Streamlit 앱 실행
CMD ["streamlit", "run", "src/dashboard/app.py", "--server.port=8080", "--server.address=0.0.0.0"]
