# -*- coding: utf-8 -*-
"""
Patch 4: 真正的自动更新
- 检查更新按钮调用 updater 真实检测
- 有更新时弹窗让用户一键下载更新
- 启动时后台检查更新(延迟5秒, 不打扰)
- 添加 _check_update_now / _do_download_update / _maybe_auto_check 方法
"""
import ast

filepath = r'C:\Users\bllaa\Doubao\chats\2026-08-28\new-chat\VoxelLauncher\ui_main.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# ---------- 1. 替换检查更新按钮 ----------
old_btn = '''        ttk.Button(btn_frame, text="🔄 检查更新",
                   command=lambda: messagebox.showinfo("检查更新",
                       "当前已是最新版本 " + version.VERSION_TAG + chr(10) +
                       "感谢使用 VoxelLauncher!")).pack(side="left", padx=5)'''
new_btn = '''        ttk.Button(btn_frame, text="🔄 检查更新",
                   command=self._check_update_now).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="🎁 彩蛋",
                   command=self._egg_toggle).pack(side="left", padx=5)'''
if old_btn in content:
    content = content.replace(old_btn, new_btn, 1)
    print("[1] 检查更新按钮已替换 ✓")
else:
    print("[1] ❌ 未找到检查更新按钮")

# ---------- 2. 添加更新方法（放在 _open_launcher_dir 前） ----------
anchor = '''    def _open_launcher_dir(self):'''
methods = '''    # ---------------- 自动更新 ----------------
    def _check_update_now(self):
        """手动点击检查更新"""
        def _work():
            try:
                self._post("upd_status", "正在检查更新...")
                result = updater.check_for_update()
                if result is None:
                    self._post("upd_status", "检查失败(网络问题), 请稍后重试")
                    messagebox.showwarning("检查更新", "无法连接更新服务器, 请检查网络后重试")
                    return
                has_new, latest = result
                if has_new:
                    self._post("upd_status", "发现新版本 v" + latest)
                    self.root.after(0, lambda: self._ask_update(latest))
                else:
                    self._post("upd_status", "已是最新版本 v" + version.VERSION)
                    messagebox.showinfo("检查更新",
                        "当前已是最新版本 " + version.VERSION_TAG + chr(10) +
                        "感谢使用 VoxelLauncher!")
            except Exception as e:
                self._post("upd_status", "检查更新出错: " + str(e))
        threading.Thread(target=_work, daemon=True).start()

    def _ask_update(self, latest):
        """询问是否下载更新"""
        ans = messagebox.askyesno("发现新版本",
            "发现新版本 v" + latest + chr(10) +
            "当前版本 v" + version.VERSION + chr(10) + chr(10) +
            "是否现在下载并安装?")
        if ans:
            self._do_download_update(latest)

    def _do_download_update(self, latest):
        """下载新版本并应用"""
        _, url = updater.get_latest_version()
        if not url:
            messagebox.showerror("更新失败", "获取下载地址失败, 请手动到官网下载")
            return
        import tempfile
        dl_path = os.path.join(tempfile.gettempdir(), "VoxelLauncher_new.exe")
        # 下载进度窗口
        prog = tk.Toplevel(self.root)
        prog.title("正在下载更新")
        prog.geometry("380x120")
        tk.Label(prog, text="正在下载 v" + latest + " ...").pack(pady=10)
        bar = ttk.Progressbar(prog, length=300, maximum=100)
        bar.pack(pady=5)

        def _progress(done, total):
            pct = int(done / total * 100) if total else 0
            bar["value"] = pct

        def _work():
            ok, err = updater.download_update(url, dl_path, _progress)
            self.root.after(0, lambda: self._after_download(ok, err, dl_path, prog, latest))

        threading.Thread(target=_work, daemon=True).start()

    def _after_download(self, ok, err, dl_path, prog_win, latest):
        """下载完成后处理"""
        prog_win.destroy()
        if not ok:
            messagebox.showerror("下载失败", "下载失败: " + err + chr(10) +
                                 "请到官网手动下载")
            return
        # 校验大小>10MB 认为是有效 exe
        if not os.path.exists(dl_path) or os.path.getsize(dl_path) < 10 * 1024 * 1024:
            messagebox.showerror("下载失败", "下载的文件不完整, 请到官网手动下载")
            return
        ans = messagebox.askyesno("更新就绪",
            "新版 v" + latest + " 已下载完成(共 " +
            "{:.1f} MB)".format(os.path.getsize(dl_path) / 1024 / 1024) + chr(10) +
            "点击确定将自动替换并重启启动器")
        if ans:
            self._apply_update(dl_path)

    def _apply_update(self, dl_path):
        """应用更新(替换exe并重启)"""
        ok, err = updater.apply_update(dl_path)
        if not ok:
            messagebox.showerror("更新失败", "自动更新失败: " + err + chr(10) +
                                 "请手动替换 VoxelLauncher.exe")
            return
        # 关闭当前程序
        try:
            self.root.destroy()
        except Exception:
            os._exit(0)

    def _maybe_auto_check(self):
        """启动后延迟自动检查更新(不打扰用户, 有新版才提示)"""
        def _work():
            time.sleep(3)
            try:
                result = updater.check_for_update()
                if result and result[0]:  # 有新版
                    latest = result[1]
                    self.root.after(0, lambda: self._ask_update(latest))
            except Exception:
                pass
        threading.Thread(target=_work, daemon=True).start()

    def _egg_toggle(self):
        """彩蛋按钮: 直接弹出一个彩蛋"""
        import random
        eggs = [
            "你知道吗? 这个启动器是 AI 帮忙开发的 😎",
            "彩蛋: 试着快速点 10 下标题 'VoxelLauncher' 试试!",
            "彩蛋: 切换主题到 '苦力怕绿', 有惊喜哦",
            "提示: 在启动页点版本号 5 次可以解锁隐藏功能",
            "VoxelLauncher v" + version.VERSION + " 祝你挖矿愉快! ⛏",
        ]
        messagebox.showinfo("🎉 彩蛋", random.choice(eggs))

    def _open_launcher_dir(self):'''

if anchor in content:
    content = content.replace(anchor, methods, 1)
    print("[2] 更新方法已添加 ✓")
else:
    print("[2] ❌ 未找到 _open_launcher_dir")

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
ast.parse(content)
print("语法 OK")
