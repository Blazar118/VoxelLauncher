# -*- coding: utf-8 -*-
"""updater.py: _detect_proxy 优先读取 config 手动代理"""
filepath = r'C:\Users\bllaa\Doubao\chats\2026-08-28\new-chat\VoxelLauncher\updater.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

old = '''def _detect_proxy():
    """按优先级探测可用代理"""
    # 1. 环境变量(用户手动配置过优先)
    p = _env_proxy()
    if p:
        return p
    # 2. 系统代理
    p = _read_system_proxy()
    if p:
        return p
    # 3. 常见本地代理端口
    p = _probe_local_proxy()
    if p:
        return p
    return None'''

new = '''def _detect_proxy():
    """按优先级探测可用代理"""
    # 1. 启动器设置页手动配置的代理(最优先)
    try:
        from config import CONFIG
        manual = CONFIG.get("proxy") or ""
        manual = manual.strip()
        if manual:
            if not manual.startswith(("http://", "https://", "socks")):
                manual = "http://" + manual
            return manual
    except Exception:
        pass
    # 2. 环境变量(用户手动配置过优先)
    p = _env_proxy()
    if p:
        return p
    # 3. 系统代理
    p = _read_system_proxy()
    if p:
        return p
    # 4. 常见本地代理端口
    p = _probe_local_proxy()
    if p:
        return p
    return None'''

if old in content:
    content = content.replace(old, new, 1)
    print("updater.py 代理优先级更新 ✓")
else:
    print("❌ 未找到 _detect_proxy")

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
import ast
ast.parse(content)
print("语法 OK")
