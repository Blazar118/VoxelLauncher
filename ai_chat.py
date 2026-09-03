# -*- coding: utf-8 -*-
"""
AI 对话模块 - 支持豆包、Deepseek、Kimi 三个 API
用于宠物对话功能
"""
import json
import requests
from config import CONFIG


class AIChat:
    """AI 对话管理器"""

    def __init__(self):
        self.provider = CONFIG.get("ai_provider", "doubao")  # doubao / deepseek / kimi
        self.api_key = CONFIG.get("ai_api_key", "")
        self._last_request_time = 0  # 最后请求时间, 用于限制请求间隔
        # 各 API 的配置
        self.providers = {
            "doubao": {
                "name": "豆包",
                "url": "https://ark.cn-beijing.volces.com/api/v3/chat/completions",
                "model": "doubao-1-5-pro-32k-250115",
                "backup_models": ["doubao-pro-32k", "doubao-lite-32k", "ep-20250101000000-xxxxx"],
            },
            "deepseek": {
                "name": "Deepseek",
                "url": "https://api.deepseek.com/chat/completions",
                "model": "deepseek-v4-flash",
                "backup_models": ["deepseek-v4-pro", "deepseek-chat", "deepseek-reasoner"],
            },
            "kimi": {
                "name": "Kimi",
                "url": "https://api.moonshot.cn/v1/chat/completions",
                "model": "kimi-k2.5",
                "backup_models": ["kimi-k3", "moonshot-v1-8k", "moonshot-v1-32k", "moonshot-v1-128k"],
            },
            "zhipu": {
                "name": "智谱清言",
                "url": "https://open.bigmodel.cn/api/paas/v4/chat/completions",
                "model": "glm-4.5-air",
                "backup_models": ["glm-4-flash", "glm-4", "glm-4-plus", "glm-3-turbo"],
            },
        }

    def set_provider(self, provider):
        """设置 AI 服务商"""
        if provider in self.providers:
            self.provider = provider
            CONFIG.set("ai_provider", provider)

    def set_api_key(self, api_key):
        """设置 API key"""
        self.api_key = api_key.strip()
        CONFIG.set("ai_api_key", self.api_key)

    def is_configured(self):
        """检查是否已配置 API key"""
        return bool(self.api_key)

    def chat(self, message, system_prompt="", temperature=0.7):
        """
        发送对话请求, 返回 AI 的回复。自动尝试备用模型。
        message: 用户消息
        system_prompt: 系统提示词(用于设定角色性格)
        temperature: 温度(0-1, 越高越随机)
        返回: (成功, 回复内容/错误信息)
        """
        if not self.api_key:
            return False, "未配置 API key，请在设置页配置"

        provider_config = self.providers.get(self.provider)
        if not provider_config:
            return False, "未知的 AI 服务商"

        url = provider_config["url"]
        # 主模型 + 备用模型
        models_to_try = [provider_config["model"]]
        if "backup_models" in provider_config:
            models_to_try.extend(provider_config["backup_models"])

        # 构建消息
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": message})

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        import time as _time
        last_error = "未知错误"
        max_retries = 3  # 最多重试3次

        for model in models_to_try:
            data = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": 500,
            }
            for retry in range(max_retries):
                # 限制请求间隔: 两次请求之间至少间隔5秒(避免Kimi限流)
                now = _time.time()
                if now - self._last_request_time < 5:
                    _time.sleep(5 - (now - self._last_request_time))
                self._last_request_time = _time.time()

                try:
                    response = requests.post(url, headers=headers, json=data, timeout=15)
                    # 如果是 401/403, 说明 key 有问题, 不用试其他模型了
                    if response.status_code in (401, 403):
                        try:
                            err_detail = response.json().get("error", {}).get("message", response.text[:200])
                        except Exception:
                            err_detail = response.text[:200]
                        return False, f"认证失败({response.status_code}): {err_detail}"
                    # 如果是 429, 限流, 等待后重试
                    if response.status_code == 429:
                        if retry < max_retries - 1:
                            wait_time = 5 * (retry + 1)  # 等待5秒、10秒、15秒
                            _time.sleep(wait_time)
                            continue
                        else:
                            return False, "请求太频繁(429)，Kimi限流很严格，请等1-2分钟后再试"
                    response.raise_for_status()
                    result = response.json()
                    if "choices" in result and len(result["choices"]) > 0:
                        reply = result["choices"][0]["message"]["content"].strip()
                        # 成功了, 把这个模型设为默认
                        provider_config["model"] = model
                        return True, reply
                    else:
                        last_error = f"API 返回格式异常: {json.dumps(result, ensure_ascii=False)[:200]}"
                        break
                except requests.exceptions.Timeout:
                    last_error = "请求超时"
                    if retry < max_retries - 1:
                        _time.sleep(2)
                        continue
                    break
                except requests.exceptions.RequestException as e:
                    last_error = f"请求失败: {str(e)}"
                    if retry < max_retries - 1:
                        _time.sleep(2)
                        continue
                    break
                except Exception as e:
                    last_error = f"未知错误: {str(e)}"
                    break

        return False, last_error

    def test_connection(self):
        """测试 API 连接是否正常"""
        return self.chat("你好", system_prompt="你是一个测试助手，请回复'连接成功'")

    def auto_detect_provider(self, api_key=None):
        """
        自动检测 API key 属于哪个服务商。
        遍历三个服务商, 找到能连接成功的那个。
        429 限流也认为 key 有效(只是请求太频繁)。
        返回: (成功, 服务商ID/错误信息)
        """
        if api_key:
            self.api_key = api_key.strip()
        if not self.api_key:
            return False, "未输入 API key"

        import time as _time
        errors = []
        for provider_id, provider_config in self.providers.items():
            try:
                url = provider_config["url"]
                models_to_try = [provider_config["model"]]  # 只试主模型, 减少请求次数避免限流

                for model in models_to_try:
                    headers = {
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {self.api_key}",
                    }
                    data = {
                        "model": model,
                        "messages": [{"role": "user", "content": "hi"}],
                        "max_tokens": 5,
                    }
                    response = requests.post(url, headers=headers, json=data, timeout=10)
                    if response.status_code == 200:
                        # 连接成功, 这个 key 属于这个服务商
                        self.provider = provider_id
                        provider_config["model"] = model
                        CONFIG.set("ai_provider", provider_id)
                        CONFIG.set("ai_api_key", self.api_key)
                        return True, provider_id
                    elif response.status_code == 429:
                        # 429 限流 = key 有效, 只是请求太频繁
                        self.provider = provider_id
                        provider_config["model"] = model
                        CONFIG.set("ai_provider", provider_id)
                        CONFIG.set("ai_api_key", self.api_key)
                        return True, provider_id + " (限流, key有效, 稍后即可使用)"
                    elif response.status_code in (401, 403):
                        # 认证失败, 记录错误但继续试其他服务商
                        try:
                            err_msg = response.json().get("error", {}).get("message", "认证失败")
                        except Exception:
                            err_msg = f"HTTP {response.status_code}"
                        errors.append(f"{provider_config['name']}: {err_msg[:60]}")
                        break  # 这个服务商认证失败, 不用试其他模型了
                    else:
                        errors.append(f"{provider_config['name']}: HTTP {response.status_code}")
            except requests.exceptions.Timeout:
                errors.append(f"{provider_config['name']}: 超时")
            except requests.exceptions.RequestException as e:
                errors.append(f"{provider_config['name']}: {str(e)[:60]}")
            except Exception as e:
                errors.append(f"{provider_config['name']}: {str(e)[:60]}")
            # 每个服务商之间加1秒延迟, 避免被限流
            _time.sleep(1)

        error_detail = "\n".join(errors) if errors else "未知错误"
        return False, f"三个服务商都连接失败:\n{error_detail}"


# 全局实例
ai_chat = AIChat()


# 宠物角色设定
PET_PERSONAS = {
    "creeper": {
        "name": "苦力怕",
        "system_prompt": """你是一只 Minecraft 里的苦力怕（Creeper），性格暴躁、易怒，动不动就想爆炸。
你说话简短、直接，经常提到"炸"、"嘶嘶"、"TNT"等词。
你讨厌猫，喜欢黑暗和爆炸。
你跟玩家说话时，虽然嘴上凶，但其实很喜欢玩家。
请用第一人称回答，保持苦力怕的性格，回复不要太长（50字以内）。""",
    },
    "villager": {
        "name": "村民",
        "system_prompt": """你是一个 Minecraft 里的村民（Villager），性格憨厚、爱交易，说话喜欢"嗯哼哼"。
你喜欢绿宝石，喜欢交易，经常提到"绿宝石"、"交易"、"价格"等词。
你有点胆小，害怕僵尸，喜欢住在村庄里。
你跟玩家说话时，很热情，总想跟玩家做交易。
请用第一人称回答，保持村民的性格，回复不要太长（50字以内）。""",
    },
}


def chat_with_pet(pet_type, message, chat_history=None):
    """
    跟宠物对话
    pet_type: creeper / villager / both
    message: 玩家消息
    chat_history: 对话历史(可选, 用于上下文)
    返回: (成功, 回复内容/错误信息)
    """
    if pet_type == "both":
        # 苦力怕和村民一起回复
        system_prompt = """你要同时扮演 Minecraft 里的苦力怕（Creeper）和村民（Villager）两个角色。
苦力怕性格暴躁、易怒，动不动就想爆炸，说话简短直接，经常提到"炸"、"嘶嘶"、"TNT"。
村民性格憨厚、爱交易，说话喜欢"嗯哼哼"，经常提到"绿宝石"、"交易"、"价格"。

玩家说话后，苦力怕先说一句，然后村民再说一句。
格式要求：
第一行是苦力怕的回复，以"苦力怕:"开头
第二行是村民的回复，以"村民:"开头
每句回复不要超过30字。"""
        return ai_chat.chat(message, system_prompt=system_prompt, temperature=0.8)

    persona = PET_PERSONAS.get(pet_type)
    if not persona:
        return False, "未知的宠物类型"
    return ai_chat.chat(message, system_prompt=persona["system_prompt"], temperature=0.8)
