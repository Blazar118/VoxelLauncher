# -*- coding: utf-8 -*-
"""给ui_main.py添加新功能: 强大崩溃分析、模组冲突检查、FPS显示、一键联机"""
import re

filepath = r'C:\Users\bllaa\Doubao\chats\2026-08-28\new-chat\VoxelLauncher\ui_main.py'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# ========== 1. 在 main() 函数之前添加新方法 ==========
# 找到 "def main():" 的位置
main_pos = content.find('\ndef main():')
if main_pos == -1:
    main_pos = content.find('def main():')

new_methods = '''
    # ================================================================
    # 强大崩溃分析 (使用 crash_analyzer 模块)
    # ================================================================
    def _analyze_crash_advanced(self):
        """强大的崩溃日志分析"""
        sel = self.crash_log_listbox.curselection()
        if not sel:
            messagebox.showinfo("提示", "请先选择一个崩溃日志")
            return
        game_dir = self._get_tools_instance_dir()
        if not game_dir:
            return
        item = self.crash_log_listbox.get(sel[0])
        if item.startswith("("):
            return
        log_name = item.split(" | ")[0]
        log_path = str(Path(game_dir) / "crash-reports" / log_name)

        try:
            import crash_analyzer
            analyzer = crash_analyzer.CrashAnalyzer(str(game_dir))
            result = analyzer.analyze(log_path)
        except Exception as e:
            messagebox.showerror("分析失败", str(e))
            return

        self.crash_result.delete("1.0", "end")
        self.crash_result.insert("end", "=== 🔍 智能崩溃分析 ===\\n\\n")
        self.crash_result.insert("end", "📄 日志: {}\\n".format(result["file"]))
        self.crash_result.insert("end", "⏰ 时间: {}\\n".format(result["time"]))
        if result.get("game_version"):
            self.crash_result.insert("end", "🎮 版本: {}\\n".format(result["game_version"]))
        if result.get("loader"):
            self.crash_result.insert("end", "🔧 加载器: {}\\n".format(result["loader"]))
        if result.get("java_version"):
            self.crash_result.insert("end", "☕ Java: {}\\n".format(result["java_version"]))
        self.crash_result.insert("end", "\\n")

        # 检测到的问题
        if result["causes"]:
            self.crash_result.insert("end", "⚠️  检测到 {} 个问题:\\n\\n".format(len(result["causes"])))
            for i, cause in enumerate(result["causes"], 1):
                severity_icon = "🔴" if cause["severity"] == "high" else ("🟡" if cause["severity"] == "medium" else "🟢")
                self.crash_result.insert("end", "{} 问题{}: {}\\n".format(severity_icon, i, cause["name"]))
                self.crash_result.insert("end", "   💡 建议: {}\\n\\n".format(cause["solution"]))
        else:
            self.crash_result.insert("end", "✅ 未检测到常见崩溃原因\\n\\n")

        # 可疑模组
        if result.get("suspected_mods"):
            self.crash_result.insert("end", "🔗 可疑模组 (出现在堆栈中):\\n")
            for mod in result["suspected_mods"]:
                self.crash_result.insert("end", "   - {}\\n".format(mod))
            self.crash_result.insert("end", "\\n")

        self.crash_result.insert("end", "📋 摘要: {}\\n".format(result["summary"]))

    # ================================================================
    # 强大模组冲突检查 (使用 mod_checker 模块)
    # ================================================================
    def _detect_mod_conflicts_advanced(self):
        """强大的模组冲突检查"""
        self.mod_tools_result.delete("1.0", "end")
        self.mod_tools_result.insert("end", "🔍 正在深度检测模组冲突...\\n\\n")
        self.mod_tools_result.update()

        game_dir = self._get_tools_instance_dir()
        if not game_dir:
            self.mod_tools_result.insert("end", "❌ 请先选择实例\\n")
            return

        try:
            import mod_checker
            checker = mod_checker.ModChecker(str(Path(game_dir) / "mods"))
            result = checker.check_conflicts()
        except Exception as e:
            self.mod_tools_result.insert("end", "❌ 检测失败: {}\\n".format(e))
            return

        summary = result["summary"]
        self.mod_tools_result.insert("end", "📊 检测结果:\\n")
        self.mod_tools_result.insert("end", "   总模组数: {}\\n".format(summary["total_mods"]))
        self.mod_tools_result.insert("end", "   Fabric模组: {}\\n".format(summary["fabric_mods"]))
        self.mod_tools_result.insert("end", "   Forge模组: {}\\n".format(summary["forge_mods"]))
        self.mod_tools_result.insert("end", "   无法识别: {}\\n".format(summary["unknown_mods"]))
        self.mod_tools_result.insert("end", "   🔴 严重问题: {}\\n".format(summary["errors"]))
        self.mod_tools_result.insert("end", "   🟡 警告: {}\\n".format(summary["warnings"]))
        self.mod_tools_result.insert("end", "   ℹ️  信息: {}\\n\\n".format(summary["infos"]))

        if not result["issues"]:
            self.mod_tools_result.insert("end", "✅ 未发现问题! 模组配置良好。\\n")
            return

        self.mod_tools_result.insert("end", "📝 详细问题:\\n\\n")
        for i, issue in enumerate(result["issues"], 1):
            severity_icon = "🔴" if issue["severity"] == "error" else ("🟡" if issue["severity"] == "warning" else "ℹ️")
            self.mod_tools_result.insert("end", "{} {}. {}\\n".format(severity_icon, i, issue["title"]))
            self.mod_tools_result.insert("end", "   {}\\n".format(issue["description"]))
            if issue.get("mods"):
                self.mod_tools_result.insert("end", "   涉及文件:\\n")
                for m in issue["mods"]:
                    self.mod_tools_result.insert("end", "      - {}\\n".format(m))
            self.mod_tools_result.insert("end", "   💡 解决: {}\\n\\n".format(issue["solution"]))

    # ================================================================
    # FPS 显示 (通过游戏日志或Bridge)
    # ================================================================
    def _start_fps_monitor(self):
        """启动FPS监控"""
        self._fps_monitoring = True
        self._fps_value = 0
        self._fps_last_frames = 0
        self._fps_last_time = 0
        self._fps_update_loop()

    def _stop_fps_monitor(self):
        """停止FPS监控"""
        self._fps_monitoring = False

    def _fps_update_loop(self):
        """FPS更新循环"""
        if not getattr(self, '_fps_monitoring', False):
            return
        try:
            # 尝试从游戏日志读取FPS (Minecraft 按 F3 会显示)
            # 或者通过Bridge读取
            proc = getattr(self, '_game_proc', None)
            if proc and proc.is_alive():
                # 简单估算: 游戏运行中显示一个占位FPS
                # 实际FPS需要Bridge模组配合
                if hasattr(self, '_perf_status_label'):
                    self._perf_status_label.config(
                        text="🎮 游戏运行中 | FPS: 监测中...",
                        foreground="#00aa00")
            else:
                if hasattr(self, '_perf_status_label'):
                    self._perf_status_label.config(text="游戏未运行", foreground="#999")
        except Exception:
            pass
        self.root.after(2000, self._fps_update_loop)

    # ================================================================
    # 一键创建局域网世界
    # ================================================================
    def _one_click_lan(self):
        """一键创建局域网世界并显示连接信息"""
        # 检查游戏是否在运行
        proc = getattr(self, '_game_proc', None)
        if not proc or not proc.is_alive():
            messagebox.showinfo("提示", "请先启动游戏并进入一个世界\\n然后按 ESC -> 对局域网开放")
            return

        # 获取本机IP
        try:
            import socket
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)
        except Exception:
            local_ip = "127.0.0.1"

        # 显示连接信息
        win = tk.Toplevel(self.root)
        win.title("🌐 局域网联机信息")
        win.geometry("400x300")
        win.resizable(False, False)

        tk.Label(win, text="🌐 局域网联机信息", font=("Arial", 14, "bold")).pack(pady=10)

        info_frame = ttk.LabelFrame(win, text=" 连接信息 ")
        info_frame.pack(fill="x", padx=20, pady=10)

        tk.Label(info_frame, text="本机IP:", font=("Arial", 10)).pack(anchor="w", padx=10, pady=5)
        ip_entry = ttk.Entry(info_frame, font=("Consolas", 12))
        ip_entry.insert(0, local_ip)
        ip_entry.pack(fill="x", padx=10, pady=2)
        ip_entry.config(state="readonly")

        tk.Label(info_frame, text="端口号 (游戏里显示):", font=("Arial", 10)).pack(anchor="w", padx=10, pady=5)
        port_entry = ttk.Entry(info_frame, font=("Consolas", 12))
        port_entry.insert(0, "25565")
        port_entry.pack(fill="x", padx=10, pady=2)

        tk.Label(info_frame, text="完整地址:", font=("Arial", 10)).pack(anchor="w", padx=10, pady=5)
        addr_entry = ttk.Entry(info_frame, font=("Consolas", 12, "bold"), foreground="#0066cc")
        addr_entry.insert(0, "{}:25565".format(local_ip))
        addr_entry.pack(fill="x", padx=10, pady=2)
        addr_entry.config(state="readonly")

        def update_addr(*args):
            addr_entry.config(state="normal")
            addr_entry.delete(0, "end")
            addr_entry.insert(0, "{}:{}".format(local_ip, port_entry.get()))
            addr_entry.config(state="readonly")
        port_entry.bind("<KeyRelease>", update_addr)

        btn_frame = tk.Frame(win)
        btn_frame.pack(pady=10)

        def copy_addr():
            self.root.clipboard_clear()
            self.root.clipboard_append(addr_entry.get())
            messagebox.showinfo("已复制", "地址已复制到剪贴板:\\n" + addr_entry.get())

        ttk.Button(btn_frame, text="📋 复制完整地址", command=copy_addr).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="📋 复制IP",
                   command=lambda: self._copy_to_clipboard(local_ip)).pack(side="left", padx=5)

        steps = tk.Label(win, text="步骤:\\n1. 游戏里按 ESC -> 对局域网开放\\n2. 记住左下角显示的端口号\\n3. 把上面的完整地址发给朋友\\n4. 朋友在多人游戏里添加这个地址",
                        justify="left", font=("Arial", 9), foreground="#666")
        steps.pack(pady=10)

'''

# 在 main() 函数之前插入新方法
content = content[:main_pos] + new_methods + content[main_pos:]

# ========== 2. 替换崩溃分析按钮的调用 ==========
old_crash_btn = 'ttk.Button(top, text="📋 分析选中日志", command=self._analyze_crash_log).pack('
new_crash_btn = 'ttk.Button(top, text="🔍 智能分析", command=self._analyze_crash_advanced).pack('
if old_crash_btn in content:
    content = content.replace(old_crash_btn, new_crash_btn, 1)
    print("2. 崩溃分析按钮已升级")
else:
    print("2. 未找到崩溃分析按钮")

# ========== 3. 替换模组冲突检测按钮的调用 ==========
old_mod_btn = 'ttk.Button(bar, text="⚠ 冲突检测", command=self._detect_mod_conflicts).pack('
new_mod_btn = 'tttk.Button(bar, text="🔍 深度冲突检测", command=self._detect_mod_conflicts_advanced).pack('
# 修正拼写
new_mod_btn = 'ttk.Button(bar, text="🔍 深度冲突检测", command=self._detect_mod_conflicts_advanced).pack('
if old_mod_btn in content:
    content = content.replace(old_mod_btn, new_mod_btn, 1)
    print("3. 模组冲突检测按钮已升级")
else:
    print("3. 未找到模组冲突检测按钮")

# ========== 4. 在性能监控页面加FPS显示 ==========
old_perf_hint = 'ttk.Label(content, text="提示: FPS 数据需要游戏内 Mod 支持, 这里显示进程级别的性能数据",'
new_perf_hint = '''# FPS显示
        self._fps_label = ttk.Label(content, text="🎮 FPS: -- (需游戏联动Mod)",
                                     font=("Arial", 11, "bold"), foreground="#ff8800")
        self._fps_label.pack(pady=5)
        ttk.Button(content, text="▶ 启动FPS监控",
                   command=self._start_fps_monitor).pack(pady=5)
        ttk.Label(content, text="提示: FPS数据需要游戏联动Mod支持, 或按F3查看",
'''
if old_perf_hint in content:
    content = content.replace(old_perf_hint, new_perf_hint, 1)
    print("4. FPS显示已添加")
else:
    print("4. 未找到性能监控提示位置")

# ========== 5. 在联机页面加一键局域网按钮 ==========
old_join_btn = 'ttk.Button(toolbar, text="🎮 加入选中服务器",'
new_join_btn = '''ttk.Button(toolbar, text="🌐 一键局域网",
                   command=self._one_click_lan).pack(side="left", padx=2)
        ttk.Button(toolbar, text="🎮 加入选中服务器",'''
if old_join_btn in content:
    content = content.replace(old_join_btn, new_join_btn, 1)
    print("5. 一键局域网按钮已添加")
else:
    print("5. 未找到加入服务器按钮位置")

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

import ast
ast.parse(content)
print("语法OK")
print("完成!")
