# -*- coding: utf-8 -*-
"""新建实例对话框: 合并模式默认勾选 (与 PCL 一致)"""
import ast

p = r'C:\Users\bllaa\Doubao\chats\2026-08-28\new-chat\VoxelLauncher\ui_main.py'
with open(p, 'r', encoding='utf-8') as f:
    c = f.read()

# 只在 _new_instance 里改 (该处紧邻 ver_entry), 不碰 _install_loader(已删勾选框)
old = '''        ver_entry.pack(padx=20)

        merged_var = tk.BooleanVar(value=False)
        tk.Checkbutton(dlg, text="PCL2 合并模式 (版本文件夹=游戏目录, mods/saves 都在版本目录里)",
                       variable=merged_var).pack(anchor="w", padx=20, pady=(10, 5))'''
new = '''        ver_entry.pack(padx=20)

        merged_var = tk.BooleanVar(value=True)
        tk.Checkbutton(dlg, text="PCL2 合并模式 (版本文件夹=游戏目录, mods/saves 都在版本目录里)",
                       variable=merged_var).pack(anchor="w", padx=20, pady=(10, 5))'''

if old in c:
    c = c.replace(old, new, 1)
    print('新建实例对话框: 合并模式默认勾选')
else:
    print('WARN: 未找到新建实例的合并勾选框')

with open(p, 'w', encoding='utf-8') as f:
    f.write(c)
ast.parse(c)
print('语法检查通过')
