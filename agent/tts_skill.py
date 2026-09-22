"""TTS 语音合成：把执行结果文字转成语音，形成「说 → 听」闭环。

使用微软 Edge 在线 TTS（免费、中文音质好），与 LLM 网关解耦，
不依赖中转平台是否支持 audio 接口。合成失败时由调用方降级为纯文字展示。
"""

import asyncio

import edge_tts

from agent.common import TTS_PROXY, TTS_VOICE

# TTS 合成失败后的最大重试次数（edge-tts 在线服务偶发抖动）
TTS_MAX_RETRIES = 2
# 重试间隔基数（秒），按次数递增：1s、2s、…
TTS_RETRY_BASE_DELAY = 1.0


async def synthesize(text: str, voice: str | None = None) -> bytes:
    """把文字合成 MP3 音频字节，失败自动重试。

    参数：
        text: 要朗读的文字（空字符串会抛 ValueError）。
        voice: 发音人，默认取 common.TTS_VOICE。

    返回：
        MP3 音频字节流。重试仍失败则抛出最后一个异常，交由上层提示用户。
    """
    text = (text or "").strip()
    if not text:
        raise ValueError("要播报的文字为空")

    voice = voice or TTS_VOICE
    last_err = None
    for attempt in range(TTS_MAX_RETRIES + 1):
        try:
            return await _synthesize_once(text, voice)
        except Exception as e:  # noqa: BLE001 - 网络类异常类型不固定，统一重试
            last_err = e
            if attempt < TTS_MAX_RETRIES:
                await asyncio.sleep(TTS_RETRY_BASE_DELAY * (attempt + 1))
    raise last_err


async def _synthesize_once(text: str, voice: str) -> bytes:
    """单次合成（不重试），拆出来便于测试重试逻辑。"""
    communicate = edge_tts.Communicate(text, voice, proxy=TTS_PROXY or None)

    chunks: list[bytes] = []
    async for chunk in communicate.stream():
        if chunk.get("type") == "audio":
            chunks.append(chunk["data"])
    return b"".join(chunks)
