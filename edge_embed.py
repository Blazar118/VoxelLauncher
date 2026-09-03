# -*- coding: utf-8 -*-
"""
EdgePlayer - 把 Edge --app 窗口嵌入 tkinter 区域, 实现在启动器内看视频/登录。
不依赖 WebView2Loader/COM 回调, 纯 Win32 SetParent 跨进程嵌入, 稳定可靠。
"""
import ctypes
import ctypes.wintypes as wt
import subprocess
import time
import os

user32 = ctypes.windll.user32

# ---------- 正确设置 argtypes/restype (64位 HWND 必须) ----------
user32.SetParent.argtypes = [wt.HWND, wt.HWND]
user32.SetParent.restype = wt.HWND
user32.MoveWindow.argtypes = [wt.HWND, ctypes.c_int, ctypes.c_int,
                              ctypes.c_int, ctypes.c_int, wt.BOOL]
user32.MoveWindow.restype = wt.BOOL
user32.GetWindowLongW.argtypes = [wt.HWND, ctypes.c_int]
user32.GetWindowLongW.restype = ctypes.c_long
user32.SetWindowLongW.argtypes = [wt.HWND, ctypes.c_int, ctypes.c_long]
user32.SetWindowLongW.restype = ctypes.c_long
user32.GetParent.argtypes = [wt.HWND]
user32.GetParent.restype = wt.HWND
user32.ShowWindow.argtypes = [wt.HWND, ctypes.c_int]
user32.ShowWindow.restype = wt.BOOL
user32.IsWindowVisible.argtypes = [wt.HWND]
user32.IsWindowVisible.restype = wt.BOOL
user32.GetWindowThreadProcessId.argtypes = [wt.HWND, ctypes.POINTER(wt.DWORD)]
user32.GetWindowThreadProcessId.restype = wt.DWORD
user32.SetWindowPos.argtypes = [wt.HWND, wt.HWND, ctypes.c_int, ctypes.c_int,
                                ctypes.c_int, ctypes.c_int, ctypes.c_uint]
user32.SetWindowPos.restype = wt.BOOL
user32.PostMessageW.argtypes = [wt.HWND, ctypes.c_uint, wt.WPARAM, wt.LPARAM]
user32.PostMessageW.restype = wt.BOOL

GWL_STYLE = -16
WS_CHILD = 0x40000000
WS_POPUP = 0x80000000
SWP_FRAMECHANGED = 0x0020
SWP_SHOWWINDOW = 0x0040
WM_CLOSE = 0x0010

DEFAULT_EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"


def _find_edge():
    cands = [
        DEFAULT_EDGE,
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        os.path.join(os.environ.get("PROGRAMFILES", ""),
                     r"Microsoft\Edge\Application\msedge.exe"),
    ]
    for c in cands:
        if os.path.exists(c):
            return c
    return None


def _find_window_by_pid(pid):
    result = []
    EnumWindowsProc = ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)

    def cb(hwnd, lparam):
        if not user32.IsWindowVisible(hwnd):
            return True
        wpid = wt.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(wpid))
        if wpid.value == pid:
            result.append(hwnd)
        return True

    user32.EnumWindows(EnumWindowsProc(cb), 0)
    return result[0] if result else None


class EdgePlayer:
    """管理一个嵌入到 tkinter 区域的 Edge 实例"""
    def __init__(self):
        self.proc = None
        self.hwnd = 0
        self.parent_hwnd = 0
        self.url = None
        self.last_error = None
        self._user_data = os.path.join(
            os.environ.get("LOCALAPPDATA", ""), "VoxelLauncherEdge")

    @property
    def available(self):
        return _find_edge() is not None

    def play(self, parent_hwnd, url, w=800, h=450):
        """启动 Edge --app 并嵌入到 parent_hwnd 内。若已有实例则先关旧的。"""
        if self.proc is not None or self.hwnd:
            self.close()
        edge = _find_edge()
        if not edge:
            self.last_error = "未找到 Edge 浏览器"
            return False
        self.parent_hwnd = parent_hwnd
        self.url = url
        try:
            user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
        except Exception:
            pass
        try:
            self.proc = subprocess.Popen(
                [edge, "--app=" + url,
                 "--window-size=%d,%d" % (max(w, 300), max(h, 200)),
                 "--no-first-run", "--no-default-browser-check",
                 "--disable-features=msEdgeSidebarV2",
                 "--user-data-dir=" + self._user_data],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as e:
            self.last_error = "启动 Edge 失败: " + str(e)
            return False
        # 等窗口出现
        hwnd = None
        for _ in range(60):
            time.sleep(0.2)
            hwnd = _find_window_by_pid(self.proc.pid)
            if hwnd:
                break
        if not hwnd:
            self.last_error = "Edge 窗口未出现"
            self.close()
            return False
        self.hwnd = hwnd
        # 设 WS_CHILD + SetParent + 定位
        style = user32.GetWindowLongW(hwnd, GWL_STYLE)
        if not (style & WS_CHILD):
            style |= WS_CHILD
            style &= ~WS_POPUP
            user32.SetWindowLongW(hwnd, GWL_STYLE, style)
        user32.SetParent(hwnd, parent_hwnd)
        user32.SetWindowPos(hwnd, 0, 0, 0, max(w, 100), max(h, 100),
                            SWP_FRAMECHANGED | SWP_SHOWWINDOW)
        user32.MoveWindow(hwnd, 0, 0, max(w, 100), max(h, 100), True)
        user32.ShowWindow(hwnd, 5)
        time.sleep(0.3)
        return True

    def resize(self, w, h):
        """跟随宿主控件尺寸"""
        if self.hwnd:
            user32.MoveWindow(self.hwnd, 0, 0,
                              max(int(w), 100), max(int(h), 100), True)

    def is_alive(self):
        if self.proc is None or not self.hwnd:
            return False
        try:
            return self.proc.poll() is None
        except Exception:
            return False

    def close(self):
        if self.hwnd:
            try:
                user32.PostMessageW(self.hwnd, WM_CLOSE, 0, 0)
            except Exception:
                pass
        if self.proc is not None:
            try:
                self.proc.terminate()
            except Exception:
                pass
            try:
                self.proc.wait(timeout=3)
            except Exception:
                try:
                    self.proc.kill()
                except Exception:
                    pass
        self.proc = None
        self.hwnd = 0


if __name__ == "__main__":
    import tkinter as tk

    root = tk.Tk()
    root.geometry("1000x650")
    root.title("EdgePlayer 测试")
    frame = tk.Frame(root, bg="#222", width=900, height=500)
    frame.pack(expand=True, fill="both", padx=10, pady=10)
    info = tk.Label(root, text="启动...")
    info.pack()
    player = EdgePlayer()

    def do():
        ok = player.play(frame.winfo_id(),
                         "https://www.bilibili.com", 900, 500)
        info.config(text="✅ 已嵌入" if ok else "❌ " + str(player.last_error))
        print("✅ 已嵌入" if ok else "❌ " + str(player.last_error))

        def on_resize(_e=None):
            try:
                player.resize(frame.winfo_width(), frame.winfo_height())
            except Exception:
                pass
        frame.bind("<Configure>", on_resize)

    root.after(500, do)
    root.after(18000, root.quit)
    root.mainloop()
    player.close()
