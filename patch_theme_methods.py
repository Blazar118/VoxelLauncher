# -*- coding: utf-8 -*-
"""
Patch 3: 添加主题相关方法 + 保存设置里保存主题
- 添加 _update_theme_desc / _on_theme_selected 方法
- 在 _save_settings 里保存主题
"""
import ast

filepath = r'C:\Users\bllaa\Doubao\chats\2026-08-28\new-chat\VoxelLauncher\ui_main.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# ---------- 1. 添加方法（放在 _browse_background 前） ----------
anchor = '''    def _browse_background(self):'''
methods = '''    def _update_theme_desc(self):
        """更新主题描述标签"""
        if not hasattr(self, "theme_desc_label"):
            return
        key = self.theme_var.get() if hasattr(self, "theme_var") else "default"
        theme = themes.get_theme(key)
        self.theme_desc_label.config(text="{} - {}".format(theme["name"], theme["desc"]))

    def _on_theme_selected(self, event=None):
        """主题选中立即生效"""
        key = self.theme_var.get()
        CONFIG.set("theme", key)
        self._update_theme_desc()
        self._apply_launch_background()

    def _browse_background(self):'''

if anchor in content:
    content = content.replace(anchor, methods, 1)
    print("[1] 主题方法已添加 ✓")
else:
    print("[1] ❌ 未找到 _browse_background")

# ---------- 2. 保存设置里保存主题 ----------
old_save = '''        # 保存背景图片
        bg = self.setting_bg.get().strip()
        CONFIG.set("background_image", bg if bg else None)
        self._apply_launch_background()'''
new_save = '''        # 保存背景图片
        bg = self.setting_bg.get().strip()
        CONFIG.set("background_image", bg if bg else None)
        # 保存主题
        if hasattr(self, "theme_var"):
            CONFIG.set("theme", self.theme_var.get())
        self._apply_launch_background()'''
if old_save in content:
    content = content.replace(old_save, new_save, 1)
    print("[2] 保存主题 ✓")
else:
    print("[2] ❌ 未找到保存背景位置")

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
ast.parse(content)
print("语法 OK")
