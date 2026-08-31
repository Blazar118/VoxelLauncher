# -*- coding: utf-8 -*-
"""
联机模块
- 局域网服务器扫描
- 服务器列表管理
- 一键加入服务器
- 一键创建局域网世界
"""
import socket
import threading
import time
import json
import os
import struct
from pathlib import Path


# 局域网扫描配置
LAN_SCAN_PORT = 4445  # Minecraft 局域网发现端口
LAN_SCAN_TIMEOUT = 3  # 扫描超时(秒)


def get_local_ip():
    """获取本机局域网IP"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def get_network_prefix(ip):
    """获取网段前缀 (如 192.168.1)"""
    parts = ip.split(".")
    if len(parts) == 4:
        return ".".join(parts[:3])
    return "192.168.1"


def scan_lan_servers(callback=None):
    """
    扫描局域网内的 Minecraft 服务器
    callback(server_info) 每找到一个服务器就调用
    返回服务器列表
    """
    found_servers = []
    local_ip = get_local_ip()
    prefix = get_network_prefix(local_ip)

    def _check_server(ip, port=25565):
        """检查单个IP是否有MC服务器"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(0.5)
            result = sock.connect_ex((ip, port))
            if result == 0:
                # 尝试获取服务器信息
                info = _get_server_info(ip, port)
                if info:
                    found_servers.append(info)
                    if callback:
                        callback(info)
            sock.close()
        except Exception:
            pass

    # 扫描常见端口 25565
    threads = []
    for i in range(1, 255):
        ip = f"{prefix}.{i}"
        if ip == local_ip:
            continue
        t = threading.Thread(target=_check_server, args=(ip, 25565), daemon=True)
        threads.append(t)
        t.start()
        # 控制并发数
        if len(threads) >= 50:
            for t in threads:
                t.join(timeout=1)
            threads = []

    for t in threads:
        t.join(timeout=1)

    # 同时监听局域网广播 (Minecraft 标准发现机制)
    broadcast_servers = _listen_for_lan_broadcast()
    for srv in broadcast_servers:
        if not any(s["ip"] == srv["ip"] and s["port"] == srv["port"] for s in found_servers):
            found_servers.append(srv)
            if callback:
                callback(srv)

    return found_servers


def _listen_for_lan_broadcast(timeout=3):
    """监听 Minecraft 局域网开放广播"""
    servers = []
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("", LAN_SCAN_PORT))
        sock.settimeout(timeout)

        start = time.time()
        while time.time() - start < timeout:
            try:
                data, addr = sock.recvfrom(1024)
                message = data.decode("utf-8", errors="ignore")
                # 解析 [MOTD]port 格式
                if "[MOTD]" in message and "port" in message.lower():
                    info = _parse_lan_broadcast(message, addr[0])
                    if info:
                        servers.append(info)
            except socket.timeout:
                break
            except Exception:
                continue
        sock.close()
    except Exception:
        pass
    return servers


def _parse_lan_broadcast(message, ip):
    """解析局域网广播消息"""
    try:
        # 格式: [MOTD]description[MOTD]port=12345
        motd_start = message.find("[MOTD]") + len("[MOTD]")
        motd_end = message.find("[MOTD]", motd_start)
        motd = message[motd_start:motd_end] if motd_end > motd_start else "Minecraft World"

        port_str = message.lower().split("port=")[-1].strip()
        port = int(port_str.split("\n")[0].split(" ")[0])

        return {
            "name": motd,
            "ip": ip,
            "port": port,
            "type": "lan",
            "players": "?",
            "version": "?"
        }
    except Exception:
        return None


def _get_server_info(ip, port):
    """获取服务器详细信息 (Minecraft Server List Ping)"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        sock.connect((ip, port))

        # 发送握手包
        handshake = b"\x00"  # packet id
        handshake += _varint(47)  # protocol version
        handshake += _varint(len(ip)) + ip.encode("utf-8")
        handshake += struct.pack(">H", port)
        handshake += _varint(1)  # next state: status

        sock.sendall(_varint(len(handshake)) + handshake)
        sock.sendall(b"\x01\x00")  # status request

        # 读取响应
        length = _read_varint(sock)
        if length <= 0:
            sock.close()
            return None

        packet_id = _read_varint(sock)
        json_length = _read_varint(sock)
        data = b""
        while len(data) < json_length:
            chunk = sock.recv(json_length - len(data))
            if not chunk:
                break
            data += chunk

        sock.close()

        info = json.loads(data.decode("utf-8"))
        return {
            "name": info.get("description", {}).get("text", "Minecraft Server")
                    if isinstance(info.get("description"), dict)
                    else str(info.get("description", "Minecraft Server")),
            "ip": ip,
            "port": port,
            "type": "server",
            "players": f"{info.get('players', {}).get('online', '?')}/{info.get('players', {}).get('max', '?')}",
            "version": info.get("version", {}).get("name", "?")
        }
    except Exception:
        # 连不上但端口开着, 返回基本信息
        return {
            "name": f"Minecraft Server ({ip})",
            "ip": ip,
            "port": port,
            "type": "server",
            "players": "?",
            "version": "?"
        }


def _varint(value):
    """编码 VarInt"""
    result = b""
    while True:
        byte = value & 0x7F
        value >>= 7
        if value:
            result += bytes([byte | 0x80])
        else:
            result += bytes([byte])
            break
    return result


def _read_varint(sock):
    """读取 VarInt"""
    result = 0
    shift = 0
    while True:
        byte = sock.recv(1)
        if not byte:
            return 0
        value = byte[0]
        result |= (value & 0x7F) << shift
        if not (value & 0x80):
            break
        shift += 7
        if shift > 35:
            break
    return result


class ServerList:
    """服务器列表管理"""

    def __init__(self):
        self.config_dir = Path(os.environ.get("APPDATA", ".")) / "VoxelLauncher"
        self.config_file = self.config_dir / "servers.json"
        self.servers = []
        self._load()

    def _load(self):
        """加载服务器列表"""
        try:
            if self.config_file.exists():
                with open(self.config_file, "r", encoding="utf-8") as f:
                    self.servers = json.load(f)
        except Exception:
            self.servers = []

    def _save(self):
        """保存服务器列表"""
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self.servers, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def add(self, name, ip, port=25565):
        """添加服务器"""
        server = {
            "name": name,
            "ip": ip,
            "port": port,
            "type": "saved",
            "players": "?",
            "version": "?"
        }
        self.servers.append(server)
        self._save()
        return server

    def remove(self, index):
        """删除服务器"""
        if 0 <= index < len(self.servers):
            self.servers.pop(index)
            self._save()

    def get_all(self):
        """获取所有服务器"""
        return self.servers.copy()

    def refresh(self, callback=None):
        """刷新所有服务器状态"""
        def _worker():
            for i, srv in enumerate(self.servers):
                try:
                    info = _get_server_info(srv["ip"], srv["port"])
                    if info:
                        self.servers[i].update({
                            "players": info["players"],
                            "version": info["version"],
                            "name": info["name"]
                        })
                        if callback:
                            callback(i, self.servers[i])
                except Exception:
                    pass
            self._save()

        threading.Thread(target=_worker, daemon=True).start()


def create_lan_world(instance_dir, port=25565):
    """
    创建局域网世界 (通过修改 options.txt 或启动参数)
    返回是否成功
    """
    try:
        # Minecraft 局域网开放是在游戏内操作的, 启动器能做的是:
        # 1. 确保端口可用
        # 2. 提示用户在游戏内按 ESC -> 对局域网开放
        # 3. 或者通过启动参数设置

        # 检查端口是否被占用
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(("127.0.0.1", port))
        sock.close()

        if result == 0:
            return False, f"端口 {port} 已被占用"

        return True, f"请在游戏内按 ESC -> 对局域网开放 -> 选择端口 {port}"
    except Exception as e:
        return False, str(e)


def get_server_address(server):
    """获取服务器地址字符串"""
    if server["port"] == 25565:
        return server["ip"]
    return f"{server['ip']}:{server['port']}"
