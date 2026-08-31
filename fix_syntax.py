# -*- coding: utf-8 -*-
filepath = r'C:\Users\bllaa\Doubao\chats\2026-08-28\new-chat\VoxelLauncher\ui_main.py'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# 先恢复语法: 去掉刚才加的 try:
old_try = '''    def _mr_download(self):
        try:
            sel = self.mr_tree.selection()'''

new_try = '''    def _mr_download(self):
        sel = self.mr_tree.selection()'''

if old_try in content:
    content = content.replace(old_try, new_try, 1)
    print("恢复try成功")

# 去掉刚才加的 except 块
old_except_block = '''        self._thread(_worker)
        except Exception as e:
            import traceback
            traceback.print_exc()
            try:
                self.mr_status.config(text="下载失败: " + str(e))
            except Exception:
                pass
            messagebox.showerror("下载失败", str(e))

    def _import_mrpack(self):'''

new_except_block = '''        self._thread(_worker)

    def _import_mrpack(self):'''

if old_except_block in content:
    content = content.replace(old_except_block, new_except_block, 1)
    print("恢复except成功")

# 恢复方法体缩进 (把 sel 开始的8空格缩进恢复成4空格)
# 这个比较复杂, 让我直接检查语法
import ast
try:
    ast.parse(content)
    print("语法OK")
except SyntaxError as e:
    print("语法错误:", e)
    # 打印错误附近的内容
    lines = content.split('\n')
    for i in range(max(0, e.lineno-5), min(len(lines), e.lineno+5)):
        print(f"{i+1}: {lines[i]}")

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
