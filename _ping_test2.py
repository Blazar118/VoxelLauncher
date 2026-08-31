# -*- coding: utf-8 -*-
"""实测多个纯生存候选服务器"""
import socket, struct, json, time

def ping_server(host, port=25565, timeout=5):
    try:
        s = socket.create_connection((host, port), timeout=timeout)
        host_b = host.encode('utf-8')
        handshake = b'\x00\x00' + bytes([len(host_b)]) + host_b + struct.pack('>H', port) + b'\x01'
        s.sendall(bytes([len(handshake)]) + handshake)
        s.sendall(b'\x01\x00')
        time.sleep(0.5)
        def read_varint():
            num = 0
            for i in range(5):
                b = s.recv(1)
                if not b:
                    break
                num |= (b[0] & 0x7f) << (7 * i)
                if not (b[0] & 0x80):
                    break
            return num
        ln = read_varint()
        s.recv(1)
        data = b''
        while len(data) < ln - 1:
            chunk = s.recv(ln - 1 - len(data))
            if not chunk:
                break
            data += chunk
        s.close()
        if data:
            slen = data[0]
            return json.loads(data[1:1 + slen].decode('utf-8', errors='replace'))
    except Exception as e:
        return {'error': str(e)}
    return {'error': 'no data'}

candidates = [
    # 纯生存候选
    ('mczym.cn', 25565),              # zym 纯净生存
    ('mchlt.cn', 25565),              # 坞中客 1.21.1纯净生存
    ('喵.fun', 25565),                # 喵方
    ('mc.craftcraftia.top', 25565),   # CraftCraftia 纯净生存
    ('play.eternalmc.net', 25565),    # EternalMC (有响应那个)
]
for host, port in candidates:
    st = ping_server(host, port)
    if 'error' in st:
        print('{}:{} -> 不可用 ({})'.format(host, port, str(st['error'])[:45]))
    else:
        desc = st.get('description', {})
        if isinstance(desc, dict):
            desc = desc.get('text', desc)
        ver = st.get('version', {}).get('name')
        pl = st.get('players', {})
        print('{}:{} -> OK 在线 | {} | 版本:{} | 玩家:{}/{}'.format(
            host, port, str(desc)[:40], ver, pl.get('online'), pl.get('max')))
