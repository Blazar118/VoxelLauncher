# -*- coding: utf-8 -*-
"""修复自动加入服务器：改用 --quickPlayMultiplayer 参数"""
import re

filepath = r'C:\Users\bllaa\Doubao\chats\2026-08-28\new-chat\VoxelLauncher\launcher.py'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# 找到 server_args 部分并替换
old = '''    server_args = []
    if server_address:
        # 支持 IP:端口 格式
        if ":" in server_address:
            parts = server_address.rsplit(":", 1)
            server_ip = parts[0]
            server_port = parts[1]
            server_args = ["--server", server_ip, "--port", server_port]
        else:
            server_args = ["--server", server_address]'''

new = '''    server_args = []
    if server_address:
        # Minecraft 1.20+ 使用 Quick Play 参数, 旧的 --server 会被忽略
        # 格式: --quickPlayMultiplayer <ip:port>
        server_args = ["--quickPlayMultiplayer", server_address]'''

if old in content:
    content = content.replace(old, new, 1)
    print("替换成功!")
else:
    print("未找到旧代码，尝试正则...")
    # 用正则匹配
    pattern = r'    server_args = \[\]\s*\n\s*if server_address:.*?server_args = \["--server", server_address\]'
    match = re.search(pattern, content, re.DOTALL)
    if match:
        content = content[:match.start()] + new + content[match.end():]
        print("正则替换成功!")
    else:
        print("还是没找到，打印附近内容")
        idx = content.find('server_args = []')
        print(repr(content[idx:idx+500]))

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

import ast
ast.parse(content)
print("语法OK")

# 验证
with open(filepath, 'r', encoding='utf-8') as f:
    c2 = f.read()
idx = c2.find('server_args = []')
print("替换后:")
print(c2[idx:idx+300])
