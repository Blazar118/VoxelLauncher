# -*- coding: utf-8 -*-
"""修复 _build_history_tab: LabelFrame 不能传 padx/pady 给构造函数"""
import ast

filepath = r'C:\Users\bllaa\Doubao\chats\2026-08-28\new-chat\VoxelLauncher\ui_main.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

old = '        detail_frame = ttk.LabelFrame(f, text=" 选中版本 ", padx=8, pady=4)\n'
new = '        detail_frame = ttk.LabelFrame(f, text=" 选中版本 ")\n'
if old in content:
    content = content.replace(old, new, 1)
    print('[1] LabelFrame padx/pady 已移除')
else:
    print('[1] FAIL')

# 同时检查其它 LabelFrame 是否也有同样问题(history tab 里)
import re
lines = content.split('\n')
for idx, line in enumerate(lines):
    if 'ttk.LabelFrame(' in line and ('padx=' in line or 'pady=' in line):
        print('其他问题行 {}: {}'.format(idx + 1, line.strip()))

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
ast.parse(content)
print('语法 OK')
