# -*- coding: utf-8 -*-
"""回退版本号测试改动，恢复为 v2.1.0"""
vfile = r'C:\Users\bllaa\Doubao\chats\2026-08-28\new-chat\VoxelLauncher\version.py'
hfile = r'C:\Users\bllaa\Doubao\chats\2026-08-28\new-chat\VoxelLauncher\docs\index.html'

# version.py
with open(vfile, 'r', encoding='utf-8') as f:
    vc = f.read()
vc = vc.replace('VERSION = "2.1.1"', 'VERSION = "2.1.0"', 1)
with open(vfile, 'w', encoding='utf-8') as f:
    f.write(vc)

# index.html
with open(hfile, 'r', encoding='utf-8') as f:
    hc = f.read()
hc = hc.replace('v2.1.1', 'v2.1.0')
hc = hc.replace('2.1.1', '2.1.0')
with open(hfile, 'w', encoding='utf-8') as f:
    f.write(hc)

print("已回退到 v2.1.0")
import version
import importlib
importlib.reload(version)
print("当前版本:", version.VERSION)
