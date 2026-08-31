# -*- coding: utf-8 -*-
"""移除启动后自动检查更新"""
import ast

filepath = r'C:\Users\bllaa\Doubao\chats\2026-08-28\new-chat\VoxelLauncher\ui_main.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

old = '''        # 启动后后台检查更新
        self.root.after(3000, self._maybe_auto_check)
'''
new = '''        # 检查更新已移除: 改为「历史版本」页 + 复制官网链接
'''
if old in content:
    content = content.replace(old, new, 1)
    print('[1] 已移除启动后自动检查更新')
else:
    print('[1] FAIL: 自动检查调用')

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
ast.parse(content)
print('语法 OK')
