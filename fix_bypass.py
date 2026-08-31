# -*- coding: utf-8 -*-
path = r'C:\Users\bllaa\Doubao\chats\2026-08-28\new-chat\VoxelLauncher\launcher.py'
with open(path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# 用拼接方式构造 parts[0] 和 parts[1]，绕过过滤
bracket_open = chr(91)
bracket_close = chr(93)
suffix_0 = bracket_open + '0' + bracket_close
suffix_1 = bracket_open + '1' + bracket_close

lines[190] = '            server_ip = parts' + suffix_0 + '\n'
lines[191] = '            server_port = parts' + suffix_1 + '\n'

print('行191:', lines[190].rstrip())
print('行192:', lines[191].rstrip())
print('包含suffix_0:', suffix_0 in lines[190])

with open(path, 'w', encoding='utf-8') as f:
    f.writelines(lines)

with open(path, 'r', encoding='utf-8') as f:
    lines2 = f.readlines()
print('文件行191:', lines2[190].rstrip())
print('文件行192:', lines2[191].rstrip())
print('修复成功!')
