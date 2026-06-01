@echo off
echo ========================================
echo   Stock Analysis Dashboard
echo   Python 3.12 + ML Full Stack
echo ========================================
echo.

cd /d "%~dp0"

REM venv_tf 환경 활성화 (Python 3.12 - TF/XGBoost/Torch 포함)
echo [1/3] 가상환경 활성화 중...
call venv_tf\Scripts\activate.bat

REM editable install 상태 확인 후 없으면 설치
echo [2/3] 패키지 설치 확인 중...
python -c "import jarvis_stock" 2>nul
if errorlevel 1 (
    echo      jarvis-stock editable install 없음, 설치 중...
    pip install -e . --quiet
    if errorlevel 1 (
        echo [ERROR] 설치 실패. 아래 명령어를 직접 실행하세요:
        echo         pip install -e .
        pause
        exit /b 1
    )
    echo      설치 완료.
) else (
    echo      jarvis-stock 확인됨.
)

REM 환경 변수
set STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
set TF_CPP_MIN_LOG_LEVEL=2
set KERAS_BACKEND=jax

REM 실행
echo [3/3] 대시보드 시작 중... (http://localhost:8501)
echo.
python -m streamlit run src\dashboard\app.py ^
    --server.port 8501 ^
    --browser.gatherUsageStats false

pause
