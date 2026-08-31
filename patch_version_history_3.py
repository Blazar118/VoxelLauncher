# -*- coding: utf-8 -*-
"""历史版本列表补充 v2.2.7 / v2.2.6"""
import ast

p = r'C:\Users\bllaa\Doubao\chats\2026-08-28\new-chat\VoxelLauncher\version.py'
with open(p, 'r', encoding='utf-8') as f:
    c = f.read()

old = '''HISTORY_VERSIONS = [
    {
        "tag": "v2.2.5",
        "title": "v2.2.5 - 历史版本+官网链接版",
        "desc": "新增「历史版本」页(可下载所有已发布版本)、关于页一键复制官网链接; 移除检查更新(改为直连官网和历史版本); 修复历史版本页崩溃、性能监控偶发崩溃",
        "url": GITHUB_URL + "/releases/download/v2.2.5/VoxelLauncher.exe",
    },'''

new = '''HISTORY_VERSIONS = [
    {
        "tag": "v2.2.7",
        "title": "v2.2.7 - 默认合并模式版",
        "desc": "安装模组加载器(Fabric/Quilt/Forge/NeoForge)默认使用 PCL 合并模式, 不再弹窗询问; 版本文件夹即游戏目录, mods/saves 都在版本文件夹里",
        "url": GITHUB_URL + "/releases/download/v2.2.7/VoxelLauncher.exe",
    },
    {
        "tag": "v2.2.6",
        "title": "v2.2.6 - 历史版本完善版",
        "desc": "修复历史版本页崩溃(LabelFrame 参数错误); 修复性能监控偶发崩溃",
        "url": GITHUB_URL + "/releases/download/v2.2.6/VoxelLauncher.exe",
    },
    {
        "tag": "v2.2.5",
        "title": "v2.2.5 - 历史版本+官网链接版",
        "desc": "新增「历史版本」页(可下载所有已发布版本)、关于页一键复制官网链接; 移除检查更新(改为直连官网和历史版本); 修复历史版本页崩溃、性能监控偶发崩溃",
        "url": GITHUB_URL + "/releases/download/v2.2.5/VoxelLauncher.exe",
    },'''

if old in c:
    c = c.replace(old, new, 1)
    with open(p, 'w', encoding='utf-8') as f:
        f.write(c)
    ast.parse(c)
    print('OK: 已补充 v2.2.7 / v2.2.6 到历史版本列表')
else:
    print('FAIL: 未找到锚点')
