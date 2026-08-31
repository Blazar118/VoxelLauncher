# -*- coding: utf-8 -*-
import os, re, glob

# 找所有 py 文件里的版本号定义
files = glob.glob(r'C:\Users\bllaa\Doubao\chats\2026-08-28\new-chat\VoxelLauncher\*.py')
# 排除备份和临时文件
skip = ['backup_', 'fix_', 'debug_', 'enhance_', 'update_', 'add_', 'comprehensive_', 'patch_', 'test_', 'check_', '_res_']
for fname in files:
    base = os.path.basename(fname)
    if any(base.startswith(s) for s in skip):
        continue
    with open(fname, 'r', encoding='utf-8') as f:
        content = f.read()
    for m in re.finditer(r'(__version__|VERSION|APP_VERSION|LAUNCHER_VERSION|version_info)\s*[=:]\s*["\']([^"\']+)["\']', content):
        print(f'{base}: {m.group(0).strip()}')
