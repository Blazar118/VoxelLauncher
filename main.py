# -*- coding: utf-8 -*-
"""
VoxelLauncher - 程序入口
用法: python main.py
"""
import os
import sys


def _setup_frozen_env():
    """PyInstaller 打包后需要把解压目录加入 sys.path 以找到模块"""
    if getattr(sys, "frozen", False):
        base = sys._MEIPASS  # noqa: SLF001  PyInstaller 解压目录
        if base not in sys.path:
            sys.path.insert(0, base)
        os.chdir(os.path.dirname(sys.executable))


def main():
    _setup_frozen_env()
    import ai_chat  # noqa: F401  确保打包时包含
    import ui_main
    ui_main.main()


if __name__ == "__main__":
    main()
