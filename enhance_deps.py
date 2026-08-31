# -*- coding: utf-8 -*-
"""增强自动下载依赖功能：递归依赖、已安装检查、进度显示"""
import re

filepath = r'C:\Users\bllaa\Doubao\chats\2026-08-28\new-chat\VoxelLauncher\modrinth.py'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# 替换 download_versions_with_deps 方法
old_method = '''def download_versions_with_deps(version_id, game_version, loader, dest_dir,
                                progress_cb=None):
    """
    下载指定版本文件并自动补装 required 依赖。
    返回 [(filename, is_dependency)]
    """
    ver = _get("/version/" + version_id)
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    results = []
    file_data = _pick_file(ver)
    if file_data:
        hashes = file_data.get("hashes", {})
        download_file(file_data["url"], dest_dir / file_data["filename"],
                      expected_sha1=hashes.get("sha1"))
        results.append((file_data["filename"], False))

    # 依赖
    seen = set()
    for dep in ver.get("dependencies", []):
        if dep.get("dependency_type") != "required":
            continue
        pid = dep.get("project_id")
        if not pid or pid in seen:
            continue
        seen.add(pid)
        if progress_cb:
            progress_cb("补装依赖: " + pid, 0, 0)
        try:
            fn = download_latest_to(pid, game_version, loader, dest_dir)
            results.append((fn, True))
        except Exception:
            continue
    return results'''

new_method = '''def download_versions_with_deps(version_id, game_version, loader, dest_dir,
                                progress_cb=None, installed_ids=None):
    """
    下载指定版本文件并自动补装 required 依赖(支持递归)。
    返回 [(filename, is_dependency, project_id)]
    installed_ids: 已安装的 project_id 集合, 用于跳过重复下载
    """
    ver = _get("/version/" + version_id)
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    if installed_ids is None:
        installed_ids = set()
    results = []
    downloaded_ids = set(installed_ids)

    file_data = _pick_file(ver)
    if file_data:
        hashes = file_data.get("hashes", {})
        fname = file_data["filename"]
        # 检查是否已安装
        existing = dest_dir / fname
        if existing.exists():
            if progress_cb:
                progress_cb("已存在: " + fname, 0, 0)
        else:
            if progress_cb:
                progress_cb("下载主模组: " + fname, 0, 0)
            download_file(file_data["url"], existing,
                          expected_sha1=hashes.get("sha1"))
        pid = ver.get("project_id", "")
        results.append((fname, False, pid))
        downloaded_ids.add(pid)

    # 递归下载依赖
    def _resolve_deps(ver_obj, depth=0):
        if depth > 5:  # 防止无限递归
            return
        for dep in ver_obj.get("dependencies", []):
            if dep.get("dependency_type") != "required":
                continue
            pid = dep.get("project_id")
            if not pid or pid in downloaded_ids:
                continue
            downloaded_ids.add(pid)
            try:
                # 获取依赖项目信息, 显示名称
                try:
                    proj = get_project(pid)
                    dep_name = proj.get("title", pid)
                except Exception:
                    dep_name = pid
                if progress_cb:
                    progress_cb("下载依赖" + ("(嵌套" + str(depth) + ")" if depth > 0 else "") + ": " + dep_name, 0, 0)
                # 下载依赖的最新兼容版本
                dep_ver = _get_latest_version(pid, game_version, loader)
                if dep_ver:
                    dep_file = _pick_file(dep_ver)
                    if dep_file:
                        dfname = dep_file["filename"]
                        dexisting = dest_dir / dfname
                        if not dexisting.exists():
                            dhashes = dep_file.get("hashes", {})
                            download_file(dep_file["url"], dexisting,
                                          expected_sha1=dhashes.get("sha1"))
                        results.append((dfname, True, pid))
                        # 递归处理依赖的依赖
                        _resolve_deps(dep_ver, depth + 1)
            except Exception as e:
                if progress_cb:
                    progress_cb("依赖下载失败: " + pid + " (" + str(e) + ")", 0, 0)
                continue

    _resolve_deps(ver)
    return results


def _get_latest_version(project_id, game_version, loader):
    """获取指定项目的最新兼容版本(优先release)"""
    versions = get_versions(project_id, game_version=game_version, loader=loader)
    if not versions:
        versions = get_versions(project_id)
    if not versions:
        return None
    # 优先 release, 然后 beta, 然后 alpha
    for vtype in ("release", "beta", "alpha"):
        for v in versions:
            if v.get("version_type") == vtype:
                return v
    return versions[0]'''

if old_method in content:
    content = content.replace(old_method, new_method, 1)
    print("方法替换成功!")
else:
    print("未找到旧方法，尝试查找...")
    idx = content.find('def download_versions_with_deps')
    print("位置:", idx)
    print(repr(content[idx:idx+200]))

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

import ast
ast.parse(content)
print("语法OK")
