import re

filepath = 'D:/Stock/src/dashboard/app.py'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# update_layout 호출에 dragmode=False 추가
# 패턴: fig.update_layout(...) 또는 fig_xxx.update_layout(...)

def add_dragmode(match):
    full = match.group(0)
    # 이미 dragmode가 있으면 그대로 반환
    if 'dragmode' in full:
        return full
    # 마지막 ) 앞에 dragmode=False 추가
    # update_layout( ... ) -> update_layout( ... , dragmode=False)
    # 닫는 괄호 찾기
    idx = full.rfind(')')
    if idx != -1:
        # 마지막 인자 뒤에 콤마가 없을 수 있음
        before = full[:idx].rstrip()
        if before.endswith(','):
            new_content = before + " dragmode=False)"
        else:
            new_content = before + ", dragmode=False)"
        return new_content
    return full

# fig.update_layout( ... ) 형태 매칭
# 간단한 방법: update_layout( 로 시작하고 ) 로 끝나는 부분 찾기
# 복잡한 중첩이 있을 수 있어서 간단한 케이스만 처리

# 더 간단한 방법: 줄 단위로 처리
lines = content.split('\n')
new_lines = []

for line in lines:
    # update_layout( 가 포함된 줄에서
    if '.update_layout(' in line and 'dragmode' not in line and line.rstrip().endswith(')'):
        # 단일 줄 update_layout
        line = line.rstrip()[:-1] + ', dragmode=False)'
    new_lines.append(line)

content = '\n'.join(new_lines)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("Done! Added dragmode=False to single-line update_layout calls.")
