# -*- coding: utf-8 -*-
"""修复 _find_minecraft_process: cmdline 可能为 None"""
import ast

filepath = r'C:\Users\bllaa\Doubao\chats\2026-08-28\new-chat\VoxelLauncher\ui_main.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

old = '''        for proc in psutil.process_iter(["pid", "name", "cmdline"]):
            try:
                name = proc.info["name"].lower()
                cmdline = " ".join(proc.info.get("cmdline", [])).lower()
                if "java" in name and ("minecraft" in cmdline or "net.minecraft" in cmdline
                                       or "launcher" in cmdline):
                    return proc
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return None'''
new = '''        for proc in psutil.process_iter(["pid", "name", "cmdline"]):
            try:
                name = (proc.info.get("name") or "").lower()
                cmd_parts = proc.info.get("cmdline") or []
                if not isinstance(cmd_parts, (list, tuple)):
                    cmd_parts = []
                cmdline = " ".join(str(x) for x in cmd_parts).lower()
                if "java" in name and ("minecraft" in cmdline or "net.minecraft" in cmdline
                                       or "launcher" in cmdline):
                    return proc
            except (psutil.NoSuchProcess, psutil.AccessDenied, TypeError):
                continue
        return None'''
if old in content:
    content = content.replace(old, new, 1)
    print('_find_minecraft_process 已修复')
else:
    print('FAIL: 未找到原代码')

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
ast.parse(content)
print('语法 OK')
