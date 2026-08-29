# -*- coding: utf-8 -*-
"""
VoxelLauncher - 游戏联动模块
通过本地 HTTP 端口与 VoxelLauncher Bridge Mod 通信,
把启动器里挖到的矿石实时发送到游戏背包。
"""
import json
import urllib.request
import urllib.error


BRIDGE_PORT = 25585
BRIDGE_URL = f"http://127.0.0.1:{BRIDGE_PORT}"


def is_bridge_running(timeout=1.0):
    """检查联动 Mod 是否在运行(游戏是否已启动且装了 Mod)"""
    try:
        req = urllib.request.Request(f"{BRIDGE_URL}/status", method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("in_game", False)
    except Exception:
        return False


def send_item(item_id, count=1, timeout=2.0):
    """
    发送物品给游戏内玩家。
    item_id: 如 "minecraft:diamond" 或 "diamond"
    count: 数量(最多64, 超过的需要多次调用)
    返回 (是否成功, 消息)
    """
    if not is_bridge_running():
        return False, "联动 Mod 未运行(游戏未启动或未安装 Mod)"

    # 超过 64 的拆分
    remaining = count
    results = []
    while remaining > 0:
        batch = min(remaining, 64)
        try:
            payload = json.dumps({"item": item_id, "count": batch},
                                  separators=(',', ':')).encode("utf-8")
            req = urllib.request.Request(
                f"{BRIDGE_URL}/give",
                data=payload,
                method="POST",
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if data.get("status") == "ok":
                    results.append(True)
                else:
                    results.append(False)
        except urllib.error.HTTPError as e:
            return False, f"HTTP 错误 {e.code}"
        except Exception as e:
            return False, f"发送失败: {e}"
        remaining -= batch

    if all(results):
        return True, f"已发送 {count} 个 {item_id} 到游戏背包"
    return False, "部分物品发送失败"


def send_inventory(inventory, timeout=2.0):
    """
    把整个背包的物品都发送给游戏。
    inventory: {item_id: count}
    返回 (成功数, 失败数, 详情列表)
    """
    success = 0
    failed = 0
    details = []
    for item_id, count in inventory.items():
        if count <= 0:
            continue
        ok, msg = send_item(item_id, count, timeout)
        if ok:
            success += 1
            details.append(f"✓ {item_id} x{count}")
        else:
            failed += 1
            details.append(f"✗ {item_id} x{count}: {msg}")
    return success, failed, details
