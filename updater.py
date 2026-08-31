# -*- coding: utf-8 -*-
"""
VoxelLauncher - 自动更新模块
- 启动时后台检查 GitHub 最新 Release
- 与本地版本号对比, 有新版则提示一键更新
- 下载新版 exe 并替换当前程序
"""
import os
import re
import shutil
import subprocess
import sys
import threading
import time

import requests

import version


def get_latest_version():
    """
    从 GitHub API 获取最新 Release 版本号。
    返回 (version_str, download_url) 或 (None, None) 表示获取失败。
    """
    api = "https://api.github.com/repos/{}/releases/latest".format(version.GITHUB_REPO)
    try:
        r = requests.get(api, timeout=8)
        if r.status_code != 200:
            return None, None
        data = r.json()
        tag = data.get("tag_name", "")  # 例如 v2.1.0
        ver = tag.lstrip("v")
        # 找 exe 下载地址
        url = None
        for asset in data.get("assets", []):
            if asset.get("name", "").endswith(".exe"):
                url = asset.get("browser_download_url")
                break
        if not url:
            url = version.DOWNLOAD_URL
        return ver, url
    except Exception:
        return None, None


def is_newer(latest, current):
    """判断 latest 是否比 current 新 (纯数字版本比较)"""
    def _parse(v):
        parts = re.findall(r"\d+", v or "")
        return [int(x) for x in parts[:3]] + [0] * (3 - len(parts))
    return _parse(latest) > _parse(current)


def check_for_update():
    """
    检查是否有更新。返回:
        None  = 获取失败(网络问题)
        (False, "") = 已是最新
        (True, latest_ver) = 有新版本
    """
    latest, url = get_latest_version()
    if not latest:
        return None
    if is_newer(latest, version.VERSION):
        return (True, latest)
    return (False, latest)


def download_update(url, dest_path, progress_cb=None):
    """
    流式下载新版 exe 到指定路径。
    progress_cb(current, total) 用于显示进度。
    返回 (ok, error_msg)
    """
    try:
        with requests.get(url, stream=True, timeout=30) as r:
            r.raise_for_status()
            total = int(r.headers.get("content-length", 0))
            done = 0
            with open(dest_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=1024 * 256):
                    if chunk:
                        f.write(chunk)
                        done += len(chunk)
                        if progress_cb:
                            progress_cb(done, total)
        return True, ""
    except Exception as e:
        return False, str(e)


def apply_update(new_exe_path):
    """
    用新 exe 替换当前程序并重启。
    由于 Windows 上正在运行的文件不能覆盖, 先写 .update_tmp,
    再通过一个很小的 cmd 脚本延迟替换并重启。
    """
    cur_exe = sys.executable
    if not cur_exe.lower().endswith(".exe") or "VoxelLauncher" not in os.path.basename(cur_exe):
        # 非打包环境(开发模式), 直接提示手动替换
        return False, "开发模式下无法自动替换, 请手动替换 exe"

    exe_dir = os.path.dirname(cur_exe)
    tmp_exe = os.path.join(exe_dir, "VoxelLauncher.update_tmp.exe")
    bat_path = os.path.join(exe_dir, "_update.bat")

    # 把下载的新 exe 复制到临时名
    shutil.copy2(new_exe_path, tmp_exe)

    # 生成更新脚本: 等待当前进程退出 -> 替换 -> 启动新版
    bat = (
        "@echo off\r\n"
        "timeout /t 2 /nobreak >nul\r\n"
        'del /f /q "{}"\r\n'.format(cur_exe.replace("/", "\\")) +
        'move /y "{}" "{}"\r\n'.format(tmp_exe.replace("/", "\\"),
                                        cur_exe.replace("/", "\\")) +
        'start "" "{}"\r\n'.format(cur_exe.replace("/", "\\")) +
        'del /f /q "{}"\r\n'.format(bat_path.replace("/", "\\"))
    )
    with open(bat_path, "w", encoding="gbk") as f:
        f.write(bat)

    # 静默启动更新脚本
    subprocess.Popen(
        ["cmd", "/c", bat_path],
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    return True, ""
