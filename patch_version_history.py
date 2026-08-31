# -*- coding: utf-8 -*-
"""version.py 添加 HISTORY_VERSIONS"""
filepath = r'C:\Users\bllaa\Doubao\chats\2026-08-28\new-chat\VoxelLauncher\version.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

anchor = '# 官网地址\nWEBSITE_URL = "https://blazar118.github.io/VoxelLauncher/"'
addition = anchor + '''


# ---------------------------------------------------------------
# 历史版本（启动器"历史版本"页展示, 每版对应一个 Release 下载直链）
# 按从新到旧排列
# ---------------------------------------------------------------
HISTORY_VERSIONS = [
    {
        "tag": "v2.2.2",
        "title": "v2.2.2 - 网络修复版",
        "desc": "修复检查更新连不上的问题: 网络策略改为优先直连(自动适配 Watt Toolkit 等加速器), 直连失败才走代理; 彩蛋改为隐蔽触发(关于页连点标题10次); 代理设置支持 Socks5",
        "url": GITHUB_URL + "/releases/download/v2.2.2/VoxelLauncher.exe",
    },
    {
        "tag": "v2.2.1",
        "title": "v2.2.1 - 彩蛋隐藏版",
        "desc": "彩蛋从明面按钮改为隐蔽触发, 不让用户轻易发现; 支持加速器代理自动检测",
        "url": GITHUB_URL + "/releases/download/v2.2.1/VoxelLauncher.exe",
    },
    {
        "tag": "v2.2.0",
        "title": "v2.2.0 - 稳定版",
        "desc": "整体稳定性优化与细节修复",
        "url": GITHUB_URL + "/releases/download/v2.2.0/VoxelLauncher.exe",
    },
    {
        "tag": "v2.1.0",
        "title": "v2.1.0 - 联机增强版",
        "desc": "自动加入服务器、自动下载依赖、智能崩溃分析、深度模组冲突检测、一键开服增强、FPS监控、一键局域网; 修复自动加入服务器不工作(改用 --quickPlayMultiplayer 参数)",
        "url": GITHUB_URL + "/releases/download/v2.1.0/VoxelLauncher.exe",
    },
    {
        "tag": "v2.0.0",
        "title": "v2.0.0 - 首个公开版",
        "desc": "版本下载、Fabric/Forge 加载器、Modrinth/CurseForge 模组、实例管理、资源/数据/光影/整合包、高速下载、微软账号登录; 娱乐(挖矿/钓鱼/养殖/宠物AI/苦力怕+村民)、战斗(僵尸/武器/掉落)、游戏联动",
        "url": GITHUB_URL + "/releases/download/v2.0.0/VoxelLauncher.exe",
    },
]'''

if anchor in content:
    content = content.replace(anchor, addition, 1)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    import ast
    ast.parse(content)
    print('version.py 已添加 HISTORY_VERSIONS OK')
else:
    print('FAIL: 未找到锚点')
