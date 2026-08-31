# -*- coding: utf-8 -*-
"""
VoxelLauncher - 启动核心模块
- 完整解析 version.json, 拼接 Java 启动命令
- 处理 native 库解压
- 启动前文件完整性校验
- 子进程启动 Minecraft, 捕获 stdout/stderr 实时输出
"""
import json
import os
import shutil
import subprocess
import threading
import zipfile
from pathlib import Path

from config import CONFIG
import java_manager
import version
import version_manager

LAUNCHER_NAME = "VoxelLauncher"
LAUNCHER_VERSION = version.VERSION  # 与 version.py 统一


# ---------------------------------------------------------------
# 参数替换
# ---------------------------------------------------------------
def _tokens(instance, account, version_id, version_data, classpath,
            natives_dir, assets_root, assets_index, mc_root, game_dir):
    cfg = dict(CONFIG.data)
    return {
        "auth_player_name": account.get("name", "Steve"),
        "auth_uuid": account.get("uuid", ""),
        "auth_access_token": account.get("access_token", "0"),
        "auth_session": account.get("access_token", "0"),
        "user_type": account.get("user_type", "legacy"),
        "version_name": version_id,
        "version_type": version_data.get("type", "release"),
        "game_directory": str(game_dir),
        "assets_root": str(assets_root),
        "assets_index_name": assets_index,
        "natives_directory": str(natives_dir),
        "classpath": classpath,
        "classpath_separator": os.pathsep,
        "launcher_name": LAUNCHER_NAME,
        "launcher_version": LAUNCHER_VERSION,
        "library_directory": str(mc_root / "libraries"),
        "resolution_width": instance.get("width") or cfg.get("width") or 854,
        "resolution_height": instance.get("height") or cfg.get("height") or 480,
        "clientid": account.get("clientid") or "",
        "auth_xuid": account.get("xuid") or "0",
    }


def substitute(text, tokens):
    out = text
    for k, v in tokens.items():
        out = out.replace("${" + k + "}", str(v))
    return out


# ---------------------------------------------------------------
# Native 解压
# ---------------------------------------------------------------
def extract_natives(mc_root, native_artifacts, natives_dir):
    """把 native jar 里的 dll/so/dylib 解压到 natives_dir"""
    natives_dir = Path(natives_dir)
    natives_dir.mkdir(parents=True, exist_ok=True)
    for ca in native_artifacts:
        jar = Path(mc_root) / "libraries" / ca["path"]
        if not jar.exists():
            continue
        try:
            with zipfile.ZipFile(jar) as zf:
                for name in zf.namelist():
                    base = os.path.basename(name)
                    if not base:
                        continue
                    if base.lower().endswith((".dll", ".so", ".dylib")):
                        # 防止路径穿越
                        target = natives_dir / base
                        with zf.open(name) as src, open(target, "wb") as dst:
                            shutil.copyfileobj(src, dst)
        except (zipfile.BadZipFile, OSError):
            continue
    return natives_dir


# ---------------------------------------------------------------
# 启动命令构建
# ---------------------------------------------------------------
def _optimized_jvm_args():
    """
    默认 JVM 优化参数列表(兼容 Java 8 ~ Java 21)。
    目标: 加快启动速度、降低 GC 卡顿、减少 IO 开销。
    用户可在自定义参数中用 -XX:-XXX 关闭某项。
    """
    return [
        # --- GC 优化: G1 回收器 + 低暂停 ---
        "-XX:+UseG1GC",              # G1 垃圾回收器(Java9+默认,显式指定兼容Java8)
        "-XX:+ParallelRefProcEnabled",  # 并行引用处理,减少GC停顿
        "-XX:MaxGCPauseMillis=200",  # 最大GC暂停目标200ms
        "-XX:+UnlockExperimentalVMOptions",  # 解锁实验性选项(部分G1参数需要)
        "-XX:+DisableExplicitGC",     # 禁用System.gc()显式回收,避免卡顿
        "-XX:G1NewSizePercent=20",    # G1新生代初始比例20%,加快启动
        "-XX:G1ReservePercent=20",    # G1堆预留20%,减少扩容开销
        "-XX:+UseStringDeduplication", # 字符串去重,节省内存
        # --- 启动速度优化 ---
        "-XX:+PerfDisableSharedMem",   # 禁用共享内存性能计数,减少IO和文件锁
        "-Dsun.rmi.dgc.server.gcInterval=2147483646",  # RMI服务端GC间隔拉到最大
        "-Dsun.rmi.dgc.client.gcInterval=2147483646",  # RMI客户端GC间隔拉到最大
        # --- 编码与兼容性 ---
        "-Dfile.encoding=UTF-8",       # 强制UTF-8,避免中文乱码
        "-XX:+UseCompressedOops",       # 压缩对象指针(默认开启,显式指定省内存)
    ]


def build_command(instance, account, java_path, version_data, server_address=None):
    """
    构建完整启动命令(列表形式)。
    instance: 实例 dict(含 version_id / 内存等)
    account : 账号 dict
    java_path: java.exe 绝对路径
    version_data: 解析后的 version.json
    server_address: 自动加入的服务器地址(可选), 支持 IP 或 IP:端口
    """
    mc_root = Path(CONFIG.get("game_dir"))
    version_id = instance["version_id"]
    game_dir = Path(instance["game_dir"])  # 实例目录即游戏目录(隔离)
    game_dir.mkdir(parents=True, exist_ok=True)

    version_dir = mc_root / "versions" / version_id

    # 依赖库
    cp_artifacts, native_artifacts = version_manager.collect_launch_libraries(
        version_data)
    natives_dir = game_dir / "natives"
    extract_natives(mc_root, native_artifacts, natives_dir)

    # classpath
    cp = [str(mc_root / "libraries" / a["path"]) for a in cp_artifacts]
    # 继承版本的 jar 在基础版本目录(如 fabric 继承 1.20.1)
    jar_ver = version_data.get("_jar_version") or version_id
    cp.append(str(mc_root / "versions" / jar_ver / (jar_ver + ".jar")))
    classpath = os.pathsep.join(cp)

    # assets
    assets_root = mc_root / "assets"
    assets_index = version_data.get("assets") or \
        (version_data.get("assetIndex") or {}).get("id", "legacy")

    tokens = _tokens(instance, account, version_id, version_data, classpath,
                     natives_dir, assets_root, assets_index, mc_root, game_dir)

    # 主类
    main_class = version_data.get("mainClass", "")

    # 参数
    if "arguments" in version_data:
        jvm_args = [a for a in version_data["arguments"].get("jvm", [])
                    if isinstance(a, str)]
        game_args = [a for a in version_data["arguments"].get("game", [])
                     if isinstance(a, str)]
        # log4j 配置模板处理: 无配置时不注入该参数
        jvm_args = _handle_log4j(jvm_args, version_data, mc_root)
    else:
        # 旧版(1.12-)
        game_args = version_data.get("minecraftArguments", "").split()
        jvm_args = ["-Djava.library.path=${natives_directory}",
                    "-cp", "${classpath}"]

    # 兜底: 无论参数来自哪里, 必须保证存在类路径与 native 目录。
    # (Fabric/Quilt 继承版本的子参数可能挤掉父版本的 -cp, 缺失会导致
    #  ClassNotFoundException / UnsatisfiedLinkError)
    jvm_joined = " ".join(jvm_args)
    if "${classpath}" not in jvm_joined:
        jvm_args += ["-cp", "${classpath}"]
    if "${natives_directory}" not in jvm_joined:
        jvm_args.append("-Djava.library.path=${natives_directory}")

    # 用户自定义 JVM 参数
    extra = instance.get("extra_jvm_args") or ""
    custom_jvm = extra.split() if isinstance(extra, str) else []

    # 自动加入服务器参数(必须放在游戏参数中, 主类之后)
    server_args = []
    if server_address:
        # Minecraft 1.20+ 使用 Quick Play 参数, 旧的 --server 会被忽略
        # 格式: --quickPlayMultiplayer <ip:port>
        server_args = ["--quickPlayMultiplayer", server_address]

    # 组装
    cmd = [java_path]
    cmd.append("-Xms{}M".format(instance.get("min_memory") or 512))
    cmd.append("-Xmx{}M".format(instance.get("max_memory") or 2048))
    # 默认优化参数(在用户自定义之前, 用户可覆盖)
    cmd += _optimized_jvm_args()
    cmd += custom_jvm
    cmd += [substitute(a, tokens) for a in jvm_args]
    if main_class:
        cmd.append(main_class)
    cmd += [substitute(a, tokens) for a in game_args]
    # 服务器参数放在最后, Minecraft 会解析
    cmd += server_args
    return cmd


def _handle_log4j(jvm_args, version_data, mc_root):
    """处理 log4j 配置模板; 无法提供配置时移除该参数"""
    result = []
    logging = version_data.get("logging", {}).get("client", {})
    config_file = logging.get("file", {})
    cfg_path = None
    if config_file:
        dest = Path(mc_root) / "assets" / "log_configs" / (
            config_file.get("id", "log4j2.xml"))
        cfg_path = str(dest)
    for arg in jvm_args:
        if "${log4j_configuration_file}" in arg:
            if cfg_path:
                result.append(arg.replace("${log4j_configuration_file}",
                                          cfg_path))
            # 无配置则跳过该参数
            continue
        result.append(arg)
    return result


# ---------------------------------------------------------------
# 启动前完整性校验
# ---------------------------------------------------------------
def verify_launch_files(instance, version_data):
    """返回问题列表(空 = 完整可启动)"""
    return version_manager.check_version_files(
        instance["version_id"], version_data)


# ---------------------------------------------------------------
# 子进程启动与日志
# ---------------------------------------------------------------
class GameProcess:
    def __init__(self, proc, log_cb, stop_cb=None):
        self.proc = proc
        self.log_cb = log_cb
        self.stop_cb = stop_cb
        self._alive = True
        self._reader = threading.Thread(target=self._pump, daemon=True)
        self._reader.start()

    def _pump(self):
        try:
            for line in iter(self.proc.stdout.readline, ""):
                if line:
                    self.log_cb(line.rstrip("\r\n"))
            self.proc.stdout.close()
        except Exception:
            pass
        self._alive = False
        if self.stop_cb:
            self.stop_cb()

    def is_alive(self):
        return self._alive

    def stop(self):
        try:
            self.proc.terminate()
        except Exception:
            pass


def launch_game(instance, account, java_path, log_cb=None, on_exit=None, server_address=None):
    """
    启动游戏。
    - 先做完整性校验, 有问题抛 RuntimeError
    - 微软账号失效自动刷新
    - server_address: 要连接的服务器地址(可选), 会自动加入游戏
    - 返回 GameProcess
    """
    import accounts

    mc_root = Path(CONFIG.get("game_dir"))
    version_id = instance["version_id"]
    vjson = mc_root / "versions" / version_id / (version_id + ".json")
    if not vjson.exists():
        raise RuntimeError("版本 {} 未安装, 请先下载".format(version_id))
    # 解析版本并合并继承链(Fabric/Quilt 继承原版)
    version_data = version_manager.resolve_version_json(version_id)

    # 完整性校验
    problems = verify_launch_files(instance, version_data)
    if problems:
        raise RuntimeError("启动前完整性校验失败:\n" + "\n".join(problems[:15]))

    # 账号有效性
    account = accounts.ensure_valid_account(account)

    # Java
    if not java_path:
        java_path = java_manager.find_suitable_java(version_id)
    if not java_path:
        raise RuntimeError("未选择 Java, 请先在设置中扫描/选择")
    java_path = java_manager.ensure_console_java(java_path)

    cmd = build_command(instance, account, java_path, version_data,
                       server_address=server_address)
    if server_address:
        if log_cb:
            log_cb("自动加入服务器: " + server_address)
    if log_cb:
        log_cb("启动命令: " + " ".join(cmd))

    # 启动
    creationflags = 0
    if os.name == "nt":
        creationflags = subprocess.CREATE_NO_WINDOW
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        stdin=subprocess.DEVNULL,
        bufsize=1,
        text=True,
        encoding="utf-8",
        errors="replace",
        creationflags=creationflags,
    )
    return GameProcess(proc, log_cb or (lambda x: None), on_exit)


# ---------------------------------------------------------------
# 导出启动脚本 (.bat)
# ---------------------------------------------------------------
def export_launch_script(instance, account, java_path, output_path):
    """
    导出 Windows .bat 启动脚本, 双击即可启动游戏, 无需打开启动器。
    - 复用 build_command 构建完整命令
    - 脚本含 chcp 65001(UTF-8)、cd 到实例目录、完整 java 命令、退出 pause
    返回输出文件路径。
    """
    import accounts

    mc_root = Path(CONFIG.get("game_dir"))
    version_id = instance["version_id"]
    version_data = version_manager.resolve_version_json(version_id)
    account = accounts.ensure_valid_account(account)
    if not java_path:
        java_path = java_manager.find_suitable_java(version_id)
    java_path = java_manager.ensure_console_java(java_path)

    cmd = build_command(instance, account, java_path, version_data)

    # 将命令列表转为 bat 单行字符串: 含空格的参数用双引号包裹
    def _quote(arg):
        if " " in arg and not (arg.startswith('"') and arg.endswith('"')):
            return '"' + arg + '"'
        return arg

    cmd_line = " ".join(_quote(a) for a in cmd)

    game_dir = Path(instance["game_dir"])
    title = "启动 {}".format(version_id)

    bat_lines = [
        "@echo off",
        "chcp 65001>nul",
        "title {}".format(title),
        "echo 游戏正在启动，请稍候。",
        'cd /D "{}"'.format(game_dir),
        cmd_line,
        "echo.",
        "echo 游戏已退出。",
        "pause",
    ]
    bat_content = "\r\n".join(bat_lines) + "\r\n"

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    # UTF-8 with BOM, 配合 chcp 65001 保证中文正常显示
    output_path.write_text(bat_content, encoding="utf-8-sig")
    return str(output_path)
