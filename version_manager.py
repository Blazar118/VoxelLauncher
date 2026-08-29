# -*- coding: utf-8 -*-
"""
VoxelLauncher - 游戏版本管理模块
- 拉取官方 version_manifest_v2.json, 获取全部正式版/快照/旧版列表
- 下载指定版本的 version.json、游戏 jar、全部 libraries、assets 资源
- 解析 version.json 供启动器使用(规则判定/类路径/本地库文件)
"""
import json
import re
import threading
import time
from pathlib import Path

import requests

from config import CONFIG
from downloader import DownloadPool, download_file, rewrite_url, sha1_of_file
from downloader import _force_mirror_url

# 版本清单地址(官方 + BMCLAPI 镜像)
MANIFEST_URLS = {
    "mojang": "https://launchermeta.mojang.com/mc/game/version_manifest_v2.json",
    "bmclapi": "https://bmclapi2.bangbang93.com/mc/game/version_manifest_v2.json",
}

OS_NAME = "windows"          # 本启动器优先面向 Windows
OS_ARCH = "x86"              # 规则里 arch=="x86" 表示 32 位; 64 位时该字段不匹配


# ---------------------------------------------------------------
# 规则判定(library / arguments 里的 os rules)
# ---------------------------------------------------------------
def _rule_matches(rule):
    """判断一条规则是否匹配当前平台"""
    if "os" not in rule:
        return True
    os_cfg = rule["os"]
    if os_cfg.get("name") and os_cfg["name"] != OS_NAME:
        return False
    # arch 字段: "x86" 表示 32 位, 我们运行在 64 位则不应匹配
    if os_cfg.get("arch") and os_cfg["arch"] != OS_ARCH:
        return False
    return True


def rules_allow(rules):
    """按 Minecraft 规则语义计算 allow/disallow 列表"""
    if not rules:
        return True
    result = False
    for rule in rules:
        if rule.get("action") == "allow":
            if _rule_matches(rule):
                result = True
        elif rule.get("action") == "disallow":
            if _rule_matches(rule):
                return False
    return result


# ---------------------------------------------------------------
# manifest
# ---------------------------------------------------------------
def fetch_manifest():
    """
    拉取版本清单, 带重试 + 官方/镜像自动互备:
    - 按下载源配置优先请求, 失败自动切换另一源(镜像)重试
    - 每源最多尝试 2 次, 共最多 4 次; 解决国内访问官方源
      (launchermeta.mojang.com) 被重置(ConnectionResetError)的问题
    返回 [{id, type, url, releaseTime}, ...] 按时间倒序。
    """
    preferred = CONFIG.get("download_source", "mojang")
    other = "bmclapi" if preferred == "mojang" else "mojang"
    order = [preferred, other, preferred, other]  # 交替互备
    last_err = None
    for src in order:
        url = MANIFEST_URLS[src]
        try:
            resp = requests.get(url, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            return data.get("versions", [])
        except Exception as exc:
            last_err = exc
    raise ConnectionError(
        "版本清单获取失败(官方与镜像均不可用): {}".format(last_err))


def get_version_json_url(version_id):
    """从 manifest 中找到某版本的 json 下载地址(镜像时用镜像端点)"""
    source = CONFIG.get("download_source", "mojang")
    if source == "bmclapi":
        return "https://bmclapi2.bangbang93.com/version/{}/json".format(version_id)
    for v in fetch_manifest():
        if v["id"] == version_id:
            return v["url"]
    return None


def get_base_game_version(version_id, game_dir=None):
    """
    沿本地版本 json 的继承链(inheritsFrom)找到最底层的基础 MC 版本号。
    只读本地文件, 不触发网络。例如:
      fabric-loader-0.19.3-1.21.1 -> 1.21.1
      forge-47.1.0(继承1.20.1)    -> 1.20.1
      1.20.1(原版)                -> 1.20.1
    """
    game_dir = game_dir or CONFIG.get("game_dir")
    vjson_path = get_version_dir(game_dir, version_id) / (version_id + ".json")
    if not vjson_path.exists():
        # 本地无描述文件: 从 id 尾部尽量推断(如 xxx-1.20.1)
        return version_id.split("-")[-1] if "-" in version_id else version_id
    try:
        data = json.loads(vjson_path.read_text(encoding="utf-8"))
    except Exception:
        return version_id.split("-")[-1] if "-" in version_id else version_id
    parent = data.get("inheritsFrom")
    if parent:
        return get_base_game_version(parent, game_dir)
    return data.get("id") or version_id


def fetch_version_json(version_id):
    """
    下载并解析某版本的 version.json。
    官方/镜像自动互备: 先按配置的源请求, 失败(含404)自动切另一个源。
    每源最多重试 2 次, 共最多 4 次。
    """
    # 从 manifest 取官方 URL(远古版本的 url 在 manifest 里)
    official_url = None
    for v in fetch_manifest():
        if v["id"] == version_id:
            official_url = v.get("url")
            break
    if not official_url:
        raise ValueError("未在 manifest 中找到版本: " + version_id)
    mirror_url = _force_mirror_url(official_url)

    # 按配置决定优先顺序
    source = CONFIG.get("download_source", "mojang")
    urls = [mirror_url, official_url] if source == "bmclapi" else [official_url, mirror_url]

    last_err = None
    for url in urls:
        for _ in range(2):
            try:
                resp = requests.get(url, timeout=20)
                resp.raise_for_status()
                return resp.json()
            except Exception as exc:
                last_err = exc
                time.sleep(0.4)
    raise last_err if last_err else ValueError("版本 json 下载失败: " + version_id)


# ---------------------------------------------------------------
# 路径/URL 工具
# ---------------------------------------------------------------
def library_artifact(lib):
    """返回库的主 artifact 字典(downloads.artifact 或按 name 推导)"""
    downloads = lib.get("downloads") or {}
    if downloads.get("artifact"):
        return downloads["artifact"]
    name = lib.get("name", "")
    return {"path": maven_path_from_name(name), "url": maven_url_from_name(name)}


def maven_path_from_name(name):
    """org.lwjgl:lwjgl:3.3.1 -> org/lwjgl/lwjgl/3.3.1/lwjgl-3.3.1.jar"""
    parts = name.split(":")
    group, artifact, version = parts[0], parts[1], parts[2]
    suffix = ""
    if len(parts) > 3:      # 带 classifier 的名称
        suffix = "-" + parts[3]
    base = "{}/{}/{}/{}-{}{}.jar".format(
        group.replace(".", "/"), artifact, version, artifact, version, suffix)
    return base


def maven_url_from_name(name):
    path = maven_path_from_name(name)
    return "https://libraries.minecraft.net/" + path


def library_classifiers(lib):
    """返回该库在当前平台需要下载并解压的 classifier artifact 列表"""
    result = []
    downloads = lib.get("downloads") or {}
    classifiers = downloads.get("classifiers") or {}
    natives_map = lib.get("natives") or {}
    # 旧版: natives 字段指定平台 classifier
    if natives_map:
        key = natives_map.get(OS_NAME)
        if key and key in classifiers:
            result.append(classifiers[key])
    # 新版(1.17+): 直接用 natives-windows 命名的 classifier
    if "natives-" + OS_NAME in classifiers:
        result.append(classifiers["natives-" + OS_NAME])
    return result


def _name_classifier(name):
    """从 maven name 中取 classifier(第4段), 没有返回 None"""
    parts = (name or "").split(":")
    if len(parts) >= 4 and parts[3]:
        return parts[3]
    return None


def _artifact_from_lib(lib):
    """
    从库条目解析出下载 artifact 字典 {path, url, sha1, size}。
    支持两种格式:
    - 新版: downloads.artifact
    - maven 风格(Fabric/Quilt 子库): 只有 name + url + sha1
    解析失败返回 None。
    """
    downloads = lib.get("downloads") or {}
    if downloads.get("artifact"):
        return downloads["artifact"]
    name = lib.get("name", "")
    if not name or ":" not in name:
        return None
    path = maven_path_from_name(name)
    base_url = lib.get("url") or "https://libraries.minecraft.net/"
    return {
        "path": path,
        "url": base_url + path,
        "sha1": lib.get("sha1"),
        "size": lib.get("size"),
    }


def collect_launch_libraries(version_data):
    """
    返回 (classpath artifact 列表, native artifact 列表)。
    每个 artifact 形如 {path, url, sha1, size}, 供下载与启动两处复用。

    新版(1.17+): native 是独立库条目, 名称第4段为 natives-windows / natives-linux
                 等, 其 artifact 即 native jar, 需下载并解压到 natives 目录。
    旧版(1.12-): 库通过 "natives" 映射 / downloads.classifiers 声明 native。
    """
    cp_artifacts = []
    native_artifacts = []
    for lib in version_data.get("libraries", []):
        if not rules_allow(lib.get("rules")):
            continue
        downloads = lib.get("downloads") or {}
        classifier = _name_classifier(lib.get("name", ""))

        # 新版独立 native 库条目
        if classifier and classifier.startswith("natives-"):
            if classifier == "natives-" + OS_NAME:
                artifact = downloads.get("artifact")
                if artifact and artifact.get("path"):
                    native_artifacts.append(artifact)
            continue  # 其它平台 / arm64 / x86 的 native 一律跳过

        # 普通库: 主 artifact 进 classpath
        artifact = _artifact_from_lib(lib)
        if artifact and artifact.get("path"):
            cp_artifacts.append(artifact)

        # 旧版 natives map / classifiers
        for ca in library_classifiers(lib):
            if ca.get("path"):
                native_artifacts.append(ca)
    return cp_artifacts, native_artifacts


# ---------------------------------------------------------------
# 版本完整下载
# ---------------------------------------------------------------
def get_version_dir(game_dir, version_id):
    return Path(game_dir) / "versions" / version_id


# ---------------------------------------------------------------
# 版本继承解析(Fabric / Quilt 的 profile json 通过 inheritsFrom 继承原版)
# ---------------------------------------------------------------
def resolve_version_json(version_id, game_dir=None, _depth=0):
    """
    读取本地 versions/{id}/{id}.json 并解析继承链(inheritsFrom),
    返回合并后的完整 version dict, 供启动与完整性校验使用。
    """
    if _depth > 8:
        raise ValueError("版本继承链过深: " + version_id)
    game_dir = game_dir or CONFIG.get("game_dir")
    vjson_path = get_version_dir(game_dir, version_id) / (version_id + ".json")
    if not vjson_path.exists():
        raise FileNotFoundError("版本描述文件缺失: " + version_id)
    data = json.loads(vjson_path.read_text(encoding="utf-8"))
    parent_id = data.get("inheritsFrom")
    if parent_id:
        parent = resolve_version_json(parent_id, game_dir, _depth + 1)
        return _merge_version(parent, data)
    data["_jar_version"] = version_id
    return data


def _merge_version(parent, child):
    merged = dict(parent)
    merged["id"] = child.get("id", parent.get("id"))
    merged.pop("inheritsFrom", None)
    # jar 归属: 子版本有 downloads 用子版本, 否则继承父版本
    merged["_jar_version"] = (child.get("id")
                              if "downloads" in child
                              else parent.get("_jar_version", parent.get("id")))
    # libraries: 子版本优先, 按 name 去重
    libs, seen = [], set()
    for lib in child.get("libraries", []) + parent.get("libraries", []):
        key = lib.get("name") or json.dumps(lib, sort_keys=True)
        if key in seen:
            continue
        seen.add(key)
        libs.append(lib)
    merged["libraries"] = libs
    # arguments: game/jvm 分层拼接(子在前父在后)。
    # 关键: 加载器子版本(Fabric/Quilt)的 game 常为空、jvm 只有自己的杂项,
    # 而 -cp ${classpath} / -Djava.library.path / --username 等在父版本里,
    # 绝不能整体覆盖, 否则启动命令丢失类路径。
    if "arguments" in child or "arguments" in parent:
        child_args = child.get("arguments") or {}
        parent_args = parent.get("arguments") or {}
        merged_args = {}
        for key in ("game", "jvm"):
            c_list = child_args.get(key)
            p_list = parent_args.get(key)
            c = c_list if isinstance(c_list, list) else []
            p = p_list if isinstance(p_list, list) else []
            merged_args[key] = list(c) + list(p)
        merged["arguments"] = merged_args
    # 其余字段: 子版本有则覆盖(arguments 已单独处理, 不再整体覆盖)
    for key in ("downloads", "assetIndex", "assets", "mainClass",
                "minecraftArguments", "javaVersion", "logging", "type"):
        if key in child:
            merged[key] = child[key]
    return merged


def download_version(version_id, progress_cb=None, cancel_event=None):
    """
    完整下载一个版本(含 jar/libraries/assets)。
    若该版本继承原版(inheritsFrom), 会先确保原版完整下载。
    progress_cb(phase, current, total) 用于界面刷新。
    """
    game_dir = CONFIG.get("game_dir")
    if cancel_event and cancel_event.is_set():
        return

    # 1. version.json
    version_json = fetch_version_json(version_id)
    vdir = get_version_dir(game_dir, version_id)
    vdir.mkdir(parents=True, exist_ok=True)
    (vdir / (version_id + ".json")).write_text(
        json.dumps(version_json, ensure_ascii=False, indent=2), encoding="utf-8")
    if progress_cb:
        progress_cb("已下载版本描述文件", 0, 0)

    # 1.5 继承版本: 先确保原版完整
    base = version_json.get("inheritsFrom")
    if base:
        if progress_cb:
            progress_cb("需要先安装基础版本: " + base, 0, 0)
        download_version(base, progress_cb=progress_cb,
                         cancel_event=cancel_event)

    # 2. 客户端 jar(仅当本版本自带 jar)
    dl = version_json.get("downloads", {})
    client = dl.get("client") or {}
    if client:
        dest = vdir / (version_id + ".jar")
        if progress_cb:
            progress_cb("下载游戏jar(多线程分块)", 0, 0)
        # 大文件用多线程分块下载, 支持断点续传
        from downloader import fast_download
        fast_download(client.get("url", ""), dest,
                      expected_sha1=client.get("sha1"))

    # 3. libraries(含 native)
    cp_artifacts, native_artifacts = collect_launch_libraries(version_json)
    lib_base = Path(game_dir) / "libraries"
    pool = DownloadPool(max_workers=8)
    total = len(cp_artifacts) + len(native_artifacts)
    done = [0]

    def _cb(url, dest, sha1=None):
        def _one():
            try:
                download_file(url, dest, expected_sha1=sha1)
                done[0] += 1
                if progress_cb:
                    progress_cb("下载依赖库 {}/{}".format(done[0], total),
                                done[0], total)
            except Exception:
                done[0] += 1
        pool.submit(_one)

    for art in cp_artifacts:
        url = art.get("url") or "https://libraries.minecraft.net/" + art["path"]
        _cb(url, lib_base / art["path"], art.get("sha1"))
    for ca in native_artifacts:
        url = ca.get("url") or "https://libraries.minecraft.net/" + ca["path"]
        _cb(url, lib_base / ca["path"], ca.get("sha1"))

    pool.wait()
    if pool.failed:
        raise RuntimeError("部分依赖库下载失败: " + "; ".join(
            "{}: {}".format(p, e) for p, e in pool.failed[:10]))
    if progress_cb:
        progress_cb("依赖库下载完成", total, total)

    # 4. assets(继承版本不重复下, 原版已下)
    if not base:
        download_assets(version_json, progress_cb=progress_cb,
                        cancel_event=cancel_event)


def _name_from_path(rel_path):
    """根据相对路径反推 maven name(用于缺 url 时兜底)"""
    p = rel_path.replace("\\", "/")
    # org/lwjgl/lwjgl/3.3.1/lwjgl-3.3.1.jar -> org.lwjgl:lwjgl:3.3.1
    parts = p.split("/")
    if len(parts) >= 4:
        group = parts[:-3]
        artifact, version = parts[-3], parts[-2]
        return "{}:{}:{}".format(".".join(group), artifact, version)
    return rel_path


def download_assets(version_json, progress_cb=None, cancel_event=None):
    """
    下载 assets 资源索引与所有资源文件。
    - 24 线程并发(资源文件上千个小文件, 高并发才能跑满带宽)
    - 下载前先校验本地已有文件 sha1, 已存在且正确直接跳过(零开销复用)
    - 单个文件失败自动重试 3 次(内部 sha1 校验, 损坏自动重下)
    - 镜像源: URL 经 rewrite_url 重写, 官方源 <-> BMCLAPI
    - 进度按 文件数+字节 高频刷新, 界面不会"看起来卡死"
    """
    game_dir = CONFIG.get("game_dir")
    assets_dir = Path(game_dir) / "assets"
    index = version_json.get("assetIndex") or {}
    index_id = index.get("id") or version_json.get("assets", "legacy")
    if not index:
        return
    idx_file = assets_dir / "indexes" / (index_id + ".json")
    if progress_cb:
        progress_cb("下载资源索引", 0, 0)
    download_file(index.get("url", ""), idx_file,
                  expected_sha1=index.get("sha1"))
    index_data = json.loads(idx_file.read_text(encoding="utf-8"))
    objects = index_data.get("objects", {})

    # 先统计总字节数(用于百分比)与文件数
    total_bytes = sum(obj.get("size", 0) for obj in objects.values())
    total = len(objects)
    if total == 0:
        return

    pool = DownloadPool(max_workers=24)
    lock = threading.Lock()
    done = [0]          # 已处理文件数(成功+跳过+失败)
    done_bytes = [0]    # 已下载(含跳过)字节数
    skipped = [0]       # 哈希已存在跳过的文件数
    failed = [0]        # 下载失败的文件数

    def _report():
        """低频刷新进度: 每 5 个文件 或 每跨 1MB 一次"""
        if not progress_cb:
            return
        if done[0] % 5 == 0 or (done_bytes[0] % (1 << 20)) < (1 << 15):
            pct = (done_bytes[0] / total_bytes * 100) if total_bytes else 0
            progress_cb(
                "下载资源 {}/{}  ({} MB / {} MB, {:.0f}%)".format(
                    done[0], total, done_bytes[0] >> 20, total_bytes >> 20, pct),
                done[0], total)

    def _one(h, size):
        """单资源任务: 哈希校验跳过 -> 下载(3次重试) -> 更新计数"""
        dest = assets_dir / "objects" / h[:2] / h
        try:
            # 1) 下载前先校验本地 sha1, 已存在且正确 -> 跳过
            if dest.exists() and dest.stat().st_size > 0:
                if sha1_of_file(dest) == h:
                    with lock:
                        skipped[0] += 1
                        done[0] += 1
                        done_bytes[0] += size
                        _report()
                    return
                # 哈希不对 -> 删掉重新下载
                dest.unlink(missing_ok=True)
            # 2) 下载 + sha1 校验 + 自动重试 3 次
            url = "https://resources.download.minecraft.net/{}/{}".format(h[:2], h)
            download_file(url, dest, expected_sha1=h, max_retry=3)
            with lock:
                done[0] += 1
                done_bytes[0] += size
                _report()
        except Exception:
            # 单个资源失败不中断整体(游戏仍可启动, 最多缺个别资源)
            with lock:
                failed[0] += 1
                done[0] += 1
                _report()

    for obj in objects.values():
        if cancel_event and cancel_event.is_set():
            break
        pool.submit(_one, obj["hash"], obj.get("size", 0))

    pool.wait()
    if progress_cb:
        pct = (done_bytes[0] / total_bytes * 100) if total_bytes else 0
        progress_cb(
            "资源下载完成  {}/{} ({} MB), 跳过 {} 个, 失败 {} 个, 约 {:.0f}%".format(
                done[0], total, done_bytes[0] >> 20, skipped[0], failed[0], pct),
            done[0], total)


def check_version_files(version_id, version_data=None):
    """
    启动前文件完整性检查。返回缺失/损坏文件描述列表(空列表表示完整)。
    支持继承版本(会自动解析到原版)。
    """
    game_dir = CONFIG.get("game_dir")
    problems = []
    if version_data is None:
        try:
            version_data = resolve_version_json(version_id)
        except Exception as exc:
            return [str(exc)]

    # 游戏 jar(继承版本用原版 jar)
    jar_ver = version_data.get("_jar_version") or version_id
    jar = get_version_dir(game_dir, jar_ver) / (jar_ver + ".jar")
    if not jar.exists():
        problems.append("游戏 jar 缺失: {}".format(jar))

    cp_artifacts, native_artifacts = collect_launch_libraries(version_data)
    lib_base = Path(game_dir) / "libraries"
    for art in cp_artifacts:
        if not (lib_base / art["path"]).exists():
            problems.append("依赖库缺失: {}".format(art["path"]))
    for ca in native_artifacts:
        if not (lib_base / ca["path"]).exists():
            problems.append("Native库缺失: {}".format(ca["path"]))

    idx = version_data.get("assetIndex") or {}
    idx_file = Path(game_dir) / "assets" / "indexes" / (idx.get("id", "") + ".json")
    if idx and not idx_file.exists():
        problems.append("资源索引缺失: {}".format(idx_file))
    return problems
