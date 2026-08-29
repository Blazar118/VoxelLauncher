# -*- coding: utf-8 -*-
"""
VoxelLauncher - 成就系统(搞笑版)
追踪用户使用行为, 解锁各种搞笑成就, 带 Steam 风格弹窗通知。
成就数据保存在配置目录 achievements.json。
"""
import json
import os
from pathlib import Path
from datetime import datetime


# 成就定义: id -> {name, desc, icon(emoji), condition(描述)}
ACHIEVEMENTS = {
    "first_launch": {
        "name": "梦开始的地方",
        "desc": "第一次启动 Minecraft",
        "icon": "🎮",
    },
    "brave_soul": {
        "name": "勇敢者",
        "desc": "点了那个「千万别点」按钮",
        "icon": "⚠️",
    },
    "mod_master": {
        "name": "模组大师",
        "desc": "在一个实例里装了 10 个以上 mod",
        "icon": "📦",
    },
    "crash_expert": {
        "name": "崩溃专家",
        "desc": "见证了游戏的第一次崩溃",
        "icon": "💥",
    },
    "night_owl": {
        "name": "夜猫子",
        "desc": "在凌晨 2 点后还在启动游戏",
        "icon": "🦉",
    },
    "rich_guy": {
        "name": "土豪",
        "desc": "把最大内存设到了 8G 以上",
        "icon": "💰",
    },
    "minimalist": {
        "name": "极简主义",
        "desc": "一个 mod 都没装就启动了游戏",
        "icon": "✨",
    },
    "download_maniac": {
        "name": "下载狂魔",
        "desc": "下载了 3 个以上游戏版本",
        "icon": "⬇️",
    },
    "nonsense_writer": {
        "name": "废话文学家",
        "desc": "看了 10 条加载界面的废话提示",
        "icon": "📝",
    },
    "explorer": {
        "name": "探险家",
        "desc": "创建了 3 个以上实例",
        "icon": "🗺️",
    },
    "script_kid": {
        "name": "脚本小子",
        "desc": "导出了启动脚本",
        "icon": "📜",
    },
    "cf_victim": {
        "name": "CurseForge 受害者",
        "desc": "尝试使用 CurseForge 但没有 API 密钥",
        "icon": "🔒",
    },
    "xray_hunter": {
        "name": "矿物追踪者",
        "desc": "搜索过 Xray 相关资源包",
        "icon": "💎",
    },
    "chaos_lover": {
        "name": "混乱爱好者",
        "desc": "在混乱模式下坚持了 30 秒以上",
        "icon": "🌀",
    },
    "charged_creeper": {
        "name": "⚡ 闪电苦力怕",
        "desc": "把苦力怕喂到 5 次, 它变成了闪电苦力怕",
        "icon": "⚡",
    },
    "creeper_super_explosion": {
        "name": "💥 核爆现场",
        "desc": "把苦力怕喂到 10 次, 触发了超级大爆炸",
        "icon": "💥",
    },
    "first_diamond": {
        "name": "💎 第一颗钻石",
        "desc": "在启动器里挖到了第一颗钻石",
        "icon": "💎",
    },
    "diamond_hunter": {
        "name": "⛏ 钻石猎人",
        "desc": "在启动器里挖到了 10 颗钻石",
        "icon": "⛏",
    },
    "herobrine_encounter": {
        "name": "👁 你看到了他",
        "desc": "挖到了 ??? 矿石, 遭遇了 Herobrine",
        "icon": "👁",
    },
    "netherite_pickaxe": {
        "name": "⚒ 下界合金之主",
        "desc": "在锻造台锻造出了下界合金镐",
        "icon": "⚒",
    },
    "trading_master": {
        "name": "🤝 奸商克星",
        "desc": "通过村民交易获得了下界合金锭",
        "icon": "🤝",
    },
}


class AchievementManager:
    """成就管理器: 加载/保存/解锁成就"""

    def __init__(self, config_dir=None):
        if config_dir is None:
            config_dir = Path(os.environ.get("APPDATA", ".")) / "VoxelLauncher"
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.data_file = self.config_dir / "achievements.json"
        self._load()
        # 统计用计数器(不持久化, 仅本次运行)
        self._tip_count = 0
        self._chaos_start_time = None

    def _load(self):
        """加载成就数据"""
        if self.data_file.exists():
            try:
                with open(self.data_file, "r", encoding="utf-8") as f:
                    self.data = json.load(f)
            except Exception:
                self.data = {"unlocked": {}, "stats": {}}
        else:
            self.data = {"unlocked": {}, "stats": {}}
        if "unlocked" not in self.data:
            self.data["unlocked"] = {}
        if "stats" not in self.data:
            self.data["stats"] = {}

    def _save(self):
        """保存成就数据"""
        try:
            with open(self.data_file, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def is_unlocked(self, ach_id):
        """检查成就是否已解锁"""
        return ach_id in self.data["unlocked"]

    def unlock(self, ach_id):
        """
        解锁成就。
        返回 (是否新解锁, 成就信息)。已解锁过返回 (False, None)。
        """
        if ach_id not in ACHIEVEMENTS:
            return False, None
        if self.is_unlocked(ach_id):
            return False, None
        ach = ACHIEVEMENTS[ach_id]
        self.data["unlocked"][ach_id] = {
            "unlocked_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        self._save()
        return True, ach

    def get_all(self):
        """获取所有成就及解锁状态"""
        result = []
        for ach_id, ach in ACHIEVEMENTS.items():
            unlocked = self.is_unlocked(ach_id)
            info = dict(ach)
            info["id"] = ach_id
            info["unlocked"] = unlocked
            if unlocked:
                info["unlocked_at"] = self.data["unlocked"][ach_id].get(
                    "unlocked_at", "")
            result.append(info)
        return result

    def get_unlocked_count(self):
        """已解锁成就数量"""
        return len(self.data["unlocked"])

    def get_total_count(self):
        """成就总数"""
        return len(ACHIEVEMENTS)

    # ---- 统计辅助 ----
    def inc_stat(self, key, amount=1):
        """增加统计值"""
        self.data["stats"][key] = self.data["stats"].get(key, 0) + amount
        self._save()
        return self.data["stats"][key]

    def get_stat(self, key, default=0):
        """获取统计值"""
        return self.data["stats"].get(key, default)


# 全局单例
_manager = None


def get_manager():
    global _manager
    if _manager is None:
        _manager = AchievementManager()
    return _manager
