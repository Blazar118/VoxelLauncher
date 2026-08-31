# -*- coding: utf-8 -*-
"""
Patch 5: 启动时自动检查更新 + logo彩蛋
- __init__ 末尾调用 _maybe_auto_check
- 关于页标题点击10次触发彩蛋
"""
import ast

filepath = r'C:\Users\bllaa\Doubao\chats\2026-08-28\new-chat\VoxelLauncher\ui_main.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# ---------- 1. __init__ 末尾加自动检查更新 ----------
anchor = '''        # 刷新积分显示
        self.root.after(1000, self._refresh_points)'''
addition = anchor + '''

        # 启动后后台检查更新
        self.root.after(3000, self._maybe_auto_check)'''
if anchor in content:
    content = content.replace(anchor, addition, 1)
    print("[1] 启动自动检查更新 ✓")
else:
    print("[1] ❌ 未找到 __init__ 锚点")

# ---------- 2. 关于页标题点击彩蛋 ----------
old_title = '''        tk.Label(title_frame, text="VoxelLauncher", bg="#2b2b2b",
                 fg="#ffffff", font=("Arial", 24, "bold")).pack(pady=(15, 0))'''
new_title = '''        self.about_title_label = tk.Label(title_frame, text="VoxelLauncher", bg="#2b2b2b",
                 fg="#ffffff", font=("Arial", 24, "bold"))
        self.about_title_label.pack(pady=(15, 0))
        self._about_click_count = 0
        self.about_title_label.bind("<Button-1>", self._on_about_title_click)'''
if old_title in content:
    content = content.replace(old_title, new_title, 1)
    print("[2] 关于页标题点击绑定 ✓")
else:
    print("[2] ❌ 未找到关于页标题")

# ---------- 3. 添加彩蛋方法 ----------
anchor2 = '''    def _open_launcher_dir(self):'''
methods = '''    def _on_about_title_click(self, event=None):
        """点击关于页标题10次触发彩蛋"""
        self._about_click_count += 1
        if self._about_click_count >= 10:
            self._about_click_count = 0
            self._show_egg("超级彩蛋")
        elif self._about_click_count == 5:
            self._post("status", "再点 " + str(10 - self._about_click_count) + " 次标题有惊喜...")

    def _show_egg(self, title):
        """显示彩蛋"""
        import random
        eggs = [
            "🎉 你发现了隐藏彩蛋!\n\nVoxelLauncher 是由 AI 和你一起开发的!\n继续加油!",
            "🎉 彩蛋!\n\n为什么苦力怕害怕猫? 因为怕被喵喵哒～",
            "🎉 恭喜!\n\n你已经点了 10 次标题了, 手速不错!\n送你一个成就: 手速达人",
            "🎉 隐藏内容解锁!\n\n提示: 去设置页把主题切成 '苦力怕绿' 看看效果",
            "🎉 厉害!\n\n这个启动器里还有更多彩蛋等你发现!",
        ]
        messagebox.showinfo("🎉 " + title, random.choice(eggs))

    def _open_launcher_dir(self):'''

if anchor2 in content:
    content = content.replace(anchor2, methods, 1)
    print("[3] 彩蛋方法已添加 ✓")
else:
    print("[3] ❌ 未找到 _open_launcher_dir")

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
ast.parse(content)
print("语法 OK")
