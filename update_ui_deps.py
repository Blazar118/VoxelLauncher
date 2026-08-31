# -*- coding: utf-8 -*-
"""修改UI的_mr_download方法，添加依赖下载进度显示"""
import re

filepath = r'C:\Users\bllaa\Doubao\chats\2026-08-28\new-chat\VoxelLauncher\ui_main.py'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# 找到调用 download_versions_with_deps 的地方并替换
old_call = '''                # 下载选中版本并自动补装依赖
                modrinth.download_versions_with_deps(
                    version_id, mc, loader, dest_dir)
                self._post("mr_status", "已下载 {} 到 {}".format(ver_name, dest_dir))
                self._post("mods_reload", None)'''

new_call = '''                # 下载选中版本并自动补装依赖(带进度)
                dep_results = []
                def _dl_progress(msg, cur, total):
                    self._post("mr_status", msg)
                dl_results = modrinth.download_versions_with_deps(
                    version_id, mc, loader, dest_dir,
                    progress_cb=_dl_progress)
                # 统计结果
                main_mods = [r for r in dl_results if not r[1]]
                dep_mods = [r for r in dl_results if r[1]]
                result_msg = "下载完成: 主模组{}个, 依赖{}个".format(len(main_mods), len(dep_mods))
                if dep_mods:
                    dep_names = "\\n".join(["  - " + r[0] for r in dep_mods])
                    result_msg += "\\n已安装依赖:\\n" + dep_names
                self._post("mr_status", result_msg)
                self._post("mods_reload", None)'''

if old_call in content:
    content = content.replace(old_call, new_call, 1)
    print("UI调用替换成功!")
else:
    print("未找到旧调用，尝试查找...")
    idx = content.find('download_versions_with_deps')
    if idx != -1:
        print(repr(content[idx-100:idx+200]))
    else:
        print("找不到 download_versions_with_deps")

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

import ast
ast.parse(content)
print("语法OK")
