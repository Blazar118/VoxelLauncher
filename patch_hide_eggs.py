# -*- coding: utf-8 -*-
"""
移除暴露的彩蛋入口, 改成纯隐蔽触发
- 删除"🎁 彩蛋"按钮
- 删除 _egg_toggle 方法(其提示文本暴露了彩蛋线索)
- 标题点击彩蛋完全静默: 不弹任何"再点几次"提示, 只在满10次时触发
"""
import ast

filepath = r'C:\Users\bllaa\Doubao\chats\2026-08-28\new-chat\VoxelLauncher\ui_main.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# ---------- 1. 删除彩蛋按钮 ----------
old_btn = '''        ttk.Button(btn_frame, text="🔄 检查更新",
                   command=self._check_update_now).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="🎁 彩蛋",
                   command=self._egg_toggle).pack(side="left", padx=5)'''
new_btn = '''        ttk.Button(btn_frame, text="🔄 检查更新",
                   command=self._check_update_now).pack(side="left", padx=5)'''
if old_btn in content:
    content = content.replace(old_btn, new_btn, 1)
    print("[1] 已删除彩蛋按钮 ✓")
else:
    print("[1] ❌ 未找到彩蛋按钮")

# ---------- 2. 删除 _egg_toggle 方法 ----------
start = content.find('    def _egg_toggle(self):')
if start != -1:
    # 找到下一个方法定义
    next_def = content.find('\n    def ', start + 10)
    if next_def != -1:
        block = content[start:next_def]
        content = content[:start] + content[next_def:]
        print("[2] 已删除 _egg_toggle 方法 ✓")
    else:
        print("[2] ❌ 找不到方法边界")
else:
    print("[2] _egg_toggle 不存在")

# ---------- 3. 标题点击彩蛋完全静默 ----------
old_click = '''    def _on_about_title_click(self, event=None):
        """点击关于页标题10次触发彩蛋"""
        self._about_click_count += 1
        if self._about_click_count >= 10:
            self._about_click_count = 0
            self._show_egg("超级彩蛋")
        elif self._about_click_count == 5:
            self._post("status", "再点 " + str(10 - self._about_click_count) + " 次标题有惊喜...")'''
new_click = '''    def _on_about_title_click(self, event=None):
        """隐蔽彩蛋: 连点标题10次触发(不留任何提示, 靠玩家自己发现)"""
        self._about_click_count += 1
        if self._about_click_count >= 10:
            self._about_click_count = 0
            self._show_egg("隐藏成就解锁")'''
if old_click in content:
    content = content.replace(old_click, new_click, 1)
    print("[3] 标题点击彩蛋改为静默 ✓")
else:
    print("[3] ❌ 未找到 _on_about_title_click")

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
ast.parse(content)
print("语法 OK")
