"""TTS 语音合成：把执行结果文字转成语音，形成「说 → 听」闭环。

使用微软 Edge 在线 TTS（免费、中文音质好），与 LLM 网关解耦，
不依赖中转平台是否支持 audio 接口。合成失败时由调用方降级为纯文字展示。
"""

import asyncio
import re

import edge_tts

from agent.common import TTS_PROXY, TTS_VOICE

# TTS 合成失败后的最大重试次数（edge-tts 在线服务偶发抖动）
TTS_MAX_RETRIES = 2
# 重试间隔基数（秒），按次数递增：1s、2s、…
TTS_RETRY_BASE_DELAY = 1.0


def strip_markdown(text: str) -> str:
    """把 LLM 输出里的 markdown 标记清掉，只留纯文字供 TTS 朗读。

    TTS 会把 "**"、"`"、"#" 这类符号逐字念出来（听起来很怪），播报前先清洗。
    只影响朗读内容，不影响页面展示——页面仍渲染原始富文本。
    """
    if not text:
        return ""

    # 行内代码 / 代码块：去掉反引号，保留内容
    text = re.sub(r"`{1,3}([^`]*)`{1,3}", r"\1", text)
    # 图片 ![alt](url) → 保留 alt（必须先于链接处理，否则 alt 前会残留感叹号）
    text = re.sub(r"!\[([^\]]*)\]\([^)]*\)", r"\1", text)
    # 链接 [文字](url) → 只保留文字（URL 念出来毫无意义）
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    # 加粗 / 斜体 / 删除线：**x**、*x*、__x__、~~x~~ → x
    text = re.sub(r"\*{1,3}([^*]+)\*{1,3}", r"\1", text)
    text = re.sub(r"_{2}([^_]+)_{2}", r"\1", text)
    text = re.sub(r"~{2}([^~]+)~{2}", r"\1", text)
    # 标题 # 与引用 > 的行首标记
    text = re.sub(r"^[ \t]{0,3}#{1,6}[ \t]*", "", text, flags=re.M)
    text = re.sub(r"^[ \t]{0,3}>[ \t]?", "", text, flags=re.M)
    # 列表项行首符号：- / * / + / 1. → 去掉
    text = re.sub(r"^[ \t]*[-*+][ \t]+", "", text, flags=re.M)
    text = re.sub(r"^[ \t]*\d+\.[ \t]+", "", text, flags=re.M)
    # 分隔线 --- / *** → 整行删掉
    text = re.sub(r"^[ \t]*([-*_])[ \t]*\1*[ \t]*$", "", text, flags=re.M)
    # 表格竖线 → 空格
    text = re.sub(r"\|", " ", text)
    # 连续空行压缩为一个，去掉首尾空白
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


async def synthesize(text: str, voice: str | None = None) -> bytes:
    """把文字合成 MP3 音频字节，失败自动重试。

    参数：
        text: 要朗读的文字（空字符串会抛 ValueError）。
        voice: 发音人，默认取 common.TTS_VOICE。

    返回：
        MP3 音频字节流。重试仍失败则抛出最后一个异常，交由上层提示用户。
    """
    text = strip_markdown(text)
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
