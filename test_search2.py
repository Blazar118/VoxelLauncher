# -*- coding: utf-8 -*-
import time
import sys
sys.path.insert(0, r'C:\Users\bllaa\Doubao\chats\2026-08-28\new-chat\VoxelLauncher')
import modrinth

print('测试空查询(热门模组)...')
start = time.time()
try:
    hits = modrinth.search_projects('', game_version='1.21.1', loader='fabric', limit=10)
    elapsed = time.time() - start
    print('成功! 耗时 {:.1f}秒, 找到 {} 个结果'.format(elapsed, len(hits)))
    for h in hits[:5]:
        title = h.get('title', '?')
        dl = h.get('downloads', 0)
        icon = h.get('icon_url', '')
        print('  - {} (下载: {}, 图标: {})'.format(title, dl, '有' if icon else '无'))
except Exception as e:
    elapsed = time.time() - start
    print('失败! 耗时 {:.1f}秒, 错误: {}'.format(elapsed, e))
