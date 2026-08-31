# -*- coding: utf-8 -*-
"""
Patch 2: 设置页添加主题切换下拉
在"启动页背景"行后面加"主题风格"下拉
"""
import ast

filepath = r'C:\Users\bllaa\Doubao\chats\2026-08-28\new-chat\VoxelLauncher\ui_main.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# 在清除背景按钮后添加主题下拉行
anchor = '''        ttk.Button(row_bg, text="清除", command=self._clear_background).pack(
            side="left", padx=3)'''

addition = anchor + '''

        row_theme = ttk.Frame(box)
        row_theme.pack(fill="x", padx=6, pady=3)
        ttk.Label(row_theme, text="主题风格:").pack(side="left")
        self.theme_var = tk.StringVar(value=CONFIG.get("theme", "default"))
        theme_keys = list(themes.THEMES.keys())
        self.theme_combo = ttk.Combobox(row_theme, textvariable=self.theme_var,
                                        values=theme_keys, state="readonly", width=12)
        self.theme_combo.pack(side="left", padx=4)
        # 显示当前主题描述
        self.theme_desc_label = tk.Label(row_theme, text="", fg="#888")
        self.theme_desc_label.pack(side="left", padx=6)
        self._update_theme_desc()
        self.theme_combo.bind("<<ComboboxSelected>>", self._on_theme_selected)
        ttk.Label(row_theme, text="(选择后立即生效, 可在启动页看到效果)", foreground="#888").pack(side="left")'''

if anchor in content:
    content = content.replace(anchor, addition, 1)
    print("[1] 主题下拉已添加 ✓")
else:
    print("[1] ❌ 未找到清除按钮锚点")

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
ast.parse(content)
print("语法 OK")
