# -*- coding: utf-8 -*-
"""
voice_assistant.py - 语音助手
- 麦克风录音(sounddevice)
- 本地语音识别(faster-whisper, 中文)
- 命令词解析: 启动游戏/停止/音乐/音量/主题等 → 返回动作
- 非命令内容交给 AI 闲聊

使用: assistant = VoiceAssistant(); text = assistant.listen_and_transcribe()
      action = assistant.parse_command(text)  # 返回 (action, value) 或 None
"""
import os
import sys
import threading

def _model_dir():
    """定位内置 whisper 模型目录:
    1) PyInstaller 打包资源 (sys._MEIPASS/whisper_models/tiny)
    2) 项目根 whisper_models/tiny
    """
    candidates = []
    try:
        if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
            candidates.append(os.path.join(sys._MEIPASS, "whisper_models", "tiny"))
    except Exception:
        pass
    candidates.append(os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "whisper_models", "tiny"))
    for p in candidates:
        if os.path.isfile(os.path.join(p, "model.bin")):
            return p
    # 兜底: 取第一个候选并尽量创建
    os.makedirs(candidates[-1], exist_ok=True)
    return candidates[-1]


MODEL_CACHE_DIR = _model_dir()


class VoiceAssistant:
    """语音助手: 录音 + ASR + 命令解析"""

    # 命令关键词表: (动作, [关键词列表], 说明)
    COMMANDS = [
        ("launch_game", ["启动游戏", "打开游戏", "开始游戏", "启动"]),
        ("stop_game", ["停止游戏", "关闭游戏", "退出游戏", "停止"]),
        ("music_play", ["播放音乐", "放音乐", "听歌", "播歌", "播放"]),
        ("music_pause", ["暂停音乐", "暂停播放", "暂停"]),
        ("music_resume", ["继续播放", "继续放", "接着放"]),
        ("music_next", ["下一首", "切歌", "下一曲"]),
        ("music_prev", ["上一首", "上一曲"]),
        ("music_stop", ["停止音乐", "关音乐", "停止播放"]),
        ("volume_up", ["音量加", "大声点", "调大声", "声音调大", "声音大点", "音量大"]),
        ("volume_down", ["音量减", "小声点", "调小声", "声音调小", "声音小点", "音量小"]),
        ("theme_cyber", ["科技主题", "暗色主题", "毛玻璃"]),
        ("theme_default", ["默认主题", "浅色主题"]),
        ("open_music", ["打开音乐", "打开音乐页", "音乐页"]),
        ("open_video", ["打开视频", "打开电视", "看视频"]),
        ("open_tools", ["打开工具", "工具页"]),
        ("open_settings", ["打开设置", "设置页"]),
        ("what_can_you_do", ["你能做什么", "你会什么", "帮助", "怎么用"]),
    ]

    def __init__(self, model_size="tiny"):
        self.model_size = model_size
        self._model = None
        self._model_lock = threading.Lock()
        self._ready = False
        self._init_error = None
        self._load_model_async()

    # ---------- 模型加载 ----------
    def _load_model_async(self):
        def _load():
            try:
                from faster_whisper import WhisperModel
                model_path = MODEL_CACHE_DIR
                if os.path.isfile(os.path.join(model_path, "model.bin")):
                    # 内置模型: 直接加载本地目录
                    with self._model_lock:
                        self._model = WhisperModel(
                            model_path, device="cpu", compute_type="int8")
                        self._ready = True
                else:
                    # 没有内置模型才联网下载
                    os.makedirs(model_path, exist_ok=True)
                    with self._model_lock:
                        self._model = WhisperModel(
                            self.model_size, device="cpu",
                            compute_type="int8",
                            download_root=model_path)
                        self._ready = True
            except Exception as e:
                self._init_error = str(e)
        threading.Thread(target=_load, daemon=True).start()

    @property
    def is_ready(self):
        return self._ready

    @property
    def init_error(self):
        return self._init_error

    # ---------- 录音 ----------
    def record(self, duration=4.0, samplerate=16000):
        """录音并返回 float32 音频数组"""
        import numpy as np
        import sounddevice as sd
        sd.default.samplerate = samplerate
        sd.default.channels = 1
        frames = int(duration * samplerate)
        audio = sd.rec(frames, samplerate=samplerate, channels=1, dtype="float32")
        sd.wait()
        return np.asarray(audio, dtype="float32").flatten()

    # ---------- 语音识别 ----------
    def transcribe(self, audio):
        """转写音频为文本(中文)"""
        if not self._ready or self._model is None:
            if self._init_error:
                return None, "语音识别引擎未就绪: " + self._init_error
            return None, "语音识别引擎加载中, 请稍候..."
        try:
            segments, info = self._model.transcribe(
                audio, language="zh", vad_filter=True)
            text = " ".join(seg.text for seg in segments).strip()
            if not text:
                return None, "没听清, 再说一次?"
            return text, None
        except Exception as e:
            return None, "识别失败: " + str(e)

    def listen_and_transcribe(self, duration=4.0):
        """一步: 录音 + 转写, 返回 (文本, 错误)"""
        try:
            audio = self.record(duration)
        except Exception as e:
            return None, "录音失败: " + str(e)
        return self.transcribe(audio)

    # ---------- 命令解析 ----------
    def parse_command(self, text):
        """解析命令词, 返回 (action, matched_keyword) 或 None"""
        if not text:
            return None
        t = text.lower()
        for action, keywords in self.COMMANDS:
            for kw in keywords:
                if kw in t:
                    return action, kw
        return None

    # ---------- 语音命令帮助文本 ----------
    @staticmethod
    def help_text():
        lines = ["🗣️ 你可以对我说:", ""]
        for action, kws in VoiceAssistant.COMMANDS:
            lines.append(" · " + " / ".join(kws[:3]))
        return "\n".join(lines)


# 全局单例
_voice = None


def get_assistant(model_size="tiny"):
    global _voice
    if _voice is None:
        _voice = VoiceAssistant(model_size)
    return _voice


if __name__ == "__main__":
    # 自测: 加载模型状态
    a = get_assistant("tiny")
    import time
    print("语音引擎加载中...")
    for _ in range(60):
        if a.is_ready:
            print("✅ 语音识别引擎就绪")
            break
        if a.init_error:
            print("❌", a.init_error)
            break
        time.sleep(2)
    print("命令解析测试:")
    for t in ["启动游戏", "下一首", "把声音调大", "科技主题", "随便说点什么"]:
        print(" ", t, "->", a.parse_command(t))
