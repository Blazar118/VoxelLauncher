# -*- coding: utf-8 -*-
import os
p = r'C:\Users\bllaa\Doubao\chats\2026-08-28\new-chat\VoxelLauncher\ui_main.py'
st = os.stat(p)
print('只读标志:', bool(os.stat(p).st_file_attributes & 1) if hasattr(os.stat(p), 'st_file_attributes') else 'n/a')
print('大小:', st.st_size)
with open(p, 'r', encoding='utf-8') as f:
    c = f.read()
print('已含新文案:', '默认使用 PCL 合并模式' in c)
print('仍含旧合并变量:', 'result = {"name": "", "merged": False' in c)
