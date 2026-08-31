# -*- coding: utf-8 -*-
import re

with open('launcher.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 用正则修复，不管缩进多少
content = re.sub(
    r'server_ip\s*=\s*parts(\s*\n\s*)server_port\s*=\s*parts',
    r'server_ip = parts[0]\1server_port = parts[1]',
    content
)

with open('launcher.py', 'w', encoding='utf-8') as f:
    f.write(content)

# 验证
pos = content.find('server_ip = parts')
print('修复后:', repr(content[pos:pos+100]))

import ast
ast.parse(content)
print('语法OK')
