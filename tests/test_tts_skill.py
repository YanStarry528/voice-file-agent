"""tts_skill.synthesize 的重试逻辑测试（mock 单次合成，不联网）。"""
import asyncio

import pytest

from agent import tts_skill


def _run(coro):
    return asyncio.run(coro)


def test_空文本抛错():
    with pytest.raises(ValueError):
        _run(tts_skill.synthesize("   "))


def test_首次成功不重试(monkeypatch):
    calls = []

    async def fake_once(text, voice):
        calls.append(text)
        return b"MP3"

    monkeypatch.setattr(tts_skill, "_synthesize_once", fake_once)
    monkeypatch.setattr(tts_skill, "TTS_MAX_RETRIES", 2)
    monkeypatch.setattr(tts_skill, "TTS_RETRY_BASE_DELAY", 0)

    assert _run(tts_skill.synthesize("你好")) == b"MP3"
    assert calls == ["你好"]


def test_前两次失败第三次成功(monkeypatch):
    calls = []

    async def flaky(text, voice):
        calls.append(text)
        if len(calls) < 3:
            raise RuntimeError("网络抖动")
        return b"OK"

    monkeypatch.setattr(tts_skill, "_synthesize_once", flaky)
    monkeypatch.setattr(tts_skill, "TTS_MAX_RETRIES", 2)
    monkeypatch.setattr(tts_skill, "TTS_RETRY_BASE_DELAY", 0)

    assert _run(tts_skill.synthesize("你好")) == b"OK"
    assert len(calls) == 3  # 初始 1 次 + 重试 2 次


def test_全部失败抛最后一个异常(monkeypatch):
    async def always_fail(text, voice):
        raise RuntimeError("网络断了")

    monkeypatch.setattr(tts_skill, "_synthesize_once", always_fail)
    monkeypatch.setattr(tts_skill, "TTS_MAX_RETRIES", 2)
    monkeypatch.setattr(tts_skill, "TTS_RETRY_BASE_DELAY", 0)

    with pytest.raises(RuntimeError):
        _run(tts_skill.synthesize("你好"))


def test_清洗加粗标记():
    assert tts_skill.strip_markdown("找到了 **会议纪要.txt**") == "找到了 会议纪要.txt"


def test_清洗标题与列表符号():
    raw = "# 标题\n- 第一项\n- 第二项"
    assert tts_skill.strip_markdown(raw) == "标题\n第一项\n第二项"


def test_清洗链接只留文字():
    assert tts_skill.strip_markdown("见 [文档](http://a.com)") == "见 文档"


def test_纯文字不受影响():
    assert tts_skill.strip_markdown("会议纪要.txt 共 15 字、1 行。") == "会议纪要.txt 共 15 字、1 行。"


def test_只有标记的文本清洗后为空():
    assert tts_skill.strip_markdown("***") == ""


def test_播报前自动清洗(monkeypatch):
    calls = []

    async def fake_once(text, voice):
        calls.append(text)
        return b"MP3"

    monkeypatch.setattr(tts_skill, "_synthesize_once", fake_once)
    monkeypatch.setattr(tts_skill, "TTS_MAX_RETRIES", 0)
    monkeypatch.setattr(tts_skill, "TTS_RETRY_BASE_DELAY", 0)

    _run(tts_skill.synthesize("找到了 **会议纪要.txt**"))
    assert calls == ["找到了 会议纪要.txt"]
