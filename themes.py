# -*- coding: utf-8 -*-
"""
VoxelLauncher - 壁纸/主题模块
内置多套预设主题: 默认/深邃星空/苦力怕绿/末地紫/烈焰橙/水下蓝
每套主题含:
  - 主背景色 (canvas/窗口底色)
  - 强调色 (按钮/进度条)
  - 可选壁纸生成函数 (生成纯色渐变/纹理背景)
"""
import os

THEMES = {
    "default": {
        "name": "默认",
        "bg": "#f0f0f0",
        "accent": "#2b6cb0",
        "desc": "经典浅色",
    },
    "deepspace": {
        "name": "深邃星空",
        "bg": "#0f0f1a",
        "accent": "#38bdf8",
        "desc": "深蓝星空",
    },
    "creeper": {
        "name": "苦力怕绿",
        "bg": "#0f1a12",
        "accent": "#4ade80",
        "desc": "苦力怕专属绿",
    },
    "end": {
        "name": "末地紫",
        "bg": "#160f1a",
        "accent": "#a855f7",
        "desc": "末影之地紫",
    },
    "blaze": {
        "name": "烈焰橙",
        "bg": "#1a0f0a",
        "accent": "#fb923c",
        "desc": "下界烈焰橙",
    },
    "ocean": {
        "name": "水下蓝",
        "bg": "#0a1626",
        "accent": "#22d3ee",
        "desc": "深海蓝",
    },
    "cyber": {
        "name": "科技暗色",
        "bg": "#0a0e1a",
        "accent": "#22d3ee",
        "desc": "暗色毛玻璃 · 科技发光",
    },
}


def get_theme(name="default"):
    """获取主题配置"""
    return THEMES.get(name, THEMES["default"])


def list_theme_names():
    """返回主题 key 列表"""
    return list(THEMES.keys())


def generate_wallpaper(theme_key, width=1600, height=900, out_dir=None):
    """
    为指定主题生成一张渐变壁纸 PNG。
    返回生成的文件路径。
    """
    theme = get_theme(theme_key)
    bg = theme["bg"]
    accent = theme["accent"]

    # 把 #rrggbb 转成 (r,g,b)
    def _hex(c):
        c = c.lstrip("#")
        return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))

    bg_rgb = _hex(bg)
    acc_rgb = _hex(accent)

    try:
        from PIL import Image, ImageDraw
    except Exception:
        return None

    img = Image.new("RGB", (width, height), bg_rgb)
    draw = ImageDraw.Draw(img)

    # 画对角线渐变 (从左上角 accent 渐隐到 bg)
    steps = 100
    for i in range(steps):
        alpha = i / steps
        color = tuple(int(bg_rgb[k] + (acc_rgb[k] - bg_rgb[k]) * (1 - alpha))
                      for k in range(3))
        # 画一条从左上到右下的斜带
        y0 = int(height * (1 - alpha))
        draw.line([(0, y0), (width, y0)], fill=color, width=int(height / steps) + 1)

    # 加一些方块纹理点缀 (MC 风格)
    import random
    rnd = random.Random(hash(theme_key) & 0xffff)
    for _ in range(40):
        x = rnd.randint(0, width - 60)
        y = rnd.randint(0, height - 60)
        s = rnd.randint(16, 48)
        a = rnd.randint(20, 60)
        overlay = Image.new("RGBA", (s, s), acc_rgb + (a,))
        img.paste(overlay, (x, y), overlay)

    if out_dir is None:
        out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               "themes")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "wallpaper_{}.png".format(theme_key))
    img.save(path, "PNG")
    return path
