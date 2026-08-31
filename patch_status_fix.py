# -*- coding: utf-8 -*-
"""修正 updater 的状态消息: 用 status 而非不存在的 upd_status"""
import ast

filepath = r'C:\Users\bllaa\Doubao\chats\2026-08-28\new-chat\VoxelLauncher\ui_main.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

replacements = [
    ('self._post("upd_status", "正在检查更新...")', 'self._post("status", "正在检查更新...")'),
    ('self._post("upd_status", "检查失败(网络问题), 请稍后重试")', 'self._post("status", "检查失败(网络问题)")'),
    ('self._post("upd_status", "发现新版本 v" + latest)', 'self._post("status", "发现新版本 v" + latest)'),
    ('self._post("upd_status", "已是最新版本 v" + version.VERSION)', 'self._post("status", "已是最新版本 v" + version.VERSION)'),
    ('self._post("upd_status", "检查更新出错: " + str(e))', 'self._post("status", "检查更新出错")'),
]
cnt = 0
for old, new in replacements:
    if old in content:
        content = content.replace(old, new)
        cnt += 1
with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
ast.parse(content)
print("修正", cnt, "处状态消息 ✓")
