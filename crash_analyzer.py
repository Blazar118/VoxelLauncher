# -*- coding: utf-8 -*-
"""崩溃日志分析器"""
import os
import re
import glob
from datetime import datetime


class CrashAnalyzer:
    """Minecraft 崩溃日志分析器"""

    # 常见崩溃原因关键词
    CRASH_PATTERNS = [
        {
            "pattern": r"OutOfMemoryError|Java heap space",
            "name": "内存不足",
            "solution": "增加游戏内存分配：启动器 → 设置 → 最大内存，调到4096M或更高",
            "severity": "high"
        },
        {
            "pattern": r"NullPointerException",
            "name": "空指针异常",
            "solution": "通常是模组冲突或模组bug，尝试移除最近安装的模组",
            "severity": "medium"
        },
        {
            "pattern": r"ClassNotFoundException|NoClassDefFoundError",
            "name": "缺少类/依赖缺失",
            "solution": "某个模组缺少依赖库，检查是否安装了 required 的前置模组",
            "severity": "high"
        },
        {
            "pattern": r"ConcurrentModificationException",
            "name": "并发修改异常",
            "solution": "模组在多线程时冲突，通常是 ModMenu 等模组的已知问题，不影响游戏",
            "severity": "low"
        },
        {
            "pattern": r"EXCEPTION_ACCESS_VIOLATION|igxelpicd|igdumdim|nvidia|atio",
            "name": "显卡驱动崩溃",
            "solution": "更新显卡驱动！如果是Intel核显，去Intel官网下载最新驱动；N卡去NVIDIA官网",
            "severity": "high"
        },
        {
            "pattern": r"Mixin apply failed|mixin.*failed",
            "name": "Mixin注入失败",
            "solution": "模组版本不兼容，检查模组是否支持当前游戏版本和加载器版本",
            "severity": "high"
        },
        {
            "pattern": r"DuplicateMod|duplicate mod|Mod .* already exists",
            "name": "重复模组",
            "solution": "有重复的模组，删除重复的jar文件",
            "severity": "medium"
        },
        {
            "pattern": r"IncompatibleMod|incompatible mod|requires.*version",
            "name": "模组版本不兼容",
            "solution": "某个模组要求特定版本的其他模组，检查版本要求",
            "severity": "high"
        },
        {
            "pattern": r"Shader|shader.*failed|OpenGL",
            "name": "光影/OpenGL错误",
            "solution": "关闭光影或更新显卡驱动，某些光影不支持你的显卡",
            "severity": "medium"
        },
        {
            "pattern": r"IOException|Connection reset|UnknownHost",
            "name": "网络错误",
            "solution": "网络连接问题，检查网络或加速器",
            "severity": "low"
        },
        {
            "pattern": r"TickNextTick|Ticking|Exception ticking",
            "name": "游戏刻崩溃",
            "solution": "世界数据损坏或实体过多，尝试用备份恢复存档",
            "severity": "high"
        },
        {
            "pattern": r"StackOverflowError",
            "name": "栈溢出",
            "solution": "通常是模组递归调用冲突，移除最近安装的模组",
            "severity": "medium"
        },
    ]

    def __init__(self, instance_dir):
        self.instance_dir = instance_dir

    def find_crash_reports(self):
        """查找所有崩溃日志"""
        crash_dir = os.path.join(self.instance_dir, "crash-reports")
        reports = []

        if os.path.exists(crash_dir):
            for f in glob.glob(os.path.join(crash_dir, "*.txt")):
                reports.append({
                    "path": f,
                    "name": os.path.basename(f),
                    "time": datetime.fromtimestamp(os.path.getmtime(f)),
                    "size": os.path.getsize(f)
                })

        # 也查找 hs_err_pid 文件（JVM崩溃）
        for pattern in ["hs_err_pid*.log", "hs_err_pid*.txt"]:
            for f in glob.glob(os.path.join(self.instance_dir, pattern)):
                reports.append({
                    "path": f,
                    "name": os.path.basename(f),
                    "time": datetime.fromtimestamp(os.path.getmtime(f)),
                    "size": os.path.getsize(f),
                    "type": "jvm_crash"
                })

        reports.sort(key=lambda x: x["time"], reverse=True)
        return reports

    def analyze(self, report_path):
        """分析崩溃日志"""
        result = {
            "file": os.path.basename(report_path),
            "time": datetime.fromtimestamp(os.path.getmtime(report_path)),
            "causes": [],
            "suspected_mods": [],
            "game_version": None,
            "loader": None,
            "java_version": None,
            "summary": "",
            "raw_excerpt": ""
        }

        try:
            with open(report_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
        except Exception as e:
            result["summary"] = f"无法读取日志文件: {e}"
            return result

        # 保存前2000字符作为摘要
        result["raw_excerpt"] = content[:2000]

        # 提取游戏版本
        m = re.search(r'Minecraft Version[:\s]+([0-9.]+)', content)
        if m:
            result["game_version"] = m.group(1)

        # 提取加载器
        if "Fabric" in content:
            result["loader"] = "Fabric"
        elif "Forge" in content:
            result["loader"] = "Forge"

        # 提取Java版本
        m = re.search(r'Java Version[:\s]+([0-9._]+)', content)
        if m:
            result["java_version"] = m.group(1)
        m = re.search(r'JRE version[:\s]+(.+?)\s', content)
        if m:
            result["java_version"] = m.group(1)

        # 匹配崩溃原因
        for pattern_info in self.CRASH_PATTERNS:
            if re.search(pattern_info["pattern"], content, re.IGNORECASE):
                result["causes"].append({
                    "name": pattern_info["name"],
                    "solution": pattern_info["solution"],
                    "severity": pattern_info["severity"]
                })

        # 提取可疑模组
        mod_patterns = [
            r'at\s+([a-zA-Z0-9_.]+)\.',
            r'Mod ID:\s*([a-zA-Z0-9_]+)',
            r'--\s*([a-zA-Z0-9_]+)\s*--',
        ]
        suspected = set()
        for line in content.split('\n'):
            # 查找堆栈中的模组包名
            m = re.search(r'at\s+(net\.|com\.)([a-zA-Z0-9_]+)\.', line)
            if m:
                pkg = m.group(2).lower()
                if pkg not in ['minecraft', 'java', 'sun', 'jdk', 'fabric', 'forge',
                               'google', 'mojang', 'netty', 'lwjgl', 'gson', 'guava',
                               'log4j', 'slf4j', 'apache', 'ibm', 'jopt', 'oshi',
                               'lz4', 'joml', 'craft', 'electronwill', 'twelvemonkeys',
                               'quiltmc', 'akuleshov', 'jetbrains', 'kotlinx']:
                    suspected.add(pkg)

        result["suspected_mods"] = list(suspected)[:10]

        # 生成摘要
        if result["causes"]:
            high = [c for c in result["causes"] if c["severity"] == "high"]
            if high:
                result["summary"] = f"检测到 {len(high)} 个严重问题：{high[0]['name']}"
            else:
                result["summary"] = f"检测到 {len(result['causes'])} 个可能的问题"
        else:
            result["summary"] = "未识别到常见崩溃原因，建议手动查看日志"

        return result

    def analyze_latest(self):
        """分析最新的崩溃日志"""
        reports = self.find_crash_reports()
        if not reports:
            return None
        return self.analyze(reports[0]["path"])


# ================================================================
# AI 智能排错: 把崩溃日志喂给 AI(智谱/Kimi/豆包), 返回诊断+修复方案
# ================================================================
DIAGNOSE_SYSTEM_PROMPT = """你是一位资深 Minecraft 模组排错专家, 精通 Forge/Fabric/NeoForge、Java 版本、模组冲突、崩溃日志分析。

用户会给你一段 Minecraft 的崩溃日志或报错信息, 请你:
1. 用通俗中文指出最可能的崩溃原因(一句话说清)
2. 列出具体的修复步骤(按"先试哪个"排序, 每一步都要能直接照做)
3. 如果涉及模组, 指出可能的问题模组(从堆栈包名判断)
4. 如果涉及 Java 版本/内存/显卡驱动等环境问题, 明确指出

要求:
- 只输出诊断和修复建议, 不要客套话
- 用 Markdown 分点, 步骤要可执行
- 如果日志里信息不足, 明确说"信息不足", 并列出还需要什么信息
- 不要编造日志里没有的结论, 不确定就说"可能""大概率"
"""


def ai_diagnose_crash(log_text, ai):
    """调用 AI 诊断崩溃日志
    log_text: 崩溃日志全文(可截断)
    ai: ai_chat.AIChat 实例
    返回: (成功, 诊断文本/错误)
    """
    if not ai.is_configured():
        return False, "未配置 AI 接口, 请先在「设置」页配置 AI(智谱/Kimi/豆包)"
    if not log_text or len(log_text.strip()) < 20:
        return False, "日志内容太短, 无法诊断"
    # 截取关键部分(前后各保留, 控制 token)
    text = log_text.strip()
    if len(text) > 12000:
        text = text[:6000] + "\n\n...[日志过长已截断]...\n\n" + text[-6000:]
    message = "以下是 Minecraft 崩溃日志/报错, 请诊断:\n\n" + text
    return ai.chat(message, system_prompt=DIAGNOSE_SYSTEM_PROMPT, temperature=0.3)


def ai_diagnose_latest(report_path, ai, max_chars=20000):
    """读取崩溃日志文件并交给 AI 诊断"""
    try:
        with open(report_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
    except Exception as e:
        return False, "读取日志失败: " + str(e)
    if max_chars and len(content) > max_chars:
        content = content[:max_chars]
    return ai_diagnose_crash(content, ai)

