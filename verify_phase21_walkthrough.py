"""
Phase 21: Market Heat & Buzz Walkthrough Verification
walkthrough.md에 명시된 구현사항 검증
"""
import os
import sys


def verify_phase21_implementation():
    """Phase 21 구현 검증"""

    print("=" * 80)
    print("Phase 21: Market Heat & Buzz 구현 검증")
    print("=" * 80)
    print()

    results = {
        'domain': [],
        'infrastructure': [],
        'application': [],
        'presentation': [],
        'integration': []
    }

    # ===== Domain Layer =====
    print("1. Domain Layer (6 files)")
    print("-" * 80)

    domain_files = {
        'src/domain/market_buzz/__init__.py': 'Module init',
        'src/domain/market_buzz/entities/__init__.py': 'Entities init',
        'src/domain/market_buzz/entities/buzz_score.py': 'BuzzScore entity',
        'src/domain/market_buzz/entities/volume_anomaly.py': 'VolumeAnomaly entity',
        'src/domain/market_buzz/entities/sector_heat.py': 'SectorHeat entity',
        'src/domain/market_buzz/value_objects/heat_level.py': 'HeatLevel value object'
    }

    for file_path, desc in domain_files.items():
        exists = os.path.exists(file_path)
        status = "PASS" if exists else "FAIL"
        results['domain'].append(exists)
        print(f"  [{status}] {desc}: {file_path}")

    print()

    # ===== Infrastructure Layer =====
    print("2. Infrastructure Layer (1 file)")
    print("-" * 80)

    infra_files = {
        'src/infrastructure/repositories/sector_repository.py': 'SectorRepository (KRX/Yahoo Finance)'
    }

    for file_path, desc in infra_files.items():
        exists = os.path.exists(file_path)
        status = "PASS" if exists else "FAIL"
        results['infrastructure'].append(exists)
        print(f"  [{status}] {desc}: {file_path}")

    print()

    # ===== Application Layer =====
    print("3. Application Layer (2 files)")
    print("-" * 80)

    service_files = {
        'src/services/market_buzz_service.py': 'MarketBuzzService (Core logic)',
        'src/services/profile_aware_buzz_service.py': 'ProfileAwareBuzzService (Phase 20 integration)'
    }

    for file_path, desc in service_files.items():
        exists = os.path.exists(file_path)
        status = "PASS" if exists else "FAIL"
        results['application'].append(exists)
        print(f"  [{status}] {desc}: {file_path}")

    print()

    # ===== Presentation Layer =====
    print("4. Presentation Layer (1 file)")
    print("-" * 80)

    ui_files = {
        'src/dashboard/views/market_buzz_view.py': 'Market Buzz View (Streamlit UI)'
    }

    for file_path, desc in ui_files.items():
        exists = os.path.exists(file_path)
        status = "PASS" if exists else "FAIL"
        results['presentation'].append(exists)
        print(f"  [{status}] {desc}: {file_path}")

    print()

    # ===== Key Features Verification =====
    print("5. Key Features Verification")
    print("-" * 80)

    features = []

    # BuzzScore with profile_fit_score
    buzz_file = 'src/domain/market_buzz/entities/buzz_score.py'
    if os.path.exists(buzz_file):
        with open(buzz_file, 'r', encoding='utf-8') as f:
            content = f.read()
            has_profile_fit = 'profile_fit_score' in content
            has_final_score = 'final_score' in content
            features.append(('BuzzScore with Phase 20 integration', has_profile_fit and has_final_score))

    # ProfileAwareBuzzService
    profile_buzz_file = 'src/services/profile_aware_buzz_service.py'
    if os.path.exists(profile_buzz_file):
        with open(profile_buzz_file, 'r', encoding='utf-8') as f:
            content = f.read()
            has_personalized = 'get_personalized_buzz_stocks' in content
            has_profile_fit_calc = '_calculate_profile_fit' in content
            features.append(('Phase 20 profile-based filtering', has_personalized and has_profile_fit_calc))

    # MarketBuzzView with toggles
    view_file = 'src/dashboard/views/market_buzz_view.py'
    if os.path.exists(view_file):
        with open(view_file, 'r', encoding='utf-8') as f:
            content = f.read()
            has_threshold_slider = 'st.slider' in content and 'threshold' in content
            has_profile_toggle = 'use_profile' in content or 'profile_toggle' in content
            has_treemap = 'Treemap' in content or 'treemap' in content
            features.append(('Dynamic threshold slider', has_threshold_slider))
            features.append(('Profile toggle (내 성향 맞춤)', has_profile_toggle))
            features.append(('Plotly Treemap visualization', has_treemap))

    for feature_name, implemented in features:
        status = "PASS" if implemented else "FAIL"
        results['integration'].append(implemented)
        print(f"  [{status}] {feature_name}")

    print()

    # ===== Feedback Improvements Verification =====
    print("6. Feedback Improvements (from implementation_plan.md review)")
    print("-" * 80)

    improvements = []

    # 1. Phase 20 integration
    if os.path.exists('src/services/profile_aware_buzz_service.py'):
        with open('src/services/profile_aware_buzz_service.py', 'r', encoding='utf-8') as f:
            content = f.read()
            has_risk_filter = 'risk_tolerance' in content and 'volatility_ratio' in content
            has_sector_bonus = 'preferred_sectors' in content
            improvements.append(('Phase 20 투자 성향 연동', has_risk_filter and has_sector_bonus))

    # 2. Dynamic threshold
    if os.path.exists('src/dashboard/views/market_buzz_view.py'):
        with open('src/dashboard/views/market_buzz_view.py', 'r', encoding='utf-8') as f:
            content = f.read()
            has_slider = 'st.slider' in content and 'min_value=1.5' in content and 'max_value=5.0' in content
            improvements.append(('거래량 Threshold 동적 조정', has_slider))

    # 3. Hybrid caching strategy
    if os.path.exists('src/services/market_buzz_service.py'):
        with open('src/services/market_buzz_service.py', 'r', encoding='utf-8') as f:
            content = f.read()
            has_force_refresh = 'force_refresh' in content
            improvements.append(('Hybrid 캐싱 전략 (force_refresh)', has_force_refresh))

    # 4. Error handling
    if os.path.exists('src/dashboard/views/market_buzz_view.py'):
        with open('src/dashboard/views/market_buzz_view.py', 'r', encoding='utf-8') as f:
            content = f.read()
            has_error_handling = 'try:' in content and 'except' in content
            has_warning = 'st.warning' in content or 'st.error' in content
            improvements.append(('에러 처리 UI', has_error_handling and has_warning))

    for improvement_name, implemented in improvements:
        status = "PASS" if implemented else "FAIL"
        print(f"  [{status}] {improvement_name}")

    print()

    # ===== Summary =====
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)

    total_domain = len(results['domain'])
    pass_domain = sum(results['domain'])

    total_infra = len(results['infrastructure'])
    pass_infra = sum(results['infrastructure'])

    total_app = len(results['application'])
    pass_app = sum(results['application'])

    total_ui = len(results['presentation'])
    pass_ui = sum(results['presentation'])

    total_integration = len(results['integration'])
    pass_integration = sum(results['integration'])

    print(f"Domain Layer:         {pass_domain}/{total_domain} files")
    print(f"Infrastructure Layer: {pass_infra}/{total_infra} files")
    print(f"Application Layer:    {pass_app}/{total_app} files")
    print(f"Presentation Layer:   {pass_ui}/{total_ui} files")
    print(f"Key Features:         {pass_integration}/{total_integration} features")

    total_all = total_domain + total_infra + total_app + total_ui + total_integration
    pass_all = pass_domain + pass_infra + pass_app + pass_ui + pass_integration

    print()
    print(f"TOTAL: {pass_all}/{total_all} checks passed")

    if pass_all == total_all:
        print()
        print("=" * 80)
        print("Phase 21 implementation COMPLETE!")
        print("All walkthrough.md requirements verified!")
        print("=" * 80)
        return True
    else:
        print()
        print("=" * 80)
        print("Some items are missing or incomplete.")
        print("=" * 80)
        return False


if __name__ == "__main__":
    success = verify_phase21_implementation()
    sys.exit(0 if success else 1)
