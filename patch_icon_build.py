# -*- coding: utf-8 -*-
"""release.py 打包时使用 app.ico 作为 exe 图标"""
import ast

p = r'C:\Users\bllaa\Doubao\chats\2026-08-28\new-chat\VoxelLauncher\release.py'
with open(p, 'r', encoding='utf-8') as f:
    c = f.read()

old = '''    cmd = [PY, "-m", "PyInstaller", "--onefile", "--windowed",
           "--name", "VoxelLauncher"]
    for h in hidden:
        cmd += ["--hidden-import", h]
    cmd.append("main.py")'''

new = '''    cmd = [PY, "-m", "PyInstaller", "--onefile", "--windowed",
           "--name", "VoxelLauncher",
           "--icon", os.path.join(ROOT, "app.ico")]
    for h in hidden:
        cmd += ["--hidden-import", h]
    cmd.append("main.py")'''

if old in c:
    c = c.replace(old, new, 1)
    with open(p, 'w', encoding='utf-8') as f:
        f.write(c)
    ast.parse(c)
    print('OK: build_exe 已加入 --icon app.ico')
else:
    print('FAIL: 未找到 build_exe 命令块')
