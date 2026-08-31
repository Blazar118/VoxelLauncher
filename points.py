# -*- coding: utf-8 -*-
"""
VoxelLauncher - 积分兑换系统
通过挖矿、战斗等获得积分，兑换游戏内物品，自动生成 /give 命令。
积分数据保存在配置目录 points.json。
"""
import json
import os
from pathlib import Path
from datetime import datetime


def get_points_file():
    """获取积分文件路径"""
    config_dir = Path(os.path.expanduser("~")) / ".voxellauncher"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir / "points.json"


def load_points():
    """加载积分数据"""
    f = get_points_file()
    if f.exists():
        try:
            with open(f, "r", encoding="utf-8") as fp:
                return json.load(fp)
        except Exception:
            pass
    return {"points": 0, "total_earned": 0, "history": []}


def save_points(data):
    """保存积分数据"""
    f = get_points_file()
    with open(f, "w", encoding="utf-8") as fp:
        json.dump(data, fp, ensure_ascii=False, indent=2)


def add_points(amount, reason=""):
    """增加积分"""
    data = load_points()
    data["points"] += amount
    data["total_earned"] += amount
    data["history"].append({
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "amount": amount,
        "reason": reason
    })
    # 只保留最近100条记录
    if len(data["history"]) > 100:
        data["history"] = data["history"][-100:]
    save_points(data)
    return data["points"]


def spend_points(amount, reason=""):
    """消耗积分"""
    data = load_points()
    if data["points"] < amount:
        return False, data["points"]
    data["points"] -= amount
    data["history"].append({
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "amount": -amount,
        "reason": reason
    })
    if len(data["history"]) > 100:
        data["history"] = data["history"][-100:]
    save_points(data)
    return True, data["points"]


def get_balance():
    """获取当前积分"""
    return load_points()["points"]


# 可兑换物品列表
# 格式: id -> {name, item_id, cost, icon, desc}
REDEEMABLE_ITEMS = [
    {
        "id": "diamond",
        "name": "钻石 x64",
        "item_id": "minecraft:diamond",
        "count": 64,
        "cost": 100,
        "icon": "💎",
        "desc": "64个钻石，一夜暴富"
    },
    {
        "id": "netherite_ingot",
        "name": "下界合金锭 x4",
        "item_id": "minecraft:netherite_ingot",
        "count": 4,
        "cost": 500,
        "icon": "🟫",
        "desc": "4个下界合金锭，顶级装备材料"
    },
    {
        "id": "gold_ingot",
        "name": "金锭 x64",
        "item_id": "minecraft:gold_ingot",
        "count": 64,
        "cost": 50,
        "icon": "🥇",
        "desc": "64个金锭，黄金万两"
    },
    {
        "id": "iron_ingot",
        "name": "铁锭 x64",
        "item_id": "minecraft:iron_ingot",
        "count": 64,
        "cost": 20,
        "icon": "⚙️",
        "desc": "64个铁锭，基础材料"
    },
    {
        "id": "emerald",
        "name": "绿宝石 x32",
        "item_id": "minecraft:emerald",
        "count": 32,
        "cost": 80,
        "icon": "💚",
        "desc": "32个绿宝石，村民最爱"
    },
    {
        "id": "diamond_sword",
        "name": "钻石剑",
        "item_id": "minecraft:diamond_sword",
        "count": 1,
        "cost": 150,
        "icon": "⚔️",
        "desc": "锋利的钻石剑，打怪神器"
    },
    {
        "id": "diamond_pickaxe",
        "name": "钻石镐",
        "item_id": "minecraft:diamond_pickaxe",
        "count": 1,
        "cost": 150,
        "icon": "⛏️",
        "desc": "效率满满的钻石镐"
    },
    {
        "id": "diamond_armor",
        "name": "钻石套（四件）",
        "item_id": "minecraft:diamond_chestplate",
        "count": 1,
        "cost": 400,
        "icon": "🛡️",
        "desc": "头盔+胸甲+护腿+靴子全套钻石装备",
        "multi": [
            "minecraft:diamond_helmet",
            "minecraft:diamond_chestplate",
            "minecraft:diamond_leggings",
            "minecraft:diamond_boots"
        ]
    },
    {
        "id": "enchanted_golden_apple",
        "name": "附魔金苹果 x8",
        "item_id": "minecraft:enchanted_golden_apple",
        "count": 8,
        "cost": 300,
        "icon": "🍎",
        "desc": "8个附魔金苹果，不死图腾"
    },
    {
        "id": "ender_eye",
        "name": "末影之眼 x12",
        "item_id": "minecraft:ender_eye",
        "count": 12,
        "cost": 60,
        "icon": "👁️",
        "desc": "12个末影之眼，找末地门"
    },
    {
        "id": "firework_rocket",
        "name": "烟花火箭 x64",
        "item_id": "minecraft:firework_rocket",
        "count": 64,
        "cost": 30,
        "icon": "🎆",
        "desc": "64个烟花，鞘翅飞行必备"
    },
    {
        "id": "experience_bottle",
        "name": "经验瓶 x32",
        "item_id": "minecraft:experience_bottle",
        "count": 32,
        "cost": 100,
        "icon": "🧪",
        "desc": "32个经验瓶，快速升级"
    },
    {
        "id": "shulker_box",
        "name": "潜影盒 x4",
        "item_id": "minecraft:shulker_box",
        "count": 4,
        "cost": 200,
        "icon": "📦",
        "desc": "4个潜影盒，搬家神器"
    },
    {
        "id": "totem_of_undying",
        "name": "不死图腾 x4",
        "item_id": "minecraft:totem_of_undying",
        "count": 4,
        "cost": 250,
        "icon": "🗿",
        "desc": "4个不死图腾，保命神器"
    },
    {
        "id": "nether_star",
        "name": "下界之星 x1",
        "item_id": "minecraft:nether_star",
        "count": 1,
        "cost": 1000,
        "icon": "⭐",
        "desc": "稀有的下界之星，做信标"
    }
]


def generate_give_command(player_name, item):
    """生成 /give 命令"""
    commands = []
    if "multi" in item:
        for i, item_id in enumerate(item["multi"]):
            commands.append("/give {} {} 1".format(player_name, item_id))
    else:
        commands.append("/give {} {} {}".format(
            player_name, item["item_id"], item["count"]))
    return commands


def redeem_item(item_id, player_name):
    """兑换物品"""
    item = None
    for it in REDEEMABLE_ITEMS:
        if it["id"] == item_id:
            item = it
            break
    if not item:
        return False, "物品不存在", 0

    success, balance = spend_points(item["cost"], "兑换: " + item["name"])
    if not success:
        return False, "积分不足，需要 {} 积分，当前 {} 积分".format(item["cost"], balance), balance

    commands = generate_give_command(player_name, item)
    return True, commands, balance


def get_earn_ways():
    """获取积分获取方式说明"""
    return [
        {"action": "挖矿（普通矿石）", "points": 1, "icon": "⛏️"},
        {"action": "挖矿（稀有矿石）", "points": 5, "icon": "💎"},
        {"action": "战斗胜利", "points": 10, "icon": "⚔️"},
        {"action": "每日签到", "points": 20, "icon": "📅"},
        {"action": "首次启动游戏", "points": 50, "icon": "🎮"},
        {"action": "下载模组", "points": 2, "icon": "📦"},
        {"action": "创建服务器", "points": 30, "icon": "🖥️"},
    ]
