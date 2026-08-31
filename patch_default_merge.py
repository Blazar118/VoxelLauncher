# -*- coding: utf-8 -*-
"""默认使用 PCL 合并模式: 去掉 _install_loader 里的合并模式勾选框"""
import io

p = r'C:\Users\bllaa\Doubao\chats\2026-08-28\new-chat\VoxelLauncher\ui_main.py'
with open(p, 'r', encoding='utf-8') as f:
    c = f.read()

# 旧对话框块 (安装加载器)
old_block = '''        # 自定义对话框: 实例名 + 合并模式
        dlg = tk.Toplevel(self.root)
        dlg.title("安装 " + loader)
        dlg.geometry("400x200")
        dlg.resizable(False, False)
        dlg.transient(self.root)
        dlg.grab_set()
        result = {"name": "", "merged": False, "ok": False}

        tk.Label(dlg, text="实例名:").pack(anchor="w", padx=20, pady=(15, 2))
        name_entry = tk.Entry(dlg, width=45)
        name_entry.insert(0, "{}-{}".format(vid, loader))
        name_entry.pack(padx=20)

        merged_var = tk.BooleanVar(value=False)
        tk.Checkbutton(dlg, text="PCL2 合并模式 (版本文件夹=游戏目录)",
                       variable=merged_var).pack(anchor="w", padx=20, pady=(10, 5))
        tk.Label(dlg, text="合并模式: mods/saves/config 都放在版本文件夹里, 和 PCL2 一样",
                 fg="gray", font=("Arial", 8)).pack(anchor="w", padx=20)

        def _ok():
            result["name"] = name_entry.get().strip()
            result["merged"] = merged_var.get()
            result["ok"] = True
            dlg.destroy()

        def _cancel():
            dlg.destroy()

        btn_frame = tk.Frame(dlg)
        btn_frame.pack(pady=15)
        tk.Button(btn_frame, text="确定", width=10, command=_ok).pack(side="left", padx=10)
        tk.Button(btn_frame, text="取消", width=10, command=_cancel).pack(side="left", padx=10)

        name_entry.focus_set()
        dlg.wait_window()

        if not result["ok"] or not result["name"]:
            return
        inst_name = result["name"]
        use_merged = result["merged"] and loader == "Fabric"  # 目前只支持 Fabric 合并'''

new_block = '''        # 自定义对话框: 仅实例名 (与 PCL 一致, 默认自动使用合并模式, 不再询问)
        dlg = tk.Toplevel(self.root)
        dlg.title("安装 " + loader)
        dlg.geometry("380x150")
        dlg.resizable(False, False)
        dlg.transient(self.root)
        dlg.grab_set()
        result = {"name": "", "ok": False}

        tk.Label(dlg, text="实例名:").pack(anchor="w", padx=20, pady=(15, 2))
        name_entry = tk.Entry(dlg, width=45)
        name_entry.insert(0, "{}-{}".format(vid, loader))
        name_entry.pack(padx=20)
        tk.Label(dlg, text="默认使用 PCL 合并模式 (mods/saves 都在版本文件夹里)",
                 fg="gray", font=("Arial", 8)).pack(anchor="w", padx=20, pady=(6, 0))

        def _ok():
            result["name"] = name_entry.get().strip()
            result["ok"] = True
            dlg.destroy()

        def _cancel():
            dlg.destroy()

        btn_frame = tk.Frame(dlg)
        btn_frame.pack(pady=10)
        tk.Button(btn_frame, text="确定", width=10, command=_ok).pack(side="left", padx=10)
        tk.Button(btn_frame, text="取消", width=10, command=_cancel).pack(side="left", padx=10)

        name_entry.focus_set()
        dlg.wait_window()

        if not result["ok"] or not result["name"]:
            return
        inst_name = result["name"]
        # 与 PCL 一致: Fabric 默认直接使用合并模式, 不再弹出询问
        use_merged = (loader == "Fabric")'''

if old_block not in c:
    print('FAIL: 未找到旧对话框块')
else:
    c = c.replace(old_block, new_block, 1)
    with open(p, 'w', encoding='utf-8') as f:
        f.write(c)
    # 语法检查
    import ast
    ast.parse(c)
    print('OK: _install_loader 已改为默认合并, 不再询问')
