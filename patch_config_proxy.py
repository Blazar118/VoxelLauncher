# -*- coding: utf-8 -*-
"""config.py 添加 proxy 配置项"""
filepath = r'C:\Users\bllaa\Doubao\chats\2026-08-28\new-chat\VoxelLauncher\config.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

old = '    "window_geometry": None,               # 主窗口位置(可选)'
new = '''    "window_geometry": None,               # 主窗口位置(可选)
    "proxy": "",                          # 手动代理地址(如 http://127.0.0.1:7890), 留空自动探测'''
if old in content:
    content = content.replace(old, new, 1)
    print("config.py 添加 proxy 字段 ✓")
else:
    print("❌ 未找到 window_geometry")

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
import ast
ast.parse(content)
print("语法 OK")
