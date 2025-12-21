@echo off
echo ========================================
echo   Stock Analysis Dashboard (Phase 2)
echo   Using Python 3.12 + TensorFlow + XGBoost
echo ========================================
echo.

cd /d "%~dp0"

echo [INFO] Activating virtual environment (venv_tf)...
call venv_tf\Scripts\activate.bat

echo [INFO] Starting Streamlit Dashboard...
echo.

REM 이메일 프롬프트 비활성화
set STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

python -m streamlit run src\dashboard\app.py --server.port 8501 --browser.gatherUsageStats false

pause
