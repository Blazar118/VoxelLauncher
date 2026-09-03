# -*- coding: utf-8 -*-
"""
glass_ui.py - 科技暗色 UI 组件
- enable_acrylic: Windows 10 DWM 毛玻璃(Acrylic)背景
- GlowButton: 带 hover 发光动画的按钮
- 科技暗色配色常量
"""
import ctypes
import ctypes.wintypes as wt

# ---------- DWM Acrylic 毛玻璃 ----------
ACCENT_ENABLE_BLURBEHIND = 3
ACCENT_ENABLE_ACRYLICBLURBEHIND = 4
WCA_ACCENT_POLICY = 19


class _ACCENTPOLICY(ctypes.Structure):
    _fields_ = [("AccentState", ctypes.c_uint),
                ("AccentFlags", ctypes.c_uint),
                ("GradientColor", ctypes.c_uint),
                ("AnimationId", ctypes.c_uint)]


class _WINCOMPATTRDATA(ctypes.Structure):
    _fields_ = [("Attribute", ctypes.c_int),
                ("Data", ctypes.c_void_p),
                ("SizeOfData", ctypes.c_size_t)]


def enable_acrylic(hwnd, tint_abgr=0x001A0E1A, opacity=0x8C):
    """
    给窗口启用 Acrylic 毛玻璃(Windows 10 1803+)
    hwnd: 目标窗口句柄
    tint_abgr: 底色 0xAABBGGRR
    opacity: 0~255 不透明度(越高越不透明)
    返回: bool 是否成功
    """
    try:
        accent = _ACCENTPOLICY()
        accent.AccentState = ACCENT_ENABLE_ACRYLICBLURBEHIND
        accent.AccentFlags = 2  # 绘制所有窗口(含子窗口背景)
        accent.GradientColor = (opacity << 24) | (tint_abgr & 0xFFFFFF)

        data = _WINCOMPATTRDATA()
        data.Attribute = WCA_ACCENT_POLICY
        data.Data = ctypes.cast(ctypes.pointer(accent), ctypes.c_void_p)
        data.SizeOfData = ctypes.sizeof(accent)

        fn = ctypes.windll.user32.SetWindowCompositionAttribute
        fn.argtypes = [wt.HWND, ctypes.POINTER(_WINCOMPATTRDATA)]
        fn.restype = wt.BOOL
        return bool(fn(ctypes.c_void_p(hwnd), ctypes.byref(data)))
    except Exception:
        return False


def enable_blur(hwnd):
    """启用旧式模糊(兼容性更好)"""
    try:
        accent = _ACCENTPOLICY()
        accent.AccentState = ACCENT_ENABLE_BLURBEHIND
        data = _WINCOMPATTRDATA()
        data.Attribute = WCA_ACCENT_POLICY
        data.Data = ctypes.cast(ctypes.pointer(accent), ctypes.c_void_p)
        data.SizeOfData = ctypes.sizeof(accent)
        fn = ctypes.windll.user32.SetWindowCompositionAttribute
        fn.argtypes = [wt.HWND, ctypes.POINTER(_WINCOMPATTRDATA)]
        fn.restype = wt.BOOL
        return bool(fn(ctypes.c_void_p(hwnd), ctypes.byref(data)))
    except Exception:
        return False


def disable_accent(hwnd):
    """关闭毛玻璃"""
    try:
        accent = _ACCENTPOLICY()
        accent.AccentState = 0
        data = _WINCOMPATTRDATA()
        data.Attribute = WCA_ACCENT_POLICY
        data.Data = ctypes.cast(ctypes.pointer(accent), ctypes.c_void_p)
        data.SizeOfData = ctypes.sizeof(accent)
        fn = ctypes.windll.user32.SetWindowCompositionAttribute
        fn.argtypes = [wt.HWND, ctypes.POINTER(_WINCOMPATTRDATA)]
        fn.restype = wt.BOOL
        return bool(fn(ctypes.c_void_p(hwnd), ctypes.byref(data)))
    except Exception:
        return False


# ---------- 科技暗色配色 ----------
CYBER = {
    "bg": "#0a0e1a",          # 深蓝黑底
    "bg2": "#111827",         # 次级底
    "panel": "#0f1626",       # 面板
    "accent": "#22d3ee",      # 青色主发光
    "accent2": "#38bdf8",     # 亮蓝
    "glow": "#67e8f9",        # 高亮发光
    "text": "#e2e8f0",        # 主文字
    "text_dim": "#64748b",    # 次要文字
    "danger": "#f87171",      # 危险
    "ok": "#4ade80",          # 成功
    "warn": "#fbbf24",        # 警告
}


def _hex_to_rgb(c):
    c = c.lstrip("#")
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))


def _rgb_to_hex(r, g, b):
    return "#{:02x}{:02x}{:02x}".format(
        max(0, min(255, int(r))), max(0, min(255, int(g))),
        max(0, min(255, int(b))))


class GlowButton:
    """
    发光按钮(封装 tk.Button): hover 时外发光 + 颜色渐变, 科技感。
    用 highlightbackground 模拟外发光辉光。
    """
    def __init__(self, master, text="", command=None, bg=None, fg="#e2e8f0",
                 accent=None, font=None, padx=14, pady=6, **kw):
        import tkinter as tk
        bg = bg or CYBER["bg2"]
        accent = accent or CYBER["accent"]
        self._base = bg
        self._accent = accent
        self._fg = fg
        self._step = 0
        self._anim = None
        self.btn = tk.Button(
            master, text=text, command=command, bg=bg, fg=fg,
            activebackground=bg, activeforeground=accent,
            relief="flat", bd=0, cursor="hand2",
            highlightthickness=2,
            highlightbackground=CYBER["bg"],
            highlightcolor=accent,
            font=font, padx=padx, pady=pady, **kw)
        self.btn.bind("<Enter>", self._on_enter)
        self.btn.bind("<Leave>", self._on_leave)
        self.btn._glow = self

    def _on_enter(self, _e=None):
        if self._anim:
            self.btn.after_cancel(self._anim)
        self._anim = self._animate(0)

    def _on_leave(self, _e=None):
        if self._anim:
            self.btn.after_cancel(self._anim)
        self._anim = self._animate(1)

    def _animate(self, direction):
        """direction: 0=进入(变亮), 1=离开(恢复)"""
        base_rgb = _hex_to_rgb(self._base)
        acc_rgb = _hex_to_rgb(self._accent)
        total = 10
        if direction == 0:
            self._step = min(self._step + 1, total)
        else:
            self._step = max(self._step - 1, 0)
        t = self._step / total
        # 背景从 base 向 accent 混合
        new_bg = _rgb_to_hex(
            base_rgb[0] + (acc_rgb[0] - base_rgb[0]) * t * 0.6,
            base_rgb[1] + (acc_rgb[1] - base_rgb[1]) * t * 0.6,
            base_rgb[2] + (acc_rgb[2] - base_rgb[2]) * t * 0.6)
        # 外发光: 边框颜色从 bg 向 glow 过渡
        glow_rgb = _hex_to_rgb(CYBER["glow"])
        frame = _rgb_to_hex(
            base_rgb[0] + (glow_rgb[0] - base_rgb[0]) * t,
            base_rgb[1] + (glow_rgb[1] - base_rgb[1]) * t,
            base_rgb[2] + (glow_rgb[2] - base_rgb[2]) * t)
        try:
            self.btn.config(bg=new_bg, highlightbackground=frame)
        except Exception:
            pass
        if self._step > 0 and self._step < total:
            self._anim = self.btn.after(16, lambda: self._animate(direction))
        else:
            self._anim = None


if __name__ == "__main__":
    import tkinter as tk
    root = tk.Tk()
    root.geometry("520x320")
    root.title("科技暗色 UI 测试")
    hwnd = root.winfo_id()
    # 启用毛玻璃
    ok = enable_acrylic(hwnd)
    print("Acrylic 毛玻璃:", "✅ 已启用" if ok else "❌ 失败(可能非Win10 1803+)")
    # 窗口半透明(让模糊透出)
    try:
        root.attributes("-alpha", 0.94)
    except Exception:
        pass

    frame = tk.Frame(root, bg="#0a0e1a")
    frame.pack(fill="both", expand=True, padx=24, pady=24)
    tk.Label(frame, text="🌌 科技暗色 · 毛玻璃 + 发光", bg="#0a0e1a",
             fg="#e2e8f0", font=("Arial", 16, "bold")).pack(pady=10)

    gb1 = GlowButton(frame, text="🚀 启动游戏", command=lambda: print("启动!"),
                     accent="#22d3ee", font=("Arial", 11, "bold"))
    gb1.btn.pack(pady=8)
    gb2 = GlowButton(frame, text="🧪 测试发光", accent="#a855f7",
                     font=("Arial", 11))
    gb2.btn.pack(pady=8)

    root.after(8000, root.quit)
    root.mainloop()
