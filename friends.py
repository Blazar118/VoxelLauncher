# -*- coding: utf-8 -*-
"""
VoxelLauncher - 好友系统
本地存储好友列表, 支持服务器状态检测、邀请码联机
"""
import json
import os
import socket
import base64
import urllib.request
from pathlib import Path
from datetime import datetime


FRIENDS_FILE = Path.home() / "AppData" / "Roaming" / ".voxellauncher" / "friends.json"
RECENT_FILE = Path.home() / "AppData" / "Roaming" / ".voxellauncher" / "recent_servers.json"


def _ensure_dir():
    FRIENDS_FILE.parent.mkdir(parents=True, exist_ok=True)


def load_friends():
    """加载好友列表"""
    _ensure_dir()
    if not FRIENDS_FILE.exists():
        return []
    try:
        with open(FRIENDS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def save_friends(friends):
    """保存好友列表"""
    _ensure_dir()
    with open(FRIENDS_FILE, "w", encoding="utf-8") as f:
        json.dump(friends, f, ensure_ascii=False, indent=2)


def add_friend(username, note="", server_ip="", server_port=25565):
    """添加好友"""
    friends = load_friends()
    for f in friends:
        if f["username"].lower() == username.lower():
            return False, "好友已存在"
    friend = {
        "username": username,
        "note": note,
        "server_ip": server_ip,
        "server_port": server_port,
        "uuid": "",
        "added_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "last_online": "",
        "last_ping": 0
    }
    try:
        uuid = get_uuid(username)
        if uuid:
            friend["uuid"] = uuid
    except Exception:
        pass
    friends.append(friend)
    save_friends(friends)
    return True, "添加成功"


def remove_friend(username):
    """删除好友"""
    friends = load_friends()
    new_friends = [f for f in friends if f["username"].lower() != username.lower()]
    if len(new_friends) == len(friends):
        return False, "好友不存在"
    save_friends(new_friends)
    return True, "删除成功"


def update_friend(username, note=None, server_ip=None, server_port=None):
    """更新好友信息"""
    friends = load_friends()
    for f in friends:
        if f["username"].lower() == username.lower():
            if note is not None:
                f["note"] = note
            if server_ip is not None:
                f["server_ip"] = server_ip
            if server_port is not None:
                f["server_port"] = server_port
            save_friends(friends)
            return True, "更新成功"
    return False, "好友不存在"


def get_uuid(username):
    """通过Mojang API获取玩家UUID"""
    try:
        url = f"https://api.mojang.com/users/profiles/minecraft/{username}"
        req = urllib.request.Request(url, headers={"User-Agent": "VoxelLauncher"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("id", "")
    except Exception:
        return ""


def get_avatar_url(username, size=64):
    """获取玩家头像URL"""
    return f"https://crafatar.com/avatars/{username}?size={size}&overlay"


def ping_server(ip, port=25565, timeout=3):
    """
    检测Minecraft服务器是否在线
    返回 (是否在线, 延迟ms, 描述)
    """
    if not ip:
        return False, 0, "未设置服务器IP"
    try:
        start = datetime.now()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((ip, int(port)))
        elapsed = int((datetime.now() - start).total_seconds() * 1000)
        sock.close()
        if result == 0:
            return True, elapsed, "在线 ({}ms)".format(elapsed)
        return False, 0, "离线 (连接被拒绝)"
    except socket.timeout:
        return False, 0, "离线 (连接超时)"
    except Exception as e:
        return False, 0, "离线 ({})".format(str(e)[:30])


def generate_invite_code(ip, port=25565, note=""):
    """
    生成联机邀请码
    格式: base64编码的 ip:port:note
    """
    raw = "{}:{}:{}".format(ip, port, note)
    code = base64.b64encode(raw.encode("utf-8")).decode("utf-8")
    # 去掉末尾的=，更短
    code = code.rstrip("=")
    return "VL-" + code


def parse_invite_code(code):
    """
    解析联机邀请码
    返回 (ip, port, note) 或 None
    """
    try:
        if code.startswith("VL-"):
            code = code[3:]
        # 补全base64填充
        padding = 4 - len(code) % 4
        if padding != 4:
            code += "=" * padding
        raw = base64.b64decode(code).decode("utf-8")
        parts = raw.split(":", 2)
        if len(parts) >= 2:
            ip = parts[0]
            port = int(parts[1])
            note = parts[2] if len(parts) > 2 else ""
            return ip, port, note
    except Exception:
        pass
    return None


def load_recent_servers():
    """加载最近联机记录"""
    _ensure_dir()
    if not RECENT_FILE.exists():
        return []
    try:
        with open(RECENT_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def add_recent_server(ip, port, name=""):
    """添加最近联机记录"""
    recent = load_recent_servers()
    # 去重
    recent = [r for r in recent if not (r["ip"] == ip and r["port"] == port)]
    recent.insert(0, {
        "ip": ip,
        "port": port,
        "name": name,
        "last_joined": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })
    # 只保留最近20条
    recent = recent[:20]
    _ensure_dir()
    with open(RECENT_FILE, "w", encoding="utf-8") as f:
        json.dump(recent, f, ensure_ascii=False, indent=2)


def get_friend_count():
    """获取好友数量"""
    return len(load_friends())
