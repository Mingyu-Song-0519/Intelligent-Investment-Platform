import sys
from pathlib import Path

# 프로젝트 루트를 시스템 경로에 추가
# (이 파일은 프로젝트 루트에 위치함)
PROJECT_ROOT = Path(__file__).parent.absolute()
sys.path.insert(0, str(PROJECT_ROOT))

# 실제 대시보드 메인 함수 임포트 및 실행
try:
    from src.dashboard.app import main
    if __name__ == "__main__":
        main()
except ImportError as e:
    import streamlit as st
    st.error(f"애플리케이션 실행 중 오류가 발생했습니다: {e}")
    st.info("필요한 모듈(src.dashboard.app)을 찾을 수 없습니다. 경로 설정을 확인해주세요.")
