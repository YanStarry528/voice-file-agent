"""tool_calling.run_agent 的单元测试（mock LLM 响应，不联网）。"""
from types import SimpleNamespace

import pytest

from agent import tool_calling
from agent.tool_calling import NeedConfirm, run_agent


def _tool_call(name, arguments, call_id="call_1"):
    return SimpleNamespace(
        id=call_id,
        type="function",
        function=SimpleNamespace(name=name, arguments=arguments),
    )


def _resp(tool_calls=None, content=""):
    msg = SimpleNamespace(content=content, tool_calls=tool_calls)
    return SimpleNamespace(choices=[SimpleNamespace(message=msg)])


class _FakeCompletions:
    """按顺序吐出预设响应，并记录每次 create 的入参，便于断言调用轮数。"""

    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return self._responses.pop(0)


@pytest.fixture
def fake_llm(monkeypatch):
    """安装一个假的 llm_client，返回其调用记录器。"""

    def install(responses):
        fc = _FakeCompletions(responses)
        client = SimpleNamespace(chat=SimpleNamespace(completions=fc))
        monkeypatch.setattr(tool_calling, "llm_client", client)
        return fc

    return install


def test_单步保存文件(fake_llm, isolated_output_dir):
    fc = fake_llm([
        _resp(tool_calls=[_tool_call("save_file", '{"filename": "a.txt", "content": "hi"}')]),
        _resp(content="已保存。"),
    ])
    out = run_agent("保存 a.txt")
    assert out["result"] == "已保存。"
    assert out["intent"] == "save_file"
    assert (isolated_output_dir / "a.txt").read_text(encoding="utf-8") == "hi"
    assert len(fc.calls) == 2  # 工具调用一轮 + 总结一轮


def test_复合指令拆多步(fake_llm, isolated_output_dir):
    fc = fake_llm([
        _resp(tool_calls=[_tool_call("save_file", '{"filename": "a.txt", "content": "1"}', "c1")]),
        _resp(tool_calls=[_tool_call("save_file", '{"filename": "b.txt", "content": "2"}', "c2")]),
        _resp(content="两个都存好了。"),
    ])
    out = run_agent("存两个文件")
    assert out["result"] == "两个都存好了。"
    assert (isolated_output_dir / "a.txt").read_text(encoding="utf-8") == "1"
    assert (isolated_output_dir / "b.txt").read_text(encoding="utf-8") == "2"
    assert len(fc.calls) == 3


def test_危险操作抛NeedConfirm(fake_llm):
    fake_llm([
        _resp(tool_calls=[_tool_call("delete_file", '{"filename": "a.txt"}')]),
    ])
    with pytest.raises(NeedConfirm) as ei:
        run_agent("删掉 a.txt")
    assert ei.value.intent == "delete_file"
    assert ei.value.params == {"filename": "a.txt"}


def test_无工具调用直接追问(fake_llm):
    fake_llm([_resp(content="请问文件名叫什么？")])
    out = run_agent("保存文件")
    assert out["result"] == "请问文件名叫什么？"
    assert out["intent"] is None
    assert out["args"] == {}


def test_工具参数非json时容错(fake_llm, isolated_output_dir):
    fake_llm([
        _resp(tool_calls=[_tool_call("save_file", "不是合法json", "c1")]),
        _resp(content="完成。"),
    ])
    # 参数解析失败 → args={} → save_file 回退默认文件名 untitled.txt
    out = run_agent("保存")
    assert (isolated_output_dir / "untitled.txt").exists()
    assert out["result"] == "完成。"
