# -*- coding: utf-8 -*-
"""模组冲突检查器"""
import os
import json
import zipfile
import re


class ModChecker:
    """Minecraft 模组冲突检查器"""

    def __init__(self, mods_dir):
        self.mods_dir = mods_dir

    def _read_fabric_mod_json(self, jar_path):
        """读取 fabric.mod.json"""
        try:
            with zipfile.ZipFile(jar_path, 'r') as zf:
                # 查找 fabric.mod.json
                for name in zf.namelist():
                    if name.endswith('fabric.mod.json'):
                        with zf.open(name) as f:
                            return json.loads(f.read().decode('utf-8'))
        except Exception:
            pass
        return None

    def _read_forge_mods_toml(self, jar_path):
        """读取 mods.toml (Forge)"""
        try:
            with zipfile.ZipFile(jar_path, 'r') as zf:
                for name in zf.namelist():
                    if name.endswith('mods.toml'):
                        with zf.open(name) as f:
                            content = f.read().decode('utf-8')
                            # 简单解析 modId
                            ids = re.findall(r'modId\s*=\s*"([^"]+)"', content)
                            return {"id": ids[0] if ids else None}
        except Exception:
            pass
        return None

    def scan_mods(self):
        """扫描所有模组"""
        mods = []
        if not os.path.exists(self.mods_dir):
            return mods

        for filename in os.listdir(self.mods_dir):
            if not filename.endswith('.jar'):
                continue
            filepath = os.path.join(self.mods_dir, filename)
            mod_info = {
                "filename": filename,
                "path": filepath,
                "size": os.path.getsize(filepath),
                "id": None,
                "name": None,
                "version": None,
                "loader": None,
                "depends": {},
                "breaks": {},
                "raw": None
            }

            # 尝试 Fabric
            fabric_info = self._read_fabric_mod_json(filepath)
            if fabric_info:
                mod_info["loader"] = "fabric"
                mod_info["id"] = fabric_info.get("id")
                mod_info["name"] = fabric_info.get("name", fabric_info.get("id"))
                mod_info["version"] = fabric_info.get("version")
                mod_info["depends"] = fabric_info.get("depends", {})
                mod_info["breaks"] = fabric_info.get("breaks", {})
                mod_info["raw"] = fabric_info
            else:
                # 尝试 Forge
                forge_info = self._read_forge_mods_toml(filepath)
                if forge_info and forge_info.get("id"):
                    mod_info["loader"] = "forge"
                    mod_info["id"] = forge_info["id"]
                    mod_info["name"] = filename
                    mod_info["raw"] = forge_info

            mods.append(mod_info)

        return mods

    def check_conflicts(self, game_version=None, loader_version=None):
        """检查冲突"""
        mods = self.scan_mods()
        issues = []

        # 1. 检查重复模组ID
        id_map = {}
        for mod in mods:
            if mod["id"]:
                if mod["id"] in id_map:
                    id_map[mod["id"]].append(mod)
                else:
                    id_map[mod["id"]] = [mod]

        for mod_id, mod_list in id_map.items():
            if len(mod_list) > 1:
                issues.append({
                    "type": "duplicate",
                    "severity": "error",
                    "title": f"重复模组: {mod_id}",
                    "description": f"发现 {len(mod_list)} 个相同ID的模组",
                    "mods": [m["filename"] for m in mod_list],
                    "solution": "只保留一个版本，删除其他重复的jar文件"
                })

        # 2. 检查加载器混合
        fabric_mods = [m for m in mods if m["loader"] == "fabric"]
        forge_mods = [m for m in mods if m["loader"] == "forge"]
        unknown_mods = [m for m in mods if m["loader"] is None]

        if fabric_mods and forge_mods:
            issues.append({
                "type": "loader_mix",
                "severity": "error",
                "title": "加载器混合",
                "description": f"发现 {len(fabric_mods)} 个Fabric模组和 {len(forge_mods)} 个Forge模组",
                "fabric_mods": [m["filename"] for m in fabric_mods[:5]],
                "forge_mods": [m["filename"] for m in forge_mods[:5]],
                "solution": "Fabric和Forge模组不能混用！请删除不匹配的模组"
            })

        # 3. 检查依赖缺失
        installed_ids = set(id_map.keys())
        for mod in mods:
            if not mod["depends"]:
                continue
            for dep_id, dep_version in mod["depends"].items():
                # 跳过一些通用依赖
                if dep_id in ["minecraft", "fabricloader", "java", "fabric",
                              "forge", "minecraft", "fabric-api"]:
                    continue
                if dep_id not in installed_ids:
                    issues.append({
                        "type": "missing_dependency",
                        "severity": "warning",
                        "title": f"缺少依赖: {dep_id}",
                        "description": f"模组 {mod['name'] or mod['filename']} 需要 {dep_id} {dep_version}",
                        "mod": mod["filename"],
                        "missing": dep_id,
                        "solution": f"下载并安装 {dep_id} 模组"
                    })

        # 4. 检查版本不兼容 (breaks)
        for mod in mods:
            if not mod["breaks"]:
                continue
            for break_id, break_version in mod["breaks"].items():
                if break_id in installed_ids:
                    issues.append({
                        "type": "incompatible",
                        "severity": "error",
                        "title": f"模组不兼容: {mod['name']} 与 {break_id}",
                        "description": f"{mod['name']} 声明与 {break_id} {break_version} 不兼容",
                        "mod": mod["filename"],
                        "conflict_with": break_id,
                        "solution": "移除其中一个不兼容的模组"
                    })

        # 5. 检查无法识别的模组
        if unknown_mods:
            issues.append({
                "type": "unknown",
                "severity": "info",
                "title": f"无法识别的模组: {len(unknown_mods)} 个",
                "description": "这些模组可能是旧版本或损坏的",
                "mods": [m["filename"] for m in unknown_mods],
                "solution": "检查这些文件是否是有效的模组"
            })

        # 统计
        summary = {
            "total_mods": len(mods),
            "fabric_mods": len(fabric_mods),
            "forge_mods": len(forge_mods),
            "unknown_mods": len(unknown_mods),
            "errors": len([i for i in issues if i["severity"] == "error"]),
            "warnings": len([i for i in issues if i["severity"] == "warning"]),
            "infos": len([i for i in issues if i["severity"] == "info"]),
        }

        return {"issues": issues, "mods": mods, "summary": summary}
