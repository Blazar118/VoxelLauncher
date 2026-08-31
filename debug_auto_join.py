# -*- coding: utf-8 -*-
"""调试自动加入服务器功能"""
import sys
sys.path.insert(0, r'C:\Users\bllaa\Doubao\chats\2026-08-28\new-chat\VoxelLauncher')

import launcher
from pathlib import Path
import json

# 模拟一个实例
mc_root = Path(r'C:\Users\bllaa\.minecraft')
version_id = '1.21.1-fabric'
vjson = mc_root / 'versions' / version_id / (version_id + '.json')

print('版本JSON存在:', vjson.exists())

if vjson.exists():
    with open(vjson, 'r', encoding='utf-8') as f:
        version_data = json.load(f)
    
    instance = {
        'version_id': version_id,
        'game_dir': str(mc_root / 'instances' / '1.21.1-fabric'),
        'min_memory': 1024,
        'max_memory': 2048,
        'jvm_args': '',
    }
    account = {
        'username': 'test',
        'uuid': 'test-uuid',
        'access_token': 'test-token',
        'user_type': 'msa',
    }
    java_path = r'C:\Users\bllaa\AppData\Local\Programs\Eclipse Adoptium\jdk-21.0.12.8-hotspot\bin\java.exe'
    
    # 测试带 server_address
    cmd = launcher.build_command(instance, account, java_path, version_data, 
                                  server_address='127.0.0.1:25565')
    
    print('\n=== 带 IP:端口 的命令 ===')
    # 找 --server 和 --port
    for i, arg in enumerate(cmd):
        if 'server' in arg.lower() or 'port' in arg.lower() or arg == '127.0.0.1' or arg == '25565':
            print(f'  参数[{i}]: {arg}')
    
    # 测试纯IP
    cmd2 = launcher.build_command(instance, account, java_path, version_data,
                                   server_address='127.0.0.1')
    print('\n=== 纯IP的命令 ===')
    for i, arg in enumerate(cmd2):
        if 'server' in arg.lower() or 'port' in arg.lower() or arg == '127.0.0.1':
            print(f'  参数[{i}]: {arg}')
    
    # 打印主类位置和后面的参数
    print('\n=== 主类及之后的参数 ===')
    for i, arg in enumerate(cmd):
        if 'KnotClient' in arg or 'main.Main' in arg:
            print(f'主类位置[{i}]: {arg}')
            print('主类之后的参数:')
            for j in range(i+1, min(i+10, len(cmd))):
                print(f'  [{j}]: {cmd[j]}')
            break
else:
    print('版本JSON不存在，检查路径')
