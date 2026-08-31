# -*- coding: utf-8 -*-
"""设置页添加代理设置行 + 保存"""
import ast

filepath = r'C:\Users\bllaa\Doubao\chats\2026-08-28\new-chat\VoxelLauncher\ui_main.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# ---------- 1. 在主题行后加代理行 ----------
anchor = '''        self.theme_combo.bind("<<ComboboxSelected>>", self._on_theme_selected)
        ttk.Label(row_theme, text="(选择后立即生效, 可在启动页看到效果)", foreground="#888").pack(side="left")

        row_bridge = ttk.Frame(box)'''
addition = '''        self.theme_combo.bind("<<ComboboxSelected>>", self._on_theme_selected)
        ttk.Label(row_theme, text="(选择后立即生效, 可在启动页看到效果)", foreground="#888").pack(side="left")

        row_proxy = ttk.Frame(box)
        row_proxy.pack(fill="x", padx=6, pady=3)
        ttk.Label(row_proxy, text="代理(加速器):").pack(side="left")
        self.setting_proxy = ttk.Entry(row_proxy, width=30)
        self.setting_proxy.pack(side="left", padx=4)
        self.setting_proxy.insert(0, CONFIG.get("proxy") or "")
        ttk.Label(row_proxy, text="留空自动探测 (如 http://127.0.0.1:7890)", foreground="#888").pack(side="left")

        row_bridge = ttk.Frame(box)'''
if anchor in content:
    content = content.replace(anchor, addition, 1)
    print("[1] 代理设置行已添加 ✓")
else:
    print("[1] ❌ 未找到主题行锚点")

# ---------- 2. 保存设置时保存代理 ----------
old_save = '''        # 保存主题
        if hasattr(self, "theme_var"):
            CONFIG.set("theme", self.theme_var.get())
        self._apply_launch_background()'''
new_save = '''        # 保存主题
        if hasattr(self, "theme_var"):
            CONFIG.set("theme", self.theme_var.get())
        # 保存代理
        if hasattr(self, "setting_proxy"):
            CONFIG.set("proxy", self.setting_proxy.get().strip())
        self._apply_launch_background()'''
if old_save in content:
    content = content.replace(old_save, new_save, 1)
    print("[2] 保存代理设置 ✓")
else:
    print("[2] ❌ 未找到保存主题位置")

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
ast.parse(content)
print("语法 OK")
