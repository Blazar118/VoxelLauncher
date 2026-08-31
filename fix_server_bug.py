# -*- coding: utf-8 -*-
with open('launcher.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 修复 server_ip = parts -> parts[0], server_port = parts -> parts[1]
old = 'server_ip = parts\n            server_port = parts'
new = 'server_ip = parts[0]\n            server_port = parts[1]'

if old in content:
    content = content.replace(old, new)
    with open('launcher.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print('修复成功!')
else:
    print('未找到，尝试查找...')
    import re
    # 查找所有 server_ip = parts 的位置
    for m in re.finditer(r'server_ip\s*=\s*parts', content):
        print(f'位置 {m.start()}: {repr(content[m.start():m.start()+80])}')
