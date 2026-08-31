# -*- coding: utf-8 -*-
"""
VoxelLauncher - 模组加载器一键安装模块
- Fabric  : 通过 meta.fabricmc.net 获取 profile json, 无需运行安装器
- Quilt   : 通过 meta.quiltmc.org 获取 profile json
- Forge   : 下载官方 installer jar 并用 Java 静默安装到目标目录
- 安装 Fabric 时自动一并安装 Fabric API(Modrinth)
- 安装 Quilt  时自动一并安装 Quilt API(Modrinth)
- 加载器与游戏版本兼容性自动匹配, 不兼容时抛异常提示
"""
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import requests

from config import CONFIG
from downloader import download_file
import java_manager
import version_manager

# ---------------------------------------------------------------
# 通用工具
# ---------------------------------------------------------------
def _get(url, timeout=30):
    resp = requests.get(url, timeout=timeout)
    resp.raise_for_status()
    return resp.json()


def _installed_version_dir(version_id):
    return Path(CONFIG.get("game_dir")) / "versions" / version_id


def _write_version_json(version_id, data):
    d = _installed_version_dir(version_id)
    d.mkdir(parents=True, exist_ok=True)
    (d / (version_id + ".json")).write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _download_version_libs(version_data, progress_cb=None):
    """
    按 version.json 下载 jar 与 libraries。
    - 继承版本(inheritsFrom): 先确保原版完整, 再只下子版本自己的库
    - 完整版本(Forge): 下载 jar + 全部库
    """
    from downloader import DownloadPool
    version_id = version_data.get("id", "unknown")
    base = version_data.get("inheritsFrom")
    if base:
        # 继承模式: 先保证原版完整下载
        if progress_cb:
            progress_cb("下载基础版本: " + base, 0, 0)
        version_manager.download_version(base, progress_cb=progress_cb)
    else:
        vdir = _installed_version_dir(version_id)
        vdir.mkdir(parents=True, exist_ok=True)
        dl = version_data.get("downloads", {})
        client = dl.get("client") or {}
        if client:
            if progress_cb:
                progress_cb("下载游戏jar(加载器整合)", 0, 0)
            download_file(client.get("url", ""),
                          vdir / (version_id + ".jar"),
                          expected_sha1=client.get("sha1"))

    cp_artifacts, native_artifacts = version_manager.collect_launch_libraries(
        version_data)
    lib_base = Path(CONFIG.get("game_dir")) / "libraries"
    total = len(cp_artifacts) + len(native_artifacts)
    done = [0]
    pool = DownloadPool(max_workers=8)

    def _dl(url, dest, sha1):
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
        _dl(url, lib_base / art["path"], art.get("sha1"))
    for ca in native_artifacts:
        url = ca.get("url") or "https://libraries.minecraft.net/" + ca["path"]
        _dl(url, lib_base / ca["path"], ca.get("sha1"))
    pool.wait()
    if pool.failed:
        raise RuntimeError("加载器依赖库下载失败: " + str(pool.failed[:5]))
    if progress_cb:
        progress_cb("加载器依赖库下载完成", total, total)


def _install_api_mod(api_slug, game_version, loader, mods_dir, api_version=None, progress_cb=None):
    """
    从 Modrinth 下载某 API mod 到 mods 目录。
    api_version: 指定版本号(如 "0.92.1"), None 则下载最新兼容版。
    返回安装的文件名, 无兼容版本返回 None。
    """
    from modrinth import download_latest_to, download_specific_to, get_versions
    if progress_cb:
        progress_cb("正在安装 API: " + api_slug, 0, 0)
    try:
        if api_version:
            # 找指定版本号对应的 version_id
            versions = get_versions(api_slug, game_version=game_version, loader=loader)
            target = None
            for v in versions:
                if v.get("version_number") == api_version:
                    target = v
                    break
            if not target:
                if progress_cb:
                    progress_cb("未找到 API 版本 {}, 改用最新版".format(api_version), 0, 0)
                fn = download_latest_to(api_slug, game_version, loader, Path(mods_dir))
            else:
                fn = download_specific_to(target["id"], Path(mods_dir))
        else:
            fn = download_latest_to(api_slug, game_version, loader, Path(mods_dir))
        return fn
    except Exception as exc:
        if progress_cb:
            progress_cb("API 安装失败(可稍后手动装): {}".format(exc), 0, 0)
        return None


def api_version_list(api_slug, game_version, loader):
    """获取某 API 的可用版本列表(用于 UI 下拉框)"""
    from modrinth import get_versions
    try:
        versions = get_versions(api_slug, game_version=game_version, loader=loader)
        return [v.get("version_number", "") for v in versions if v.get("version_number")]
    except Exception:
        return []


# ---------------------------------------------------------------
# Fabric
# ---------------------------------------------------------------
def fabric_loader_versions(game_version):
    """获取 Fabric 加载器可用版本列表(稳定版优先)"""
    loaders = _get("https://meta.fabricmc.net/v2/versions/loader/{}".format(
        game_version))
    if not loaders:
        return []
    stable = [item["loader"]["version"] for item in loaders
              if item.get("loader", {}).get("stable")]
    all_ver = [item["loader"]["version"] for item in loaders]
    return stable if stable else all_ver


def latest_fabric_loader(game_version):
    """返回 (loader版本, installer版本)。Fabric 的 loader 列表不含
    installer, 需从独立的 installer 接口获取。"""
    versions = fabric_loader_versions(game_version)
    if not versions:
        raise RuntimeError("Fabric 不支持该游戏版本: {}".format(game_version))
    loader_ver = versions[0]
    installers = _get("https://meta.fabricmc.net/v2/versions/installer")
    installer_ver = None
    for item in installers:
        if item.get("stable") is not False:
            installer_ver = item["version"]
            break
    if not installer_ver and installers:
        installer_ver = installers[0]["version"]
    return loader_ver, installer_ver


def install_fabric(game_version, loader_version=None, api_version=None,
                    mods_dir=None, progress_cb=None):
    """安装 Fabric, 生成版本 id: fabric-loader-{loader}-{game}
    loader_version: 指定加载器版本, None 用最新
    api_version: 指定 Fabric API 版本, None 用最新
    """
    _, installer = latest_fabric_loader(game_version)
    if loader_version:
        loader = loader_version
    else:
        loader = fabric_loader_versions(game_version)[0]
    if progress_cb:
        progress_cb("Fabric 加载器: {}, 安装器: {}".format(loader, installer), 0, 0)
    profile = _get(
        "https://meta.fabricmc.net/v2/versions/loader/{}/{}/profile/json".format(
            game_version, loader))
    version_id = profile["id"]
    _write_version_json(version_id, profile)
    _download_version_libs(profile, progress_cb=progress_cb)
    if mods_dir:
        _install_api_mod("fabric-api", game_version, "fabric", mods_dir,
                         api_version=api_version, progress_cb=progress_cb)
    return version_id


def install_fabric_merged(game_version, loader_version=None, api_version=None,
                          progress_cb=None):
    """
    PCL2 风格合并模式安装 Fabric。
    版本文件夹名: {game_version}-Fabric {loader_version}
    文件夹内同时包含版本 jar/json 和游戏运行时目录(mods/saves/config)。
    """
    if loader_version:
        loader = loader_version
    else:
        loader = fabric_loader_versions(game_version)[0]
    if progress_cb:
        progress_cb("Fabric 加载器: {} (合并模式)".format(loader), 0, 0)

    # 获取 Fabric profile
    profile = _get(
        "https://meta.fabricmc.net/v2/versions/loader/{}/{}/profile/json".format(
            game_version, loader))

    # PCL2 风格版本 id: 1.21.1-Fabric 0.19.3
    merged_id = "{}-Fabric {}".format(game_version, loader)
    profile["id"] = merged_id

    # 确保原版已下载
    version_manager.download_version(game_version, progress_cb=progress_cb)

    # 创建合并版本文件夹
    merged_dir = _installed_version_dir(merged_id)
    merged_dir.mkdir(parents=True, exist_ok=True)

    # 复制原版 jar 并重命名
    original_jar = _installed_version_dir(game_version) / (game_version + ".jar")
    merged_jar = merged_dir / (merged_id + ".jar")
    if original_jar.exists():
        shutil.copy2(original_jar, merged_jar)
        if progress_cb:
            progress_cb("已复制游戏 jar 到合并目录", 0, 0)

    # 写入合并后的 version.json
    (merged_dir / (merged_id + ".json")).write_text(
        json.dumps(profile, ensure_ascii=False, indent=2), encoding="utf-8")

    # 下载 Fabric 库
    _download_version_libs(profile, progress_cb=progress_cb)

    # 在合并目录里创建游戏运行时子目录(PCL2 风格)
    for sub in ["mods", "saves", "resourcepacks", "shaderpacks", "config",
                "logs", "crash-reports"]:
        (merged_dir / sub).mkdir(parents=True, exist_ok=True)

    # 自动安装 Fabric API 到合并目录的 mods 文件夹
    _install_api_mod("fabric-api", game_version, "fabric",
                     str(merged_dir / "mods"), api_version=api_version,
                     progress_cb=progress_cb)

    if progress_cb:
        progress_cb("Fabric 合并模式安装完成: {}".format(merged_id), 0, 0)
    return merged_id


# ---------------------------------------------------------------
# Quilt
# ---------------------------------------------------------------
def quilt_loader_versions(game_version):
    """获取 Quilt 加载器可用版本列表"""
    loaders = _get("https://meta.quiltmc.org/v3/versions/loader/{}".format(
        game_version))
    if not loaders:
        return []
    stable = [item["loader"]["version"] for item in loaders
              if item.get("loader", {}).get("stable")]
    all_ver = [item["loader"]["version"] for item in loaders]
    return stable if stable else all_ver


def latest_quilt_loader(game_version):
    """返回 (loader版本, installer版本), installer 需单独接口获取"""
    versions = quilt_loader_versions(game_version)
    if not versions:
        raise RuntimeError("Quilt 不支持该游戏版本: {}".format(game_version))
    loader_ver = versions[0]
    installers = _get("https://meta.quiltmc.org/v3/versions/installer")
    installer_ver = None
    for item in installers:
        if item.get("stable") is not False:
            installer_ver = item["version"]
            break
    if not installer_ver and installers:
        installer_ver = installers[0]["version"]
    return loader_ver, installer_ver


def install_quilt(game_version, loader_version=None, api_version=None,
                  mods_dir=None, progress_cb=None):
    """安装 Quilt
    loader_version: 指定加载器版本, None 用最新
    api_version: 指定 Quilt API(QSL)版本, None 用最新
    """
    _, installer = latest_quilt_loader(game_version)
    if loader_version:
        loader = loader_version
    else:
        loader = quilt_loader_versions(game_version)[0]
    if progress_cb:
        progress_cb("Quilt 加载器: {}, 安装器: {}".format(loader, installer), 0, 0)
    profile = _get(
        "https://meta.quiltmc.org/v3/versions/loader/{}/{}/profile/json".format(
            game_version, loader))
    version_id = profile["id"]
    _write_version_json(version_id, profile)
    _download_version_libs(profile, progress_cb=progress_cb)
    if mods_dir:
        _install_api_mod("qsl", game_version, "quilt", mods_dir,
                         api_version=api_version, progress_cb=progress_cb)
    return version_id


# ---------------------------------------------------------------
# Forge
# ---------------------------------------------------------------
def forge_promos():
    """获取 Forge 推荐/最新版本(失败时返回空, 由 maven-metadata 兜底)"""
    try:
        data = _get(
            "https://files.minecraftforge.net/net/minecraftforge/forge/index_promos_slim.json")
        return data.get("promos", {})
    except Exception:
        return {}

def forge_versions(game_version):
    """获取 Forge 某游戏版本的全部可用版本列表"""
    promos = forge_promos()
    # promos 只有 recommended 和 latest, 完整列表需要从 maven-metadata
    import re
    try:
        resp = requests.get(
            "https://maven.minecraftforge.net/net/minecraftforge/forge/maven-metadata.xml",
            timeout=20)
        versions = re.findall(r"<version>([^<]+)</version>", resp.text)
        prefix = game_version + "-"
        matched = [v.replace(prefix, "") for v in versions if v.startswith(prefix)]
        if matched:
            return matched
    except Exception:
        pass
    # 回退: 只用 promos 里的
    result = []
    rec = promos.get(game_version + "-recommended")
    latest = promos.get(game_version + "-latest")
    if rec:
        result.append(rec)
    if latest and latest != rec:
        result.append(latest)
    return result


def forge_version_for(game_version):
    """返回 (forge_version, 是否recommended)"""
    versions = forge_versions(game_version)
    if not versions:
        raise RuntimeError(
            "Forge 不支持该游戏版本: {} (请确认版本号正确)".format(game_version))
    return versions[0], True


def _prepare_forge_target(game_version, target):
    """Forge 1.17+(含 47.x)安装器 --installClient 要求目标目录已有 Minecraft 安装:
    需要在 target/versions/<mc> 放置 vanilla 的 json 与 jar, 并存在 launcher_profiles.json。
    否则会报 "There is no Minecraft launcher profile ... you need to run the launcher first!"。
    """
    vdir = target / "versions" / game_version
    vdir.mkdir(parents=True, exist_ok=True)
    vjson = vdir / (game_version + ".json")
    vjar = vdir / (game_version + ".jar")
    # 优先复用本地已下载的原版版本
    local_v = _installed_version_dir(game_version)
    if (local_v / (game_version + ".json")).exists():
        shutil.copy2(local_v / (game_version + ".json"), vjson)
        if (local_v / (game_version + ".jar")).exists():
            shutil.copy2(local_v / (game_version + ".jar"), vjar)
    else:
        # 从 Mojang 版本清单下载 vanilla json + jar
        manifest = requests.get(
            "https://piston-meta.mojang.com/mc/game/version_manifest_v2.json",
            timeout=30).json()
        url = None
        for ent in manifest.get("versions", []):
            if ent.get("id") == game_version:
                url = ent.get("url")
                break
        if not url:
            raise RuntimeError("未找到 Minecraft {} 的版本信息".format(game_version))
        vdata = requests.get(url, timeout=30).json()
        vjson.write_text(json.dumps(vdata, ensure_ascii=False, indent=2),
                         encoding="utf-8")
        client = (vdata.get("downloads") or {}).get("client") or {}
        if client and client.get("url"):
            download_file(client["url"], vjar,
                          expected_sha1=client.get("sha1"))
    # launcher profile 标记(Forge 安装器检查)
    prof = target / "launcher_profiles.json"
    if not prof.exists():
        prof.write_text('{"profiles":{}}', encoding="utf-8")
    # libraries/assets 目录
    (target / "libraries").mkdir(parents=True, exist_ok=True)
    (target / "assets").mkdir(parents=True, exist_ok=True)
    # 同步 vanilla 到正式版本目录(Forge 版本 inheritsFrom 需要原版存在)
    dst_v = _installed_version_dir(game_version)
    if not (dst_v / (game_version + ".jar")).exists():
        dst_v.mkdir(parents=True, exist_ok=True)
        if vjar.exists():
            shutil.copy2(vjar, dst_v / (game_version + ".jar"))
        if vjson.exists():
            shutil.copy2(vjson, dst_v / (game_version + ".json"))

def install_forge(game_version, forge_version=None, mods_dir=None,
                 progress_cb=None):
    """
    安装 Forge: 下载官方 installer.jar 并用 Java 静默安装到游戏目录。
    forge_version: 指定 Forge 版本号(如 "47.2.0"), None 用最新
    """
    if forge_version:
        forge_ver = forge_version
        is_rec = False
    else:
        forge_ver, is_rec = forge_version_for(game_version)
    if progress_cb:
        progress_cb("Forge 版本: {}-{} (recommended={})".format(
            game_version, forge_ver, is_rec), 0, 0)

    installer_name = "forge-{}-{}-installer.jar".format(game_version, forge_ver)
    installer_url = ("https://maven.minecraftforge.net/net/minecraftforge/"
                     "forge/{}-{}/{}".format(game_version, forge_ver,
                                             installer_name))

    # 找到适合的 Java
    java = java_manager.find_suitable_java(game_version)
    if not java:
        raise RuntimeError(
            "未找到适合 {} 的 Java(需要 Java {})，请先在 Java 管理中扫描/选择".format(
                game_version, java_manager.recommend_java_major(game_version)))

    tmp = Path(tempfile.mkdtemp(prefix="voxel_forge_"))
    installer_jar = tmp / installer_name
    try:
        if progress_cb:
            progress_cb("下载 Forge 安装器", 0, 0)
        download_file(installer_url, installer_jar)

        target = tmp / "install"
        if progress_cb:
            progress_cb("准备 Minecraft 原版(Forge 需要)", 0, 0)
        _prepare_forge_target(game_version, target)

        if progress_cb:
            progress_cb("运行 Forge 安装器(需要 Java, 请耐心等待)", 0, 0)
        # 静默安装到临时目录(避免污染正式 versions)
        cmd = [java_manager.ensure_console_java(java), "-jar",
               str(installer_jar), "--installClient", str(target)]
        nf = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
        proc = subprocess.run(cmd, capture_output=True, text=True,
                              timeout=900, creationflags=nf)
        out = (proc.stdout or "") + (proc.stderr or "")
        if proc.returncode != 0:
            raise RuntimeError(
                "Forge 安装失败(Java 版本可能不匹配):\n" + out[-1500:])

        # 安装器会在 target/versions 下生成 {game}-forge-{forge} 版本
        src_version = "{}-forge-{}".format(game_version, forge_ver)
        src_vdir = target / "versions" / src_version
        if not src_vdir.exists():
            # 兼容不同命名: 排除 vanilla, 优先取带 forge 标记的目录
            candidates = []
            if (target / "versions").exists():
                candidates = [d for d in (target / "versions").iterdir()
                              if d.is_dir()]
            tagged = [d for d in candidates if "forge" in d.name.lower()]
            if tagged:
                src_vdir = tagged[0]
                src_version = src_vdir.name
            elif candidates:
                src_vdir = candidates[0]
                src_version = src_vdir.name
            else:
                raise RuntimeError("Forge 安装完成但未找到版本目录:\n" + out[-800:])

        # 复制版本目录
        dest_vdir = _installed_version_dir(src_version)
        if dest_vdir.exists():
            shutil.rmtree(dest_vdir)
        shutil.copytree(src_vdir, dest_vdir)

        # 复制 libraries(增量合并)
        src_libs = target / "libraries"
        if src_libs.exists():
            dst_libs = Path(CONFIG.get("game_dir")) / "libraries"
            for p in src_libs.rglob("*"):
                if p.is_file():
                    rel = p.relative_to(src_libs)
                    d = dst_libs / rel
                    d.parent.mkdir(parents=True, exist_ok=True)
                    if not d.exists():
                        shutil.copy2(p, d)
        if progress_cb:
            progress_cb("Forge 安装完成: {}".format(src_version), 0, 0)
        return src_version
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------
# NeoForge (1.20.1+ 的 Forge 分支)
# ---------------------------------------------------------------
def neoforge_versions():
    """从 maven-metadata.xml 获取全部 NeoForge 版本列表"""
    import re
    resp = requests.get(
        "https://maven.neoforged.net/releases/net/neoforged/neoforge/maven-metadata.xml",
        headers={"User-Agent": "VoxelLauncher/1.0"}, timeout=20)
    resp.raise_for_status()
    return re.findall(r"<version>([^<]+)</version>", resp.text)


def neoforge_versions_for(game_version):
    """根据游戏版本获取对应 NeoForge 可用版本列表。
    NeoForge 从 1.20.1 开始支持:
      - 1.20.1: NeoForge 使用 Forge 47.x 版本号, 与 Forge 共用加载器(返回 Forge 版本列表)
      - 1.20.2+: 独立版本号(20.x 等), 从 NeoForge maven 获取
    """
    parts = game_version.split(".")
    if len(parts) < 3:
        return []
    major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])
    # NeoForge 1.20.1 = Forge 47.x, 直接复用 Forge 版本列表
    if major == 1 and minor == 20 and patch == 1:
        return forge_versions(game_version)
    # 1.20.0 及以下 NeoForge 不支持
    if major == 1 and minor == 20 and patch == 0:
        return []
    # 独立 NeoForge 版本, 前缀 = {minor}.{patch}(如 1.20.2 -> 20.2, 1.21.1 -> 21.1)
    prefix = "{}.{}".format(minor, patch)

    versions = neoforge_versions()
    matched = [v for v in versions if v.startswith(prefix + ".") and "beta" not in v.lower()]
    if not matched:
        matched = [v for v in versions if v.startswith(prefix + ".")]
    return matched

def neoforge_version_for(game_version):
    """根据游戏版本找到对应 NeoForge 最新版本。"""
    versions = neoforge_versions_for(game_version)
    if not versions:
        raise RuntimeError("NeoForge 不支持该游戏版本: {}".format(game_version))
    return versions[-1]


def install_neoforge(game_version, nf_version=None, mods_dir=None,
                     progress_cb=None):
    """安装 NeoForge: 下载 installer jar 并用 Java 静默安装。
    NeoForge 从 1.20.1 开始支持; 1.20.1 使用 Forge 47.x 加载器(直接走 Forge 安装)。
    nf_version: 指定 NeoForge 版本号, None 用最新
    """
    # NeoForge 1.20.1 = Forge 47.x, 转用 Forge 安装器
    try:
        parts = game_version.split(".")
        if len(parts) >= 3 and int(parts[0]) == 1 and int(parts[1]) == 20 and int(parts[2]) == 1:
            if progress_cb:
                progress_cb("NeoForge 1.20.1 即 Forge 47.x, 使用 Forge 加载器安装", 0, 0)
            return install_forge(game_version, forge_version=nf_version,
                                 mods_dir=mods_dir, progress_cb=progress_cb)
    except Exception:
        pass
    if nf_version:
        nf_ver = nf_version
    else:
        nf_ver = neoforge_version_for(game_version)
    if progress_cb:
        progress_cb("NeoForge 版本: {} (游戏 {})".format(nf_ver, game_version), 0, 0)

    installer_name = "neoforge-{}-installer.jar".format(nf_ver)
    installer_url = ("https://maven.neoforged.net/releases/net/neoforged/"
                     "neoforge/{}/{}".format(nf_ver, installer_name))

    java = java_manager.find_suitable_java(game_version)
    if not java:
        raise RuntimeError(
            "未找到适合 {} 的 Java(需要 Java {})，请先在 Java 管理中扫描/选择".format(
                game_version, java_manager.recommend_java_major(game_version)))

    tmp = Path(tempfile.mkdtemp(prefix="voxel_neoforge_"))
    installer_jar = tmp / installer_name
    try:
        if progress_cb:
            progress_cb("下载 NeoForge 安装器", 0, 0)
        download_file(installer_url, installer_jar)

        if progress_cb:
            progress_cb("运行 NeoForge 安装器(需要 Java, 请耐心等待)", 0, 0)
        target = tmp / "install"
        cmd = [java_manager.ensure_console_java(java), "-jar",
               str(installer_jar), "--installClient", str(target)]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        out = (proc.stdout or "") + (proc.stderr or "")
        if proc.returncode != 0:
            raise RuntimeError("NeoForge 安装失败(Java 版本可能不匹配):\n" + out[-1500:])

        # NeoForge 安装后版本目录名: {game_version}-{nf_ver} 或类似
        src_vdir = None
        src_version = None
        versions_dir = target / "versions"
        if versions_dir.exists():
            for d in versions_dir.iterdir():
                if d.is_dir() and "neoforge" in d.name.lower():
                    src_vdir = d
                    src_version = d.name
                    break
        if not src_vdir and versions_dir.exists():
            candidates = list(versions_dir.iterdir())
            if candidates:
                src_vdir = candidates[0]
                src_version = src_vdir.name
        if not src_vdir:
            raise RuntimeError("NeoForge 安装完成但未找到版本目录:\n" + out[-800:])

        dest_vdir = _installed_version_dir(src_version)
        if dest_vdir.exists():
            shutil.rmtree(dest_vdir)
        shutil.copytree(src_vdir, dest_vdir)

        # 复制 libraries
        src_libs = target / "libraries"
        if src_libs.exists():
            dst_libs = Path(CONFIG.get("game_dir")) / "libraries"
            for p in src_libs.rglob("*"):
                if p.is_file():
                    rel = p.relative_to(src_libs)
                    d = dst_libs / rel
                    d.parent.mkdir(parents=True, exist_ok=True)
                    if not d.exists():
                        shutil.copy2(p, d)
        if progress_cb:
            progress_cb("NeoForge 安装完成: {}".format(src_version), 0, 0)
        return src_version
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------
# 对外统一入口
# ---------------------------------------------------------------
def install_loader(game_version, loader_type, loader_version=None,
                   api_version=None, mods_dir=None, progress_cb=None):
    """
    统一安装入口。
    loader_type: "fabric" / "quilt" / "forge" / "neoforge"
    loader_version: 指定加载器版本, None 用最新
    api_version: 指定 API 版本(仅 fabric/quilt 有效), None 用最新
    返回新版本 id。
    """
    loader_type = loader_type.lower()
    if loader_type == "fabric":
        return install_fabric(game_version, loader_version=loader_version,
                              api_version=api_version, mods_dir=mods_dir,
                              progress_cb=progress_cb)
    if loader_type == "quilt":
        return install_quilt(game_version, loader_version=loader_version,
                             api_version=api_version, mods_dir=mods_dir,
                             progress_cb=progress_cb)
    if loader_type == "forge":
        return install_forge(game_version, forge_version=loader_version,
                             mods_dir=mods_dir, progress_cb=progress_cb)
    if loader_type == "neoforge":
        return install_neoforge(game_version, nf_version=loader_version,
                                mods_dir=mods_dir, progress_cb=progress_cb)
    raise ValueError("未知加载器类型: " + loader_type)


def detect_loader_from_id(version_id):
    """根据版本 id 猜测是否带加载器(用于 UI 展示与下载版本匹配)"""
    vid = version_id.lower()
    if "neoforge" in vid:
        return "neoforge"
    if "forge" in vid:
        return "forge"
    if "fabric" in vid:
        return "fabric"
    if "quilt" in vid:
        return "quilt"
    return "vanilla"
