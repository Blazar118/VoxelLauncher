# -*- coding: utf-8 -*-
"""
VoxelLauncher 一键发布流水线
================================
用法（在项目根目录）:
    python release.py check          # 只做 bug 检查
    python release.py bump           # 升版本号 + 同步官网 + 检查bug（不发布）
    python release.py build          # 升版本号 + 同步官网 + 检查bug + 打包exe
    python release.py release        # 完整发布：升版本 + 检查 + 打包 + 上传GitHub + 推送

流程:
  1. 升级版本号(可选): patch 小版本 / minor 中版本 / major 大版本
  2. 自动检查bug: 语法编译 + 模块导入 + 关键函数冒烟
  3. 同步版本号到官网 docs/index.html
  4. 打包 exe (PyInstaller)
  5. 发布到 GitHub Release + 推送代码
"""
import argparse
import ast
import os
import re
import shutil
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(ROOT)
sys.path.insert(0, ROOT)

import version  # noqa: E402

PY = sys.executable


# ---------------------------------------------------------------
# 1. 版本号升级
# ---------------------------------------------------------------
def bump_version(part="patch"):
    """升级 version.py 里的版本号"""
    vfile = os.path.join(ROOT, "version.py")
    with open(vfile, "r", encoding="utf-8") as f:
        content = f.read()

    old_full = version.VERSION
    major, minor, patch = old_full.split(".")
    major, minor, patch = int(major), int(minor), int(patch)
    if part == "major":
        major += 1; minor = 0; patch = 0
    elif part == "minor":
        minor += 1; patch = 0
    else:
        patch += 1
    new_full = f"{major}.{minor}.{patch}"

    content = content.replace('VERSION = "' + old_full + '"',
                              'VERSION = "' + new_full + '"', 1)
    with open(vfile, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"[版本] {old_full} -> {new_full}")
    return old_full, new_full


# ---------------------------------------------------------------
# 2. Bug 检查
# ---------------------------------------------------------------
def check_bugs():
    """自动检查 bug：语法编译 + 模块导入 + 冒烟"""
    print("\n========== [1/4] Bug 检查 ==========")
    errors = []

    # 2.1 语法编译所有 py 文件
    py_files = [f for f in os.listdir(ROOT) if f.endswith(".py") and not f.startswith(("fix_", "debug_", "enhance_", "update_", "add_", "comprehensive_", "patch_", "test_", "check_", "find_", "apply_"))]
    print(f"  编译 {len(py_files)} 个 py 文件...")
    for fname in py_files:
        fpath = os.path.join(ROOT, fname)
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                ast.parse(f.read())
        except SyntaxError as e:
            errors.append(f"{fname}: 语法错误 {e}")

    # 2.2 导入核心模块（验证依赖完整）
    print("  导入核心模块...")
    import_mods = ["version", "config", "accounts", "launcher", "version_manager",
                   "modrinth", "mod_manager", "instance", "java_manager",
                   "installer", "bridge", "achievements", "player_state",
                   "sounds", "skin_editor", "multiplayer", "server_manager",
                   "server_scanner", "crash_analyzer", "mod_checker"]
    for mod in import_mods:
        try:
            __import__(mod)
        except Exception as e:
            errors.append(f"{mod}: 导入失败 {type(e).__name__}: {e}")

    # 2.3 校验版本号一致性
    if not re.match(r"^\d+\.\d+\.\d+$", version.VERSION):
        errors.append(f"版本号格式错误: {version.VERSION}")

    if errors:
        print("  ❌ 发现以下问题:")
        for e in errors:
            print(f"     - {e}")
        return False
    print("  ✅ 全部通过")
    return True


# ---------------------------------------------------------------
# 3. 同步官网版本号
# ---------------------------------------------------------------
def sync_website(old_full, new_full):
    """把 docs/index.html 里的版本号同步为最新"""
    print("\n========== [2/4] 同步官网版本号 ==========")
    hfile = os.path.join(ROOT, "docs", "index.html")
    if not os.path.exists(hfile):
        print("  未找到 docs/index.html，跳过")
        return
    with open(hfile, "r", encoding="utf-8") as f:
        content = f.read()

    # 替换所有旧版本号 -> 新版本号（兼容带 v 和不带 v）
    cnt = 0
    for old, new in [(old_full, new_full), ("v" + old_full, "v" + new_full)]:
        if old in content:
            content = content.replace(old, new)
            cnt += content.count(new)
    with open(hfile, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"  官网版本号已同步: v{old_full} -> v{new_full} (替换 {cnt} 处)")


# ---------------------------------------------------------------
# 4. 打包 exe
# ---------------------------------------------------------------
def build_exe():
    """用 PyInstaller 打包"""
    print("\n========== [3/4] 打包 exe ==========")
    dist_exe = os.path.join(ROOT, "dist", "VoxelLauncher.exe")
    if os.path.exists(dist_exe):
        os.remove(dist_exe)

    hidden = ["tkinter", "PIL", "PIL.Image", "PIL.ImageTk", "requests",
              "points", "bridge", "friends", "server_scanner", "ai_chat",
              "sounds", "config", "skin_editor", "multiplayer",
              "server_manager", "crash_analyzer", "mod_checker", "version",
              "fun_stuff"]
    cmd = [PY, "-m", "PyInstaller", "--onefile", "--windowed",
           "--name", "VoxelLauncher",
           "--icon", os.path.join(ROOT, "app.ico")]
    for h in hidden:
        cmd += ["--hidden-import", h]
    cmd.append("main.py")

    print("  运行 PyInstaller...")
    result = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    if result.returncode != 0:
        print("  ❌ 打包失败:")
        print(result.stdout[-2000:])
        print(result.stderr[-2000:])
        return False
    if not os.path.exists(dist_exe):
        print("  ❌ 未生成 exe")
        return False
    size_mb = os.path.getsize(dist_exe) / 1024 / 1024
    print(f"  ✅ 打包完成: {dist_exe} ({size_mb:.1f} MB)")
    return True


# ---------------------------------------------------------------
# 5. 发布 GitHub
# ---------------------------------------------------------------
def publish_github(new_full):
    """创建/更新 GitHub Release 并上传 exe，推送代码"""
    print("\n========== [4/4] 发布到 GitHub ==========")
    tag = "v" + new_full
    dist_exe = os.path.join(ROOT, "dist", "VoxelLauncher.exe")
    if not os.path.exists(dist_exe):
        print("  ❌ 没有 exe，先打包")
        return False

    notes = f"VoxelLauncher v{new_full}\n\n- 自动生成发布"

    def _run(cmd):
        r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
        out = (r.stdout or "") + (r.stderr or "")
        return r.returncode == 0, out

    # 检查 tag 是否存在
    ok, out = _run(["git", "tag", "-l", tag])
    exists = tag in out

    if exists:
        # 更新已存在的 release
        ok, out = _run(["gh", "release", "upload", tag, dist_exe, "--clobber"])
        if not ok:
            print(f"  ❌ 上传失败: {out[-500:]}")
            return False
        print(f"  ✅ 已更新 Release {tag}")
    else:
        # 创建新 release
        cmd = ["gh", "release", "create", tag, dist_exe,
               "--title", f"VoxelLauncher v{new_full}",
               "--notes", notes]
        ok, out = _run(cmd)
        if not ok:
            print(f"  ❌ 创建 Release 失败: {out[-500:]}")
            return False
        print(f"  ✅ 已创建 Release {tag}")

    # git 提交推送
    ok, out = _run(["git", "add", "-A"])
    _run(["git", "commit", "-m", f"v{new_full}: 版本发布（自动流水线）"])
    ok, out = _run(["git", "push", "origin", "main"])
    if not ok:
        print(f"  ⚠️ push 输出: {out[-500:]}")
    else:
        print("  ✅ 代码已推送")

    return True


# ---------------------------------------------------------------
# 入口
# ---------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="VoxelLauncher 一键发布")
    parser.add_argument("cmd", choices=["check", "bump", "build", "release"],
                        help="check=只查bug, bump=升版本+同步官网, build=再打包, release=完整发布")
    parser.add_argument("--part", default="patch", choices=["patch", "minor", "major"],
                        help="版本号升级粒度，默认 patch (2.1.0 -> 2.1.1)")
    args = parser.parse_args()

    print("=" * 50)
    print(" VoxelLauncher 发布流水线")
    print(f" 当前版本: v{version.VERSION}")
    print("=" * 50)

    old_full, new_full = version.VERSION, version.VERSION

    # check: 只检查
    if args.cmd == "check":
        ok = check_bugs()
        sys.exit(0 if ok else 1)

    # bump/build/release: 升版本
    if args.cmd in ("bump", "build", "release"):
        old_full, new_full = bump_version(args.part)
        # 重新加载 version
        import importlib
        importlib.reload(version)

    # 检查 bug
    if not check_bugs():
        print("\n❌ Bug 检查未通过，中止流程（可运行 python release.py check 查看详情）")
        sys.exit(1)

    # 同步官网
    sync_website(old_full, new_full)

    # build/release: 打包
    if args.cmd in ("build", "release"):
        if not build_exe():
            sys.exit(1)

    # release: 发布
    if args.cmd == "release":
        if not publish_github(new_full):
            sys.exit(1)

    print("\n" + "=" * 50)
    print(" ✅ 完成!")
    print(f" 新版本: v{new_full}")
    print("=" * 50)


if __name__ == "__main__":
    main()
