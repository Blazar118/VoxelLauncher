# -*- coding: utf-8 -*-
"""
Patch 1: 添加 import + 主题支持
- 添加 import themes, updater
- _apply_launch_background 支持主题壁纸(无自定义图时用主题色/生成壁纸)
- 设置页添加主题下拉
"""
import ast

filepath = r'C:\Users\bllaa\Doubao\chats\2026-08-28\new-chat\VoxelLauncher\ui_main.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

orig = content

# ---------- 1. 添加 import ----------
if 'import themes' not in content:
    content = content.replace('import version\nimport version_manager',
                              'import version\nimport version_manager\nimport themes\nimport updater', 1)
    print("[1] import themes/updater ✓")

# ---------- 2. 改造 _apply_launch_background ----------
old_bg = '''    def _apply_launch_background(self):
        """应用启动页背景图片"""
        bg_path = CONFIG.get("background_image")
        if not bg_path or not os.path.exists(bg_path):
            self._launch_canvas.configure(bg="#f0f0f0")
            self._launch_bg_img = None
            return
        try:
            from PIL import Image, ImageTk
            img = Image.open(bg_path).convert("RGBA")
            # 缩放到 Canvas 大小
            cw = self._launch_canvas.winfo_width() or 800
            ch = self._launch_canvas.winfo_height() or 600
            img = img.resize((cw, ch), Image.LANCZOS)
            self._launch_bg_img = ImageTk.PhotoImage(img)
            self._launch_canvas.delete("bg")
            self._launch_canvas.create_image(0, 0, anchor="nw",
                image=self._launch_bg_img, tags="bg")
            self._launch_canvas.tag_lower("bg")
        except Exception:
            self._launch_canvas.configure(bg="#f0f0f0")
            self._launch_bg_img = None'''

new_bg = '''    def _apply_launch_background(self):
        """应用启动页背景/主题壁纸"""
        # 主题色
        theme_key = CONFIG.get("theme", "default")
        theme = themes.get_theme(theme_key)
        # 优先自定义背景图片
        bg_path = CONFIG.get("background_image")
        if not bg_path or not os.path.exists(bg_path):
            # 用主题壁纸
            wpath = themes.generate_wallpaper(theme_key, 1600, 900)
            if wpath and os.path.exists(wpath):
                bg_path = wpath
            else:
                self._launch_canvas.configure(bg=theme["bg"])
                self._launch_bg_img = None
                return
        try:
            from PIL import Image, ImageTk
            img = Image.open(bg_path).convert("RGBA")
            # 缩放到 Canvas 大小
            cw = self._launch_canvas.winfo_width() or 800
            ch = self._launch_canvas.winfo_height() or 600
            img = img.resize((cw, ch), Image.LANCZOS)
            self._launch_bg_img = ImageTk.PhotoImage(img)
            self._launch_canvas.delete("bg")
            self._launch_canvas.create_image(0, 0, anchor="nw",
                image=self._launch_bg_img, tags="bg")
            self._launch_canvas.tag_lower("bg")
        except Exception:
            self._launch_canvas.configure(bg=theme["bg"])
            self._launch_bg_img = None'''

if old_bg in content:
    content = content.replace(old_bg, new_bg, 1)
    print("[2] 背景主题支持 ✓")
else:
    print("[2] ❌ 未找到 _apply_launch_background 原文")

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
ast.parse(content)
print("语法 OK")
