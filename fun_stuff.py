# -*- coding: utf-8 -*-
"""
VoxelLauncher - 娱乐功能模块(今日人品 / 命运卡抽卡 / 游戏周报)

- 今日人品: 每天按日期种子生成固定人品值(0~100), 带等级梗文案, 经典"开箱前先看人品"
- 命运卡抽卡: 随机抽取命运卡, 今日人品值直接影响稀有度概率, 收集图鉴
- 游戏周报: 记录每次游玩时长, 按周聚合生成"周报卡"(时长换算成梗文案)

数据保存在 %APPDATA%/VoxelLauncher/fun_stuff.json
"""
import json
import os
import random
from datetime import date, datetime, timedelta
from pathlib import Path

APP_DIR = Path(os.environ.get("APPDATA", str(Path.home()))) / "VoxelLauncher"
FUN_FILE = APP_DIR / "fun_stuff.json"

# ------------------------------------------------------------------
# 今日人品
# ------------------------------------------------------------------
# 人品等级: (最低值, 名称, 颜色)
LUCK_LEVELS = [
    (90, "人品爆棚", "#ff4500"),
    (70, "人品不错", "#ff8c00"),
    (40, "人品一般", "#9e9e9e"),
    (20, "人品堪忧", "#4682b4"),
    (0,  "天打雷劈", "#8b0000"),
]

# 人品梗文案: 按区间给随机文案
LUCK_SAYINGS = {
    "爆棚": [
        "今天出门踩到钻石", "适合去附魔台梭哈", "连僵尸都会绕着你走",
        "今天抽卡, 非酋退散", "可以去试试末影龙了",
    ],
    "不错": [
        "适合挖矿, 钻石在等你", "今天运气在线", "可以正常交易, 别担心",
        "今天适合打苦力怕, 它不会炸", "运气够用, 省着点花",
    ],
    "一般": [
        "平平无奇的一天", "不亏也不赚", "今天别碰附魔台",
        "运气一般, 稳住别浪", "适合养老玩法",
    ],
    "堪忧": [
        "出门小心苦力怕", "今天不适合下矿洞", "附魔台今天看你不爽",
        "建议先睡一觉改改运", "别抽卡, 求你",
    ],
    "天打雷劈": [
        "今天别玩MC, 真的", "连村民都嫌你晦气", "建议直接睡觉等明天",
        "今天出门会被雷劈(物理)", "抽卡必歪, 鉴定完毕",
    ],
}


def _luck_key(value):
    if value >= 90:
        return "爆棚"
    if value >= 70:
        return "不错"
    if value >= 40:
        return "一般"
    if value >= 20:
        return "堪忧"
    return "天打雷劈"


def today_luck(d=None):
    """按日期生成固定人品值 0~100(当天不变, 次日刷新)"""
    d = d or date.today()
    rnd = random.Random(d.year * 10000 + d.month * 100 + d.day)
    return rnd.randint(0, 100)


def luck_level(value):
    """人品值 -> (等级名, 颜色)"""
    for threshold, name, color in LUCK_LEVELS:
        if value >= threshold:
            return name, color
    return "天打雷劈", "#8b0000"


def luck_saying(value):
    """人品值 -> 随机梗文案"""
    pool = LUCK_SAYINGS.get(_luck_key(value), LUCK_SAYINGS["一般"])
    rnd = random.Random()  # 每次刷新文案, 但人品值固定
    return rnd.choice(pool)


# ------------------------------------------------------------------
# 命运卡
# ------------------------------------------------------------------
# (id, 名称, 稀有度 0普通/1稀有/2史诗/3传说, 描述, mc物品id, 数量)
CARDS = [
    # 普通
    ("card_stone", "石头的心事", 0, "你掉的只是一块石头, 别难过",
     "minecraft:stone", 8),
    ("card_creeper", "苦力怕路过", 0, "今天别站太近, 你知道我说的是谁",
     "minecraft:creeper_head", 1),
    ("card_piglin", "猪灵的凝视", 0, "金锭带够了再进下界",
     "minecraft:gold_ingot", 4),
    ("card_villager", "村民的凝视", 0, "今天的交易, 可能不太划算",
     "minecraft:emerald", 3),
    ("card_wood", "木剑传说", 0, "用木剑也能打僵尸, 大概",
     "minecraft:wooden_sword", 1),
    ("card_cave", "塌方警告", 0, "挖矿记得带火把, 别问为什么",
     "minecraft:torch", 16),
    # 稀有
    ("card_diamond", "钻石的呼唤", 1, "今天适合挖矿, 钻石在等你",
     "minecraft:diamond", 2),
    ("card_pearl", "末影珍珠", 1, "瞬移不一定成功, 但一定要帅",
     "minecraft:ender_pearl", 2),
    ("card_xp", "附魔之瓶", 1, "经验值+5, 附魔台在召唤",
     "minecraft:experience_bottle", 4),
    ("card_gapple", "金苹果", 1, "关键时刻能救命的好东西",
     "minecraft:golden_apple", 1),
    ("card_blaze", "烈焰火花", 1, "今天的你, 火力全开",
     "minecraft:blaze_powder", 4),
    # 史诗
    ("card_netherite", "下界合金之心", 2, "坚不可摧, 说的就是今天的你",
     "minecraft:netherite_ingot", 1),
    ("card_beacon", "信标之光", 2, "你的目标, 全图可见",
     "minecraft:beacon", 1),
    ("card_elytra", "鞘翅飞行", 2, "今天适合起飞, 摔不死算我的",
     "minecraft:elytra", 1),
    ("card_dragon", "末影龙之息", 2, "连末影龙都要忌惮你三分",
     "minecraft:dragon_breath", 3),
    # 传说
    ("card_notch", "Notch 的祝福", 3, "创世神今天看着你, 做什么都会成功",
     "minecraft:enchanted_golden_apple", 1),
    ("card_ancient", "远古之眼", 3, "你看到了别人看不到的宝藏",
     "minecraft:ender_eye", 2),
    ("card_seed", "世界之种", 3, "整个世界的运气都站在你这边",
     "minecraft:book", 1),
]

# MC 物品中文名(用于背包/发送显示)
ITEM_NAMES = {
    "minecraft:stone": "石头",
    "minecraft:creeper_head": "苦力怕头",
    "minecraft:gold_ingot": "金锭",
    "minecraft:emerald": "绿宝石",
    "minecraft:wooden_sword": "木剑",
    "minecraft:torch": "火把",
    "minecraft:diamond": "钻石",
    "minecraft:ender_pearl": "末影珍珠",
    "minecraft:experience_bottle": "附魔之瓶",
    "minecraft:golden_apple": "金苹果",
    "minecraft:blaze_powder": "烈焰粉",
    "minecraft:netherite_ingot": "下界合金锭",
    "minecraft:beacon": "信标",
    "minecraft:elytra": "鞘翅",
    "minecraft:dragon_breath": "龙息",
    "minecraft:enchanted_golden_apple": "附魔金苹果",
    "minecraft:ender_eye": "末影之眼",
    "minecraft:book": "书",
}


def item_name(mc_id):
    """MC物品中文名"""
    return ITEM_NAMES.get(mc_id, mc_id.split(":")[-1])

RARITY_NAMES = ["普通", "稀有", "史诗", "传说"]
RARITY_COLORS = ["#9e9e9e", "#2196f3", "#9c27b0", "#ff9800"]

# 每日免费抽卡次数, 超过后需要消耗积分
FREE_DRAWS_PER_DAY = 3
CARD_COST = 50  # 每次额外抽卡消耗积分


def draw_card(luck_value):
    """根据今日人品抽一张卡, 人品越高出稀有/传说概率越高
    返回 (card, rarity)"""
    luck_ratio = max(0.0, min(1.0, luck_value / 100.0))
    weights = {
        0: max(5, 55 - luck_ratio * 45),   # 普通: 人品越高越少
        1: 27 + luck_ratio * 15,           # 稀有
        2: 12 + luck_ratio * 22,           # 史诗
        3: 6 + luck_ratio * 45,            # 传说: 人品高时明显提升
    }
    rarities = [0, 1, 2, 3]
    rarity = random.choices(rarities, weights=[weights[r] for r in rarities])[0]
    pool = [c for c in CARDS if c[2] == rarity]
    return random.choice(pool), rarity


# ------------------------------------------------------------------
# 数据读写
# ------------------------------------------------------------------
def _load():
    try:
        if FUN_FILE.exists() and FUN_FILE.stat().st_size > 0:
            with open(str(FUN_FILE), "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def _save(data):
    try:
        FUN_FILE.parent.mkdir(parents=True, exist_ok=True)
        tmp = str(FUN_FILE) + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        if FUN_FILE.exists():
            FUN_FILE.unlink()
        os.rename(tmp, str(FUN_FILE))
        return True
    except Exception:
        return False


def _today_str(d=None):
    return (d or date.today()).isoformat()


# ---------------- 图鉴 ----------------
def get_collected():
    data = _load()
    return set(data.get("collected_cards", []))


def collect_card(card_id):
    """收集卡片到图鉴, 返回 (是否新卡, 收集总数, 图鉴总数)"""
    data = _load()
    collected = set(data.get("collected_cards", []))
    is_new = card_id not in collected
    if is_new:
        collected.add(card_id)
        data["collected_cards"] = sorted(collected)
        _save(data)
    return is_new, len(collected), len(CARDS)


# ---------------- 每日抽卡次数 ----------------
def get_remaining_free_draws():
    """今日剩余免费抽卡次数"""
    data = _load()
    daily = data.get("daily_draws", {})
    today = _today_str()
    used = daily.get(today, 0)
    return max(0, FREE_DRAWS_PER_DAY - used)


def consume_draw():
    """消耗一次抽卡额度, 返回 (是否还有免费次数)"""
    data = _load()
    daily = data.setdefault("daily_draws", {})
    today = _today_str()
    used = daily.get(today, 0)
    daily[today] = used + 1
    _save(data)
    return (used + 1) <= FREE_DRAWS_PER_DAY


# ---------------- 游戏周报 ----------------
def record_session(instance, seconds):
    """记录一次游玩时长(按实例名), 同时累计启动次数"""
    if instance is None:
        instance = "未知实例"
    seconds = max(0, int(seconds))
    if seconds <= 0:
        seconds = 0
    data = _load()
    today = _today_str()
    sessions = data.setdefault("sessions", {})
    inst_data = sessions.setdefault(instance, {})
    inst_data[today] = inst_data.get(today, 0) + seconds
    launches = data.setdefault("launches", {})
    launches[today] = launches.get(today, 0) + 1
    data["total_launches"] = data.get("total_launches", 0) + 1
    _save(data)


def _human_duration(seconds):
    seconds = int(seconds)
    if seconds < 60:
        return "{}秒".format(seconds)
    if seconds < 3600:
        return "{}分钟".format(seconds // 60)
    hours = seconds / 3600
    return "{:.1f}小时".format(hours)


def _fun_facts(total_seconds):
    """把总时长换算成梗文案"""
    hours = total_seconds / 3600
    facts = []
    if hours >= 0.5:
        facts.append("相当于喝了{}杯奶茶".format(int(hours * 2)))
    if hours >= 1.5:
        facts.append("相当于看了{:.0f}部电影".format(hours / 1.5))
    if hours >= 30:
        facts.append("理论上够通关{:.0f}次MC主线".format(hours / 30))
    if hours >= 1 and hours < 30:
        facts.append("差一点点就能通关MC主线(还差{:.0f}小时)".format(30 - hours))
    if not facts:
        facts.append("嗯...刚起步, 慢慢来")
    return facts


def week_report(d=None):
    """生成本周周报数据, 返回 dict:
    {total_seconds, instance_stats[(name, seconds)], launches,
     facts[list], days[list]}"""
    d = d or date.today()
    monday = d - timedelta(days=d.weekday())
    sunday = monday + timedelta(days=6)
    data = _load()
    sessions = data.get("sessions", {})
    total = 0
    inst_stats = []
    day_seconds = {}
    for inst, days_map in sessions.items():
        inst_total = 0
        for day_str, sec in days_map.items():
            try:
                day = date.fromisoformat(day_str)
            except Exception:
                continue
            if monday <= day <= sunday:
                inst_total += sec
                day_seconds[day_str] = day_seconds.get(day_str, 0) + sec
        if inst_total > 0:
            inst_stats.append((inst, inst_total))
            total += inst_total
    inst_stats.sort(key=lambda x: x[1], reverse=True)
    # 本周启动次数
    launches = data.get("launches", {})
    week_launches = 0
    for day_str, cnt in launches.items():
        try:
            day = date.fromisoformat(day_str)
        except Exception:
            continue
        if monday <= day <= sunday:
            week_launches += cnt
    return {
        "total_seconds": total,
        "instance_stats": inst_stats,
        "launches": week_launches,
        "facts": _fun_facts(total),
        "days": day_seconds,
        "monday": monday,
        "sunday": sunday,
    }


def week_report_text(d=None):
    """生成周报可分享文本"""
    r = week_report(d)
    lines = ["📊 VoxelLauncher 游戏周报",
             "统计周期: {} ~ {}".format(r["monday"].strftime("%m-%d"),
                                        r["sunday"].strftime("%m-%d"))]
    lines.append("本周总时长: {}".format(_human_duration(r["total_seconds"])))
    lines.append("本周启动: {} 次".format(r["launches"]))
    if r["instance_stats"]:
        lines.append("各版本时长:")
        for name, sec in r["instance_stats"]:
            lines.append("  · {}: {}".format(name, _human_duration(sec)))
    for fact in r["facts"]:
        lines.append("→ " + fact)
    return "\n".join(lines)
