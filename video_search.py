# -*- coding: utf-8 -*-
"""
VoxelLauncher - 在线电视模块(video_search.py)
平台视频聚合搜索 + 跳转播放。
- B站: 启动器内结构化搜索(标题/BV号/时长/作者/播放量), 点击后浏览器播放
- 腾讯/优酷/爱奇艺/芒果/抖音: 接口有风控, 直接打开平台官方搜索页(可正常登录、观看)
"""
import re
import time
import html as html_mod
import urllib.parse

import requests

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")

# 平台定义: id -> (显示名, 搜索页URL模板, 主页URL)
PLATFORMS = {
    "bilibili": ("B站", "https://search.bilibili.com/all?keyword={q}", "https://www.bilibili.com"),
    "tencent": ("腾讯视频", "https://v.qq.com/x/search/?q={q}", "https://v.qq.com"),
    "youku": ("优酷", "https://so.youku.com/search_video/q_{q}", "https://www.youku.com"),
    "iqiyi": ("爱奇艺", "https://so.iqiyi.com/so/q_{q}", "https://www.iqiyi.com"),
    "mgtv": ("芒果TV", "https://so.mgtv.com/so?k={q}", "https://www.mgtv.com"),
    "douyin": ("抖音", "https://www.douyin.com/search/{q}", "https://www.douyin.com"),
}

_session = None


def _get_session():
    global _session
    if _session is None:
        _session = requests.Session()
        _session.headers.update({"User-Agent": UA})
    return _session


def platform_names():
    """返回 [(id, 显示名), ...]"""
    return [(k, v[0]) for k, v in PLATFORMS.items()]


def platform_home(pid):
    """平台主页(用于登录/打开) - 第3个元素才是首页URL"""
    info = PLATFORMS.get(pid)
    return info[2] if info else ""


def platform_search_url(pid, keyword):
    """平台搜索页 URL"""
    info = PLATFORMS.get(pid)
    if not info:
        return ""
    return info[1].format(q=urllib.parse.quote(keyword))


def video_url(pid, vid):
    """根据平台与视频ID生成播放页 URL"""
    pid = (pid or "").lower()
    if pid == "bilibili":
        return "https://www.bilibili.com/video/" + vid
    return vid  # 其他平台直接用完整 URL


def _clean(s):
    return html_mod.unescape(re.sub(r"<[^>]+>", "", s or "")).strip()


def search_bilibili(keyword, limit=30):
    """
    B站结构化搜索, 返回 [{bvid, title, author, duration, play}]
    失败返回 []。
    """
    try:
        S = _get_session()
        # 先访问主页拿 cookie, 降低风控概率
        try:
            S.get("https://www.bilibili.com", timeout=8)
            time.sleep(0.3)
        except Exception:
            pass
        q = urllib.parse.quote(keyword)
        url = "https://search.bilibili.com/all?keyword=" + q
        r = S.get(url, headers={"Referer": "https://www.bilibili.com"}, timeout=12)
        text = r.text
        blocks = re.split(r'<div class="bili-video-card__wrap"', text)
        items = []
        for blk in blocks[1:]:
            m_bv = re.search(r'//www\.bilibili\.com/video/(BV[0-9A-Za-z]{10})', blk)
            if not m_bv:
                continue
            bvid = m_bv.group(1)
            m_t = re.search(r'title="([^"]+)"', blk)
            title = _clean(m_t.group(1)) if m_t else ""
            # 作者
            m_a = (re.search(r'class="bili-video-card__info--author"[^>]*>([^<]+)<', blk)
                   or re.search(r'class="up-name"[^>]*>([^<]+)<', blk))
            author = _clean(m_a.group(1)) if m_a else ""
            # 时长
            m_d = re.search(r'bili-video-card__stats__duration[^>]*>([^<]+)<', blk)
            duration = _clean(m_d.group(1)) if m_d else ""
            # 播放量
            m_p = re.search(r'bili-video-card__stats--item[^>]*>([^<]+)<', blk)
            play = _clean(m_p.group(1)) if m_p else ""
            items.append({
                "bvid": bvid, "title": title, "author": author,
                "duration": duration, "play": play,
            })
            if len(items) >= limit:
                break
        return items
    except Exception:
        return []


if __name__ == "__main__":
    # 自测
    res = search_bilibili("奥特曼", limit=5)
    print("B站结果:", len(res))
    for it in res:
        print(" -", it["bvid"], "|", it["title"][:40], "|", it["duration"], "|", it["author"])
