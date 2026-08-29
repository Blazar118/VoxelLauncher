# -*- coding: utf-8 -*-
"""
VoxelLauncher - Java 管理模块
- 扫描本机常见 Java 安装路径
- 识别 Java 主版本(8 / 17 / 21 ...)
- 根据游戏版本推荐合适的 Java(1.16 及以下用 8, 1.17-1.20.4 用 17, 1.20.5+ 用 21)
- 手动浏览选择 javaw.exe / java.exe
"""
import os
import re
import subprocess
from pathlib import Path

from config import CONFIG


# ---------------------------------------------------------------
# 常见 Java 安装位置(Windows 优先)
# ---------------------------------------------------------------
def common_java_roots():
    roots = []
    java_home = os.environ.get("JAVA_HOME")
    if java_home:
        roots.append(Path(java_home))

    program_files = os.environ.get("ProgramFiles", r"C:\Program Files")
    program_files_x86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
    local_appdata = os.environ.get("LOCALAPPDATA",
                                   str(Path.home() / "AppData" / "Local"))
    user_home = Path.home()

    roots += [
        Path(program_files) / "Java",
        Path(program_files) / "Eclipse Adoptium",
        Path(program_files) / "Microsoft",
        Path(program_files) / "Zulu",
        Path(program_files) / "Amazon Corretto",
        Path(program_files) / "Android" / "Android Studio" / "jbr",
        Path(program_files) / "JetBrains",
        Path(program_files_x86) / "Java",
        Path(local_appdata) / "Programs",
        Path(local_appdata) / "JetBrains",
        user_home / ".jdks",
        user_home / "scoop" / "apps",
    ]
    return roots


def find_java_exes(root):
    """在某个根目录下递归查找 java.exe / javaw.exe"""
    found = []
    try:
        if root.name.lower() == "javaw.exe" or root.name.lower() == "java.exe":
            return [root]
        if not root.exists():
            return []
        # 目录内查找
        for p in root.rglob("java.exe"):
            found.append(p)
        for p in root.rglob("javaw.exe"):
            found.append(p)
    except OSError:
        pass
    return found


def scan_java():
    """扫描全机 Java, 返回去重后的 java.exe 路径列表(含 javaw.exe 同目录)"""
    results = []
    seen = set()
    for root in common_java_roots():
        for exe in find_java_exes(root):
            if exe not in seen:
                seen.add(exe)
                results.append(exe)
    # PATH 里的 java
    try:
        which = subprocess.run(["where", "java"], capture_output=True, text=True,
                               timeout=10).stdout.strip().splitlines()
        for line in which:
            if line.strip():
                p = Path(line.strip())
                if p.exists() and p not in seen:
                    seen.add(p)
                    results.append(p)
    except Exception:
        pass
    return results


# ---------------------------------------------------------------
# Java 版本识别
# ---------------------------------------------------------------
def read_java_version(java_exe):
    """
    识别 Java 主版本号。
    优先读同目录 release 文件(快), 失败则运行 java -version(慢但可靠)。
    返回 int, 失败返回 None。
    """
    java_exe = Path(java_exe)
    home = java_exe.parent.parent if java_exe.name.lower() == "java.exe" \
        else java_exe.parent.parent

    # release 文件
    release = home / "release"
    if release.exists():
        try:
            text = release.read_text(encoding="utf-8", errors="ignore")
            m = re.search(r'JAVA_VERSION="([0-9]+)', text)
            if m:
                return int(m.group(1))
        except OSError:
            pass

    # 运行 java -version
    try:
        proc = subprocess.run([str(java_exe), "-version"],
                              capture_output=True, text=True, timeout=15)
        out = proc.stderr + proc.stdout
        # 形如: openjdk version "17.0.9" 或 java version "1.8.0_391"
        m = re.search(r'version "([0-9]+)', out)
        if m:
            ver = int(m.group(1))
            return 8 if ver == 1 else ver  # 1.8 -> 8
    except Exception:
        pass
    return None


def java_family(major):
    """把主版本归入启动器可识别档位: 8 / 16 / 17 / 21 / other"""
    if major is None:
        return "unknown"
    if major == 8:
        return 8
    if major == 16:
        return 16
    if major == 17:
        return 17
    if major == 21:
        return 21
    return major


def recommend_java_major(game_version):
    """
    根据游戏版本推荐 Java 主版本:
    - 1.16 及以下          -> 8
    - 1.17 - 1.20.4        -> 17
    - 1.20.5 及以上(含新命名 24/25/26) -> 21
    """
    if not game_version:
        return 17
    m = re.match(r"(\d+)\.(\d+)(?:\.(\d+))?", game_version)
    if not m:
        return 17
    major = int(m.group(1))
    minor = int(m.group(2))
    patch = int(m.group(3)) if m.group(3) else 0
    if major == 1:
        if minor <= 16:
            return 8
        if minor <= 19:
            return 17
        if minor == 20:
            return 17 if patch <= 4 else 21
        return 21
    # 新命名版本(24.x / 25.x / 26.x ...)统一要求 Java 21+
    return 21


def find_suitable_java(game_version, java_paths=None):
    """
    找一个适合该游戏版本的 java.exe 路径, 找不到返回 None。
    """
    if java_paths is None:
        java_paths = CONFIG.get("java_paths", [])
    want = recommend_java_major(game_version)
    fallback = None
    for p in java_paths:
        major = read_java_version(p)
        fam = java_family(major)
        if fam == want:
            return p
        if fam != "unknown" and fallback is None:
            fallback = p
    return fallback


def ensure_console_java(java_path):
    """
    若用户选了 javaw.exe, 同目录存在 java.exe 时优先返回 java.exe,
    否则无法在控制台捕获日志。
    """
    p = Path(java_path)
    if p.name.lower() == "javaw.exe":
        alt = p.parent / "java.exe"
        if alt.exists():
            return str(alt)
    return str(p)
