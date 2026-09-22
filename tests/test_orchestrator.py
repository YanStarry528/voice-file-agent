"""orchestrator 主流程与确认/补充流程的单元测试（mock LLM 与 dispatch）。"""
import pytest

from agent import orchestrator
from agent.tool_calling import NeedConfirm


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("确认", "confirm"),
        ("好的", "confirm"),
        ("取消", "cancel"),
        ("算了", "cancel"),
        ("不删", "cancel"),
        ("不确定", "unknown"),
        ("再想想", "unknown"),
        ("今天天气不错", "unknown"),
    ],
)
def test_判断确认回复(text, expected):
    assert orchestrator._judge_confirm(text) == expected


def test_取消优先于确认():
    assert orchestrator._judge_confirm("别删了，确定吗") == "cancel"


def test_缺失字段检测():
    assert "filename" in orchestrator._missing_fields("save_file", {"content": "x"})
    assert orchestrator._missing_fields("save_file", {"filename": "a.txt"}) == []


def test_追问文案含取消提示():
    msg = orchestrator._ask_message("save_file", "filename")
    assert "文件名" in msg and "取消" in msg


def test_确认后执行(monkeypatch):
    calls = []
    monkeypatch.setattr(
        orchestrator, "dispatch",
        lambda intent, args: calls.append((intent, args)) or "已删除",
    )
    result = orchestrator._handle_confirm(
        "确认", "s1", {"type": "confirm", "intent": "delete_file", "args": {"filename": "a.txt"}}
    )
    assert result["result"] == "已删除"
    assert calls == [("delete_file", {"filename": "a.txt"})]
    assert orchestrator.get_pending("s1") is None


def test_取消不执行(monkeypatch):
    dispatched = []
    monkeypatch.setattr(orchestrator, "dispatch", lambda *a, **k: dispatched.append(1))
    result = orchestrator._handle_confirm(
        "取消", "s1", {"type": "confirm", "intent": "delete_file", "args": {"filename": "a.txt"}}
    )
    assert result["intent"]["intent"] == "cancel"
    assert dispatched == []


def test_犹豫则重问(monkeypatch):
    pending = {"type": "confirm", "intent": "delete_file", "args": {"filename": "a.txt"}}
    orchestrator.set_pending("s1", pending)
    monkeypatch.setattr(orchestrator, "dispatch", lambda *a, **k: None)
    result = orchestrator._handle_confirm("不确定", "s1", pending)
    assert result["confirming"] is True
    assert orchestrator.get_pending("s1") is not None  # 保持 pending，等待再次回复


def test_补充参数后执行(monkeypatch):
    monkeypatch.setattr(orchestrator, "complete_args", lambda *a, **k: {"filename": "a.txt"})
    dispatched = []
    monkeypatch.setattr(
        orchestrator, "dispatch", lambda intent, args: dispatched.append(args) or "已保存"
    )
    result = orchestrator._handle_supplement(
        "a.txt", "s1",
        {"type": "supplement", "intent": "save_file", "args": {"content": "x"}, "missing": ["filename"]},
    )
    assert result["result"] == "已保存"
    assert dispatched == [{"intent": "save_file", "content": "x", "filename": "a.txt"}]


def test_补充时可取消(monkeypatch):
    monkeypatch.setattr(orchestrator, "complete_args", lambda *a, **k: {"intent": "cancel"})
    result = orchestrator._handle_supplement(
        "算了", "s1",
        {"type": "supplement", "intent": "save_file", "args": {}, "missing": ["filename"]},
    )
    assert result["intent"]["intent"] == "cancel"


def test_主路径回写历史与最近文件(monkeypatch):
    monkeypatch.setattr(
        orchestrator, "run_agent",
        lambda text, last_file=None, history=None: {
            "result": "已保存", "confirming": False, "intent": "save_file",
            "args": {"filename": "a.txt"},
            "history": [
                {"role": "user", "content": "保存 a.txt"},
                {"role": "assistant", "content": "已保存"},
            ],
        },
    )
    out = orchestrator.run_text("保存 a.txt", session_id="s1")
    assert out["result"] == "已保存"
    assert orchestrator.get_session("s1").last_file == "a.txt"
    assert len(orchestrator.get_history("s1")) == 2


def test_危险操作进入确认态(monkeypatch):
    def fake_run_agent(text, last_file=None, history=None):
        raise NeedConfirm("delete_file", {"filename": "a.txt"})

    monkeypatch.setattr(orchestrator, "run_agent", fake_run_agent)
    out = orchestrator.run_text("删掉 a.txt", session_id="s1")
    assert out["confirming"] is True
    assert "确认" in out["result"]
    assert orchestrator.get_pending("s1")["type"] == "confirm"
