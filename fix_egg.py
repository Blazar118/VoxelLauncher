# -*- coding: utf-8 -*-
"""修复 _show_egg 的换行转义问题"""
import ast

filepath = r'C:\Users\bllaa\Doubao\chats\2026-08-28\new-chat\VoxelLauncher\ui_main.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# 找到 _show_egg 方法的坏块并重写
import re
start = content.find('    def _show_egg(self, title):')
end = content.find('    def _open_launcher_dir(self):', start)
if start == -1 or end == -1:
    print("未找到 _show_egg")
    raise SystemExit(1)

new_method = '''    def _show_egg(self, title):
        """显示彩蛋"""
        import random
        NL = chr(10)
        eggs = [
            "🎉 你发现了隐藏彩蛋!" + NL + NL + "VoxelLauncher 是由 AI 和你一起开发的!" + NL + "继续加油!",
            "🎉 彩蛋!" + NL + NL + "为什么苦力怕害怕猫? 因为怕被喵喵哒～",
            "🎉 恭喜!" + NL + NL + "你已经点了 10 次标题了, 手速不错!" + NL + "送你一个成就: 手速达人",
            "🎉 隐藏内容解锁!" + NL + NL + "提示: 去设置页把主题切成 '苦力怕绿' 看看效果",
            "🎉 厉害!" + NL + NL + "这个启动器里还有更多彩蛋等你发现!",
        ]
        messagebox.showinfo("🎉 " + title, random.choice(eggs))

'''
content = content[:start] + new_method + content[end:]
with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
ast.parse(content)
print("_show_egg 修复完成 ✓")
