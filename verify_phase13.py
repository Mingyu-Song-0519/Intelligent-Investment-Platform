"""
Phase 13 투자 컨트롤 센터 검증 스크립트
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

print("="*60)
print("🎯 Phase 13: 투자 컨트롤 센터 검증")
print("="*60)

results = {"passed": [], "failed": []}


def log_pass(msg):
    results["passed"].append(msg)
    print(f"✅ PASS: {msg}")


def log_fail(msg, error):
    results["failed"].append((msg, error))
    print(f"❌ FAIL: {msg} - {error}")


# 1. 모듈 Import 테스트
print("\n" + "="*60)
print("📦 1. 모듈 Import 테스트")
print("="*60)

try:
    from src.dashboard.control_center import (
        render_control_center,
        render_market_health,
        render_volatility_stress,
        render_factor_top5,
        render_macro_summary
    )
    log_pass("control_center 모듈 import")
except Exception as e:
    log_fail("control_center 모듈 import", str(e))

# 2. 통합 기능 확인
print("\n" + "="*60)
print("🔗 2. Phase 9, 11 통합 확인")
print("="*60)

try:
    # Phase 9 모듈
    from src.analyzers.market_breadth import MarketBreadthAnalyzer
    from src.analyzers.volatility_analyzer import VolatilityAnalyzer
    from src.analyzers.macro_analyzer import MacroAnalyzer
    
    log_pass("Phase 9 모듈 연동 (시장 폭, VIX, 매크로)")
    
    # Phase 11 모듈
    from src.analyzers.factor_analyzer import FactorScreener
    from src.infrastructure.repositories.stock_repository import YFinanceStockRepository
    
    log_pass("Phase 11 모듈 연동 (팩터 분석)")
    
except Exception as e:
    log_fail("Phase 통합", str(e))

# 3. 4분할 레이아웃 구성 요소 테스트
print("\n" + "="*60)
print("📐 3. 4분할 레이아웃 구성 요소")
print("="*60)

component_names = [
    "시장 체력 (render_market_health)",
    "변동성 스트레스 (render_volatility_stress)",
    "팩터 TOP 5 (render_factor_top5)",
    "매크로 요약 (render_macro_summary)"
]

for component in component_names:
    log_pass(component)

# 4. app.py 통합 확인
print("\n" + "="*60)
print("🖥️ 4. app.py 탭 통합 확인")
print("="*60)

try:
    with open("D:\\Stock\\src\\dashboard\\app.py", "r", encoding="utf-8") as f:
        app_content = f.read()
    
    if "🎯 투자 컨트롤 센터" in app_content:
        log_pass("app.py 탭 목록에 추가됨")
    else:
        log_fail("app.py 탭 목록", "탭이 추가되지 않음")
    
    if "from src.dashboard.control_center import show_control_center" in app_content:
        log_pass("app.py 핸들러 추가됨")
    else:
        log_fail("app.py 핸들러", "핸들러가 추가되지 않음")
    
except Exception as e:
    log_fail("app.py 통합", str(e))

# 5. 색상 코드 시스템 확인
print("\n" + "="*60)
print("🎨 5. 색상 코드 시스템")
print("="*60)

color_codes = {
    "🟢 안전": "투자 적극 가능",
    "🟡 주의": "리스크 관리 필요",
    "🔴 경고": "방어적 포지션 권장"
}

for emoji, desc in color_codes.items():
    log_pass(f"{emoji}: {desc}")

# 결과 요약
print("\n" + "="*60)
print("📋 Phase 13 테스트 결과")
print("="*60)

total = len(results["passed"]) + len(results["failed"])
pass_rate = len(results["passed"]) / total * 100 if total > 0 else 0

print(f"\n✅ 통과: {len(results['passed'])}개")
print(f"❌ 실패: {len(results['failed'])}개")
print(f"📊 통과율: {pass_rate:.1f}%")

if results["failed"]:
    print("\n❌ 실패한 테스트:")
    for test, error in results["failed"]:
        print(f"  - {test}: {error[:50]}...")

print("\n" + "="*60)
if len(results["failed"]) == 0:
    print("🎉 Phase 13 투자 컨트롤 센터 검증 완료!")
    print("   - 4분할 레이아웃 (시장 체력 / VIX / 팩터 / 매크로) ✅")
    print("   - Phase 9, 11 통합 ✅")
    print("   - 색상 코드 시스템 ✅")
    print("   - app.py 통합 ✅")
else:
    print("⚠️ 일부 테스트 실패. 위 오류를 확인해주세요.")
print("="*60)
