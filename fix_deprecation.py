import os

files_to_fix = [
    'D:/Stock/src/dashboard/app.py',
    'D:/Stock/src/dashboard/realtime_tab.py'
]

for filepath in files_to_fix:
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        content = content.replace('use_container_width=True', "width='stretch'")
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"Fixed: {filepath}")
    else:
        print(f"Not found: {filepath}")

print("Done!")
