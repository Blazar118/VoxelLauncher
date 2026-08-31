# -*- coding: utf-8 -*-
"""临时冒烟: 资源包/数据包/光影包/整合包 四个新 tab"""
import os
import sys
import tempfile
import tkinter as tk
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ["APPDATA"] = tempfile.mkdtemp()

from config import CONFIG
import ui_main

root = tk.Tk()
app = ui_main.VoxelApp(root)


def step1():
    tabs = [app.nb.tab(t, "text") for t in app.nb.tabs()]
    for need in (" 资源包 ", " 数据包 ", " 光影包 ", " 整合包 "):
        assert need in tabs, "缺少 tab " + need
    print("步骤1 通过: 四个新 tab 均已创建")

    # 资源页控件存在性
    for ptype in ("resourcepack", "datapack", "shader"):
        for attr in ("res_inst_", "res_query_", "res_gv_", "res_loader_",
                     "res_list_", "res_local_", "res_status_"):
            assert hasattr(app, attr + ptype), "缺少 " + attr + ptype
    print("步骤2 通过: 资源页控件齐全")

    # 资源页本地列表渲染 + 事件分发(延时等待队列轮询)
    app._post("res_local", ("resourcepack", ["a.zip", "b.zip"]))
    root.after(300, check_local)


def check_local():
    local_lst = app.res_local_resourcepack
    items = local_lst.get(0, "end")
    assert items == ("a.zip", "b.zip"), items
    print("步骤3 通过: 资源页本地列表事件渲染 OK")

    # res_list 事件
    app._post("res_list", ("shader", [{"title": "BSL", "downloads": 99}]))
    root.after(300, check_shader_list)


def check_shader_list():
    shader_lst = app.res_list_shader
    assert "BSL" in shader_lst.get(0), shader_lst.get(0)
    print("步骤4 通过: 资源页搜索结果事件渲染 OK")

    # Modrinth search_projects 带 project_type
    with mock.patch.object(ui_main.modrinth, "search_projects",
                           return_value=[{"project_id": 1, "title": "T"}]):
        app._res_search("resourcepack")
    root.after(500, step2)


def step2():
    app.pk_query.insert(0, "skyblock")
    app._post("pk_list_update", [{"title": "Pack", "downloads": 5}])
    root.update()
    assert "Pack" in app.pk_list.get(0), app.pk_list.get(0)
    print("步骤5 通过: 整合包列表事件渲染 OK")

    # _import_pack_auto 类型识别: 构造假 mrpack 与 CF zip
    d = tempfile.mkdtemp()
    import zipfile, json

    mr = os.path.join(d, "a.mrpack")
    with zipfile.ZipFile(mr, "w") as z:
        z.writestr("modrinth.index.json",
                   json.dumps({"formatVersion": 1, "files": [],
                               "dependencies": {"minecraft": "1.20.1"},
                               "name": "x"}))
    # mock import_mrpack 避免真实安装
    with mock.patch.object(ui_main.modrinth, "import_mrpack",
                           return_value="fake-inst") as m:
        got = app._import_pack_auto(mr)
        assert got == "fake-inst" and m.called, "应走 mrpack 分支"

    cf = os.path.join(d, "b.zip")
    with zipfile.ZipFile(cf, "w") as z:
        z.writestr("manifest.json",
                   json.dumps({"minecraft": {"version": "1.20.1"}}))
    with mock.patch.object(ui_main.curseforge, "import_modpack",
                           return_value="fake-cf") as m2:
        got2 = app._import_pack_auto(cf)
        assert got2 == "fake-cf" and m2.called, "应走 CF zip 分支"

    bad = os.path.join(d, "c.zip")
    with zipfile.ZipFile(bad, "w") as z:
        z.writestr("random.txt", "x")
    try:
        app._import_pack_auto(bad)
        assert False, "未知格式应抛错"
    except ValueError:
        pass
    print("步骤6 通过: 整合包类型自动识别(mrpack/CF zip/未知)")

    root.destroy()


root.after(300, step1)
root.mainloop()
print("四个新 tab 冒烟全部通过")
