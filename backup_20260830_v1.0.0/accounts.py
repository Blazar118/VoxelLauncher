# -*- coding: utf-8 -*-
"""
VoxelLauncher - 账号系统模块
- 离线账号: 自定义用户名, 自动生成离线UUID, 本地json保存
- 微软账号: 设备码 OAuth 登录, 获取 access_token / 玩家UUID / 玩家名
  (XBL -> XSTS -> Minecraft 认证链), 持久保存, 支持刷新
- 多账号管理: 切换 / 删除 / 设置默认
"""
import hashlib
import json
import time
import uuid
import webbrowser
from pathlib import Path

import requests

from config import CONFIG

# ---------------------------------------------------------------
# 微软 OAuth 参数(旧版 live.com 设备码流程)
# 使用 Minecraft Java 版官方 Client ID, 无需用户自行注册 Azure 应用。
# 旧版端点: login.live.com/oauth20_connect.srf (设备码)
#           login.live.com/oauth20_token.srf   (轮询/刷新)
# scope 为 service::user.auth.xboxlive.com::MBI_SSL (RPS 票据)
# 拿到 access_token 后走 XBL -> XSTS -> Minecraft 认证链, 与现代流程一致。
MS_CLIENT_ID = "00000000402b5328"  # Minecraft: Java / Win32 官方 Client ID
MS_SCOPE = "service::user.auth.xboxlive.com::MBI_SSL"
DEVICE_CODE_URL = "https://login.live.com/oauth20_connect.srf"
TOKEN_URL = "https://login.live.com/oauth20_token.srf"


def _ms_client_id():
    """优先用配置中的 Client ID, 未配置则用官方默认 ID"""
    cid = CONFIG.get("ms_client_id", "").strip()
    return cid or MS_CLIENT_ID


# ---------------------------------------------------------------
# 离线 UUID(与官方 "OfflinePlayer:" 规则一致)
# ---------------------------------------------------------------
def offline_uuid(name):
    data = ("OfflinePlayer:" + name).encode("utf-8")
    digest = bytearray(hashlib.md5(data).digest())
    digest[6] = (digest[6] & 0x0F) | 0x30  # version 3
    digest[8] = (digest[8] & 0x3F) | 0x80  # IETF variant
    return str(uuid.UUID(bytes=bytes(digest)))


# ---------------------------------------------------------------
# 账号存取
# ---------------------------------------------------------------
def _accounts():
    return CONFIG.get("accounts", [])


def _save(accounts):
    CONFIG.set("accounts", accounts)


def add_offline_account(name):
    """新增离线账号, 返回账号 dict"""
    name = name.strip()
    if not name:
        raise ValueError("用户名不能为空")
    accounts = _accounts()
    acct = {
        "type": "offline",
        "name": name,
        "uuid": offline_uuid(name),
        "access_token": "0",          # 离线账号固定占位 token
        "user_type": "legacy",
        "created": time.time(),
    }
    accounts.append(acct)
    _save(accounts)
    return acct


def add_account(acct):
    accounts = _accounts()
    # 同类型同名称去重
    accounts = [a for a in accounts
                if not (a.get("type") == acct.get("type")
                        and a.get("name") == acct.get("name"))]
    accounts.append(acct)
    _save(accounts)


def remove_account(index):
    accounts = _accounts()
    if 0 <= index < len(accounts):
        accounts.pop(index)
        _save(accounts)


def set_default_account(index):
    accounts = _accounts()
    if 0 <= index < len(accounts):
        CONFIG.set("default_account", index)
        return True
    return False


def get_default_account_index():
    idx = CONFIG.get("default_account")
    if isinstance(idx, int) and 0 <= idx < len(_accounts()):
        return idx
    return 0 if _accounts() else -1


def list_accounts():
    return list(_accounts())


# ---------------------------------------------------------------
# 微软设备码登录
# ---------------------------------------------------------------
def _device_code():
    """获取 device_code 与 user_code(旧版 live.com 端点), 返回 dict"""
    client_id = _ms_client_id()
    resp = requests.post(
        DEVICE_CODE_URL,
        data={
            "client_id": client_id,
            "scope": MS_SCOPE,
            "response_type": "device_code",
        },
        timeout=30,
    )
    if resp.status_code != 200:
        try:
            data = resp.json()
            err = data.get("error", "")
            desc = data.get("error_description", "")
        except Exception:
            err, desc = "", resp.text
        raise RuntimeError("微软登录失败({}): {}".format(err or resp.status_code, desc))
    return resp.json()


def _poll_token(device_code, interval=5, timeout=300):
    """轮询等待用户授权(旧版 live.com 端点), 返回 token 响应"""
    client_id = _ms_client_id()
    start = time.time()
    while time.time() - start < timeout:
        resp = requests.post(
            TOKEN_URL,
            data={
                "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                "client_id": client_id,
                "device_code": device_code,
            },
            timeout=30,
        )
        data = resp.json()
        if resp.status_code == 200:
            return data
        err = data.get("error", "")
        if err == "authorization_pending":
            time.sleep(interval)
            continue
        if err == "authorization_declined":
            raise RuntimeError("用户拒绝了授权")
        if err == "expired_token":
            raise RuntimeError("登录码已过期, 请重试")
        raise RuntimeError("登录失败: " + str(data))
    raise RuntimeError("登录超时")


def _xbl_authenticate(ms_token, rps_prefix=False):
    """
    用微软 access_token 登录 Xbox Live。
    rps_prefix: 现代 OAuth JWT token 需要 "d=" 前缀;
                旧版 live.com RPS 票据直接传 token, 不加前缀。
    """
    ticket = ("d=" + ms_token) if rps_prefix else ms_token
    resp = requests.post(
        "https://user.auth.xboxlive.com/user/authenticate",
        json={
            "Properties": {
                "AuthMethod": "RPS",
                "SiteName": "user.auth.xboxlive.com",
                "RpsTicket": ticket,
            },
            "RelyingParty": "http://auth.xboxlive.com",
            "TokenType": "JWT",
        },
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        timeout=30,
    )
    if resp.status_code != 200:
        raise RuntimeError(
            "Xbox Live 认证失败 (HTTP {}): {}".format(resp.status_code, resp.text[:300]))
    data = resp.json()
    uhs = data["DisplayClaims"]["xui"][0]["uhs"]
    return data["Token"], uhs


def _xsts_authenticate(xbl_token):
    resp = requests.post(
        "https://xsts.auth.xboxlive.com/xsts/authorize",
        json={
            "Properties": {"SandboxId": "RETAIL", "UserTokens": [xbl_token]},
            "RelyingParty": "rp://api.minecraftservices.com/",
            "TokenType": "JWT",
        },
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    uhs = data["DisplayClaims"]["xui"][0]["uhs"]
    return data["Token"], uhs


def _minecraft_login(xsts_token, uhs):
    resp = requests.post(
        "https://api.minecraftservices.com/authentication/login_with_xbox",
        json={"identityToken": "XBL3.0 x={};{}".format(uhs, xsts_token)},
        headers={"Content-Type": "application/json"},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def _mc_profile(access_token):
    resp = requests.get(
        "https://api.minecraftservices.com/minecraft/profile",
        headers={"Authorization": "Bearer " + access_token},
        timeout=30,
    )
    if resp.status_code == 404:
        # 该账号没有购买 Minecraft, 无皮肤档案
        return None
    resp.raise_for_status()
    data = resp.json()
    return {"id": data["id"], "name": data["name"]}


def login_microsoft(progress_cb=None, timeout=300):
    """
    完整微软登录流程(阻塞, 建议放后台线程)。
    progress_cb(msg) 用于界面提示用户输入设备码。
    返回账号 dict; 用户取消/超时抛 RuntimeError。
    """
    # 1. 设备码
    dev = _device_code()
    if progress_cb:
        progress_cb(
            "请在浏览器打开 {} 并输入代码: {}".format(
                dev["verification_uri"], dev["user_code"]))
    webbrowser.open(dev["verification_uri"])

    # 2. 轮询获取微软 token
    tok = _poll_token(dev["device_code"], interval=dev.get("interval", 5),
                      timeout=timeout)
    ms_token = tok["access_token"]
    refresh_token = tok.get("refresh_token")

    # 3. XBL -> XSTS -> Minecraft
    xbl, uhs = _xbl_authenticate(ms_token)
    xsts, uhs2 = _xsts_authenticate(xbl)
    mc_token = _minecraft_login(xsts, uhs2)

    # 4. 玩家档案
    profile = _mc_profile(mc_token)
    if profile is None:
        raise RuntimeError("该微软账号未购买 Minecraft Java 版, 无法登录")

    acct = {
        "type": "microsoft",
        "name": profile["name"],
        "uuid": profile["id"],
        "access_token": mc_token,
        "refresh_token": refresh_token,
        "user_type": "msa",
        "expires_at": time.time() + tok.get("expires_in", 3600),
        "skin": _profile_skin(profile, mc_token),
        "created": time.time(),
    }
    return acct


def _profile_skin(profile, mc_token):
    """读取微软账号官方皮肤(最佳努力, 失败返回 None)"""
    try:
        resp = requests.get(
            "https://api.minecraftservices.com/minecraft/profile/skins",
            headers={"Authorization": "Bearer " + mc_token}, timeout=15)
        if resp.status_code == 200:
            skins = resp.json().get("skins", [])
            if skins:
                return skins[0].get("url")
    except Exception:
        pass
    return None


# ---------------------------------------------------------------
# 微软 token 刷新与失效处理
# ---------------------------------------------------------------
def refresh_microsoft(acct):
    """
    用 refresh_token 刷新微软账号。失败(令牌失效)抛 RuntimeError。
    成功返回刷新后的账号 dict。
    """
    refresh_token = acct.get("refresh_token")
    if not refresh_token:
        raise RuntimeError("该账号没有 refresh_token, 请重新登录")
    client_id = _ms_client_id()
    resp = requests.post(
        TOKEN_URL,
        data={
            "grant_type": "refresh_token",
            "client_id": client_id,
            "refresh_token": refresh_token,
            "scope": MS_SCOPE,
        },
        timeout=30,
    )
    if resp.status_code != 200:
        raise RuntimeError("refresh_token 失效, 需要重新登录")
    tok = resp.json()
    ms_token = tok["access_token"]
    new_refresh = tok.get("refresh_token", refresh_token)

    xbl, _ = _xbl_authenticate(ms_token)
    xsts, uhs = _xsts_authenticate(xbl)
    mc_token = _minecraft_login(xsts, uhs)
    profile = _mc_profile(mc_token)
    if profile is None:
        raise RuntimeError("该微软账号已无 Minecraft 权限")

    acct = dict(acct)
    acct.update({
        "name": profile["name"],
        "uuid": profile["id"],
        "access_token": mc_token,
        "refresh_token": new_refresh,
        "expires_at": time.time() + tok.get("expires_in", 3600),
        "skin": _profile_skin(profile, mc_token),
    })
    return acct


def ensure_valid_account(acct):
    """
    启动前保证账号有效:
    - 微软账号过期则自动刷新
    - 刷新失败抛异常(需要重新登录)
    """
    if acct.get("type") == "microsoft":
        expires = acct.get("expires_at", 0)
        if time.time() >= expires - 60:
            fresh = refresh_microsoft(acct)
            # 更新存储
            accounts = _accounts()
            for i, a in enumerate(accounts):
                if (a.get("type") == "microsoft"
                        and a.get("uuid") == acct.get("uuid")):
                    accounts[i] = fresh
                    break
            _save(accounts)
            return fresh
    return acct


def load_from_file(path):
    """读取账号 json 文件(兼容手工备份恢复)"""
    return json.loads(Path(path).read_text(encoding="utf-8"))
