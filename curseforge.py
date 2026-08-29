# -*- coding: utf-8 -*-
"""
VoxelLauncher - CurseForge V2 API 接入模块
- 模组搜索 / 版本(文件)列表 / 下载链接 / 依赖解析
- CurseForge zip 格式整合包(manifest.json)解析与安装
- 密钥由用户在设置页填写并保存到 config.json, 代码内不内置任何密钥。
- 网络异常(403/429/超时/连接失败)统一抛出 CurseForgeError,
  UI 层据此弹出"CurseForge密钥无效或者网络访问受限"并自动降级。
"""
import json
import zipfile
from pathlib import Path

import requests

from downloader import download_file

# CurseForge V2 API 基础地址
CF_API = "https://api.curseforge.com/v1"
CF_GAME_ID = 432      # Minecraft 的游戏 ID
CF_TIMEOUT = 15       # 单次请求超时(秒)

# Minecraft 资源分类 classId(CurseForge 公开常量, 非密钥;
# 依据社区维护的 classId 表: 6=Mods 12=ResourcePacks 17=Worlds
# 4471=Modpacks 6552=Shaders 6945=DataPacks)
CF_CLASS = {
    "mods": 6,            # 模组
    "resourcepacks": 12,  # 资源包
    "modpacks": 4471,     # 整合包
    "worlds": 17,         # 世界/地图
    "shaders": 6552,      # 光影
    "datapacks": 6945,    # 数据包
}

# 加载器类型(API 数值定义)
CF_LOADER_TYPE = {0: "Any", 1: "Forge", 4: "Fabric", 5: "Quilt",
                  6: "NeoForge"}
# 内部名称 -> API 数值
CF_LOADER_MAP = {"any": 0, "forge": 1, "fabric": 4, "quilt": 5,
                 "neoforge": 6}

# 依赖关系类型: 1=内置库 2=可选依赖 3=必需依赖 4=工具 5=不兼容 6=包含
CF_DEP_REQUIRED = 3


class CurseForgeError(Exception):
    """CurseForge 调用异常(密钥无效/网络受限/服务错误)"""
    pass


# ---------------------------------------------------------------
# 密钥与请求封装
# ---------------------------------------------------------------
def get_api_key():
    """从全局配置读取密钥(用户在设置页填写)"""
    from config import CONFIG
    return (CONFIG.get("cf_api_key") or "").strip()


def has_key():
    """是否已配置非空密钥"""
    return bool(get_api_key())


def _headers():
    """构造带密钥的请求头"""
    return {"x-api-key": get_api_key(), "Accept": "application/json"}


def _request(path, params=None):
    """
    GET 请求统一封装。
    403/401(密钥无效)、429(限流)、超时、连接失败 -> CurseForgeError,
    提示信息统一为"CurseForge密钥无效或者网络访问受限"。
    """
    if not has_key():
        raise CurseForgeError("CurseForge 密钥为空, 请先在设置页填写")
    url = CF_API + path
    try:
        resp = requests.get(url, headers=_headers(), params=params,
                            timeout=CF_TIMEOUT)
    except (requests.exceptions.Timeout,
            requests.exceptions.ConnectionError):
        raise CurseForgeError("CurseForge密钥无效或者网络访问受限")
    if resp.status_code in (401, 403, 429):
        raise CurseForgeError("CurseForge密钥无效或者网络访问受限")
    if resp.status_code != 200:
        raise CurseForgeError("CurseForge 接口异常(HTTP {})".format(
            resp.status_code))
    try:
        return resp.json().get("data")
    except Exception:
        raise CurseForgeError("CurseForge 返回数据无法解析")


# ---------------------------------------------------------------
# 搜索与详情
# ---------------------------------------------------------------
def _norm_mod(m):
    """把 CF 原始 mod 对象转为 UI 友好字段"""
    logo = m.get("logo") or {}
    return {
        "id": m.get("id"),
        "slug": m.get("slug"),
        "name": m.get("name"),
        "summary": m.get("summary", ""),
        "downloads": m.get("downloadCount", 0),
        "logo_url": logo.get("thumbnailUrl"),
    }


def search_mods(query, class_id=CF_CLASS["mods"], game_version=None,
                loader=None, page=1, page_size=20):
    """
    搜索模组/资源/整合包, 返回标准化结果列表。
    class_id: 取 CF_CLASS 里的分类; game_version/loader 可选筛选。
    """
    params = {
        "gameId": CF_GAME_ID,
        "classId": class_id,
        "searchFilter": query,
        "sortField": 6,          # 6 = 总下载量
        "sortOrder": "desc",
        "pageSize": page_size,
        "index": (page - 1) * page_size,
    }
    if game_version:
        params["gameVersion"] = game_version
    if loader:
        params["modLoaderType"] = CF_LOADER_MAP.get(loader, 0)
    data = _request("/mods/search", params)
    return [_norm_mod(m) for m in (data or [])]


def get_mod_files(mod_id, game_version=None, loader=None, page=1):
    """
    获取某项目的文件(版本)列表。
    返回原始 file 对象列表, 每个含 id/displayName/fileName/gameVersions
    /dependencies 等字段。
    """
    params = {"pageSize": 50, "index": (page - 1) * 50}
    if game_version:
        params["gameVersion"] = game_version
    if loader:
        params["modLoaderType"] = CF_LOADER_MAP.get(loader, 0)
    data = _request("/mods/{}/files".format(mod_id), params)
    return data or []


def get_download_url(mod_id, file_id):
    """获取文件真实下载链接, 失败返回 None"""
    data = _request("/mods/{}/files/{}/download-url".format(mod_id, file_id))
    if isinstance(data, dict):
        return data.get("downloadUrl")
    return None


def get_file_deps(mod_id, file_id):
    """
    解析文件的必需依赖(RequiredDependency)。
    返回 [modId, ...](CF 只返回依赖的 modId, 不返回显示名)。
    """
    data = _request("/mods/{}/files/{}".format(mod_id, file_id))
    if not isinstance(data, dict):
        return []
    deps = []
    for d in data.get("dependencies") or []:
        if d.get("relationType") == CF_DEP_REQUIRED and d.get("modId"):
            deps.append(d["modId"])
    return deps


# ---------------------------------------------------------------
# 下载
# ---------------------------------------------------------------
def download_mod_file(mod_id, file_id, dest_dir):
    """
    下载指定文件到 dest_dir, 返回文件名。
    先取真实下载链接, 再复用 downloader(断点续传/重试/镜像判断)。
    """
    url = get_download_url(mod_id, file_id)
    if not url:
        raise CurseForgeError("无法获取下载链接(该文件可能已被作者删除)")
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    # 从 URL 尾部推断文件名
    fname = url.split("?")[0].rstrip("/").split("/")[-1]
    if not fname or "." not in fname:
        fname = "cf-{}-{}.jar".format(mod_id, file_id)
    download_file(url, dest_dir / fname)
    return fname


def download_with_deps(mod_id, file_id, game_version, loader, dest_dir,
                       progress_cb=None):
    """
    下载文件并自动补装必需依赖。
    返回 [(filename, is_dependency)]
    """
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    results = []
    fn = download_mod_file(mod_id, file_id, dest_dir)
    results.append((fn, False))
    for dep_id in get_file_deps(mod_id, file_id):
        if progress_cb:
            progress_cb("补装依赖(CurseForge): " + str(dep_id), 0, 0)
        try:
            dep_files = get_mod_files(dep_id, game_version, loader)
            if dep_files:
                d_fn = download_mod_file(dep_id, dep_files[0]["id"], dest_dir)
                results.append((d_fn, True))
        except Exception:
            # 单个依赖失败不阻断主文件
            continue
    return results


# ---------------------------------------------------------------
# CurseForge zip 整合包
# ---------------------------------------------------------------
def parse_modpack_manifest(zip_path):
    """
    解析 CurseForge 整合包 zip 内的 manifest.json。
    结构示例:
    {
      "minecraft": {"version": "1.20.1",
                    "modLoaders": [{"id": "forge-47.1.0"}]},
      "name": "xxx", "version": "1.0",
      "files": [{"projectID": 123, "fileID": 456, "required": true}],
      "overrides": "overrides"
    }
    """
    with zipfile.ZipFile(zip_path) as zf:
        return json.loads(zf.read("manifest.json").decode("utf-8"))


def import_modpack(zip_path, instance_name=None, progress_cb=None):
    """
    导入 CurseForge 整合包(.zip, 含 manifest.json):
    1. 解析 minecraft 版本与加载器, 安装游戏版本 + 加载器
    2. 下载 manifest.files 中 required 的 mod 到实例 mods
    3. 解压 overrides 目录到实例根目录
    返回创建的实例名。
    """
    import instance as instance_mod
    import installer
    import version_manager

    zip_path = Path(zip_path)
    manifest = parse_modpack_manifest(zip_path)
    mc = manifest.get("minecraft") or {}
    game_version = mc.get("version")
    if not game_version:
        raise ValueError("该整合包未声明 minecraft 版本")

    # 从 modLoaders[0].id("forge-47.1.0"/"fabric-0.15.0")识别加载器类型
    loaders = mc.get("modLoaders") or []
    loader_type = None
    if loaders:
        first = (loaders[0].get("id") or "").lower()
        for name in ("forge", "fabric", "quilt", "neoforge"):
            if first.startswith(name):
                loader_type = name
                break

    if progress_cb:
        progress_cb("安装游戏版本 " + game_version, 0, 0)
    # 确保原版已下载
    version_manager.download_version(game_version, progress_cb=progress_cb)

    # 安装加载器(forge/fabric/quilt; neoforge 若未支持会报错并中断)
    if loader_type and loader_type != "neoforge":
        if progress_cb:
            progress_cb("安装加载器 " + loader_type, 0, 0)
        loader_version_id = installer.install_loader(game_version,
                                                     loader_type)
    else:
        loader_version_id = game_version

    # 创建实例
    if not instance_name:
        instance_name = (manifest.get("name") or "pack") + "-" + game_version
    inst = instance_mod.create_instance(instance_name, loader_version_id)
    game_dir = instance_mod.instance_dir(instance_name)
    mods_dir = game_dir / "mods"
    mods_dir.mkdir(parents=True, exist_ok=True)

    # 下载全部必需文件到 mods
    files = manifest.get("files") or []
    if progress_cb:
        progress_cb("下载整合包文件 0/{}".format(len(files)), 0, len(files))
    for i, f in enumerate(files, 1):
        if not f.get("required", True):
            continue
        if progress_cb:
            progress_cb("下载整合包文件 {}/{}".format(i, len(files)),
                        i, len(files))
        try:
            download_mod_file(f.get("projectID"), f.get("fileID"), mods_dir)
        except Exception as exc:
            if progress_cb:
                progress_cb("文件失败(继续): {} - {}".format(
                    f.get("projectID"), exc), i, len(files))

    # overrides 解压到实例根目录(配置/脚本/材质等)
    with zipfile.ZipFile(zip_path) as zf:
        for name in zf.namelist():
            if name.startswith("overrides/"):
                rel = name[len("overrides/"):]
                if not rel:
                    continue
                dest = game_dir / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(zf.read(name))
    return instance_name
