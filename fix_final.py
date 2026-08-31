# -*- coding: utf-8 -*-
path = r'C:\Users\bllaa\Doubao\chats\2026-08-28\new-chat\VoxelLauncher\launcher.py'
with open(path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

print('修改前行191:', repr(lines[190]))
print('修改前行192:', repr(lines[191]))

lines[190] = '            server_ip = parts[0]\n'
lines[191] = '            server_port = parts[1]\n'

print('内存中191:', repr(lines[190]))
print('内存中192:', repr(lines[191]))

with open(path, 'w', encoding='utf-8') as f:
    f.writelines(lines)

print('写入完成')

with open(path, 'r', encoding='utf-8') as f:
    lines2 = f.readlines()
print('重新读取行191:', repr(lines2[190]))
print('重新读取行192:', repr(lines2[191]))
