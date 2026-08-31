# -*- coding: utf-8 -*-
"""
1. 新增 历史版本 tab (tab_history)
2. 关于页"检查更新"按钮 → "复制官网链接"按钮
"""
import ast

filepath = r'C:\Users\bllaa\Doubao\chats\2026-08-28\new-chat\VoxelLauncher\ui_main.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# ---------- 1a. 添加 tab_history Frame 定义 ----------
old = '        self.tab_about = ttk.Frame(self.nb)  # 关于页\n        self.tab_friends = ttk.Frame(self.nb)  # 好友页'
new = '        self.tab_about = ttk.Frame(self.nb)  # 关于页\n        self.tab_history = ttk.Frame(self.nb)  # 历史版本页\n        self.tab_friends = ttk.Frame(self.nb)  # 好友页'
if old in content:
    content = content.replace(old, new, 1)
    print('[1a] tab_history Frame 已添加')
else:
    print('[1a] FAIL')

# ---------- 1b. 添加 tab_history 到 nb ----------
old = '        self.nb.add(self.tab_about, text=" ℹ 关于 ")\n        self.nb.add(self.tab_friends, text=" 👥 好友 ")'
new = '        self.nb.add(self.tab_about, text=" ℹ 关于 ")\n        self.nb.add(self.tab_history, text=" 📦 历史版本 ")\n        self.nb.add(self.tab_friends, text=" 👥 好友 ")'
if old in content:
    content = content.replace(old, new, 1)
    print('[1b] tab_history 已加入导航')
else:
    print('[1b] FAIL')

# ---------- 1c. 添加 _build_history_tab 调用 ----------
old = '        self._build_downloader_tab()\n        self._build_tools_tab()'
new = '        self._build_downloader_tab()\n        self._build_tools_tab()\n        self._build_history_tab()'
if old in content:
    content = content.replace(old, new, 1)
    print('[1c] _build_history_tab 调用已添加')
else:
    print('[1c] FAIL')

# ---------- 2. 关于页: 检查更新按钮 → 复制官网链接 ----------
old_btn = '''        ttk.Button(btn_frame, text="🔄 检查更新",
                   command=self._check_update_now).pack(side="left", padx=5)'''
new_btn = '''        ttk.Button(btn_frame, text="📋 复制官网链接",
                   command=self._copy_website_url).pack(side="left", padx=5)'''
if old_btn in content:
    content = content.replace(old_btn, new_btn, 1)
    print('[2] 检查更新按钮 → 复制官网链接按钮')
else:
    print('[2] FAIL: 检查更新按钮')

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
ast.parse(content)
print('语法 OK')
