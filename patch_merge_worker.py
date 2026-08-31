# -*- coding: utf-8 -*-
"""合并模式下, 非 Fabric 加载器走 install_loader + 合并式实例"""
import ast

p = r'C:\Users\bllaa\Doubao\chats\2026-08-28\new-chat\VoxelLauncher\ui_main.py'
with open(p, 'r', encoding='utf-8') as f:
    c = f.read()

old_worker = '''        def _worker():
            try:
                if use_merged:
                    # PCL2 合并模式: 直接创建合并式版本文件夹
                    version_id = installer_mod.install_fabric_merged(
                        vid, loader_version=loader_ver, api_version=api_ver,
                        progress_cb=lambda msg, c, t: self._post(
                            "vdl_status", msg))
                else:
                    version_id = installer_mod.install_loader(
                        vid, loader, loader_version=loader_ver, api_version=api_ver,
                        progress_cb=lambda msg, c, t: self._post(
                            "vdl_status", msg))
                # 创建实例
                instance_mod.create_instance(
                    inst_name.strip(), version_id,
                    java_path=self._selected_java(),
                    merged_mode=use_merged)'''

new_worker = '''        def _worker():
            try:
                if use_merged and loader == "fabric":
                    # PCL2 合并模式: 直接创建合并式版本文件夹
                    version_id = installer_mod.install_fabric_merged(
                        vid, loader_version=loader_ver, api_version=api_ver,
                        progress_cb=lambda msg, c, t: self._post(
                            "vdl_status", msg))
                else:
                    # 其他加载器(或分离): 普通安装
                    version_id = installer_mod.install_loader(
                        vid, loader, loader_version=loader_ver, api_version=api_ver,
                        progress_cb=lambda msg, c, t: self._post(
                            "vdl_status", msg))
                # 创建实例 (默认合并模式, 合并模式下会在版本文件夹内建 mods/saves 等)
                instance_mod.create_instance(
                    inst_name.strip(), version_id,
                    java_path=self._selected_java(),
                    merged_mode=use_merged)'''

if old_worker in c:
    c = c.replace(old_worker, new_worker, 1)
    print('worker 分支已修复: 非 Fabric 合并走 install_loader + 合并式实例')
else:
    print('WARN: 未找到 worker 块')

with open(p, 'w', encoding='utf-8') as f:
    f.write(c)
ast.parse(c)
print('语法检查通过')
