# -*- coding: utf-8 -*-
filepath = r'C:\Users\bllaa\Doubao\chats\2026-08-28\new-chat\VoxelLauncher\ui_main.py'

with open(filepath, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# 修复 3945-3957 行的缩进 (从 12 空格改成 8 空格)
# 注意: Python 行号从 0 开始, 所以 3945 行是 index 3944
for i in range(3944, 3957):
    if i < len(lines):
        line = lines[i]
        if line.startswith('            '):  # 12空格
            lines[i] = '        ' + line[12:]  # 改成8空格
            print(f"修复行 {i+1}: {lines[i].rstrip()}")

with open(filepath, 'w', encoding='utf-8') as f:
    f.writelines(lines)

import ast
try:
    ast.parse(''.join(lines))
    print("语法OK")
except SyntaxError as e:
    print("语法错误:", e)
    for i in range(max(0, e.lineno-3), min(len(lines), e.lineno+3)):
        print(f"{i+1}: {lines[i].rstrip()}")
