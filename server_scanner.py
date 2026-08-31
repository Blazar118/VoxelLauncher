# -*- coding: utf-8 -*-
"""
VoxelLauncher - 服务器扫描与收藏
局域网扫描、服务器状态查询、收藏夹管理
"""
import json
import socket
import struct
import threading
import time
from pathlib import Path
from datetime import datetime


FAVORITES_FILE = Path.home() / "AppData" / "Roaming" / ".voxellauncher" / "server_favorites.json"


def _ensure_dir():
    FAVORITES_FILE.parent.mkdir(parents=True, exist_ok=True)


def load_favorites():
    """加载服务器收藏"""
    _ensure_dir()
    if not FAVORITES_FILE.exists():
        return []
    try:
        with open(FAVORITES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def save_favorites(favorites):
    """保存服务器收藏"""
    _ensure_dir()
    with open(FAVORITES_FILE, "w", encoding="utf-8") as f:
        json.dump(favorites, f, ensure_ascii=False, indent=2)


def add_favorite(name, ip, port=25565):
    """添加服务器收藏"""
    favorites = load_favorites()
    for s in favorites:
        if s["ip"] == ip and s["port"] == port:
            return False, "服务器已收藏"
    favorites.append({
        "name": name,
        "ip": ip,
        "port": port,
        "added_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })
    save_favorites(favorites)
    return True, "收藏成功"


def remove_favorite(ip, port):
    """删除服务器收藏"""
    favorites = load_favorites()
    new = [s for s in favorites if not (s["ip"] == ip and s["port"] == port)]
    if len(new) == len(favorites):
        return False, "未找到"
    save_favorites(new)
    return True, "已删除"


def get_local_ip():
    """获取本机局域网IP"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        try:
            return socket.gethostbyname(socket.gethostname())
        except Exception:
            return "127.0.0.1"


def get_network_prefix(ip):
    """获取网段前缀 (如 192.168.1)"""
    parts = ip.split(".")
    if len(parts) == 4:
        return ".".join(parts[:3])
    return "192.168.1"


def scan_lan(port=25565, timeout=0.3, progress_callback=None):
    """
    扫描局域网内的Minecraft服务器
    返回 [(ip, port, latency_ms), ...]
    """
    local_ip = get_local_ip()
    prefix = get_network_prefix(local_ip)
    found = []
    threads = []
    results = []

    def _check(ip, port):
        try:
            start = time.time()
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((ip, port))
            elapsed = int((time.time() - start) * 1000)
            sock.close()
            if result == 0:
                results.append((ip, port, elapsed))
        except Exception:
            pass

    # 扫描 1-254
    for i in range(1, 255):
        ip = "{}.{}".format(prefix, i)
        if ip == local_ip:
            continue
        t = threading.Thread(target=_check, args=(ip, port), daemon=True)
        threads.append(t)
        t.start()
        # 控制并发，每50个等一下
        if len(threads) % 50 == 0:
            time.sleep(0.1)
        if progress_callback:
            progress_callback(i, 254)

    for t in threads:
        t.join(timeout=1)

    return results


def query_server(ip, port=25565, timeout=3):
    """
    查询Minecraft服务器信息（使用Server List Ping协议）
    返回 {online, latency, version, players_max, players_online, motd}
    """
    result = {
        "online": False,
        "latency": 0,
        "version": "",
        "players_max": 0,
        "players_online": 0,
        "motd": ""
    }
    try:
        start = time.time()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect((ip, int(port)))
        result["latency"] = int((time.time() - start) * 1000)

        # 发送握手包
        # 协议版本 47 (1.8+)，实际上用-1表示只获取状态
        handshake = b"\x00"  # packet id
        handshake += b"\x00"  # protocol version (0 for status)
        # server address
        addr_bytes = ip.encode("utf-8")
        handshake += struct.pack(">B", len(addr_bytes)) + addr_bytes
        # port
        handshake += struct.pack(">H", int(port))
        # next state (1 = status)
        handshake += b"\x01"
        # 包长度
        packet = struct.pack(">B", len(handshake)) + handshake
        sock.sendall(packet)

        # 发送状态请求
        sock.sendall(b"\x01\x00")

        # 读取响应
        def _read_varint():
            value = 0
            position = 0
            while True:
                byte = sock.recv(1)
                if not byte:
                    return None
                byte = ord(byte)
                value |= (byte & 0x7F) << position
                if (byte & 0x80) == 0:
                    break
                position += 7
                if position > 32:
                    return None
            return value

        length = _read_varint()
        if length is None or length <= 0:
            result["online"] = True
            sock.close()
            return result

        packet_id = _read_varint()
        if packet_id != 0:
            result["online"] = True
            sock.close()
            return result

        # 读取JSON长度
        json_length = _read_varint()
        if json_length is None:
            result["online"] = True
            sock.close()
            return result

        # 读取JSON数据
        data = b""
        while len(data) < json_length:
            chunk = sock.recv(json_length - len(data))
            if not chunk:
                break
            data += chunk

        sock.close()

        try:
            info = json.loads(data.decode("utf-8"))
            result["online"] = True
            if "version" in info:
                result["version"] = info["version"].get("name", "")
            if "players" in info:
                result["players_max"] = info["players"].get("max", 0)
                result["players_online"] = info["players"].get("online", 0)
            if "description" in info:
                desc = info["description"]
                if isinstance(desc, str):
                    result["motd"] = desc
                elif isinstance(desc, dict):
                    result["motd"] = desc.get("text", str(desc))
        except Exception:
            result["online"] = True

    except socket.timeout:
        result["online"] = False
    except Exception:
        result["online"] = False

    return result


def scan_lan_async(port=25565, callback=None):
    """异步扫描局域网，完成后调用 callback(results)"""
    def _run():
        results = scan_lan(port)
        if callback:
            callback(results)
    threading.Thread(target=_run, daemon=True).start()
