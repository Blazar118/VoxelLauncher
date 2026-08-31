# -*- coding: utf-8 -*-
"""把 ui_main.py 里写死的版本号改成从 version 模块读取"""
filepath = r'C:\Users\bllaa\Doubao\chats\2026-08-28\new-chat\VoxelLauncher\ui_main.py'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. 添加 import version（在 version_manager 前）
if 'import version\n' not in content:
    content = content.replace('import version_manager', 'import version\nimport version_manager', 1)
    print("添加 import version ✓")

# 2. 关于页版本号
old1 = 'tk.Label(info_frame, text="版本: v2.1.0", font=("Arial", 10)).grid('
new1 = 'tk.Label(info_frame, text="版本: " + version.VERSION_TAG, font=("Arial", 10)).grid('
if old1 in content:
    content = content.replace(old1, new1, 1)
    print("关于页版本号改为统一来源 ✓")
else:
    print("未找到关于页版本号，检查实际内容...")

# 3. 检查更新弹窗版本号
old2 = '"当前已是最新版本 v2.1.0" + chr(10) +'
new2 = '"当前已是最新版本 " + version.VERSION_TAG + chr(10) +'
if old2 in content:
    content = content.replace(old2, new2, 1)
    print("检查更新弹窗版本号改为统一来源 ✓")
else:
    print("未找到检查更新弹窗版本号，检查实际内容...")

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

import ast
ast.parse(content)
print("语法检查 OK")
print("残留 v2.1.0:", content.count('v2.1.0'))
print("version.VERSION_TAG 使用数:", content.count('version.VERSION_TAG'))
