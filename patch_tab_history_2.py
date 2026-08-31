# -*- coding: utf-8 -*-
"""
新增 _build_history_tab 历史版本页 + _copy_website_url 复制官网链接方法
"""
import ast

filepath = r'C:\Users\bllaa\Doubao\chats\2026-08-28\new-chat\VoxelLauncher\ui_main.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# 在 _open_launcher_dir 之后、下载管理注释之前插入新方法
anchor = '''        except Exception:
            messagebox.showinfo("启动器目录", launcher_dir)



    # ---------------- 下载管理(断点续传) ----------------'''

addition = '''        except Exception:
            messagebox.showinfo("启动器目录", launcher_dir)


    # ============================================================
    # 历史版本页: 展示所有已发布版本, 可复制下载链接/打开下载
    # ============================================================
    def _build_history_tab(self):
        """历史版本: 启动器所有已发布版本, 一键复制下载链接或打开下载"""
        f = self.tab_history
        # 顶部标题
        title_frame = tk.Frame(f, bg="#1565c0", height=60)
        title_frame.pack(fill="x")
        title_frame.pack_propagate(False)
        tk.Label(title_frame, text="📦 历史版本", bg="#1565c0",
                 fg="white", font=("Arial", 18, "bold")).pack(side="left", padx=20, pady=10)
        tk.Label(title_frame, text="所有发布过的版本, 点选后复制下载链接或直接打开下载",
                 bg="#1565c0", fg="#bbdefb", font=("Arial", 10)).pack(side="left", padx=10)

        # 版本列表
        mid = tk.Frame(f)
        mid.pack(fill="both", expand=True, padx=10, pady=6)
        tree_frame = ttk.Frame(mid)
        tree_frame.pack(fill="both", expand=True)
        cols = ("version", "desc")
        self.history_tree = ttk.Treeview(tree_frame, columns=cols, show="headings")
        self.history_tree.heading("version", text="版本")
        self.history_tree.heading("desc", text="更新说明")
        self.history_tree.column("version", width=140, anchor="w")
        self.history_tree.column("desc", width=520, anchor="w")
        h_sb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.history_tree.yview)
        self.history_tree.configure(yscrollcommand=h_sb.set)
        self.history_tree.pack(side="left", fill="both", expand=True)
        h_sb.pack(side="right", fill="y")
        self.history_tree.bind("<<TreeviewSelect>>", self._on_history_select)

        # 填充版本数据
        self._history_items = []
        for v in version.HISTORY_VERSIONS:
            item_id = self.history_tree.insert("", "end", values=(v["title"], v["desc"]))
            self._history_items.append((item_id, v))

        # 当前选中版本详情(底部)
        detail_frame = ttk.LabelFrame(f, text=" 选中版本 ", padx=8, pady=4)
        detail_frame.pack(fill="x", padx=10, pady=4)
        self.history_detail = tk.Label(detail_frame, text="(在上方选择一个版本)",
                                       fg="#555", anchor="w", justify="left", wraplength=820)
        self.history_detail.pack(fill="x")

        # 底部按钮
        btn_frame = ttk.Frame(f)
        btn_frame.pack(fill="x", padx=10, pady=6)
        ttk.Button(btn_frame, text="📋 复制下载链接",
                   command=self._copy_history_download).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="🌐 打开下载",
                   command=self._open_history_download).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="📋 复制官网链接",
                   command=self._copy_website_url).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="🌐 打开官网",
                   command=self._open_website).pack(side="left", padx=5)
        ttk.Label(btn_frame, text="提示: 如无法直连下载, 请先开启加速器(如 Watt Toolkit)",
                  foreground="#888").pack(side="left", padx=14)

    def _on_history_select(self, event=None):
        """选中版本后显示详情"""
        sel = self.history_tree.selection()
        if not sel:
            return
        item_id = sel[0]
        for iid, v in self._history_items:
            if iid == item_id:
                self._current_history = v
                self.history_detail.config(
                    text="{} | 下载地址: {}\\n{}".format(v["title"], v["url"], v["desc"]))
                return

    def _selected_history(self):
        """返回当前选中版本 dict, 没有则返回 None"""
        if hasattr(self, "_current_history"):
            return self._current_history
        sel = self.history_tree.selection()
        if sel:
            for iid, v in self._history_items:
                if iid == sel[0]:
                    return v
        return None

    def _copy_history_download(self):
        """复制选中版本的下载链接到剪贴板"""
        v = self._selected_history()
        if not v:
            messagebox.showinfo("历史版本", "请先在上方选择一个版本")
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(v["url"])
        self._post("status", "已复制 " + v["title"] + " 下载链接到剪贴板")
        messagebox.showinfo("历史版本", "已复制下载链接:\\n" + v["url"])

    def _open_history_download(self):
        """用浏览器打开选中版本的下载链接"""
        v = self._selected_history()
        if not v:
            messagebox.showinfo("历史版本", "请先在上方选择一个版本")
            return
        webbrowser.open(v["url"])

    def _copy_website_url(self):
        """复制官网链接到剪贴板"""
        self.root.clipboard_clear()
        self.root.clipboard_append(version.WEBSITE_URL)
        self._post("status", "已复制官网链接到剪贴板")
        messagebox.showinfo("复制官网链接", "官网链接已复制:\\n" + version.WEBSITE_URL)

    def _open_website(self):
        """用浏览器打开官网"""
        webbrowser.open(version.WEBSITE_URL)


    # ---------------- 下载管理(断点续传) ----------------'''

if anchor in content:
    content = content.replace(anchor, addition, 1)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    ast.parse(content)
    print('历史版本页方法已添加 OK')
else:
    print('FAIL: 未找到锚点')
