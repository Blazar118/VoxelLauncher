# -*- coding: utf-8 -*-
"""
VoxelLauncher - Modrinth 开放平台模块
- 公开免费 API, 无需申请密钥
- 模组/资源包/数据包/光影/整合包 搜索(按游戏版本/加载器/类型筛选)
- 项目详情 / 版本列表 / 一键下载到实例对应文件夹
- 依赖自动识别与补装
- mrpack 整合包导入(自动安装游戏版本+加载器+全部mod)
- 实例导出为标准 mrpack(通过 sha1 反查 Modrinth 版本)
"""
import json
import time
import zipfile
from pathlib import Path

import requests

from downloader import download_file, sha1_of_file

API = "https://api.modrinth.com/v2"

# 搜索缓存: key -> (timestamp, data)
_search_cache = {}
CACHE_TTL = 300  # 5分钟缓存


def _get(path, params=None, retries=2):
    """带重试的 GET 请求"""
    last_err = None
    for attempt in range(retries):
        try:
            resp = requests.get(API + path, params=params, timeout=20,
                                headers={"User-Agent": "VoxelLauncher/1.0.0"})
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            last_err = e
            if attempt < retries - 1:
                time.sleep(1)
    raise last_err


# ---------------------------------------------------------------
# 搜索
# ---------------------------------------------------------------
def search_projects(query="", game_version=None, loader=None,
                    project_type=None, limit=30, offset=0):
    """
    搜索模组/资源包/数据包/光影/整合包, 返回 hits 列表。
    project_type: mod / resourcepack / datapack / shader / modpack 等。
    带5分钟缓存, 相同条件搜索直接返回缓存结果。
    """
    # 生成缓存 key
    cache_key = json.dumps({
        "q": query, "gv": game_version, "loader": loader,
        "pt": project_type, "limit": limit, "offset": offset
    }, sort_keys=True)

    # 检查缓存
    if cache_key in _search_cache:
        ts, data = _search_cache[cache_key]
        if time.time() - ts < CACHE_TTL:
            return data

    facets = []
    if game_version:
        facets.append(["versions:" + game_version])
    if loader:
        facets.append(["categories:" + loader])
    if project_type:
        facets.append(["project_type:" + project_type])
    params = {"query": query, "limit": limit, "offset": offset}
    if facets:
        params["facets"] = json.dumps(facets)
    data = _get("/search", params=params)
    hits = data.get("hits", [])

    # 存入缓存
    _search_cache[cache_key] = (time.time(), hits)
    # 缓存超过100条就清理旧的
    if len(_search_cache) > 100:
        oldest = min(_search_cache.keys(), key=lambda k: _search_cache[k][0])
        del _search_cache[oldest]

    return hits


def get_project(project_id):
    return _get("/project/" + project_id)


def get_versions(project_id, game_version=None, loader=None):
    params = {}
    if game_version:
        params["game_versions"] = json.dumps([game_version])
    if loader:
        params["loaders"] = json.dumps([loader])
    return _get("/project/{}/version".format(project_id), params=params)


def _pick_file(version_data):
    """从版本数据里挑主文件"""
    files = version_data.get("files", [])
    if not files:
        return None
    for f in files:
        if f.get("primary"):
            return f
    return files[0]


# ---------------------------------------------------------------
# 下载到本地
# ---------------------------------------------------------------
def download_latest_to(project_id, game_version, loader, dest_dir):
    """
    下载某项目最新兼容版本的主文件到 dest_dir。
    返回文件名; 无兼容版本抛 ValueError。
    """
    versions = get_versions(project_id, game_version=game_version,
                            loader=loader)
    if not versions:
        raise ValueError("{} 没有适用于 {}/{} 的版本".format(
            project_id, game_version, loader))
    ver = versions[0]
    file_data = _pick_file(ver)
    if not file_data:
        raise ValueError("版本无可用文件")
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    hashes = file_data.get("hashes", {})
    download_file(file_data["url"], dest_dir / file_data["filename"],
                  expected_sha1=hashes.get("sha1"))
    return file_data["filename"]


def download_specific_to(version_id, dest_dir, task=None):
    """
    下载指定版本 ID 的主文件到 dest_dir。
    task: 可选的 DownloadTask 对象, 传入则用下载管理器记录进度
    返回文件名。
    """
    ver = _get("/version/" + version_id)
    file_data = _pick_file(ver)
    if not file_data:
        raise ValueError("版本无可用文件")
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    hashes = file_data.get("hashes", {})
    dest_path = dest_dir / file_data["filename"]
    if task:
        # 使用下载管理器(支持断点续传)
        import downloader as dl_mod
        task.url = file_data["url"]
        task.dest_path = str(dest_path)
        task.file_name = file_data["filename"]
        task.expected_sha1 = hashes.get("sha1", "")
        dl_mod.download_with_task(task)
    else:
        download_file(file_data["url"], dest_path,
                      expected_sha1=hashes.get("sha1"))
    return file_data["filename"]


def download_versions_with_deps(version_id, game_version, loader, dest_dir,
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
    return versions[0]


# ---------------------------------------------------------------
# mrpack 整合包导入
# ---------------------------------------------------------------
def import_mrpack(mrpack_path, instance_name, progress_cb=None):
    """
    导入 Modrinth 整合包(.mrpack = zip)。
    - 读取 modrinth.index.json
    - 安装所需游戏版本与加载器
    - 下载全部文件(含 overrides)
    返回创建的实例名。
    """
    import instance as instance_mod
    import installer
    import version_manager

    mrpack_path = Path(mrpack_path)
    if not mrpack_path.exists():
        raise FileNotFoundError("找不到 mrpack 文件: " + str(mrpack_path))

    with zipfile.ZipFile(mrpack_path) as zf:
        index = json.loads(zf.read("modrinth.index.json").decode("utf-8"))

    game_version = index.get("dependencies", {}).get("minecraft")
    if not game_version:
        raise ValueError("mrpack 未声明 minecraft 版本")
    loader_dep = index.get("dependencies", {})
    loader_type = None
    if loader_dep.get("fabric-loader"):
        loader_type = "fabric"
    elif loader_dep.get("quilt-loader"):
        loader_type = "quilt"
    elif loader_dep.get("forge"):
        loader_type = "forge"

    if progress_cb:
        progress_cb("安装游戏版本 " + game_version, 0, 0)
    try:
        # 确保原版已下载
        version_manager.download_version(game_version, progress_cb=progress_cb)
    except Exception as exc:
        raise RuntimeError("游戏版本下载失败: {}".format(exc))

    # 加载器
    if loader_type:
        if progress_cb:
            progress_cb("安装加载器 " + loader_type, 0, 0)
        loader_version_id = installer.install_loader(
            game_version, loader_type)
    else:
        loader_version_id = game_version

    # 创建实例
    if not instance_name:
        base = index.get("name", "pack")
        instance_name = base + "-" + game_version
    inst = instance_mod.create_instance(instance_name, loader_version_id)
    game_dir = instance_mod.instance_dir(instance_name)

    # 下载文件
    files = index.get("files", [])
    if progress_cb:
        progress_cb("下载整合包文件 0/{}".format(len(files)), 0, len(files))
    for i, f in enumerate(files, 1):
        path = f.get("path", "")
        hashes = f.get("hashes", {})
        urls = f.get("downloads", [])
        if not urls:
            continue
        dest = game_dir / path
        if progress_cb:
            progress_cb("下载 {}/{}".format(i, len(files)), i, len(files))
        try:
            download_file(urls[0], dest, expected_sha1=hashes.get("sha1"))
        except Exception as exc:
            if progress_cb:
                progress_cb("文件失败(继续): {} - {}".format(path, exc), i,
                            len(files))

    # overrides(覆盖配置/材质等)
    with zipfile.ZipFile(mrpack_path) as zf:
        for name in zf.namelist():
            if name.startswith("overrides/"):
                rel = name[len("overrides/"):]
                if not rel:
                    continue
                dest = game_dir / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(zf.read(name))

    if progress_cb:
        progress_cb("整合包导入完成: " + instance_name, 0, 0)
    return instance_name


# ---------------------------------------------------------------
# sha1 反查与实例导出(mrpack)
# ---------------------------------------------------------------
def get_version_by_hash(sha1):
    """
    通过文件 sha1 反查 Modrinth 版本信息(/version_file)。
    命中返回 version 对象, 未命中/出错返回 None。
    """
    if not sha1:
        return None
    try:
        return _get("/version_file",
                    params={"hash": sha1.lower(), "algorithm": "sha1"})
    except Exception:
        return None


def _pick_file_data(version_data):
    """从 version 对象里挑主文件(files 列表)"""
    files = version_data.get("files") or []
    if not files:
        return None
    for f in files:
        if f.get("primary"):
            return f
    return files[0]


def export_instance_mrpack(instance_name, out_path, progress_cb=None):
    """
    把实例导出为标准 .mrpack 整合包:
    - 遍历 mods 目录, 对每个 jar 用 sha1 反查 Modrinth:
      命中 -> 写入 index.files(带 downloads/hashes, 导入时在线下载);
      未命中 -> 打包进 overrides/mods/ (导入时直接解压还原)
    - 资源包/数据包/光影/配置等目录一并打包进 overrides 对应位置
    返回 True。
    """
    import instance as instance_mod
    import installer
    import version_manager

    game_dir = instance_mod.instance_dir(instance_name)
    inst = instance_mod.get_instance(instance_name)
    version_id = inst["version_id"]

    # 推断基础游戏版本与加载器
    try:
        resolved = version_manager.resolve_version_json(version_id)
        mc_version = (resolved.get("inheritsFrom")
                      or resolved.get("id")
                      or version_id).split("-")[-1]
    except Exception:
        mc_version = version_id.split("-")[-1]
    loader = installer.detect_loader_from_id(version_id)

    dependencies = {"minecraft": mc_version}
    if loader in ("fabric", "quilt", "forge"):
        key = loader + "-loader" if loader in ("fabric", "quilt") else loader
        dependencies[key] = "*"

    files = []            # index.files: 在线引用
    overrides = []        # [(overrides 内相对路径, 源绝对路径)]

    # --- mods: 优先在线引用, 反查失败进 overrides/mods ---
    mods_dir = game_dir / "mods"
    if mods_dir.exists():
        jars = sorted(p for p in mods_dir.iterdir()
                      if p.suffix.lower() == ".jar")
        for i, j in enumerate(jars, 1):
            if progress_cb:
                progress_cb("处理 mod {}/{}: {}".format(i, len(jars),
                                                        j.name), i, len(jars))
            try:
                sha1 = sha1_of_file(j)
                ver = get_version_by_hash(sha1)
                vf = _pick_file_data(ver) if ver else None
                if vf and vf.get("url"):
                    files.append({
                        "path": "mods/" + j.name,
                        "hashes": {
                            "sha1": sha1,
                            "sha512": (vf.get("hashes") or {}).get("sha512"),
                        },
                        "env": {"client": "required", "server": "required"},
                        "downloads": [vf["url"]],
                    })
                    continue
            except Exception:
                pass
            # 反查失败 -> 直接打包进 overrides/mods
            overrides.append(("mods/" + j.name, str(j)))

    # --- 资源包 / 数据包 / 光影 / 配置 -> overrides ---
    for folder in ("resourcepacks", "datapacks", "shaderpacks"):
        d = game_dir / folder
        if d.exists():
            for p in sorted(d.iterdir()):
                if p.is_file():
                    overrides.append((folder + "/" + p.name, str(p)))
    # 根目录常用配置文件
    for name in ("options.txt", "servers.dat"):
        p = game_dir / name
        if p.exists() and p.is_file():
            overrides.append((name, str(p)))

    # 写入 mrpack(zip)
    index = {
        "formatVersion": 1,
        "game": "minecraft",
        "versionId": mc_version,
        "name": instance_name,
        "summary": "Exported by VoxelLauncher",
        "files": files,
        "dependencies": dependencies,
    }
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("modrinth.index.json",
                    json.dumps(index, ensure_ascii=False, indent=2))
        for rel, src in overrides:
            zf.write(src, "overrides/" + rel)
    return True


# ---------------------------------------------------------------
# CurseForge 由独立模块 curseforge.py 提供
# ---------------------------------------------------------------
# CurseForge 需要申请开发者 API 密钥, 完整实现见 curseforge.py。
