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
VERSION = "2.2.2"
VERSION_TAG = "v" + VERSION  # v2.1.0

# 项目信息
PROJECT_NAME = "VoxelLauncher"
GITHUB_REPO = "Blazar118/VoxelLauncher"
GITHUB_URL = "https://github.com/" + GITHUB_REPO

# 下载地址（Release 附件直链）
DOWNLOAD_URL = GITHUB_URL + "/releases/latest/download/VoxelLauncher.exe"

# 官网地址
WEBSITE_URL = "https://blazar118.github.io/VoxelLauncher/"


def get_project_root():
    """返回项目根目录（version.py 所在目录）"""
    return os.path.dirname(os.path.abspath(__file__))


def get_version():
    """返回版本号字符串，如 2.1.0"""
    return VERSION


def get_version_tag():
    """返回带 v 的版本标签，如 v2.1.0"""
    return VERSION_TAG
