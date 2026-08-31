# -*- coding: utf-8 -*-
import ast

p = r'C:\Users\bllaa\Doubao\chats\2026-08-28\new-chat\VoxelLauncher\ui_main.py'
with open(p, 'r', encoding='utf-8') as f:
    c = f.read()
ast.parse(c)
print('ui_main.py 语法 OK')

checks = {
    '安装加载器提示文案(默认合并)': '安装模组加载器默认使用合并模式' in c,
    'use_merged = True': 'use_merged = True' in c,
    'worker 分支 fabric 判定': 'if use_merged and loader == "fabric"' in c,
    '安装加载器旧勾选框已移除': 'result = {"name": "", "merged": False' not in c,
    '新建实例默认合并(value=True)': 'merged_var = tk.BooleanVar(value=True)' in c,
}
for k, v in checks.items():
    print(('PASS' if v else 'FAIL') + ' | ' + k)
