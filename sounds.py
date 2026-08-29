# -*- coding: utf-8 -*-
"""
VoxelLauncher - 音效模块
从 Minecraft 原版 assets 中提取真实游戏音效(ogg), 优先用 pygame 播放,
没有 pygame 时回退到 winsound 合成音效。
"""
import json
import os
import shutil
import threading
import time
from pathlib import Path

# 尝试导入 pygame(可选依赖)
try:
    import pygame
    HAS_PYGAME = True
except Exception:
    HAS_PYGAME = False

try:
    import winsound
    HAS_WINSOUND = True
except Exception:
    HAS_WINSOUND = False

try:
    from PIL import Image
    HAS_PIL = True
except Exception:
    HAS_PIL = False


# 音效在 Minecraft assets 索引中的 key
# 苦力怕爆炸 = 苦力怕嘶嘶声(say) + 通用爆炸声(explode)
CREEPER_SS_KEYS = [
    "minecraft/sounds/mob/creeper/say1.ogg",
    "minecraft/sounds/mob/creeper/say2.ogg",
    "minecraft/sounds/mob/creeper/say3.ogg",
    "minecraft/sounds/mob/creeper/say4.ogg",
]
EXPLODE_KEYS = [
    "minecraft/sounds/random/explode1.ogg",
    "minecraft/sounds/random/explode2.ogg",
    "minecraft/sounds/random/explode3.ogg",
    "minecraft/sounds/random/explode4.ogg",
]
# 兼容旧 key
CREEPER_EXPLOSION_KEYS = EXPLODE_KEYS

# 玩家受伤声音(史蒂夫"嗷"的一声)
# 老版本(pre-1.6): newsound/damage/hurtflesh + newsound/random/hurt
# 新版本(1.19+): 没有通用受伤声, 用 fire_hurt(爆炸=火焰伤害)代替
PLAYER_HURT_KEYS = [
    # 远古版本: 肉体受伤声(最经典的"嗷")
    "newsound/damage/hurtflesh1.ogg",
    "newsound/damage/hurtflesh2.ogg",
    "newsound/damage/hurtflesh3.ogg",
    "newsound/random/hurt.ogg",
    # 老版本正式路径
    "minecraft/sounds/game/player/hurt1.ogg",
    "minecraft/sounds/game/player/hurt2.ogg",
    "minecraft/sounds/game/player/hurt3.ogg",
    "minecraft/sounds/mob/steve/hurt1.ogg",
    "minecraft/sounds/mob/steve/hurt2.ogg",
    # 新版本: 按伤害类型, 爆炸用火焰受伤声
    "minecraft/sounds/entity/player/hurt/fire_hurt1.ogg",
    "minecraft/sounds/entity/player/hurt/fire_hurt2.ogg",
    "minecraft/sounds/entity/player/hurt/fire_hurt3.ogg",
    # 新版本通用路径(如果存在)
    "minecraft/sounds/entity/player/hurt1.ogg",
    "minecraft/sounds/entity/player/hurt2.ogg",
    "minecraft/sounds/entity/player/hurt3.ogg",
]

# 村民叫声(哼哼声)
VILLAGER_SAY_KEYS = [
    # 老版本
    "minecraft/sounds/mob/villager/idle1.ogg",
    "minecraft/sounds/mob/villager/idle2.ogg",
    "minecraft/sounds/mob/villager/idle3.ogg",
    "minecraft/sounds/mob/villager/idle4.ogg",
    "minecraft/sounds/mob/villager/say1.ogg",
    "minecraft/sounds/mob/villager/say2.ogg",
    "minecraft/sounds/mob/villager/say3.ogg",
    # 新版本(1.19+)
    "minecraft/sounds/entity/villager/idle1.ogg",
    "minecraft/sounds/entity/villager/idle2.ogg",
    "minecraft/sounds/entity/villager/idle3.ogg",
    "minecraft/sounds/entity/villager/idle4.ogg",
    "minecraft/sounds/entity/villager/ambient1.ogg",
    "minecraft/sounds/entity/villager/ambient2.ogg",
    "minecraft/sounds/entity/villager/ambient3.ogg",
    # 农民村民
    "minecraft/sounds/entity/villager/type/plains/idle1.ogg",
    "minecraft/sounds/entity/villager/type/plains/idle2.ogg",
]


def _get_assets_dir(game_dir):
    """获取 Minecraft assets 目录"""
    return Path(game_dir) / "assets"


def _find_sound_hash(game_dir, sound_keys):
    """
    在 assets 索引文件中查找音效的哈希值。
    返回 (hash_str, index_version) 或 (None, None)。
    """
    assets_dir = _get_assets_dir(game_dir)
    indexes_dir = assets_dir / "indexes"
    if not indexes_dir.exists():
        return None, None

    # 遍历所有索引文件(取最新的)
    index_files = sorted(indexes_dir.glob("*.json"))
    if not index_files:
        return None, None

    for idx_file in reversed(index_files):
        try:
            with open(idx_file, "r", encoding="utf-8") as f:
                index_data = json.load(f)
            objects = index_data.get("objects", {})
            for key in sound_keys:
                if key in objects:
                    return objects[key]["hash"], idx_file.stem
                # 尝试不带 minecraft: 前缀
                short_key = key.replace("minecraft:", "")
                if short_key in objects:
                    return objects[short_key]["hash"], idx_file.stem
        except Exception:
            continue
    return None, None


def _extract_ogg(game_dir, file_hash, dest_path):
    """从 assets/objects 中提取 ogg 文件到目标路径"""
    if not file_hash or len(file_hash) < 2:
        return False
    assets_dir = _get_assets_dir(game_dir)
    src = assets_dir / "objects" / file_hash[:2] / file_hash
    if not src.exists():
        return False
    try:
        dest_path = Path(dest_path)
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest_path)
        return True
    except Exception:
        return False


def get_creeper_explosion_sound(game_dir, cache_dir=None):
    """
    获取苦力怕爆炸音效(嘶嘶声+爆炸声组合)。
    优先从缓存读取, 没有则从 Minecraft assets 提取。
    返回 (ss_ogg_path, explode_ogg_path) 或 (None, None)。
    """
    if cache_dir is None:
        cache_dir = Path(os.environ.get("APPDATA", ".")) / "VoxelLauncher" / "sounds"
    cache_dir = Path(cache_dir)
    ss_cached = cache_dir / "creeper_ss.ogg"
    exp_cached = cache_dir / "creeper_explode.ogg"

    # 两个都有缓存则直接返回
    if ss_cached.exists() and exp_cached.exists():
        return str(ss_cached), str(exp_cached)

    # 提取苦力怕嘶嘶声(随机选一个)
    import random
    ss_key = random.choice(CREEPER_SS_KEYS)
    ss_hash, _ = _find_sound_hash(game_dir, [ss_key])
    if ss_hash:
        _extract_ogg(game_dir, ss_hash, ss_cached)

    # 提取爆炸声(随机选一个)
    exp_key = random.choice(EXPLODE_KEYS)
    exp_hash, _ = _find_sound_hash(game_dir, [exp_key])
    if exp_hash:
        _extract_ogg(game_dir, exp_hash, exp_cached)

    if ss_cached.exists() and exp_cached.exists():
        return str(ss_cached), str(exp_cached)
    return None, None


def play_ogg(ogg_path):
    """
    播放 ogg 音效文件。
    优先用 pygame.mixer, 失败则回退。
    """
    if not ogg_path or not os.path.exists(ogg_path):
        return False

    if HAS_PYGAME:
        def _play():
            try:
                if not pygame.mixer.get_init():
                    pygame.mixer.init()
                sound = pygame.mixer.Sound(ogg_path)
                sound.play()
            except Exception:
                pass
        threading.Thread(target=_play, daemon=True).start()
        return True

    return False


def play_creeper_explosion(game_dir, cache_dir=None):
    """
    播放苦力怕爆炸音效: 先嘶嘶声(0.4秒), 再爆炸声。
    优先用从 Minecraft 提取的真实音效, 没有则回退到 winsound 合成。
    """
    ss_path, exp_path = get_creeper_explosion_sound(game_dir, cache_dir)
    if ss_path and exp_path and HAS_PYGAME:
        def _combo():
            try:
                if not pygame.mixer.get_init():
                    pygame.mixer.init()
                # 先播嘶嘶声
                ss = pygame.mixer.Sound(ss_path)
                ss.play()
                # 0.4秒后播爆炸声
                time.sleep(0.4)
                exp = pygame.mixer.Sound(exp_path)
                exp.play()
            except Exception:
                pass
        threading.Thread(target=_combo, daemon=True).start()
        return True

    # 回退: winsound 合成下降噪音
    if HAS_WINSOUND:
        def _fallback():
            try:
                for f in (440, 330, 220, 165, 110):
                    winsound.Beep(f, 50)
            except Exception:
                pass
        threading.Thread(target=_fallback, daemon=True).start()
        return True

    return False


def play_player_hurt(game_dir, cache_dir=None):
    """
    播放玩家(史蒂夫)受伤声音: "嗷!" 的一声。
    苦力怕爆炸时调用, 模拟玩家受到伤害。
    """
    if cache_dir is None:
        cache_dir = Path(os.environ.get("APPDATA", ".")) / "VoxelLauncher" / "sounds"
    cache_dir = Path(cache_dir)
    cached = cache_dir / "player_hurt.ogg"

    if not cached.exists():
        import random
        for key in PLAYER_HURT_KEYS:
            h, _ = _find_sound_hash(game_dir, [key])
            if h and _extract_ogg(game_dir, h, cached):
                break

    if cached.exists() and HAS_PYGAME:
        def _play():
            try:
                if not pygame.mixer.get_init():
                    pygame.mixer.init()
                sound = pygame.mixer.Sound(str(cached))
                sound.play()
            except Exception:
                pass
        threading.Thread(target=_play, daemon=True).start()
        return True

    # 回退: winsound 合成一声短促的"嗷"
    if HAS_WINSOUND:
        def _fallback():
            try:
                for f in (600, 500, 400):
                    winsound.Beep(f, 40)
            except Exception:
                pass
        threading.Thread(target=_fallback, daemon=True).start()
        return True

    return False


def get_villager_sound(game_dir, cache_dir=None):
    """
    获取村民叫声(哼哼声)。
    优先从缓存读取, 没有则从 Minecraft assets 提取。
    返回 ogg 文件路径或 None。
    """
    if cache_dir is None:
        cache_dir = Path(os.environ.get("APPDATA", ".")) / "VoxelLauncher" / "sounds"
    cache_dir = Path(cache_dir)
    cached = cache_dir / "villager_say.ogg"

    if cached.exists():
        return str(cached)

    # 随机选一个村民叫声
    import random
    for key in random.sample(VILLAGER_SAY_KEYS, len(VILLAGER_SAY_KEYS)):
        h, _ = _find_sound_hash(game_dir, [key])
        if h and _extract_ogg(game_dir, h, cached):
            return str(cached)

    return None


def play_villager_say(game_dir, cache_dir=None):
    """
    播放村民叫声(哼哼声)。
    优先用从 Minecraft 提取的真实音效, 没有则回退到 winsound 合成。
    """
    sound_path = get_villager_sound(game_dir, cache_dir)
    if sound_path and HAS_PYGAME:
        def _play():
            try:
                if not pygame.mixer.get_init():
                    pygame.mixer.init()
                sound = pygame.mixer.Sound(sound_path)
                sound.play()
            except Exception:
                pass
        threading.Thread(target=_play, daemon=True).start()
        return True

    # 回退: winsound 合成低沉的哼哼声
    if HAS_WINSOUND:
        def _fallback():
            try:
                for f in (200, 180, 220, 200):
                    winsound.Beep(f, 80)
            except Exception:
                pass
        threading.Thread(target=_fallback, daemon=True).start()
        return True

    return False


# ---------------- 苦力怕贴图提取 ----------------
def _find_game_jar(game_dir):
    """查找任意一个可用的游戏 jar 包(用于提取贴图)"""
    versions_dir = Path(game_dir) / "versions"
    if not versions_dir.exists():
        return None
    for vdir in sorted(versions_dir.iterdir()):
        if vdir.is_dir():
            jar = vdir / (vdir.name + ".jar")
            if jar.exists():
                return str(jar)
    return None


def get_creeper_texture(game_dir, cache_dir=None, scale=4):
    """
    从游戏 jar 包提取苦力怕贴图, 拼接正面视图, 放大后保存为 PNG。
    返回 PNG 文件路径或 None。
    """
    if not HAS_PIL:
        return None

    if cache_dir is None:
        cache_dir = Path(os.environ.get("APPDATA", ".")) / "VoxelLauncher" / "sounds"
    cache_dir = Path(cache_dir)
    cached = cache_dir / f"creeper_front_x{scale}.png"

    if cached.exists():
        return str(cached)

    jar_path = _find_game_jar(game_dir)
    if not jar_path:
        return None

    try:
        import zipfile
        with zipfile.ZipFile(jar_path, "r") as z:
            with z.open("assets/minecraft/textures/entity/creeper/creeper.png") as f:
                tex = Image.open(f).convert("RGBA")

        # 拼接正面视图: 头(8x8) + 身体(8x12) + 两条腿(各4x12)
        front = Image.new("RGBA", (8, 32), (0, 0, 0, 0))
        head = tex.crop((8, 8, 16, 16))
        body = tex.crop((20, 20, 28, 32))
        leg_r = tex.crop((4, 20, 8, 32))
        leg_l = tex.crop((8, 20, 12, 32))
        front.paste(head, (0, 0))
        front.paste(body, (0, 8))
        front.paste(leg_r, (0, 20))
        front.paste(leg_l, (4, 20))

        # 放大(最近邻, 保持像素风)
        front_big = front.resize((8 * scale, 32 * scale), Image.NEAREST)
        cache_dir.mkdir(parents=True, exist_ok=True)
        front_big.save(str(cached))
        return str(cached)
    except Exception:
        return None


def get_enderman_texture(game_dir, cache_dir=None, scale=4):
    """
    从游戏 jar 包提取末影人贴图, 拼接完整正面视图(头+身体+手臂+腿), 放大后保存为 PNG。
    末影人有长手臂, 必须包含手臂才正常。
    返回 PNG 文件路径或 None。
    """
    if not HAS_PIL:
        return None

    if cache_dir is None:
        cache_dir = Path(os.environ.get("APPDATA", ".")) / "VoxelLauncher" / "sounds"
    cache_dir = Path(cache_dir)
    cached = cache_dir / f"enderman_front_x{scale}.png"

    # 删除旧的损坏缓存, 重新生成
    if cached.exists():
        try:
            cached.unlink()
        except Exception:
            pass

    jar_path = _find_game_jar(game_dir)
    if not jar_path:
        return None

    try:
        import zipfile
        with zipfile.ZipFile(jar_path, "r") as z:
            with z.open("assets/minecraft/textures/entity/enderman/enderman.png") as f:
                tex = Image.open(f).convert("RGBA")

        # 末影人完整正面视图: 16x32
        # 布局: 头(8x8)在顶部中间, 身体(8x12)在中间, 手臂(4x12)在身体两侧, 腿(4x12)在底部
        front = Image.new("RGBA", (16, 32), (0, 0, 0, 0))
        # 头: (8,8) 8x8 -> 放在 (4, 0)
        head = tex.crop((8, 8, 16, 16))
        front.paste(head, (4, 0))
        # 身体: (20,20) 8x12 -> 放在 (4, 8)
        body = tex.crop((20, 20, 28, 32))
        front.paste(body, (4, 8))
        # 右臂: (44,16) 4x12 -> 放在 (0, 8)
        arm_r = tex.crop((44, 16, 48, 28))
        front.paste(arm_r, (0, 8))
        # 左臂: (52,16) 4x12 -> 放在 (12, 8)
        arm_l = tex.crop((52, 16, 56, 28))
        front.paste(arm_l, (12, 8))
        # 右腿: (4,20) 4x12 -> 放在 (4, 20)
        leg_r = tex.crop((4, 20, 8, 32))
        front.paste(leg_r, (4, 20))
        # 左腿: (8,20) 4x12 -> 放在 (8, 20)
        leg_l = tex.crop((8, 20, 12, 32))
        front.paste(leg_l, (8, 20))

        # 放大(最近邻, 保持像素风)
        front_big = front.resize((16 * scale, 32 * scale), Image.NEAREST)
        cache_dir.mkdir(parents=True, exist_ok=True)
        front_big.save(str(cached))
        return str(cached)
    except Exception:
        return None


def get_villager_texture(game_dir, cache_dir=None, scale=4):
    """
    从游戏 jar 包提取村民贴图, 拼接正面视图(头+身体+腿), 放大后保存为 PNG。
    村民纹理布局跟苦力怕一样: 头(8x8) + 身体(8x12) + 两条腿(各4x12)。
    返回 PNG 文件路径或 None。
    """
    if not HAS_PIL:
        return None

    if cache_dir is None:
        cache_dir = Path(os.environ.get("APPDATA", ".")) / "VoxelLauncher" / "sounds"
    cache_dir = Path(cache_dir)
    cached = cache_dir / f"villager_front_x{scale}.png"

    # 删除旧缓存, 重新生成
    if cached.exists():
        try:
            cached.unlink()
        except Exception:
            pass

    jar_path = _find_game_jar(game_dir)
    if not jar_path:
        return None

    try:
        import zipfile
        with zipfile.ZipFile(jar_path, "r") as z:
            # 村民纹理: 优先用普通村民, 找不到用农民
            tex = None
            for tex_path in [
                "assets/minecraft/textures/entity/villager/villager.png",
                "assets/minecraft/textures/entity/villager/type/plains.png",
            ]:
                try:
                    with z.open(tex_path) as f:
                        tex = Image.open(f).convert("RGBA")
                        break
                except Exception:
                    continue
            if tex is None:
                return None

        # 跟苦力怕一样的拼接方式: 头(8x8) + 身体(8x12) + 两条腿(各4x12)
        front = Image.new("RGBA", (8, 32), (0, 0, 0, 0))
        head = tex.crop((8, 8, 16, 16))
        body = tex.crop((20, 20, 28, 32))
        leg_r = tex.crop((4, 20, 8, 32))
        leg_l = tex.crop((8, 20, 12, 32))
        front.paste(head, (0, 0))
        front.paste(body, (0, 8))
        front.paste(leg_r, (0, 20))
        front.paste(leg_l, (4, 20))

        # 放大(最近邻, 保持像素风)
        front_big = front.resize((8 * scale, 32 * scale), Image.NEAREST)
        cache_dir.mkdir(parents=True, exist_ok=True)
        front_big.save(str(cached))
        return str(cached)
    except Exception:
        return None


def get_zombie_texture(game_dir, cache_dir=None, scale=4):
    """
    从游戏 jar 包提取僵尸贴图, 拼接正面视图, 放大后保存为 PNG。
    返回 PNG 文件路径或 None。
    """
    if not HAS_PIL:
        return None

    if cache_dir is None:
        cache_dir = Path(os.environ.get("APPDATA", ".")) / "VoxelLauncher" / "sounds"
    cache_dir = Path(cache_dir)
    cached = cache_dir / f"zombie_front_x{scale}.png"

    if cached.exists():
        return str(cached)

    jar_path = _find_game_jar(game_dir)
    if not jar_path:
        return None

    try:
        import zipfile
        with zipfile.ZipFile(jar_path, "r") as z:
            with z.open("assets/minecraft/textures/entity/zombie/zombie.png") as f:
                tex = Image.open(f).convert("RGBA")

        # 跟苦力怕一样的拼接方式: 头(8x8) + 身体(8x12) + 两条腿(各4x12)
        front = Image.new("RGBA", (8, 32), (0, 0, 0, 0))
        head = tex.crop((8, 8, 16, 16))
        body = tex.crop((20, 20, 28, 32))
        leg_r = tex.crop((4, 20, 8, 32))
        leg_l = tex.crop((8, 20, 12, 32))
        front.paste(head, (0, 0))
        front.paste(body, (0, 8))
        front.paste(leg_r, (0, 20))
        front.paste(leg_l, (4, 20))

        front_big = front.resize((8 * scale, 32 * scale), Image.NEAREST)
        cache_dir.mkdir(parents=True, exist_ok=True)
        front_big.save(str(cached))
        return str(cached)
    except Exception:
        return None


def get_skeleton_texture(game_dir, cache_dir=None, scale=4):
    """
    从游戏 jar 包提取骷髅贴图, 拼接正面视图, 放大后保存为 PNG。
    返回 PNG 文件路径或 None。
    """
    if not HAS_PIL:
        return None

    if cache_dir is None:
        cache_dir = Path(os.environ.get("APPDATA", ".")) / "VoxelLauncher" / "sounds"
    cache_dir = Path(cache_dir)
    cached = cache_dir / f"skeleton_front_x{scale}.png"

    if cached.exists():
        return str(cached)

    jar_path = _find_game_jar(game_dir)
    if not jar_path:
        return None

    try:
        import zipfile
        with zipfile.ZipFile(jar_path, "r") as z:
            with z.open("assets/minecraft/textures/entity/skeleton/skeleton.png") as f:
                tex = Image.open(f).convert("RGBA")

        # 跟苦力怕一样的拼接方式: 头(8x8) + 身体(8x12) + 两条腿(各4x12)
        front = Image.new("RGBA", (8, 32), (0, 0, 0, 0))
        head = tex.crop((8, 8, 16, 16))
        body = tex.crop((20, 20, 28, 32))
        leg_r = tex.crop((4, 20, 8, 32))
        leg_l = tex.crop((8, 20, 12, 32))
        front.paste(head, (0, 0))
        front.paste(body, (0, 8))
        front.paste(leg_r, (0, 20))
        front.paste(leg_l, (4, 20))

        front_big = front.resize((8 * scale, 32 * scale), Image.NEAREST)
        cache_dir.mkdir(parents=True, exist_ok=True)
        front_big.save(str(cached))
        return str(cached)
    except Exception:
        return None


# ---------------- 通用贴图提取 ----------------
def get_block_texture(game_dir, block_name, cache_dir=None, scale=4):
    """
    从游戏 jar 包提取方块贴图(如 stone, iron_ore, diamond_ore)。
    block_name 如 'stone', 'iron_ore', 'diamond_ore'。
    返回 PNG 文件路径或 None。
    """
    if not HAS_PIL:
        return None
    if cache_dir is None:
        cache_dir = Path(os.environ.get("APPDATA", ".")) / "VoxelLauncher" / "sounds"
    cache_dir = Path(cache_dir)
    cached = cache_dir / f"block_{block_name}_x{scale}.png"

    if cached.exists():
        return str(cached)

    jar_path = _find_game_jar(game_dir)
    if not jar_path:
        return None

    try:
        import zipfile
        tex_path = f"assets/minecraft/textures/block/{block_name}.png"
        with zipfile.ZipFile(jar_path, "r") as z:
            with z.open(tex_path) as f:
                tex = Image.open(f).convert("RGBA")
        # 放大
        w, h = tex.size
        tex_big = tex.resize((w * scale, h * scale), Image.NEAREST)
        cache_dir.mkdir(parents=True, exist_ok=True)
        tex_big.save(str(cached))
        return str(cached)
    except Exception:
        return None


def get_block_break_sound(game_dir, cache_dir=None):
    """提取方块破碎音效"""
    if cache_dir is None:
        cache_dir = Path(os.environ.get("APPDATA", ".")) / "VoxelLauncher" / "sounds"
    cache_dir = Path(cache_dir)
    cached = cache_dir / "block_break.ogg"
    if cached.exists():
        return str(cached)

    # 随机选一个挖掘音效
    import random
    break_keys = [
        "minecraft/sounds/random/break.ogg",
        "minecraft/sounds/random/stone1.ogg",
        "minecraft/sounds/random/stone2.ogg",
        "minecraft/sounds/random/stone3.ogg",
        "minecraft/sounds/random/stone4.ogg",
    ]
    for key in break_keys:
        h, _ = _find_sound_hash(game_dir, [key])
        if h and _extract_ogg(game_dir, h, cached):
            return str(cached)
    return None


# ---------------- 物品/环境贴图提取 ----------------
def get_item_texture(game_dir, item_name, cache_dir=None, scale=4):
    """
    从游戏 jar 提取物品贴图(如 wooden_pickaxe, diamond_pickaxe)。
    返回 PNG 文件路径或 None。
    """
    if not HAS_PIL:
        return None
    if cache_dir is None:
        cache_dir = Path(os.environ.get("APPDATA", ".")) / "VoxelLauncher" / "sounds"
    cache_dir = Path(cache_dir)
    cached = cache_dir / f"item_{item_name}_x{scale}.png"

    if cached.exists():
        return str(cached)

    jar_path = _find_game_jar(game_dir)
    if not jar_path:
        return None

    try:
        import zipfile
        tex_path = f"assets/minecraft/textures/item/{item_name}.png"
        with zipfile.ZipFile(jar_path, "r") as z:
            with z.open(tex_path) as f:
                tex = Image.open(f).convert("RGBA")
        w, h = tex.size
        tex_big = tex.resize((w * scale, h * scale), Image.NEAREST)
        cache_dir.mkdir(parents=True, exist_ok=True)
        tex_big.save(str(cached))
        return str(cached)
    except Exception:
        return None


def get_environment_texture(game_dir, tex_name, cache_dir=None, scale=2):
    """
    从游戏 jar 提取环境纹理(如 rain, snow)。
    返回 PNG 文件路径或 None。
    """
    if not HAS_PIL:
        return None
    if cache_dir is None:
        cache_dir = Path(os.environ.get("APPDATA", ".")) / "VoxelLauncher" / "sounds"
    cache_dir = Path(cache_dir)
    cached = cache_dir / f"env_{tex_name}_x{scale}.png"

    if cached.exists():
        return str(cached)

    jar_path = _find_game_jar(game_dir)
    if not jar_path:
        return None

    try:
        import zipfile
        tex_path = f"assets/minecraft/textures/environment/{tex_name}.png"
        with zipfile.ZipFile(jar_path, "r") as z:
            with z.open(tex_path) as f:
                tex = Image.open(f).convert("RGBA")
        w, h = tex.size
        tex_big = tex.resize((w * scale, h * scale), Image.NEAREST)
        cache_dir.mkdir(parents=True, exist_ok=True)
        tex_big.save(str(cached))
        return str(cached)
    except Exception:
        return None
