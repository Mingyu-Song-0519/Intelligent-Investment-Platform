"""
주식 시장 동향 분석 및 주가 예측 프로그램 - 메인 진입점
"""
import subprocess
import sys
from pathlib import Path

# 프로젝트 루트 경로
PROJECT_ROOT = Path(__file__).parent.absolute()


def main():
    """Streamlit 대시보드 실행"""
    dashboard_path = PROJECT_ROOT / "src" / "dashboard" / "app.py"
    
    print("=" * 50)
    print("📈 주식 분석 대시보드 시작")
    print("=" * 50)
    print(f"대시보드 경로: {dashboard_path}")
    print()
    
    # Streamlit 실행
    subprocess.run([
        sys.executable, "-m", "streamlit", "run",
        str(dashboard_path),
        "--server.headless=true",
        "--browser.gatherUsageStats=false"
    ])


if __name__ == "__main__":
    main()
