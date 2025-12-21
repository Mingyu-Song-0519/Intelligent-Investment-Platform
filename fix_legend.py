filepath = 'D:/Stock/src/dashboard/app.py'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# 주가 차트 관련 항목만 showlegend=True로 변경
# 나머지는 showlegend=False 유지

# 1. 캔들스틱, SMA 20, SMA 60, BB Upper, BB Lower -> showlegend=True
# 2. RSI, MACD, Signal, Histogram, 거래량 -> showlegend=False (제목에 설명)

# 패턴 교체
replacements = [
    # 캔들스틱
    ("name='주가',\n            increasing_line_color='#00d775',\n            decreasing_line_color='#ff4b4b',\n            showlegend=False",
     "name='주가',\n            increasing_line_color='#00d775',\n            decreasing_line_color='#ff4b4b',\n            showlegend=True"),
    # SMA 20
    ("name='SMA 20', \n                      line=dict(color='#ffa726', width=1),\n                      showlegend=False",
     "name='SMA 20', \n                      line=dict(color='#ffa726', width=1),\n                      showlegend=True"),
    # SMA 60
    ("name='SMA 60',\n                      line=dict(color='#42a5f5', width=1),\n                      showlegend=False",
     "name='SMA 60',\n                      line=dict(color='#42a5f5', width=1),\n                      showlegend=True"),
    # BB Upper
    ("name='BB Upper',\n                      line=dict(color='rgba(128,128,128,0.5)', width=1, dash='dash'),\n                      showlegend=False",
     "name='BB Upper',\n                      line=dict(color='rgba(128,128,128,0.5)', width=1, dash='dash'),\n                      showlegend=True"),
    # BB Lower
    ("name='BB Lower',\n                      line=dict(color='rgba(128,128,128,0.5)', width=1, dash='dash'),\n                      fill='tonexty', fillcolor='rgba(128,128,128,0.1)',\n                      showlegend=False",
     "name='BB Lower',\n                      line=dict(color='rgba(128,128,128,0.5)', width=1, dash='dash'),\n                      fill='tonexty', fillcolor='rgba(128,128,128,0.1)',\n                      showlegend=True"),
    # update_layout showlegend
    ("showlegend=False,  # 범례 비활성화 (제목에 설명 포함)",
     "showlegend=True,\n        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1)")
]

for old, new in replacements:
    content = content.replace(old, new)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("Done! Restored legend for price chart items.")
