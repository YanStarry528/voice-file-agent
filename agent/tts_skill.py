"""TTS 语音合成：把执行结果文字转成语音，形成「说 → 听」闭环。

使用微软 Edge 在线 TTS（免费、中文音质好），与 LLM 网关解耦，
不依赖中转平台是否支持 audio 接口。合成失败时由调用方降级为纯文字展示。
"""

import edge_tts

from agent.common import TTS_PROXY, TTS_VOICE


async def synthesize(text: str, voice: str | None = None) -> bytes:
    """把文字合成 MP3 音频字节。

    参数：
        text: 要朗读的文字（空字符串会抛 ValueError）。
        voice: 发音人，默认取 common.TTS_VOICE。

    返回：
        MP3 音频字节流。
    """
    text = (text or "").strip()
    if not text:
        raise ValueError("要播报的文字为空")

    voice = voice or TTS_VOICE
    communicate = edge_tts.Communicate(text, voice, proxy=TTS_PROXY or None)

    chunks: list[bytes] = []
    async for chunk in communicate.stream():
        if chunk.get("type") == "audio":
            chunks.append(chunk["data"])
    return b"".join(chunks)
