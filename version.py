# -*- coding: utf-8 -*-
"""
VoxelLauncher 统一版本号管理（唯一权威来源）
- 启动器、官网、Release 全部从这里读
- 升级版本号只需改这里，或调用 release.py 自动升级
"""
import os

# ---------------------------------------------------------------
# 版本号（唯一权威来源）
# ---------------------------------------------------------------
VERSION = "2.2.9"
VERSION_TAG = "v" + VERSION  # v2.1.0

# 项目信息
PROJECT_NAME = "VoxelLauncher"
GITHUB_REPO = "Blazar118/VoxelLauncher"
GITHUB_URL = "https://github.com/" + GITHUB_REPO

# 下载地址（Release 附件直链）
DOWNLOAD_URL = GITHUB_URL + "/releases/latest/download/VoxelLauncher.exe"

# 官网地址
WEBSITE_URL = "https://blazar118.github.io/VoxelLauncher/"


# ---------------------------------------------------------------
# 历史版本（启动器"历史版本"页展示, 每版对应一个 Release 下载直链）
# 按从新到旧排列
# ---------------------------------------------------------------
HISTORY_VERSIONS = [
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
    },
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
]


def get_project_root():
    """返回项目根目录（version.py 所在目录）"""
    return os.path.dirname(os.path.abspath(__file__))


def get_version():
    """返回版本号字符串，如 2.1.0"""
    return VERSION


def get_version_tag():
    """返回带 v 的版本标签，如 v2.1.0"""
    return VERSION_TAG
