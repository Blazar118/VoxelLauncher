# -*- coding: utf-8 -*-
filepath = r'C:\Users\bllaa\Doubao\chats\2026-08-28\new-chat\VoxelLauncher\launcher.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

if 'import version\n' not in content:
    content = content.replace('import version_manager', 'import version\nimport version_manager', 1)
    print("已添加 import version")
else:
    print("import version 已存在")

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

import ast
ast.parse(content)
print("语法 OK")
