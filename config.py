# -*- coding: utf-8 -*-
"""
VoxelLauncher - 全局配置模块
负责应用配置(游戏目录/下载源/账号/Java/内存等)的读写持久化。
配置文件存放在 %APPDATA%/VoxelLauncher/config.json
"""
import json
import os
from pathlib import Path

# 应用数据目录(Windows 推荐放到 APPDATA)
APP_DIR = Path(os.environ.get("APPDATA", str(Path.home()))) / "VoxelLauncher"
CONFIG_FILE = APP_DIR / "config.json"

# 默认游戏目录(与官方一致)
DEFAULT_GAME_DIR = str(Path.home() / ".minecraft")

# 默认配置项
DEFAULTS = {
    "game_dir": DEFAULT_GAME_DIR,          # 游戏根目录(.minecraft)
    "download_source": "mojang",           # 下载源: "mojang"(官方) / "bmclapi"(BMCLAPI镜像)
    "download_threads": 10,                # 多线程下载线程数(1~50)
    "background_image": None,              # 自定义背景图片路径
    "accounts": [],                        # 账号列表
    "default_account": None,               # 默认账号(存账号的索引或唯一标识)
    "java_paths": [],                      # 已扫描到的 Java 路径列表
    "default_java": None,                  # 默认 Java 路径
    "min_memory": 1024,                    # 最小内存(MB)
    "max_memory": 2048,                    # 最大内存(MB)
    "extra_jvm_args": "",                  # 附加 JVM 参数
    "width": 854,                          # 游戏分辨率宽
    "height": 480,                         # 游戏分辨率高
    "window_geometry": None,               # 主窗口位置(可选)
    "proxy": "",                          # 手动代理地址(如 http://127.0.0.1:7890), 留空自动探测
}


class Config:
    """简单的 JSON 配置读写封装"""

    def __init__(self, path=None):
        self.path = Path(path) if path else CONFIG_FILE
        self.data = dict(DEFAULTS)
        self.load()

    def load(self):
        if self.path.exists():
            try:
                raw = json.loads(self.path.read_text(encoding="utf-8"))
                if isinstance(raw, dict):
                    # 合并, 保留默认值中未出现的键
                    merged = dict(DEFAULTS)
                    merged.update(raw)
                    self.data = merged
            except Exception:
                # 配置损坏时使用默认值
                self.data = dict(DEFAULTS)

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(self.data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def get(self, key, default=None):
        if default is None:
            default = DEFAULTS.get(key)
        return self.data.get(key, default)

    def set(self, key, value):
        self.data[key] = value
        self.save()


# 全局单例
CONFIG = Config()
