# -*- coding: utf-8 -*-
"""
VoxelLauncher - 本地 Mod / 资源包 / 光影包管理模块
- 读取 mods 目录, 解析 jar 内 fabric.mod.json / META-INF/mods.toml 获取
  名称/版本/图标/依赖
- 提取 mod 图标(供 UI 用 Pillow 显示)
- 依赖检测: 过滤游戏基础依赖, 找出缺失的模组前置
- 启用/禁用(重命名 .jar <-> .jar.disabled)
- 删除 / 复制导入
"""
import json
import shutil
import zipfile
from pathlib import Path

# tomllib 是 Python 3.11+ 标准库, 用于解析 Forge 的 mods.toml
try:
    import tomllib
except ImportError:  # pragma: no cover  (3.11 以下旧版, 极少见)
    tomllib = None

import requests


# 游戏基础依赖(不计入"模组前置", 显示依赖状态时过滤掉)
BASE_DEP_IDS = {
    "minecraft", "forge", "fabricloader", "quilt_loader", "java",
    "fml", "javafml", "minecraftforge", "mixin", "minecraft",
    # Fabric API 内部模块(安装 fabric-api 即自动包含)
    "fabric-api-base", "fabric-api-lookup-api-v1", "fabric-biome-api-v1",
    "fabric-blockrenderlayer-v1", "fabric-command-api-v1", "fabric-command-api-v2",
    "fabric-commands-v0", "fabric-containers-v0", "fabric-content-registries-v0",
    "fabric-crash-report-info-v1", "fabric-data-generation-api-v1",
    "fabric-dimensions-v1", "fabric-entity-events-v1", "fabric-events-interaction-v0",
    "fabric-events-lifecycle-v0", "fabric-game-rule-api-v1", "fabric-gametest-api-v1",
    "fabric-item-api-v1", "fabric-item-group-api-v1", "fabric-key-binding-api-v1",
    "fabric-keybindings-v0", "fabric-lifecycle-events-v1", "fabric-loot-api-v2",
    "fabric-loot-tables-v1", "fabric-mining-level-api-v1", "fabric-models-v0",
    "fabric-networking-api-v1", "fabric-networking-v0", "fabric-object-builder-api-v1",
    "fabric-particles-v1", "fabric-registry-sync-v0", "fabric-renderer-api-v1",
    "fabric-renderer-indigo", "fabric-renderer-registries-v1", "fabric-rendering-data-attachment-v1",
    "fabric-rendering-fluids-v1", "fabric-rendering-v0", "fabric-rendering-v1",
    "fabric-resource-loader-v0", "fabric-screen-api-v1", "fabric-screen-handler-api-v1",
    "fabric-sound-api-v1", "fabric-structure-api-v1", "fabric-tag-extensions-v0",
    "fabric-textures-v0", "fabric-tool-attribute-api-v1", "fabric-transfer-api-v1",
    "fabric-transitive-access-wideners-v1", "fabric-recipe-api-v1",
    "fabric-convention-tags-v1", "fabric-convention-tags-v2",
    "fabric-message-api-v1", "fabric-attachment-api-v1",
    "fabric-permissions-api-v0", "fabric-entity-events-v2",
    "fabric-biome-api-v2", "fabric-resource-conditions-api-v1",
    "fabric-version-remapping-api-v1", "fabric-language-kotlin",
    # Quilt API 内部模块
    "quilt_base", "quilt_block_extensions", "quilt_entity",
    "quilt_item_extensions", "quilt_networking", "quilt_registry",
    "quilt_rendering", "quilt_resource_loader", "quilt_tools",
    "quilted_fabric_api", "quilted_fabric_api_base",
    # 其他常见库
    "architectury", "cloth-config2", "cloth-basic-math",
    "forgeconfigapiport", "forgeservice",
}


def _is_fabric_api_module(dep_id):
    """判断是否为 Fabric API 内部模块"""
    if dep_id in BASE_DEP_IDS:
        return True
    # fabric-xxx-api-vN 格式的都是 Fabric API 内部模块
    if dep_id.startswith("fabric-") and "-api-v" in dep_id:
        return True
    if dep_id.startswith("fabric-") and dep_id.endswith("-v0"):
        return True
    if dep_id.startswith("fabric-") and dep_id.endswith("-v1"):
        return True
    if dep_id.startswith("quilt_") or dep_id.startswith("quilted_fabric"):
        return True
    return False


def _has_fabric_api(installed_ids):
    """检查是否已安装 Fabric API"""
    return ("fabric-api" in installed_ids or "fabric" in installed_ids
            or "quilted_fabric_api" in installed_ids or "qsl" in installed_ids)


# ---------------------------------------------------------------
# jar 内元数据解析
# ---------------------------------------------------------------
def _safe_read(zf, name, max_len=512 * 1024):
    try:
        data = zf.read(name)
        if len(data) > max_len:
            return None
        return data.decode("utf-8", errors="ignore")
    except (KeyError, OSError):
        return None


def _parse_toml(text):
    """解析 TOML 文本, 失败返回 None"""
    if tomllib is None:
        return None
    try:
        return tomllib.loads(text)
    except Exception:
        return None


def _parse_forge_toml(text, fallback_name):
    """解析 Forge mods.toml: 返回 {id, name, version, icon, dependencies}"""
    result = {
        "id": fallback_name, "name": fallback_name, "version": "",
        "icon": None, "dependencies": {},
    }
    data = _parse_toml(text)
    if data:
        mods = data.get("mods")
        if isinstance(mods, list) and mods:
            m = mods[0]
            if isinstance(m, dict):
                result["id"] = m.get("modId") or fallback_name
                result["name"] = (m.get("displayName") or m.get("modId")
                                  or fallback_name)
                result["version"] = str(m.get("version", ""))
                result["icon"] = m.get("logoFile")
        dep_section = data.get("dependencies")
        if isinstance(dep_section, dict):
            dep_list = dep_section.get(result["id"])
            if isinstance(dep_list, list):
                for d in dep_list:
                    if isinstance(d, dict) and d.get("modId"):
                        result["dependencies"][d["modId"]] = str(
                            d.get("versionRange", ""))
        return result
    # tomllib 解析失败 -> 简单正则兜底
    import re
    m = re.search(r'^\s*modId\s*=\s*"([^"]+)"', text, re.M)
    if m:
        result["id"] = m.group(1)
    m = re.search(r'^\s*displayName\s*=\s*"([^"]+)"', text, re.M)
    if m:
        result["name"] = m.group(1)
    m = re.search(r'^\s*logoFile\s*=\s*"([^"]+)"', text, re.M)
    if m:
        result["icon"] = m.group(1)
    # dependencies 段内收集所有 modId(尽力)
    in_dep = False
    for line in text.splitlines():
        if re.match(r'\s*\[\[dependencies\.', line):
            in_dep = True
            continue
        if in_dep and re.match(r'\s*\[\[', line):
            in_dep = False
        if in_dep:
            m = re.search(r'modId\s*=\s*"([^"]+)"', line)
            if m:
                result["dependencies"].setdefault(m.group(1), "")
    return result


def parse_mod_meta(jar_path):
    """
    解析 mod jar 的元数据。
    返回 {id, name, version, description, icon, dependencies} 或 None(非 mod)。
    - Fabric/Quilt: fabric.mod.json / quilt.mod.json(icon / depends)
    - Forge       : META-INF/mods.toml(logoFile / dependencies)
    """
    jar_path = Path(jar_path)
    if jar_path.suffix.lower() != ".jar":
        return None
    try:
        with zipfile.ZipFile(jar_path) as zf:
            # Fabric / Quilt
            for candidate in ("fabric.mod.json", "quilt.mod.json"):
                text = _safe_read(zf, candidate)
                if text:
                    try:
                        data = json.loads(text)
                        icon = data.get("icon")
                        if isinstance(icon, dict):
                            icon = icon.get("path")
                        return {
                            "id": data.get("id") or jar_path.stem,
                            "name": data.get("name") or jar_path.stem,
                            "version": str(data.get("version", "")),
                            "description": str(data.get("description", "")),
                            "icon": icon,
                            "dependencies": dict(data.get("depends") or {}),
                        }
                    except Exception:
                        pass
            # Forge (mods.toml)
            text = _safe_read(zf, "META-INF/mods.toml")
            if text:
                meta = _parse_forge_toml(text, jar_path.stem)
                meta["description"] = ""
                return meta
            # 无元数据, 仅按文件名兜底
            return {"id": jar_path.stem, "name": jar_path.stem, "version": "",
                    "description": "", "icon": None, "dependencies": {}}
    except (zipfile.BadZipFile, OSError):
        return None


# ---------------------------------------------------------------
# 图标提取
# ---------------------------------------------------------------
def extract_icon_bytes(jar_path, icon_path):
    """从 jar 中读取图标文件的原始字节, 失败返回 None"""
    if not icon_path:
        return None
    jar_path = Path(jar_path)
    try:
        with zipfile.ZipFile(jar_path) as zf:
            try:
                return zf.read(icon_path)
            except KeyError:
                # 部分 mod 的路径大小写/前缀不一致, 按尾部匹配兜底
                for name in zf.namelist():
                    if name.replace("\\", "/").endswith(
                            icon_path.replace("\\", "/")):
                        return zf.read(name)
                return None
    except (zipfile.BadZipFile, OSError):
        return None


# ---------------------------------------------------------------
# 依赖检测
# ---------------------------------------------------------------
def analyze_mods(mods_dir):
    """
    解析 mods 目录下全部 mod, 返回列表(每项含图标字节与缺失前置):
    [{filename, id, name, version, enabled, icon_bytes, missing}]
    只统计"启用(.jar)"的 mod 作为已安装前置; 已禁用(.jar.disabled)也会列出,
    但不算已安装。
    """
    mods_dir = Path(mods_dir)
    if not mods_dir.exists():
        return []
    entries = []
    for f in sorted(mods_dir.iterdir()):
        if f.suffix.lower() in (".jar", ".disabled"):
            entries.append(f)
    if not entries:
        return []

    # 第一遍: 解析元数据, 收集已安装(启用)的 modid
    metas = {}
    installed_ids = set()
    for f in entries:
        meta = parse_mod_meta(f)
        metas[f.name] = meta or {}
        enabled = f.suffix.lower() == ".jar"
        if enabled and meta and meta.get("id"):
            installed_ids.add(meta["id"])

    # 第二遍: 计算缺失前置 + 提取图标
    result = []
    for f in entries:
        meta = metas.get(f.name) or {}
        deps = meta.get("dependencies") or {}
        missing = []
        has_fapi = _has_fabric_api(installed_ids)
        for dep in deps:
            if dep in BASE_DEP_IDS or dep in installed_ids:
                continue
            # Fabric API 内部模块，且已安装 Fabric API，则不算缺失
            if has_fapi and _is_fabric_api_module(dep):
                continue
            missing.append(dep)
        icon_bytes = extract_icon_bytes(f, meta.get("icon"))
        result.append({
            "filename": f.name,
            "id": meta.get("id", f.stem),
            "name": meta.get("name", f.stem),
            "version": meta.get("version", ""),
            "enabled": f.suffix.lower() == ".jar",
            "icon_bytes": icon_bytes,
            "dependencies": [d for d in deps
                             if d not in BASE_DEP_IDS
                             and not (has_fapi and _is_fabric_api_module(d))],
            "missing": missing,
        })
    result.sort(key=lambda x: (not x["enabled"], x["name"].lower()))
    return result


# ---------------------------------------------------------------
# 列表 / 开关 / 删除
# ---------------------------------------------------------------
def list_mods(mods_dir):
    """
    返回 [{name, version, filename, enabled}], 按名称排序。
    """
    mods_dir = Path(mods_dir)
    result = []
    if mods_dir.exists():
        for f in sorted(mods_dir.iterdir()):
            if f.suffix.lower() not in (".jar", ".disabled"):
                continue
            enabled = f.suffix.lower() == ".jar"
            base = f.name[:-9] if f.name.lower().endswith(".jar.disabled") \
                else f.name
            meta = parse_mod_meta(f) if enabled else None
            result.append({
                "name": (meta or {}).get("name", f.stem),
                "version": (meta or {}).get("version", ""),
                "filename": f.name,
                "enabled": enabled,
            })
    return result


# ---------------------------------------------------------------
# 列表 / 开关 / 删除
# ---------------------------------------------------------------
def list_mods(mods_dir):
    """
    返回 [{name, version, filename, enabled}], 按名称排序。
    """
    mods_dir = Path(mods_dir)
    result = []
    if mods_dir.exists():
        for f in sorted(mods_dir.iterdir()):
            if f.suffix.lower() not in (".jar", ".disabled"):
                continue
            enabled = f.suffix.lower() == ".jar"
            base = f.name[:-9] if f.name.lower().endswith(".jar.disabled") \
                else f.name
            meta = parse_mod_meta(f) if enabled else None
            result.append({
                "name": (meta or {}).get("name", f.stem),
                "version": (meta or {}).get("version", ""),
                "filename": f.name,
                "enabled": enabled,
            })
    return result


def set_mod_enabled(mods_dir, filename, enabled):
    mods_dir = Path(mods_dir)
    f = mods_dir / filename
    if not f.exists():
        return False
    if enabled and f.suffix.lower() == ".disabled":
        f.rename(mods_dir / (f.name[:-9]))
    elif not enabled and f.suffix.lower() == ".jar":
        f.rename(mods_dir / (f.name + ".disabled"))
    return True


def delete_mod(mods_dir, filename):
    mods_dir = Path(mods_dir)
    f = mods_dir / filename
    if f.exists():
        f.unlink()
        return True
    return False


def copy_mod_into(mods_dir, source_path):
    """把外部 jar 复制进 mods 目录, 返回新文件名"""
    src = Path(source_path)
    if not src.exists() or src.suffix.lower() != ".jar":
        raise ValueError("只支持 .jar 文件")
    mods_dir = Path(mods_dir)
    mods_dir.mkdir(parents=True, exist_ok=True)
    dest = mods_dir / src.name
    if dest.exists():
        raise ValueError("同名文件已存在: " + src.name)
    shutil.copy2(src, dest)
    return dest.name


# ---------------------------------------------------------------
# 资源包 / 光影包(仅列表与打开目录, 结构一致)
# ---------------------------------------------------------------
def list_packs(pack_dir):
    """列出资源包/光影包(zip 或文件夹)的名称"""
    pack_dir = Path(pack_dir)
    result = []
    if pack_dir.exists():
        for item in sorted(pack_dir.iterdir()):
            if item.is_file() and item.suffix.lower() != ".zip":
                continue
            if item.is_dir():
                result.append(item.name)
            else:
                result.append(item.stem)
    return result
