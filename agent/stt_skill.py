import os
import tempfile

from faster_whisper import WhisperModel
from opencc import OpenCC

from agent.common import WHISPER_MODEL

# 繁体转简体：Whisper 识别普通话常输出繁体，统一转成简体
_cc = OpenCC("t2s")

# 本地语音转文字模型：tiny / base / small，越大越准也越慢。
# 权重已缓存在 C:\Users\<用户>\.cache\huggingface\hub，首次加载不会重新下载。
# WHISPER_MODEL 统一由 agent.common 从 .env 读取

_model = None


def _get_model() -> WhisperModel:
    """懒加载：首次调用时才加载模型，之后全程复用，避免 Streamlit 每次交互都重新加载。"""
    global _model
    if _model is None:
        _model = WhisperModel(WHISPER_MODEL, device="cpu", compute_type="int8")
    return _model


def transcribe(audio_data: bytes, filename: str = "audio.wav") -> str:
    """
    输入：音频字节流 + 原始文件名
    输出：识别出的文字（本地 faster-whisper，不依赖任何 API / 中转网关）
    """
    # 保留上传文件的真实扩展名（wav/mp3/m4a），解码器按扩展名判断格式
    suffix = os.path.splitext(filename)[1] or ".wav"
    fd, tmp_path = tempfile.mkstemp(suffix=suffix)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(audio_data)
        segments, _info = _get_model().transcribe(tmp_path)
        text = "".join(seg.text for seg in segments).strip()
        return _cc.convert(text)
    finally:
        # 用完即删，不残留临时文件
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
