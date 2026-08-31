# -*- coding: utf-8 -*-
"""
VoxelLauncher - 玩家状态模块
管理启动器内小游戏的经验、等级、背包、成就、统计数据。
挖矿获得的物品可以转换成 Minecraft /give 指令, 带到实际游戏里。
"""
import json
import os
import time
from pathlib import Path


# 升级所需经验: 每级需要 100 + level * 50
def exp_needed(level):
    return 100 + level * 50


# 矿石对应的 Minecraft 物品 ID
ORE_TO_ITEM = {
    "coal_ore": "minecraft:coal",
    "iron_ore": "minecraft:raw_iron",
    "gold_ore": "minecraft:raw_gold",
    "diamond_ore": "minecraft:diamond",
    "emerald_ore": "minecraft:emerald",
    "redstone_ore": "minecraft:redstone",
    "lapis_ore": "minecraft:lapis_lazuli",
    "copper_ore": "minecraft:raw_copper",
    "nether_quartz_ore": "minecraft:quartz",
    "nether_gold_ore": "minecraft:raw_gold",
    "ancient_debris": "minecraft:ancient_debris",
    "stone": "minecraft:stone",
    "cobblestone": "minecraft:cobblestone",
    "netherite_ingot": "minecraft:netherite_ingot",
    "iron_ingot": "minecraft:iron_ingot",
    "gold_ingot": "minecraft:gold_ingot",
    "diamond": "minecraft:diamond",
}

# 矿石中文名
ORE_NAMES = {
    "coal_ore": "煤炭",
    "iron_ore": "铁矿石",
    "gold_ore": "金矿石",
    "diamond_ore": "钻石",
    "emerald_ore": "绿宝石",
    "redstone_ore": "红石",
    "lapis_ore": "青金石",
    "copper_ore": "铜矿石",
    "nether_quartz_ore": "下界石英",
    "nether_gold_ore": "下界金矿石",
    "ancient_debris": "远古残骸",
    "stone": "石头",
    "cobblestone": "圆石",
    "netherite_ingot": "下界合金锭",
    "iron_ingot": "铁锭",
    "gold_ingot": "金锭",
    "diamond": "钻石",
}

# 成就定义: id -> (名称, 描述, 检测条件)
ACHIEVEMENTS = {
    "first_launch": ("初次启航", "第一次启动 Minecraft", None),
    "miner": ("矿工", "累计挖到 100 块矿石", None),
    "creeper_slayer": ("苦力怕杀手", "击杀 10 只苦力怕", None),
    "addict": ("肝帝", "累计启动游戏 50 次", None),
    "lucky": ("欧皇", "挖到钻石", None),
    "netherite": ("下界合金", "获得下界合金锭", None),
    "level_5": ("初出茅庐", "达到 5 级", None),
    "level_10": ("满级大佬", "达到 10 级", None),
    "smith": ("锻造大师", "在锻造台锻造出下界合金稿", None),
}


class PlayerState:
    """玩家状态: 经验、等级、背包、成就、统计"""

    def __init__(self, save_path=None):
        if save_path is None:
            save_path = Path(os.environ.get("APPDATA", ".")) / "VoxelLauncher" / "player.json"
        self.save_path = Path(save_path)
        self.data = {
            "level": 1,
            "exp": 0,
            "inventory": {},      # {item_id: count}
            "achievements": [],   # 已解锁成就 id 列表
            "stats": {            # 统计数据
                "launch_count": 0,
                "ore_mined": 0,
                "creeper_killed": 0,
                "play_time_minutes": 0,
                "forged_netherite": False,
            },
        }
        self.load()

    def load(self):
        """从文件加载"""
        try:
            if self.save_path.exists():
                with open(self.save_path, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                # 合并, 防止旧版本缺少字段
                for k, v in saved.items():
                    if k == "stats" and isinstance(v, dict):
                        self.data["stats"].update(v)
                    else:
                        self.data[k] = v
        except Exception:
            pass

    def save(self):
        """保存到文件"""
        try:
            self.save_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.save_path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    # ---------------- 经验/等级 ----------------
    @property
    def level(self):
        return self.data["level"]

    @property
    def exp(self):
        return self.data["exp"]

    @property
    def exp_to_next(self):
        return exp_needed(self.level)

    def add_exp(self, amount):
        """增加经验, 返回 (是否升级, 新等级)"""
        self.data["exp"] += amount
        leveled_up = False
        while self.data["exp"] >= exp_needed(self.data["level"]):
            self.data["exp"] -= exp_needed(self.data["level"])
            self.data["level"] += 1
            leveled_up = True
        self.save()
        if leveled_up:
            self._check_level_achievements()
        return leveled_up, self.data["level"]

    def _check_level_achievements(self):
        """检查等级成就"""
        if self.level >= 5 and "level_5" not in self.data["achievements"]:
            self.unlock_achievement("level_5")
        if self.level >= 10 and "level_10" not in self.data["achievements"]:
            self.unlock_achievement("level_10")

    # ---------------- 背包 ----------------
    @property
    def inventory(self):
        return self.data["inventory"]

    def add_item(self, item_key, count=1):
        """添加物品到背包, item_key 是 ORE_TO_ITEM 的 key"""
        mc_id = ORE_TO_ITEM.get(item_key, item_key)
        self.data["inventory"][mc_id] = self.data["inventory"].get(mc_id, 0) + count
        self.save()

    def remove_item(self, mc_id, count=1):
        """从背包移除物品"""
        if mc_id in self.data["inventory"]:
            self.data["inventory"][mc_id] -= count
            if self.data["inventory"][mc_id] <= 0:
                del self.data["inventory"][mc_id]
            self.save()
            return True
        return False

    def clear_inventory(self):
        """清空背包"""
        self.data["inventory"] = {}
        self.save()

    def generate_give_commands(self, player_name="@s"):
        """生成所有背包物品的 /give 指令列表"""
        commands = []
        for mc_id, count in self.data["inventory"].items():
            if count > 0:
                # Minecraft /give 每次最多 64 个, 超过的拆分
                while count > 0:
                    batch = min(count, 64)
                    commands.append(f"/give {player_name} {mc_id} {batch}")
                    count -= batch
        return commands

    # ---------------- 成就 ----------------
    @property
    def unlocked_achievements(self):
        return self.data["achievements"]

    def unlock_achievement(self, ach_id):
        """解锁成就, 返回 (是否新解锁, 成就名称)"""
        if ach_id in ACHIEVEMENTS and ach_id not in self.data["achievements"]:
            self.data["achievements"].append(ach_id)
            self.save()
            return True, ACHIEVEMENTS[ach_id][0]
        return False, None

    def check_achievement(self, ach_id):
        """检查成就是否已解锁"""
        return ach_id in self.data["achievements"]

    # ---------------- 统计 ----------------
    @property
    def stats(self):
        return self.data["stats"]

    def on_game_launch(self):
        """游戏启动时调用"""
        self.data["stats"]["launch_count"] += 1
        leveled, new_lv = self.add_exp(50)
        # 第一次启动成就
        if self.data["stats"]["launch_count"] == 1:
            self.unlock_achievement("first_launch")
        # 肝帝成就
        if self.data["stats"]["launch_count"] >= 50:
            self.unlock_achievement("addict")
        self.save()
        return leveled, new_lv

    def on_ore_mined(self, ore_key, is_rare=False):
        """挖矿时调用, ore_key 是矿石 key"""
        self.data["stats"]["ore_mined"] += 1
        exp = 50 if is_rare else 10
        leveled, new_lv = self.add_exp(exp)
        # 矿石进背包
        self.add_item(ore_key)
        # 矿工成就
        if self.data["stats"]["ore_mined"] >= 100:
            self.unlock_achievement("miner")
        # 欧皇成就
        if ore_key in ("diamond_ore", "diamond"):
            self.unlock_achievement("lucky")
        # 下界合金成就
        if ore_key in ("netherite_ingot", "ancient_debris"):
            self.unlock_achievement("netherite")
        self.save()
        return leveled, new_lv

    def on_creeper_killed(self):
        """击杀苦力怕时调用"""
        self.data["stats"]["creeper_killed"] += 1
        leveled, new_lv = self.add_exp(30)
        if self.data["stats"]["creeper_killed"] >= 10:
            self.unlock_achievement("creeper_slayer")
        self.save()
        return leveled, new_lv

    def on_forge_netherite(self):
        """锻造下界合金稿时调用"""
        self.data["stats"]["forged_netherite"] = True
        self.unlock_achievement("smith")
        self.add_exp(100)
        self.save()


# 全局单例
_player = None

def get_player():
    global _player
    if _player is None:
        _player = PlayerState()
    return _player
