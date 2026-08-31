# -*- coding: utf-8 -*-
"""给开服器页面添加外网IP显示和复制按钮"""
import re

filepath = r'C:\Users\bllaa\Doubao\chats\2026-08-28\new-chat\VoxelLauncher\ui_main.py'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# ========== 1. 在 _start_server 方法中添加外网IP显示 ==========
old_start = '''            ip = self._server_inst.get_local_ip()
            port = self._server_inst.get_port()
            self.server_info_label.config(
                text="运行中 | 局域网地址: {}:{}".format(ip, port),
                foreground="green")
            self._append_server_log("服务器启动中...")'''

new_start = '''            ip = self._server_inst.get_local_ip()
            port = self._server_inst.get_port()
            self._server_port = port
            self._server_local_ip = ip
            # 异步获取外网IP
            self._fetch_public_ip()
            self.server_info_label.config(
                text="运行中 | 本机: {}:{} | 外网: 获取中...".format(ip, port),
                foreground="green")
            self._append_server_log("服务器启动中...")
            self._append_server_log("本机连接地址: {}:{}".format(ip, port))'''

if old_start in content:
    content = content.replace(old_start, new_start, 1)
    print("1. _start_server 已更新")
else:
    print("1. 未找到 _start_server 中的旧代码")

# ========== 2. 在连接信息旁边加复制按钮 ==========
old_info = '''        # 连接信息
        self.server_info_label = ttk.Label(ctrl_frame, text="未运行", foreground="#666")
        self.server_info_label.pack(side="left", padx=20)'''

new_info = '''        # 连接信息
        info_frame = ttk.Frame(ctrl_frame)
        info_frame.pack(side="left", padx=20)
        self.server_info_label = ttk.Label(info_frame, text="未运行", foreground="#666")
        self.server_info_label.pack(side="left")
        ttk.Button(info_frame, text="📋 复制本机", command=self._copy_local_addr).pack(side="left", padx=5)
        ttk.Button(info_frame, text="🌐 复制外网", command=self._copy_public_addr).pack(side="left", padx=2)'''

if old_info in content:
    content = content.replace(old_info, new_info, 1)
    print("2. 复制按钮已添加")
else:
    print("2. 未找到连接信息代码")

# ========== 3. 添加新方法（在 main() 之前） ==========
main_pos = content.find('\ndef main():')
if main_pos == -1:
    main_pos = content.find('def main():')

new_methods = '''
    # ================================================================
    # 服务器连接地址相关
    # ================================================================
    def _get_public_ip(self):
        """获取外网IP"""
        try:
            import requests
            resp = requests.get("https://api.ipify.org", timeout=5)
            return resp.text.strip()
        except Exception:
            try:
                import requests
                resp = requests.get("https://ifconfig.me/ip", timeout=5)
                return resp.text.strip()
            except Exception:
                return None

    def _fetch_public_ip(self):
        """异步获取外网IP并更新显示"""
        def worker():
            try:
                pub_ip = self._get_public_ip()
                self.root.after(0, lambda: self._update_public_ip(pub_ip))
            except Exception:
                self.root.after(0, lambda: self._update_public_ip(None))
        import threading
        threading.Thread(target=worker, daemon=True).start()

    def _update_public_ip(self, pub_ip):
        """更新外网IP显示"""
        if pub_ip:
            self._server_public_ip = pub_ip
            port = getattr(self, '_server_port', '25565')
            local_ip = getattr(self, '_server_local_ip', '127.0.0.1')
            self.server_info_label.config(
                text="运行中 | 本机: {}:{} | 外网: {}:{}".format(local_ip, port, pub_ip, port),
                foreground="green")
            self._append_server_log("外网连接地址: {}:{}".format(pub_ip, port))
            self._append_server_log("注意: 外网连接需要路由器端口映射或内网穿透")
        else:
            self._server_public_ip = None
            port = getattr(self, '_server_port', '25565')
            local_ip = getattr(self, '_server_local_ip', '127.0.0.1')
            self.server_info_label.config(
                text="运行中 | 本机: {}:{} | 外网: 获取失败".format(local_ip, port),
                foreground="#cc8800")

    def _copy_local_addr(self):
        """复制本机地址"""
        ip = getattr(self, '_server_local_ip', None)
        port = getattr(self, '_server_port', '25565')
        if ip:
            addr = "{}:{}".format(ip, port)
            self.root.clipboard_clear()
            self.root.clipboard_append(addr)
            self._append_server_log("已复制本机地址: " + addr)
        else:
            messagebox.showinfo("提示", "服务器未启动")

    def _copy_public_addr(self):
        """复制外网地址"""
        ip = getattr(self, '_server_public_ip', None)
        port = getattr(self, '_server_port', '25565')
        if ip:
            addr = "{}:{}".format(ip, port)
            self.root.clipboard_clear()
            self.root.clipboard_append(addr)
            self._append_server_log("已复制外网地址: " + addr)
        else:
            messagebox.showinfo("提示", "外网IP未获取到，请检查网络")

'''

content = content[:main_pos] + new_methods + content[main_pos:]
print("3. 新方法已添加")

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

import ast
ast.parse(content)
print("语法OK")
print("完成!")
