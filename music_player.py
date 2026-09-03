# -*- coding: utf-8 -*-
"""
VoxelLauncher - 多平台音乐聚合播放器
- 搜索: 网易云 + 酷狗 + QQ音乐 三平台聚合
- 播放: 网易云歌曲自动下载缓存, pygame.mixer播放
- 歌词: 读取mp3内嵌ID3歌词或同目录.lrc文件
- 本地音乐: 支持扫描本地文件夹
"""
import os
import re
import json
import time
import tempfile
import threading
import hashlib
import random
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
_lyrics = []  # [(time_sec, text), ...]
_lyric_source = ""
_pause_pos = 0.0  # 暂停时的播放位置
_current_path = None  # 当前播放的文件路径
_translated_lyrics = {}  # {index: 翻译文本}
_follow_system_volume = True  # 是否跟随系统音量
# ---- 播放时钟(比pygame.get_pos更可靠) ----
_play_clock_start = None   # 开始播放时的墙钟时间
_paused_accum = 0.0        # 累计暂停时长
_pause_ts = None           # 最近一次暂停的墙钟时间
_lyric_offset = 0.0        # 歌词同步微调偏移(秒, 正=歌词提前)

# ---- 数据持久化(历史/收藏) ----
_data_dir = os.path.join(os.path.expanduser("~"), ".voxel_music")
os.makedirs(_data_dir, exist_ok=True)
_history_file = os.path.join(_data_dir, "history.json")
_fav_file = os.path.join(_data_dir, "favorites.json")
_play_mode = "order"  # order顺序 / loop列表循环 / single单曲循环 / shuffle随机
_current_playlist = []  # 当前播放列表
_history = []  # [(song, play_time_str), ...] 新歌在前
_favorites = []  # [song, ...]
_is_pure_music = False  # 当前歌曲是否纯音乐(无歌词)


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
                "playable": False,
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
                "playable": False,
            })
        return songs
    except Exception as e:
        print("QQ音乐搜索失败:", e)
        return []


# ==================== 聚合搜索 ====================
def search_songs(keyword, limit=15):
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


# ==================== 歌词 ====================
def _parse_lrc(text):
    """解析LRC歌词, 返回[(time_sec, text), ...], 自动过滤作词/作曲等元信息行"""
    lines = []
    pattern = re.compile(r'\[(\d+):(\d+)(?:\.(\d+))?\](.*)')
    meta_keys = ("作词", "作曲", "编曲", "作編曲", "訳詞", "歌詞", "歌词", "作詞", "作曲者", "OP", "ED")
    for line in text.split('\n'):
        line = line.strip()
        if not line:
            continue
        m = pattern.match(line)
        if m:
            mins = int(m.group(1))
            secs = int(m.group(2))
            ms = int(m.group(3) or 0)
            time = mins * 60 + secs + ms / 1000.0
            txt = m.group(4).strip()
            if not txt:
                continue
            # 过滤元信息行(作词/作曲/编曲等)
            if txt.startswith(meta_keys):
                continue
            lines.append((time, txt))
    lines.sort(key=lambda x: x[0])
    return lines


def _read_id3_lyrics(path):
    """从mp3的ID3标签读取歌词"""
    try:
        from mutagen.id3 import ID3, USLT
        audio = ID3(path)
        for key in audio.keys():
            if key.startswith('USLT'):
                frame = audio[key]
                if hasattr(frame, 'text') and frame.text:
                    return frame.text
        return None
    except Exception:
        return None


def _read_lrc_file(audio_path):
    """从同目录.lrc文件读取歌词"""
    try:
        base = os.path.splitext(audio_path)[0]
        lrc_path = base + ".lrc"
        if os.path.exists(lrc_path):
            with open(lrc_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        return None
    except Exception:
        return None


def _fetch_netease_lyrics(song_id):
    """从网易云API获取歌词"""
    try:
        url = "https://music.163.com/api/song/lyric"
        params = {"id": song_id, "lv": 1, "kv": 1, "tv": -1}
        r = requests.get(url, params=params, headers=_HEADERS, timeout=10)
        r.raise_for_status()
        data = r.json()
        lrc = data.get("lrc", {}).get("lyric", "")
        if lrc and len(lrc) > 10:
            return lrc
        return None
    except Exception as e:
        print("网易云歌词获取失败:", e)
        return None


def load_lyrics(audio_path, song=None):
    """加载歌词, 返回解析后的列表. 优先级: .lrc文件 > ID3内嵌 > 网易云API"""
    global _lyrics, _lyric_source
    _lyrics = []
    _lyric_source = ""

    # 1. 先试.lrc文件
    lrc_text = _read_lrc_file(audio_path)
    if lrc_text:
        _lyrics = _parse_lrc(lrc_text)
        _lyric_source = "lrc文件"
        if _lyrics:
            return _lyrics

    # 2. 再试ID3内嵌歌词
    id3_text = _read_id3_lyrics(audio_path)
    if id3_text:
        _lyrics = _parse_lrc(id3_text)
        _lyric_source = "ID3内嵌"
        if _lyrics:
            return _lyrics

    # 3. 最后试网易云API(仅网易云歌曲)
    if song and song.get("source") == "网易云":
        api_text = _fetch_netease_lyrics(song["id"])
        if api_text:
            _lyrics = _parse_lrc(api_text)
            _lyric_source = "网易云API"
            if _lyrics:
                return _lyrics

    return []


def get_lyrics():
    return _lyrics


def get_current_lyric_index(position):
    """根据播放位置返回当前歌词索引"""
    if not _lyrics:
        return -1
    idx = -1
    for i, (time, text) in enumerate(_lyrics):
        if position >= time:
            idx = i
        else:
            break
    return idx


# ==================== 下载与播放 ====================
def _is_valid_audio(path):
    if not os.path.exists(path):
        return False
    if os.path.getsize(path) < 100 * 1024:
        return False
    try:
        with open(path, "rb") as f:
            header = f.read(4)
        if (header[:3] == b"ID3" or
            (header[0] == 0xFF and header[1] in (0xFB, 0xF3, 0xF2, 0xFA)) or
            header[:4] == b"fLaC" or
            header[:4] == b"RIFF"):
            return True
        return False
    except Exception:
        return False


def _download_song(song):
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
    if song.get("local_path"):
        return song["local_path"]
    if song["source"] != "网易云":
        return None

    tmp_path = _download_song(song)
    if not tmp_path:
        return None

    if save_dir is None:
        save_dir = _local_music_dir
    os.makedirs(save_dir, exist_ok=True)

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


def play_song(song, on_play=None, on_error=None, on_lyrics=None):
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

            # 加载歌词(优先本地, 其次网易云API)
            global _is_pure_music
            load_lyrics(path, song=song)
            _is_pure_music = not bool(_lyrics)
            if on_lyrics:
                on_lyrics(_lyrics if _lyrics else [])

            # 播放
            try:
                pygame.mixer.music.stop()
                pygame.mixer.music.load(path)
                pygame.mixer.music.set_volume(_volume)
                pygame.mixer.music.play()
                _current_song = song
                _current_path = path
                _playing = True
                _paused = False
                _translated_lyrics = {}
                _play_clock_start = time.time()
                _paused_accum = 0.0
                _pause_ts = None
                _lyric_offset = 0.0
                # 记录播放历史
                try:
                    record_history(song)
                except Exception:
                    pass
                if on_play:
                    on_play("正在播放: {} - {}".format(song["name"], song["artist"]))
            except Exception as play_err:
                # 播放失败, 但不要误报"找不到文件"
                if on_error:
                    on_error("播放器错误: " + str(play_err))
                return

        except Exception as e:
            if on_error:
                on_error("播放失败: " + str(e))

    threading.Thread(target=_worker, daemon=True).start()


def pause():
    global _paused, _pause_pos, _pause_ts
    if _playing and not _paused:
        _pause_pos = get_position()
        _pause_ts = time.time()
        pygame.mixer.music.pause()
        _paused = True


def resume():
    global _paused, _paused_accum, _pause_ts, _play_clock_start
    if _playing and _paused:
        if _pause_ts is not None:
            _paused_accum += time.time() - _pause_ts
            _pause_ts = None
        # 重新校准播放时钟: 让墙钟位置对准暂停位置
        _play_clock_start = time.time() - _paused_accum - _pause_pos + _lyric_offset
        pygame.mixer.music.unpause()
        _paused = False
        # 用set_pos确保从暂停处继续(比play(start=)更可靠)
        try:
            pygame.mixer.music.set_pos(max(0, _pause_pos - 0.3))
        except Exception:
            pass
        # 验证是否真的在播放
        import time as _t
        _t.sleep(0.2)
        if not pygame.mixer.music.get_busy():
            # unpause没生效, 重新加载
            try:
                if _current_path and os.path.exists(_current_path):
                    pygame.mixer.music.stop()
                    pygame.mixer.music.load(_current_path)
                    pygame.mixer.music.set_volume(_volume)
                    pygame.mixer.music.play()
                    import time as t2
                    t2.sleep(0.1)
                    pygame.mixer.music.set_pos(max(0, _pause_pos - 0.3))
                else:
                    pygame.mixer.music.play()
            except Exception as e:
                print("resume fallback失败:", e)


def stop():
    global _playing, _paused, _is_pure_music
    pygame.mixer.music.stop()
    _playing = False
    _paused = False
    _is_pure_music = False


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
    """返回当前播放位置(秒), 用墙钟计时, 比pygame.get_pos更可靠"""
    global _play_clock_start, _paused_accum, _pause_ts
    if not _playing:
        return 0
    if _paused:
        return max(0, _pause_pos - _lyric_offset)
    if _play_clock_start is None:
        return 0
    pos = time.time() - _play_clock_start - _paused_accum
    return max(0, pos - _lyric_offset)


def set_lyric_offset(delta):
    """微调歌词同步偏移(秒), 正=歌词显示提前"""
    global _lyric_offset
    _lyric_offset += delta
    _lyric_offset = max(-60.0, min(60.0, _lyric_offset))
    return _lyric_offset


def get_lyric_offset():
    return _lyric_offset


def cleanup():
    try:
        for f in os.listdir(_temp_dir):
            if f.startswith("netease_") and f.endswith(".mp3"):
                os.remove(os.path.join(_temp_dir, f))
    except Exception:
        pass


def get_system_volume():
    """读取Windows系统音量(0-1)"""
    try:
        import ctypes
        # 用Windows API读取主音量
        try:
            from ctypes import wintypes
            # 简化方案: 用pycaw如果可用
            try:
                from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
                from ctypes import cast, POINTER
                from comtypes import CLSCTX_ALL
                devices = AudioUtilities.GetSpeakers()
                interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                volume = cast(interface, POINTER(IAudioEndpointVolume))
                return volume.GetMasterVolumeLevelScalar()
            except ImportError:
                pass
        except Exception:
            pass
        # fallback: 返回当前音量(不跟随)
        return _volume
    except Exception:
        return _volume


def set_follow_system_volume(follow):
    """设置是否跟随系统音量"""
    global _follow_system_volume
    _follow_system_volume = follow


def is_follow_system_volume():
    return _follow_system_volume


def sync_system_volume():
    """如果跟随系统音量, 同步到播放器"""
    if _follow_system_volume:
        vol = get_system_volume()
        if 0 <= vol <= 1:
            set_volume(vol)
            return vol
    return _volume


def translate_lyrics(lyrics_list, provider=None, api_key=None):
    """
    用AI翻译歌词, 返回 (翻译dict, 错误信息)
    翻译dict: {index: 翻译文本}
    """
    global _translated_lyrics
    if not lyrics_list:
        return {}, ""
    try:
        import ai_chat
        chat = ai_chat.ai_chat
        if provider:
            chat.set_provider(provider)
        if api_key:
            chat.set_api_key(api_key)
        if not chat.is_configured():
            return {}, "未配置AI API key, 请在设置页配置"
        # 歌词列表已是过滤后的(元信息行已在_parse_lrc去掉), 这里再保险过滤一次
        filtered = []
        for i, (t, text) in enumerate(lyrics_list):
            if text.strip():
                filtered.append((i, text))
        if not filtered:
            return {}, ""
        # 把歌词拼成文本翻译
        lines = [f"{i+1}. {text}" for i, (i2, text) in enumerate(filtered)]
        text = "\n".join(lines)
        prompt = f"""你是一个歌词翻译专家。请把下面的歌词翻译成中文, 保持序号对应。
要求:
1. 只输出翻译后的歌词, 每行格式为"序号. 翻译内容"
2. 保持原有的情感和意境
3. 如果某行已经是中文, 直接原样输出
4. 不要输出任何解释

歌词:
{text}"""
        provider_config = chat.providers.get(chat.provider)
        if not provider_config:
            return {}, "未知的AI服务商"
        url = provider_config["url"]
        models_to_try = [provider_config["model"]]
        if "backup_models" in provider_config:
            models_to_try.extend(provider_config["backup_models"])

        headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer " + chat.api_key,
        }
        messages = [
            {"role": "system", "content": "你是一个专业的歌词翻译, 只输出翻译结果, 不要解释。"},
            {"role": "user", "content": prompt},
        ]

        import time as _time
        last_error = "翻译失败"
        # 每个模型最多尝试2次
        for model in models_to_try:
            data = {
                "model": model,
                "messages": messages,
                "temperature": 0.3,
                "max_tokens": 1000,
            }
            for attempt in range(2):
                try:
                    resp = requests.post(url, headers=headers, json=data, timeout=40)
                    if resp.status_code in (401, 403):
                        last_error = "API认证失败, 请检查API key"
                        return {}, last_error
                    if resp.status_code == 429:
                        last_error = "请求太频繁(限流), 请稍后再试"
                        _time.sleep(6)
                        continue
                    if resp.status_code >= 500:
                        last_error = "AI服务暂时不可用(HTTP {})".format(resp.status_code)
                        _time.sleep(4)
                        continue
                    resp.raise_for_status()
                    result_json = resp.json()
                    if "choices" in result_json and result_json["choices"]:
                        result = result_json["choices"][0]["message"]["content"].strip()
                        # 解析翻译结果
                        translated = {}
                        for line in result.split("\n"):
                            line = line.strip()
                            m = re.match(r'^(\d+)[.、．:：)\]]\s*(.+)$', line)
                            if m:
                                try:
                                    idx = int(m.group(1)) - 1
                                    if 0 <= idx < len(filtered):
                                        translated[filtered[idx][0]] = m.group(2).strip()
                                except (ValueError, IndexError):
                                    continue
                        if translated:
                            _translated_lyrics = translated
                            print("翻译完成, 行数:", len(translated), "模型:", model)
                            return translated, ""
                        last_error = "AI返回内容无法解析"
                        break
                    else:
                        last_error = "AI返回格式异常"
                        break
                except requests.exceptions.Timeout:
                    last_error = "翻译请求超时(网络慢), 请重试"
                except requests.exceptions.RequestException as e:
                    last_error = "翻译请求失败: " + str(e)[:80]
                    break
                except Exception as e:
                    last_error = "翻译异常: " + str(e)[:80]
                    break
            # 换备用模型前等2秒
            _time.sleep(2)
        return {}, last_error
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {}, "翻译出错: " + str(e)[:80]


def get_translated_lyrics():
    return _translated_lyrics


def is_foreign_lyrics(lyrics_list):
    """检测是否是外语歌词(非中文为主)"""
    if not lyrics_list:
        return False
    chinese_count = 0
    total_count = 0
    for t, text in lyrics_list:
        for ch in text:
            if '\u4e00' <= ch <= '\u9fff':
                chinese_count += 1
            total_count += 1
    if total_count == 0:
        return False
    # 中文字符占比低于50%认为是外语
    return (chinese_count / total_count) < 0.5

# ==================== 历史/收藏/播放模式 ====================
def _load_json(path, default):
    try:
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as fp:
                return json.load(fp)
    except Exception as e:
        print("读取数据失败:", e)
    return default


def _save_json(path, data):
    try:
        with open(path, 'w', encoding='utf-8') as fp:
            json.dump(data, fp, ensure_ascii=False, indent=2)
    except Exception as e:
        print("保存数据失败:", e)


def _load_history():
    global _history
    _history = _load_json(_history_file, [])


def _load_favorites():
    global _favorites
    _favorites = _load_json(_fav_file, [])


def _song_key(song):
    """生成歌曲唯一key"""
    if song.get("local_path"):
        return "local:" + song["local_path"]
    return song.get("source", "") + ":" + str(song.get("id", ""))


def record_history(song):
    """记录播放历史(最近200首, 去重, 新歌在前)"""
    global _history
    try:
        if not _history:
            _load_history()
        import time as _t
        entry = {"song": song, "time": _t.strftime("%m-%d %H:%M")}
        key = _song_key(song)
        _history = [e for e in _history if _song_key(e.get("song", {})) != key]
        _history.insert(0, entry)
        _history = _history[:200]
        _save_json(_history_file, _history)
    except Exception as e:
        print("记录历史失败:", e)


def get_history():
    """返回历史列表[(song, time_str), ...]"""
    if not _history:
        _load_history()
    return [(e.get("song", {}), e.get("time", "")) for e in _history]


def toggle_favorite(song):
    """收藏/取消收藏, 返回是否已收藏"""
    global _favorites
    if not _favorites:
        _load_favorites()
    key = _song_key(song)
    _favorites = [f for f in _favorites if _song_key(f) != key]
    _save_json(_fav_file, _favorites)
    _favorites.insert(0, song)
    _save_json(_fav_file, _favorites)
    return True


def remove_favorite(song):
    global _favorites
    if not _favorites:
        _load_favorites()
    key = _song_key(song)
    _favorites = [f for f in _favorites if _song_key(f) != key]
    _save_json(_fav_file, _favorites)


def is_favorite(song):
    if not _favorites:
        _load_favorites()
    key = _song_key(song)
    return any(_song_key(f) == key for f in _favorites)


def get_favorites():
    if not _favorites:
        _load_favorites()
    return list(_favorites)


def set_play_mode(mode):
    global _play_mode
    if mode in ("order", "loop", "single", "shuffle"):
        _play_mode = mode
    return _play_mode


def get_play_mode():
    return _play_mode


def set_playlist(playlist):
    """设置当前播放列表"""
    global _current_playlist
    _current_playlist = list(playlist)


def get_playlist():
    return _current_playlist


def get_next_song(current_song):
    """根据播放模式返回下一首歌(或None)"""
    if not _current_playlist:
        return None
    n = len(_current_playlist)
    if current_song is None:
        return _current_playlist[0] if _current_playlist else None
    if _play_mode == "single":
        return current_song
    try:
        cur_idx = _current_playlist.index(current_song)
    except ValueError:
        # 当前歌不在列表里(可能来自历史/收藏), 从列表开头播
        return _current_playlist[0] if _play_mode == "shuffle" else _current_playlist[0]
    if _play_mode == "shuffle":
        return _current_playlist[random.randint(0, n - 1)]
    # order / loop
    nxt = cur_idx + 1
    if nxt >= n:
        if _play_mode == "loop":
            return _current_playlist[0]
        return None  # 顺序播放到结尾停止
    return _current_playlist[nxt]


def is_music_ended():
    """检测当前歌曲是否播放完毕(非暂停状态)"""
    if not _playing or _paused:
        return False
    try:
        if pygame.mixer.music.get_busy():
            return False
        # 不busy且位置>0.5秒, 说明播完了
        if get_position() > 0.5:
            return True
    except Exception:
        return False
    return False


def is_pure_music():
    return _is_pure_music
