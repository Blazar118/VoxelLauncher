# -*- coding: utf-8 -*-
"""
VoxelLauncher - 游戏资源提取模块
从 Minecraft 版本 jar 文件中提取纹理、语言等资源,
用于在启动器中显示游戏内真实素材(如鱼的纹理)。
"""
import zipfile
import json
from pathlib import Path
from typing import Optional, Dict


# Minecraft 原版鱼的纹理路径 (相对 jar 内)
FISH_TEXTURES = {
    "cod": "assets/minecraft/textures/entity/fish/cod.png",
    "tropical_fish": "assets/minecraft/textures/entity/fish/tropical_fish.png",
    "pufferfish": "assets/minecraft/textures/entity/fish/pufferfish.png",
    "salmon": "assets/minecraft/textures/entity/fish/salmon.png",
    # 其他水生生物
    "squid": "assets/minecraft/textures/entity/squid.png",
    "glow_squid": "assets/minecraft/textures/entity/glow_squid.png",
    "turtle": "assets/minecraft/textures/entity/turtle.png",
    "dolphin": "assets/minecraft/textures/entity/dolphin.png",
    "axolotl": "assets/minecraft/textures/entity/axolotl/axolotl.png",
    "guardian": "assets/minecraft/textures/entity/guardian.png",
    "elder_guardian": "assets/minecraft/textures/entity/elder_guardian.png",
}

# 鱼对应的物品 ID (用于发送到游戏)
FISH_ITEM_IDS = {
    "cod": "minecraft:cod",
    "tropical_fish": "minecraft:tropical_fish",
    "pufferfish": "minecraft:pufferfish",
    "salmon": "minecraft:salmon",
    "squid": None,  # 鱿鱼不是物品
    "glow_squid": None,
    "turtle": None,
    "dolphin": None,
    "axolotl": None,
    "guardian": None,
    "elder_guardian": None,
}

# 鱼的中文名称
FISH_NAMES = {
    "cod": "鳕鱼",
    "tropical_fish": "热带鱼",
    "pufferfish": "河豚",
    "salmon": "鲑鱼",
    "squid": "鱿鱼",
    "glow_squid": "发光鱿鱼",
    "turtle": "海龟",
    "dolphin": "海豚",
    "axolotl": "美西螈",
    "guardian": "守卫者",
    "elder_guardian": "远古守卫者",
}


def find_version_jar(mc_dir: str, version: str) -> Optional[Path]:
    """
    查找指定版本的 jar 文件。
    mc_dir: .minecraft 目录路径
    version: 版本号, 如 "1.20.1"
    返回 jar 文件路径, 找不到返回 None
    """
    jar_path = Path(mc_dir) / "versions" / version / f"{version}.jar"
    if jar_path.exists():
        return jar_path
    return None


def extract_texture_from_jar(jar_path: Path, texture_path: str,
                              output_dir: Path) -> Optional[Path]:
    """
    从版本 jar 中提取指定纹理文件到输出目录。
    jar_path: 版本 jar 文件路径
    texture_path: jar 内的纹理相对路径
    output_dir: 输出目录
    返回提取后的文件路径, 失败返回 None
    """
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(jar_path, 'r') as zf:
            if texture_path in zf.namelist():
                output_file = output_dir / Path(texture_path).name
                with zf.open(texture_path) as src, open(output_file, 'wb') as dst:
                    dst.write(src.read())
                return output_file
    except Exception:
        pass
    return None


def extract_all_fish_textures(mc_dir: str, version: str,
                               output_dir: str) -> Dict[str, Path]:
    """
    从指定版本提取所有鱼的纹理。
    返回 {fish_key: 纹理文件路径} 字典, 只包含成功提取的。
    """
    jar_path = find_version_jar(mc_dir, version)
    if not jar_path:
        return {}
    output = Path(output_dir)
    result = {}
    for fish_key, tex_path in FISH_TEXTURES.items():
        extracted = extract_texture_from_jar(jar_path, tex_path, output)
        if extracted:
            result[fish_key] = extracted
    return result


def get_fish_texture(fish_key: str, mc_dir: str, version: str,
                      cache_dir: str) -> Optional[Path]:
    """
    获取指定鱼的纹理(带缓存)。
    先检查缓存, 没有则从 jar 提取。
    """
    cache = Path(cache_dir) / "fish_textures"
    cached_file = cache / f"{fish_key}.png"
    if cached_file.exists():
        return cached_file
    # 从 jar 提取
    jar_path = find_version_jar(mc_dir, version)
    if jar_path and fish_key in FISH_TEXTURES:
        extracted = extract_texture_from_jar(
            jar_path, FISH_TEXTURES[fish_key], cache)
        if extracted:
            return extracted
    return None


def get_fish_item_id(fish_key: str) -> Optional[str]:
    """获取鱼对应的物品 ID(用于发送到游戏)"""
    return FISH_ITEM_IDS.get(fish_key)


def get_fish_name(fish_key: str) -> str:
    """获取鱼的中文名称"""
    return FISH_NAMES.get(fish_key, fish_key)


def list_available_fish() -> list:
    """列出所有支持的鱼"""
    return list(FISH_TEXTURES.keys())


def load_fish_texture_photo(fish_key: str, mc_dir: str, version: str,
                             cache_dir: str, scale: int = 6):
    """
    加载鱼的纹理, 用 Pillow 处理后返回 Tkinter PhotoImage。
    解决 Tkinter 不支持索引颜色 PNG 的问题。
    scale: 放大倍数
    """
    try:
        from PIL import Image, ImageTk
        import tkinter as tk
    except ImportError:
        return None

    tex_path = get_fish_texture(fish_key, mc_dir, version, cache_dir)
    if not tex_path:
        return None

    try:
        # 用 Pillow 打开图片, 转换为 RGBA (支持透明度)
        img = Image.open(str(tex_path)).convert("RGBA")
        # 最近邻放大 (保持像素风格)
        w, h = img.size
        img = img.resize((w * scale, h * scale), Image.NEAREST)
        # 转换成 Tkinter PhotoImage
        photo = ImageTk.PhotoImage(img)
        return photo
    except Exception:
        return None


def load_texture_photo(texture_path: str, scale: int = 6):
    """
    通用纹理加载函数, 用 Pillow 处理后返回 Tkinter PhotoImage。
    """
    try:
        from PIL import Image, ImageTk
    except ImportError:
        return None

    try:
        img = Image.open(str(texture_path)).convert("RGBA")
        w, h = img.size
        img = img.resize((w * scale, h * scale), Image.NEAREST)
        return ImageTk.PhotoImage(img)
    except Exception:
        return None


# ---------------------------------------------------------------
# 动物纹理(用于养殖系统)
# ---------------------------------------------------------------
ANIMAL_TEXTURES = {
    "chicken": "assets/minecraft/textures/entity/chicken.png",
    "cow": "assets/minecraft/textures/entity/cow/cow.png",
    "pig": "assets/minecraft/textures/entity/pig/pig.png",
    "sheep": "assets/minecraft/textures/entity/sheep/sheep.png",
    "sheep_wool": "assets/minecraft/textures/entity/sheep/sheep_fur.png",
    "rabbit": "assets/minecraft/textures/entity/rabbit/rabbit.png",
    "horse": "assets/minecraft/textures/entity/horse/horse.png",
    "donkey": "assets/minecraft/textures/entity/horse/donkey.png",
    "mule": "assets/minecraft/textures/entity/horse/mule.png",
    "llama": "assets/minecraft/textures/entity/llama/llama.png",
    "goat": "assets/minecraft/textures/entity/goat/goat.png",
    "cat": "assets/minecraft/textures/entity/cat/cat.png",
    "dog": "assets/minecraft/textures/entity/wolf/wolf_tame.png",
    "parrot": "assets/minecraft/textures/entity/parrot/parrot.png",
    "fox": "assets/minecraft/textures/entity/fox/fox.png",
    "bee": "assets/minecraft/textures/entity/bee/bee.png",
    "villager": "assets/minecraft/textures/entity/villager/villager.png",
}

# 动物中文名称
ANIMAL_NAMES = {
    "chicken": "鸡",
    "cow": "牛",
    "pig": "猪",
    "sheep": "羊",
    "rabbit": "兔子",
    "horse": "马",
    "donkey": "驴",
    "mule": "骡子",
    "llama": "羊驼",
    "goat": "山羊",
    "cat": "猫",
    "dog": "狗",
    "parrot": "鹦鹉",
    "fox": "狐狸",
    "bee": "蜜蜂",
    "villager": "村民",
}

# 动物喜欢的食物(用于喂食)
ANIMAL_FOODS = {
    "chicken": ["wheat_seeds", "beetroot_seeds", "melon_seeds", "pumpkin_seeds"],
    "cow": ["wheat"],
    "pig": ["carrot", "potato", "beetroot"],
    "sheep": ["wheat"],
    "rabbit": ["carrot", "golden_carrot", "dandelion"],
    "horse": ["golden_apple", "golden_carrot", "hay_block", "wheat", "apple", "sugar"],
    "donkey": ["golden_apple", "golden_carrot", "hay_block", "wheat", "apple", "sugar"],
    "llama": ["hay_block", "wheat"],
    "goat": ["wheat"],
    "cat": ["cod", "salmon", "tropical_fish", "pufferfish", "raw_cod", "raw_salmon"],
    "dog": ["bone", "beef", "porkchop", "chicken", "mutton", "rabbit", "rotten_flesh"],
    "parrot": ["wheat_seeds", "beetroot_seeds", "melon_seeds", "pumpkin_seeds"],
    "fox": ["sweet_berries", "glow_berries"],
    "bee": ["flower", "honey_bottle"],
}

# 动物产品(收获)
ANIMAL_PRODUCTS = {
    "chicken": {"egg": "鸡蛋", "feather": "羽毛", "chicken_meat": "鸡肉"},
    "cow": {"milk": "牛奶", "leather": "皮革", "beef": "牛肉"},
    "pig": {"porkchop": "猪肉"},
    "sheep": {"wool": "羊毛", "mutton": "羊肉"},
    "rabbit": {"rabbit": "兔肉", "rabbit_hide": "兔皮"},
    "goat": {"goat_horn": "山羊角", "milk": "羊奶"},
    "cat": {"nothing": "无"},
    "dog": {"nothing": "无"},
    "parrot": {"nothing": "无"},
    "fox": {"nothing": "无"},
    "bee": {"honey_bottle": "蜂蜜瓶", "honeycomb": "蜜脾"},
}


def get_animal_texture(animal_key: str, mc_dir: str, version: str,
                        cache_dir: str) -> Optional[Path]:
    """获取动物纹理(带缓存)"""
    cache = Path(cache_dir) / "animal_textures"
    cached_file = cache / f"{animal_key}.png"
    if cached_file.exists():
        return cached_file
    jar_path = find_version_jar(mc_dir, version)
    if jar_path and animal_key in ANIMAL_TEXTURES:
        extracted = extract_texture_from_jar(
            jar_path, ANIMAL_TEXTURES[animal_key], cache)
        if extracted:
            return extracted
    return None


def load_animal_texture_photo(animal_key: str, mc_dir: str, version: str,
                               cache_dir: str, scale: int = 5):
    """加载动物纹理, 用 Pillow 处理后返回 Tkinter PhotoImage"""
    try:
        from PIL import Image, ImageTk
    except ImportError:
        return None
    tex_path = get_animal_texture(animal_key, mc_dir, version, cache_dir)
    if not tex_path:
        return None
    try:
        img = Image.open(str(tex_path)).convert("RGBA")
        w, h = img.size
        img = img.resize((w * scale, h * scale), Image.NEAREST)
        return ImageTk.PhotoImage(img)
    except Exception:
        return None


def get_animal_name(animal_key: str) -> str:
    """获取动物中文名称"""
    return ANIMAL_NAMES.get(animal_key, animal_key)


def get_animal_foods(animal_key: str) -> list:
    """获取动物喜欢的食物"""
    return ANIMAL_FOODS.get(animal_key, [])


def get_animal_products(animal_key: str) -> dict:
    """获取动物产品"""
    return ANIMAL_PRODUCTS.get(animal_key, {})


def list_available_animals() -> list:
    """列出所有支持的动物"""
    return list(ANIMAL_TEXTURES.keys())


# ---------------------------------------------------------------
# 方块/工作台纹理(用于合成系统等)
# ---------------------------------------------------------------
BLOCK_TEXTURES = {
    # 工作台
    "crafting_table_top": "assets/minecraft/textures/block/crafting_table_top.png",
    "crafting_table_front": "assets/minecraft/textures/block/crafting_table_front.png",
    "crafting_table_side": "assets/minecraft/textures/block/crafting_table_side.png",
    # 常用方块
    "grass_block": "assets/minecraft/textures/block/grass_block_top.png",
    "dirt": "assets/minecraft/textures/block/dirt.png",
    "stone": "assets/minecraft/textures/block/stone.png",
    "cobblestone": "assets/minecraft/textures/block/cobblestone.png",
    "planks_oak": "assets/minecraft/textures/block/oak_planks.png",
    "log_oak": "assets/minecraft/textures/block/oak_log.png",
    "leaves_oak": "assets/minecraft/textures/block/oak_leaves.png",
    "sand": "assets/minecraft/textures/block/sand.png",
    "glass": "assets/minecraft/textures/block/glass.png",
    "bricks": "assets/minecraft/textures/block/bricks.png",
    "iron_block": "assets/minecraft/textures/block/iron_block.png",
    "gold_block": "assets/minecraft/textures/block/gold_block.png",
    "diamond_block": "assets/minecraft/textures/block/diamond_block.png",
    "obsidian": "assets/minecraft/textures/block/obsidian.png",
    "chest": "assets/minecraft/textures/block/chest_front.png",
    "furnace_front": "assets/minecraft/textures/block/furnace_front.png",
    "bookshelf": "assets/minecraft/textures/block/bookshelf.png",
    "anvil": "assets/minecraft/textures/block/anvil.png",
}

# 物品纹理(常用物品)
ITEM_TEXTURES = {
    "wooden_pickaxe": "assets/minecraft/textures/item/wooden_pickaxe.png",
    "stone_pickaxe": "assets/minecraft/textures/item/stone_pickaxe.png",
    "iron_pickaxe": "assets/minecraft/textures/item/iron_pickaxe.png",
    "golden_pickaxe": "assets/minecraft/textures/item/golden_pickaxe.png",
    "diamond_pickaxe": "assets/minecraft/textures/item/diamond_pickaxe.png",
    "wooden_axe": "assets/minecraft/textures/item/wooden_axe.png",
    "iron_axe": "assets/minecraft/textures/item/iron_axe.png",
    "diamond_axe": "assets/minecraft/textures/item/diamond_axe.png",
    "wooden_sword": "assets/minecraft/textures/item/wooden_sword.png",
    "iron_sword": "assets/minecraft/textures/item/iron_sword.png",
    "diamond_sword": "assets/minecraft/textures/item/diamond_sword.png",
    "stick": "assets/minecraft/textures/item/stick.png",
    "torch": "assets/minecraft/textures/item/torch.png",
    "crafting_table_item": "assets/minecraft/textures/item/crafting_table.png",
    "furnace_item": "assets/minecraft/textures/item/furnace.png",
    "chest_item": "assets/minecraft/textures/item/chest.png",
    "iron_ingot": "assets/minecraft/textures/item/iron_ingot.png",
    "gold_ingot": "assets/minecraft/textures/item/gold_ingot.png",
    "diamond": "assets/minecraft/textures/item/diamond.png",
    "emerald": "assets/minecraft/textures/item/emerald.png",
    "coal": "assets/minecraft/textures/item/coal.png",
    "redstone": "assets/minecraft/textures/item/redstone.png",
    "lapis_lazuli": "assets/minecraft/textures/item/lapis_lazuli.png",
    "wheat": "assets/minecraft/textures/item/wheat.png",
    "bread": "assets/minecraft/textures/item/bread.png",
    "apple": "assets/minecraft/textures/item/apple.png",
    "golden_apple": "assets/minecraft/textures/item/golden_apple.png",
    "bucket": "assets/minecraft/textures/item/bucket.png",
    "water_bucket": "assets/minecraft/textures/item/water_bucket.png",
    "lava_bucket": "assets/minecraft/textures/item/lava_bucket.png",
    "milk_bucket": "assets/minecraft/textures/item/milk_bucket.png",
    "bow": "assets/minecraft/textures/item/bow.png",
    "arrow": "assets/minecraft/textures/item/arrow.png",
    "fishing_rod": "assets/minecraft/textures/item/fishing_rod.png",
    "compass": "assets/minecraft/textures/item/compass.png",
    "clock": "assets/minecraft/textures/item/clock.png",
    "map": "assets/minecraft/textures/item/map.png",
    "book": "assets/minecraft/textures/item/book.png",
    "paper": "assets/minecraft/textures/item/paper.png",
    "leather": "assets/minecraft/textures/item/leather.png",
    "feather": "assets/minecraft/textures/item/feather.png",
    "bone": "assets/minecraft/textures/item/bone.png",
    "string": "assets/minecraft/textures/item/string.png",
    "slime_ball": "assets/minecraft/textures/item/slime_ball.png",
    "ender_pearl": "assets/minecraft/textures/item/ender_pearl.png",
    "blaze_rod": "assets/minecraft/textures/item/blaze_rod.png",
    "ghast_tear": "assets/minecraft/textures/item/ghast_tear.png",
    "nether_star": "assets/minecraft/textures/item/nether_star.png",
    "dragon_egg": "assets/minecraft/textures/item/dragon_egg.png",
    "elytra": "assets/minecraft/textures/item/elytra.png",
    "shield": "assets/minecraft/textures/item/shield.png",
    "totem_of_undying": "assets/minecraft/textures/item/totem_of_undying.png",
    "nautilus_shell": "assets/minecraft/textures/item/nautilus_shell.png",
    "heart_of_the_sea": "assets/minecraft/textures/item/heart_of_the_sea.png",
    "trident": "assets/minecraft/textures/item/trident.png",
    "phantom_membrane": "assets/minecraft/textures/item/phantom_membrane.png",
    "turtle_shell": "assets/minecraft/textures/item/turtle_helmet.png",
    "scute": "assets/minecraft/textures/item/scute.png",
}


def get_block_texture(block_key: str, mc_dir: str, version: str,
                       cache_dir: str) -> Optional[Path]:
    """获取方块纹理(带缓存)"""
    cache = Path(cache_dir) / "block_textures"
    cached_file = cache / f"{block_key}.png"
    if cached_file.exists():
        return cached_file
    jar_path = find_version_jar(mc_dir, version)
    if jar_path and block_key in BLOCK_TEXTURES:
        extracted = extract_texture_from_jar(
            jar_path, BLOCK_TEXTURES[block_key], cache)
        if extracted:
            return extracted
    return None


def get_item_texture(item_key: str, mc_dir: str, version: str,
                      cache_dir: str) -> Optional[Path]:
    """获取物品纹理(带缓存)"""
    cache = Path(cache_dir) / "item_textures"
    cached_file = cache / f"{item_key}.png"
    if cached_file.exists():
        return cached_file
    jar_path = find_version_jar(mc_dir, version)
    if jar_path and item_key in ITEM_TEXTURES:
        extracted = extract_texture_from_jar(
            jar_path, ITEM_TEXTURES[item_key], cache)
        if extracted:
            return extracted
    return None


def load_block_texture_photo(block_key: str, mc_dir: str, version: str,
                              cache_dir: str, scale: int = 4):
    """加载方块纹理, 用 Pillow 处理后返回 Tkinter PhotoImage"""
    try:
        from PIL import Image, ImageTk
    except ImportError:
        return None
    tex_path = get_block_texture(block_key, mc_dir, version, cache_dir)
    if not tex_path:
        return None
    try:
        img = Image.open(str(tex_path)).convert("RGBA")
        w, h = img.size
        img = img.resize((w * scale, h * scale), Image.NEAREST)
        return ImageTk.PhotoImage(img)
    except Exception:
        return None


def load_item_texture_photo(item_key: str, mc_dir: str, version: str,
                             cache_dir: str, scale: int = 3):
    """加载物品纹理, 用 Pillow 处理后返回 Tkinter PhotoImage"""
    try:
        from PIL import Image, ImageTk
    except ImportError:
        return None
    tex_path = get_item_texture(item_key, mc_dir, version, cache_dir)
    if not tex_path:
        return None
    try:
        img = Image.open(str(tex_path)).convert("RGBA")
        w, h = img.size
        img = img.resize((w * scale, h * scale), Image.NEAREST)
        return ImageTk.PhotoImage(img)
    except Exception:
        return None
