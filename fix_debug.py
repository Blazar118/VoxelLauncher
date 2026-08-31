# -*- coding: utf-8 -*-
path = r'C:\Users\bllaa\Doubao\chats\2026-08-28\new-chat\VoxelLauncher\launcher.py'
with open(path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

old_line = lines[190]
print('旧行长度:', len(old_line))
print('旧行内容:', old_line.rstrip())

new_line = '            server_ip = parts[0]\n'
print('新行长度:', len(new_line))
print('新行内容:', new_line.rstrip())

lines[190] = new_line
print('赋值后长度:', len(lines[190]))
print('赋值后内容:', lines[190].rstrip())
print('赋值后包含[0]:', '[0]' in lines[190])

with open(path, 'w', encoding='utf-8') as f:
    f.writelines(lines)

with open(path, 'r', encoding='utf-8') as f:
    lines2 = f.readlines()
print('文件中行191长度:', len(lines2[190]))
print('文件中行191内容:', lines2[190].rstrip())
print('文件中包含[0]:', '[0]' in lines2[190])
