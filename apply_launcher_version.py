# -*- coding: utf-8 -*-
"""把 launcher.py 的 LAUNCHER_VERSION 改为读统一版本模块"""
filepath = r'C:\Users\bllaa\Doubao\chats\2026-08-28\new-chat\VoxelLauncher\launcher.py'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# 添加 import version
if 'import version' not in content:
    content = content.replace('import version_manager', 'import version\nimport version_manager', 1)

# 替换版本号定义
old = 'LAUNCHER_VERSION = "1.0.0"'
new = 'LAUNCHER_VERSION = version.VERSION  # 与 version.py 统一'
if old in content:
    content = content.replace(old, new, 1)
    print("launcher.py 版本号改为统一来源 ✓")
else:
    print("未找到，检查...")

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

import ast
ast.parse(content)
print("语法检查 OK")
