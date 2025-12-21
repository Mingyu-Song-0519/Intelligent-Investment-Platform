import re

filepath = 'D:/Stock/src/dashboard/app.py'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. st.plotly_chart(..., width='stretch') -> st.plotly_chart(..., width='stretch', config={'scrollZoom': False})
# 기존에 config가 없는 경우에만 추가
pattern = r"st\.plotly_chart\(([^)]+), width='stretch'\)"

def add_config(match):
    inner = match.group(1)
    # 이미 config가 있으면 그대로 반환
    if 'config=' in inner:
        return match.group(0)
    return f"st.plotly_chart({inner}, width='stretch', config={{'scrollZoom': False}})"

content = re.sub(pattern, add_config, content)

# 2. update_layout에 dragmode=False 추가 (선택적 - 너무 복잡할 수 있음)
# 일단 config만 추가

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("Done! Plotly charts updated with scrollZoom: False config.")
