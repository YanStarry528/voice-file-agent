"""common.chat 的 LLM 调用重试逻辑测试（mock llm_client，不联网）。"""
from types import SimpleNamespace

import pytest

from agent import common


def _fake_client(create_fn):
    return SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create_fn)))


def test_重试后成功(monkeypatch):
    calls = []

    def create(**kwargs):
        calls.append(kwargs)
        if len(calls) < 3:
            raise RuntimeError("网关超时")
        return "OK"

    monkeypatch.setattr(common, "llm_client", _fake_client(create))
    monkeypatch.setattr(common, "LLM_MAX_RETRIES", 2)
    monkeypatch.setattr(common, "LLM_RETRY_DELAY", 0)

    assert common.chat(messages=[{"role": "user", "content": "hi"}]) == "OK"
    assert len(calls) == 3  # 初始 1 次 + 重试 2 次


def test_全部失败抛异常(monkeypatch):
    def create(**kwargs):
        raise RuntimeError("网关挂了")

    monkeypatch.setattr(common, "llm_client", _fake_client(create))
    monkeypatch.setattr(common, "LLM_MAX_RETRIES", 2)
    monkeypatch.setattr(common, "LLM_RETRY_DELAY", 0)

    with pytest.raises(RuntimeError):
        common.chat(messages=[{"role": "user", "content": "hi"}])


def test_无工具时不传tools参数(monkeypatch):
    captured = {}

    def create(**kwargs):
        captured.update(kwargs)
        return "OK"

    monkeypatch.setattr(common, "llm_client", _fake_client(create))
    monkeypatch.setattr(common, "LLM_MAX_RETRIES", 0)

    common.chat(messages=[{"role": "user", "content": "hi"}])
    assert "tools" not in captured
    assert captured["temperature"] == 0
