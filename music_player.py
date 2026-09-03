# -*- coding: utf-8 -*-
"""
VoxelLauncher - 多平台音乐聚合播放器
- 搜索: 网易云 + 酷狗 + QQ音乐 三平台聚合
- 播放: 网易云歌曲自动下载缓存, pygame.mixer播放
- 本地音乐: 支持扫描本地文件夹
"""
import os
import tempfile
import threading
import hashlib
import requests
import pygame

pygame.mixer.init()

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://music.163.com/",
}

_temp_dir = os.path.join(tempfile.gettempdir(), "voxel_music")
os.makedirs(_temp_dir, exist_ok=True)

_current_song = None
_playing = False
_paused = False
_volume = 0.7
_local_music_dir = os.path.join(os.path.expanduser("~"), "Music")


# ==================== 网易云 ====================
def _search_netease(keyword, limit=15):
    try:
        url = "https://music.163.com/api/search/get/web"
        params = {"s": keyword, "type": 1, "limit": limit}
        r = requests.get(url, params=params, headers=_HEADERS, timeout=10)
        r.raise_for_status()
        data = r.json()
        songs = []
        for s in data.get("result", {}).get("songs", []):
            songs.append({
                "id": str(s["id"]),
                "name": s["name"],
                "artist": "/".join(a["name"] for a in s.get("artists", [])),
                "album": s.get("album", {}).get("name", ""),
                "duration": s.get("duration", 0) // 1000,
                "source": "网易云",
                "playable": True,
            })
        return songs
    except Exception as e:
        print("网易云搜索失败:", e)
        return []


def _get_netease_url(song_id):
    return "https://music.163.com/song/media/outer/url?id={}.mp3".format(song_id)


# ==================== 酷狗 ====================
def _search_kugou(keyword, limit=15):
    try:
        url = "http://mobilecdn.kugou.com/api/v3/search/song"
        params = {"keyword": keyword, "page": 1, "pagesize": limit}
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
        songs = []
        for s in data.get("data", {}).get("info", []):
            songs.append({
                "id": s.get("hash", ""),
                "name": s.get("songname", ""),
                "artist": s.get("singername", ""),
                "album": s.get("album_name", ""),
                "duration": s.get("duration", 0),
                "source": "酷狗",
                "playable": False,  # 接口加密, 暂不支持播放
            })
        return songs
    except Exception as e:
        print("酷狗搜索失败:", e)
        return []


# ==================== QQ音乐 ====================
def _search_qq(keyword, limit=15):
    try:
        url = "https://c.y.qq.com/soso/fcgi-bin/client_search_cp"
        params = {"w": keyword, "format": "json", "p": 1, "n": limit}
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
        songs = []
        for s in data.get("data", {}).get("song", {}).get("list", []):
            singers = "/".join(x.get("name", "") for x in s.get("singer", []))
            songs.append({
                "id": s.get("songmid", ""),
                "name": s.get("songname", ""),
                "artist": singers,
                "album": s.get("albumname", ""),
                "duration": s.get("interval", 0),
                "source": "QQ音乐",
                "playable": False,  # 接口加密, 暂不支持播放
            })
        return songs
    except Exception as e:
        print("QQ音乐搜索失败:", e)
        return []


# ==================== 聚合搜索 ====================
def search_songs(keyword, limit=15):
    """三平台聚合搜索"""
    results = []

    def _worker(search_fn, kw):
        results.extend(search_fn(kw, limit))

    threads = [
        threading.Thread(target=_worker, args=(_search_netease, keyword)),
        threading.Thread(target=_worker, args=(_search_kugou, keyword)),
        threading.Thread(target=_worker, args=(_search_qq, keyword)),
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=15)

    # 去重(按歌名+歌手)
    seen = set()
    unique = []
    for s in results:
        key = (s["name"], s["artist"])
        if key not in seen:
            seen.add(key)
            unique.append(s)
    return unique


# ==================== 本地音乐 ====================
def set_local_music_dir(path):
    global _local_music_dir
    _local_music_dir = path


def get_local_music_dir():
    return _local_music_dir


def scan_local_music():
    """扫描本地音乐文件夹"""
    songs = []
    if not os.path.exists(_local_music_dir):
        return songs
    exts = (".mp3", ".flac", ".wav", ".ogg", ".m4a", ".aac")
    for root, dirs, files in os.walk(_local_music_dir):
        for f in files:
            if f.lower().endswith(exts):
                name = os.path.splitext(f)[0]
                songs.append({
                    "id": hashlib.md5(f.encode()).hexdigest(),
                    "name": name,
                    "artist": "本地音乐",
                    "album": os.path.basename(root),
                    "duration": 0,
                    "source": "本地",
                    "playable": True,
                    "local_path": os.path.join(root, f),
                })
    return songs


# ==================== 下载与播放 ====================
def _is_valid_audio(path):
    if not os.path.exists(path):
        return False
    if os.path.getsize(path) < 100 * 1024:  # 小于100KB基本是损坏的
        return False
    try:
        with open(path, "rb") as f:
            header = f.read(4)
        # mp3: ID3 or 0xFFFB; flac: fLaC; wav: RIFF
        if (header[:3] == b"ID3" or
            (header[0] == 0xFF and header[1] in (0xFB, 0xF3, 0xF2, 0xFA)) or
            header[:4] == b"fLaC" or
            header[:4] == b"RIFF"):
            return True
        return False
    except Exception:
        return False


def _download_song(song):
    """下载歌曲到临时文件"""
    # 本地音乐直接返回路径
    if song.get("local_path"):
        return song["local_path"]

    if song["source"] != "网易云":
        return None

    song_id = song["id"]
    url = _get_netease_url(song_id)
    tmp_path = os.path.join(_temp_dir, "netease_{}.mp3".format(song_id))

    if os.path.exists(tmp_path) and _is_valid_audio(tmp_path):
        return tmp_path

    try:
        r = requests.get(url, headers=_HEADERS, timeout=30, stream=True)
        r.raise_for_status()
        with open(tmp_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
        if not _is_valid_audio(tmp_path):
            os.remove(tmp_path)
            return None
        return tmp_path
    except Exception as e:
        print("下载失败:", e)
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        return None


def download_to_local(song, save_dir=None):
    """下载歌曲到本地音乐文件夹, 返回保存路径"""
    if song.get("local_path"):
        return song["local_path"]
    if song["source"] != "网易云":
        return None

    # 先下载到临时目录
    tmp_path = _download_song(song)
    if not tmp_path:
        return None

    # 复制到目标目录
    if save_dir is None:
        save_dir = _local_music_dir
    os.makedirs(save_dir, exist_ok=True)

    # 文件名: 歌手 - 歌名.mp3
    safe_name = "{} - {}".format(song["artist"], song["name"]).replace("/", "_").replace("\\", "_")
    for ch in '<>:"|?*':
        safe_name = safe_name.replace(ch, "_")
    save_path = os.path.join(save_dir, safe_name + ".mp3")

    try:
        import shutil
        shutil.copy2(tmp_path, save_path)
        return save_path
    except Exception as e:
        print("复制失败:", e)
        return None


def play_song(song, on_play=None, on_error=None):
    """播放歌曲"""
    global _current_song, _playing, _paused

    def _worker():
        global _playing, _paused
        try:
            if not song.get("playable"):
                if on_error:
                    on_error("{}的歌曲暂不支持播放(接口加密)".format(song["source"]))
                return

            if on_play:
                on_play("正在下载: {} - {}".format(song["name"], song["artist"]))

            path = _download_song(song)
            if not path:
                if on_error:
                    on_error("该歌曲因版权限制无法播放, 请换一首或使用本地音乐")
                return

            pygame.mixer.music.stop()
            pygame.mixer.music.load(path)
            pygame.mixer.music.set_volume(_volume)
            pygame.mixer.music.play()
            _current_song = song
            _playing = True
            _paused = False
            if on_play:
                on_play("正在播放: {} - {}".format(song["name"], song["artist"]))
        except Exception as e:
            if on_error:
                on_error("播放失败: " + str(e))

    threading.Thread(target=_worker, daemon=True).start()


def pause():
    global _paused
    if _playing and not _paused:
        pygame.mixer.music.pause()
        _paused = True


def resume():
    global _paused
    if _playing and _paused:
        pygame.mixer.music.unpause()
        _paused = False


def stop():
    global _playing, _paused
    pygame.mixer.music.stop()
    _playing = False
    _paused = False


def set_volume(val):
    global _volume
    _volume = max(0.0, min(1.0, val))
    pygame.mixer.music.set_volume(_volume)


def get_volume():
    return _volume


def is_playing():
    return _playing


def is_paused():
    return _paused


def get_current_song():
    return _current_song


def get_position():
    if _playing:
        return pygame.mixer.music.get_pos() / 1000.0
    return 0


def cleanup():
    try:
        for f in os.listdir(_temp_dir):
            if f.startswith("netease_") and f.endswith(".mp3"):
                os.remove(os.path.join(_temp_dir, f))
    except Exception:
        pass
