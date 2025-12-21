import re

filepath = 'D:/Stock/src/dashboard/app.py'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Pattern 1: update_layout에 xaxis_tickformat 추가
# fig.update_layout(...) 또는 fig_xxx.update_layout(...)에 xaxis 설정 추가

# 간단한 방법: update_layout 호출 직후에 xaxis 날짜 형식 설정 코드 추가
# fig.update_xaxes(tickformat="%Y년 %m월")

# 모든 fig.update_layout 다음 줄에 xaxis 설정 추가하는 것은 복잡함
# 대신, 한글 날짜 형식을 적용하는 헬퍼 함수를 추가하고 차트 생성 후 호출

# 더 간단한 방법: app.py 상단에 Plotly 기본 설정 추가
# plotly.io.templates.default의 xaxis 설정

# 가장 실용적인 방법: 각 차트 생성 함수(create_candlestick_chart 등)에서 설정

# create_candlestick_chart 함수의 update_layout에 xaxis_tickformat 추가
old_candlestick_layout = '''fig.update_layout(
        height=900,
        template='plotly_dark',
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        xaxis_rangeslider_visible=False
    )'''

new_candlestick_layout = '''fig.update_layout(
        height=900,
        template='plotly_dark',
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        xaxis_rangeslider_visible=False
    )
    
    # X축 날짜 형식 한글화
    fig.update_xaxes(tickformat="%Y년 %m월", row=1, col=1)
    fig.update_xaxes(tickformat="%Y년 %m월", row=2, col=1)
    fig.update_xaxes(tickformat="%Y년 %m월", row=3, col=1)
    fig.update_xaxes(tickformat="%Y년 %m월", row=4, col=1)'''

content = content.replace(old_candlestick_layout, new_candlestick_layout)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("Done! Updated create_candlestick_chart with Korean date format.")
