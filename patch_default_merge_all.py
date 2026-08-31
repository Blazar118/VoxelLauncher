# -*- coding: utf-8 -*-
"""所有模组加载器安装都默认使用合并模式"""
import ast

p = r'C:\Users\bllaa\Doubao\chats\2026-08-28\new-chat\VoxelLauncher\ui_main.py'
with open(p, 'r', encoding='utf-8') as f:
    c = f.read()

# 1) 提示文案: 说明所有加载器都默认合并
old_hint = '''        tk.Label(dlg, text="默认使用 PCL 合并模式 (mods/saves 都在版本文件夹里)",
                 fg="gray", font=("Arial", 8)).pack(anchor="w", padx=20, pady=(6, 0))'''
new_hint = '''        tk.Label(dlg, text="安装模组加载器默认使用合并模式 (mods/saves 都在版本文件夹里, 同 PCL)",
                 fg="gray", font=("Arial", 8)).pack(anchor="w", padx=20, pady=(6, 0))'''
if old_hint in c:
    c = c.replace(old_hint, new_hint, 1)
    print('提示文案已更新')
else:
    print('WARN: 未找到提示文案')

# 2) 默认合并: 所有加载器都是 True
old_use = '''        # 与 PCL 一致: Fabric 默认直接使用合并模式, 不再弹出询问
        use_merged = (loader == "Fabric")'''
new_use = '''        # 与 PCL 一致: 只要安装了模组加载器就默认使用合并模式, 不再弹出询问
        use_merged = True'''
if old_use in c:
    c = c.replace(old_use, new_use, 1)
    print('use_merged 已改为对所有加载器默认 True')
else:
    print('WARN: 未找到 use_merged 块')

with open(p, 'w', encoding='utf-8') as f:
    f.write(c)
ast.parse(c)
print('语法检查通过')
