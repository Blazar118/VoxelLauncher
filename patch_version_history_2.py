# -*- coding: utf-8 -*-
"""HISTORY_VERSIONS 加入 v2.2.5 作为最新版本"""
import ast

filepath = r'C:\Users\bllaa\Doubao\chats\2026-08-28\new-chat\VoxelLauncher\version.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

old = '''HISTORY_VERSIONS = [
    {
        "tag": "v2.2.2",
        "title": "v2.2.2 - 网络修复版",'''
new = '''HISTORY_VERSIONS = [
    {
        "tag": "v2.2.5",
        "title": "v2.2.5 - 历史版本+官网链接版",
        "desc": "新增「历史版本」页(可下载所有已发布版本)、关于页一键复制官网链接; 移除检查更新(改为直连官网和历史版本); 修复历史版本页崩溃、性能监控偶发崩溃",
        "url": GITHUB_URL + "/releases/download/v2.2.5/VoxelLauncher.exe",
    },
    {
        "tag": "v2.2.2",
        "title": "v2.2.2 - 网络修复版",'''
if old in content:
    content = content.replace(old, new, 1)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    ast.parse(content)
    print('HISTORY_VERSIONS 已加入 v2.2.5')
else:
    print('FAIL: 未找到锚点')
