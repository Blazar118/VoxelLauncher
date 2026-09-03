# -*- coding: utf-8 -*-
"""
VoxelLauncher - 实例管理模块
每个实例 = 游戏根目录下 instances/{实例名}/ 的一个独立游戏目录,
mods / saves / resourcepacks / shaderpacks 互相隔离。
实例通过 instance.json 记录其使用的版本、Java、内存、JVM 参数。
"""
import json
import shutil
import time
from pathlib import Path

from config import CONFIG

# 实例需要创建的独立子目录
SUBDIRS = ["mods", "saves", "resourcepacks", "shaderpacks", "config",
           "logs", "crash-reports", "natives"]


class InstanceError(Exception):
    """实例操作异常"""


def instances_root():
    return Path(CONFIG.get("game_dir")) / "instances"


def instance_dir(name):
    return instances_root() / name


def list_instances():
    """返回 [{name, ...instance.json字段}], 按创建时间排序
    同时扫描分离模式(instances/{name}/)和合并模式(versions/{version_id}/)
    """
    result = []
    # 1. 分离模式: instances/{name}/instance.json
    root = instances_root()
    if root.exists():
        for d in sorted(root.iterdir(), key=lambda p: p.stat().st_mtime
                        if p.is_dir() else 0):
            meta = d / "instance.json"
            if meta.exists():
                try:
                    data = json.loads(meta.read_text(encoding="utf-8"))
                except Exception:
                    data = {}
                data["name"] = d.name
                result.append(data)
    # 2. 合并模式: versions/{version_id}/instance.json
    versions_root = Path(CONFIG.get("game_dir")) / "versions"
    if versions_root.exists():
        for d in sorted(versions_root.iterdir(), key=lambda p: p.stat().st_mtime
                        if p.is_dir() else 0):
            meta = d / "instance.json"
            if meta.exists():
                try:
                    data = json.loads(meta.read_text(encoding="utf-8"))
                except Exception:
                    data = {}
                # 合并模式用 version_id 作为实例名显示
                if "name" not in data:
                    data["name"] = d.name
                data["merged_mode"] = True
                if "game_dir" not in data:
                    data["game_dir"] = str(d)
                result.append(data)
    # 按创建时间排序
    result.sort(key=lambda x: x.get("created", 0))
    return result


def get_instance(name):
    for inst in list_instances():
        if inst["name"] == name:
            return inst
    return None


def create_instance(name, version_id, java_path=None, max_memory=None,
                    min_memory=None, extra_jvm_args=None, width=None,
                    height=None, merged_mode=False):
    """创建新实例, 返回实例 dict
    merged_mode=True: PCL2 风格, 游戏目录=版本文件夹, mods/saves/config 都在版本目录里
    merged_mode=False: 默认分离模式, 游戏目录=instances/{name}/
    """
    name = name.strip()
    if not name:
        raise InstanceError("实例名不能为空")
    if not _safe_name(name):
        raise InstanceError("实例名包含非法字符")

    if merged_mode:
        # 合并模式: 直接用版本文件夹作为游戏目录
        from pathlib import Path as _Path
        version_dir = _Path(CONFIG.get("game_dir")) / "versions" / version_id
        if not version_dir.exists():
            raise InstanceError("版本文件夹不存在: " + version_id)
        # 确保游戏运行时子目录存在
        for sub in SUBDIRS:
            (version_dir / sub).mkdir(parents=True, exist_ok=True)
        d = version_dir
        meta = {
            "name": name,
            "version_id": version_id,
            "merged_mode": True,
            "game_dir": str(version_dir),
            "java_path": java_path or CONFIG.get("default_java"),
            "max_memory": max_memory if max_memory else CONFIG.get("max_memory"),
            "min_memory": min_memory if min_memory else CONFIG.get("min_memory"),
            "extra_jvm_args": (extra_jvm_args if extra_jvm_args is not None
                               else CONFIG.get("extra_jvm_args", "")),
            "width": width or CONFIG.get("width"),
            "height": height or CONFIG.get("height"),
            "created": time.time(),
        }
        # instance.json 放在版本文件夹里
        (d / "instance.json").write_text(
            json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    else:
        d = instance_dir(name)
        if d.exists():
            raise InstanceError("实例已存在: " + name)
        d.mkdir(parents=True, exist_ok=True)
        for sub in SUBDIRS:
            (d / sub).mkdir(parents=True, exist_ok=True)
        meta = {
            "name": name,
            "version_id": version_id,
            "merged_mode": False,
            "java_path": java_path or CONFIG.get("default_java"),
            "max_memory": max_memory if max_memory else CONFIG.get("max_memory"),
            "min_memory": min_memory if min_memory else CONFIG.get("min_memory"),
            "extra_jvm_args": (extra_jvm_args if extra_jvm_args is not None
                               else CONFIG.get("extra_jvm_args", "")),
            "width": width or CONFIG.get("width"),
            "height": height or CONFIG.get("height"),
            "created": time.time(),
        }
        (d / "instance.json").write_text(
            json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return meta


def get_instance_game_dir(inst):
    """获取实例的游戏目录(合并模式返回版本文件夹, 分离模式返回 instances/{name}/)"""
    if inst.get("merged_mode"):
        return inst.get("game_dir") or str(
            Path(CONFIG.get("game_dir")) / "versions" / inst["version_id"])
    return str(instance_dir(inst["name"]))


def _safe_name(name):
    # 禁止路径分隔符与常见非法字符
    forbidden = set('\\/:*?"<>|')
    return not any(c in forbidden for c in name)


def update_instance(name, **kwargs):
    """更新实例配置字段"""
    meta = get_instance(name)
    if not meta:
        raise InstanceError("实例不存在: " + name)
    for k, v in kwargs.items():
        if v is not None:
            meta[k] = v
    d = instance_dir(name)
    (d / "instance.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return meta


def rename_instance(old_name, new_name):
    """重命名实例(目录+instance.json)"""
    new_name = new_name.strip()
    if not _safe_name(new_name):
        raise InstanceError("新实例名包含非法字符")
    src = instance_dir(old_name)
    dst = instance_dir(new_name)
    if not src.exists():
        raise InstanceError("实例不存在: " + old_name)
    if dst.exists():
        raise InstanceError("目标实例已存在: " + new_name)
    src.rename(dst)
    # 更新 json 里的 name 字段
    meta_file = dst / "instance.json"
    if meta_file.exists():
        data = json.loads(meta_file.read_text(encoding="utf-8"))
        data["name"] = new_name
        meta_file.write_text(json.dumps(data, ensure_ascii=False, indent=2),
                             encoding="utf-8")
    return new_name


def copy_instance(name, new_name):
    """复制实例(含全部独立文件)"""
    new_name = new_name.strip()
    if not _safe_name(new_name):
        raise InstanceError("新实例名包含非法字符")
    src = instance_dir(name)
    dst = instance_dir(new_name)
    if not src.exists():
        raise InstanceError("实例不存在: " + name)
    if dst.exists():
        raise InstanceError("目标实例已存在: " + new_name)
    shutil.copytree(src, dst)
    meta_file = dst / "instance.json"
    if meta_file.exists():
        data = json.loads(meta_file.read_text(encoding="utf-8"))
        data["name"] = new_name
        meta_file.write_text(json.dumps(data, ensure_ascii=False, indent=2),
                             encoding="utf-8")
    return new_name


def delete_instance(name):
    """删除实例(递归)"""
    d = instance_dir(name)
    if not d.exists():
        raise InstanceError("实例不存在: " + name)
    shutil.rmtree(d, ignore_errors=True)
    return True


# ---------------------------------------------------------------
# 实例内子目录快捷方法
# ---------------------------------------------------------------
def instance_subdir(name, sub):
    inst = get_instance(name)
    if inst and inst.get("merged_mode"):
        gd = inst.get("game_dir") or str(
            Path(CONFIG.get("game_dir")) / "versions" / inst["version_id"])
        d = Path(gd) / sub
    else:
        d = instance_dir(name) / sub
    d.mkdir(parents=True, exist_ok=True)
    return d
