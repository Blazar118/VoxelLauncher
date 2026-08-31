# -*- coding: utf-8 -*-
"""更稳健的服务器ping - 完整读取响应包"""
import socket, struct, json, time

def ping_server(host, port=25565, timeout=5):
    try:
        s = socket.create_connection((host, port), timeout=timeout)
        s.settimeout(timeout)
        host_b = host.encode('utf-8')
        # 握手: protocol=47(旧) 用 0 也行
        handshake = b'\x00\x00' + bytes([len(host_b)]) + host_b + struct.pack('>H', port) + b'\x01'
        s.sendall(bytes([len(handshake)]) + handshake)
        # 状态请求 packet: id=0
        s.sendall(b'\x01\x00')

        # 读取 varint 长度
        def read_varint():
            num = 0
            for i in range(5):
                b = s.recv(1)
                if not b:
                    raise EOFError('连接关闭')
                num |= (b[0] & 0x7f) << (7 * i)
                if not (b[0] & 0x80):
                    break
            return num

        ln = read_varint()   # 包总长
        pkt_id = s.recv(1)   # packet id = 0 (status response)
        # 读字符串长度
        str_len = read_varint()
        data = b''
        while len(data) < str_len:
            chunk = s.recv(str_len - len(data))
            if not chunk:
                break
            data += chunk
        s.close()
        if data:
            return json.loads(data.decode('utf-8', errors='replace'))
    except Exception as e:
        return {'error': str(e)}
    return {'error': 'no data'}

for host, port in [('mchlt.cn', 25565), ('play.eternalmc.net', 25565), ('mczym.cn', 25565)]:
    st = ping_server(host, port)
    if 'error' in st:
        print('{}:{} -> 不可用 ({})'.format(host, port, str(st['error'])[:60]))
    else:
        desc = st.get('description', {})
        if isinstance(desc, dict):
            desc = desc.get('text', desc)
        ver = st.get('version', {})
        pl = st.get('players', {})
        print('{}:{} -> OK 在线 | {} | 版本:{} | 玩家:{}/{}'.format(
            host, port, str(desc)[:50], ver.get('name'), pl.get('online'), pl.get('max')))
