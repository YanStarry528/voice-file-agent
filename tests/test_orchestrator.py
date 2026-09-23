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


def test_空输入给出提示():
    out = orchestrator.run_text("   ")
    assert out["result"] == "请输入指令内容。"


def test_主路径失败回退旧分类(monkeypatch):
    """Agent 循环不可用（网关不支持 tools）时应走兜底的 JSON 分类路径。"""
    def boom(text, last_file=None, history=None):
        raise RuntimeError("网关不支持 tools")

    monkeypatch.setattr(orchestrator, "run_agent", boom)
    monkeypatch.setattr(
        orchestrator, "classify",
        lambda text, context=None: {"intent": "save_file", "filename": "a.txt", "content": "x"},
    )
    monkeypatch.setattr(orchestrator, "dispatch", lambda intent, args: "已保存")

    out = orchestrator.run_text("保存 a.txt", session_id="s1")
    assert out["result"] == "已保存"


def test_分类也失败时给出明确提示(monkeypatch):
    """两条路径都挂掉，也不能静默无响应。"""
    def boom(text, last_file=None, history=None):
        raise RuntimeError("网关不支持 tools")

    def fail(text, context=None):
        raise RuntimeError("网关挂了")

    monkeypatch.setattr(orchestrator, "run_agent", boom)
    monkeypatch.setattr(orchestrator, "classify", fail)

    out = orchestrator.run_text("保存 a.txt", session_id="s1")
    assert "意图分类失败" in out["result"]


def test_确认后执行失败不崩溃(monkeypatch):
    """skill 执行抛异常（如磁盘满）时，转成提示文案而不是让整个请求挂掉。"""
    def boom(intent, args):
        raise RuntimeError("磁盘已满")

    monkeypatch.setattr(orchestrator, "dispatch", boom)
    result = orchestrator._handle_confirm(
        "确认", "s1", {"type": "confirm", "intent": "delete_file", "args": {"filename": "a.txt"}}
    )
    assert "执行失败" in result["result"]


def test_无会话时危险操作安全取消(monkeypatch):
    """没有 session 就无法等待下一轮确认，必须安全地不执行。"""
    def fake(text, last_file=None, history=None):
        raise NeedConfirm("delete_file", {"filename": "a.txt"})

    monkeypatch.setattr(orchestrator, "run_agent", fake)
    out = orchestrator.run_text("删掉 a.txt")  # 不传 session_id
    assert out["confirming"] is True
    assert "需要二次确认" in out["result"]


def test_补全LLM失败退回规则清洗(monkeypatch):
    """参数补全的 LLM 调用失败时，退回规则清洗，仍能听懂「文件名叫 a.txt」。"""
    def boom(*a, **k):
        raise RuntimeError("网关超时")

    dispatched = []
    monkeypatch.setattr(orchestrator, "complete_args", boom)
    monkeypatch.setattr(
        orchestrator, "dispatch", lambda intent, args: dispatched.append(args) or "已保存"
    )
    orchestrator._handle_supplement(
        "文件名叫 a.txt", "s1",
        {"type": "supplement", "intent": "save_file", "args": {"content": "x"}, "missing": ["filename"]},
    )
    assert dispatched
    assert dispatched[0]["filename"] == "a.txt"


def test_补充但无缺失字段则按新指令处理(monkeypatch):
    """pending 里没有待补字段（异常状态）→ 清空后按正常指令重跑。"""
    monkeypatch.setattr(
        orchestrator, "run_agent",
        lambda text, last_file=None, history=None: {
            "result": "已列出", "confirming": False, "intent": "list_files",
            "args": {}, "history": [],
        },
    )
    result = orchestrator._handle_supplement(
        "有哪些文件", "s1",
        {"type": "supplement", "intent": "save_file", "args": {}, "missing": []},
    )
    assert result["result"] == "已列出"


def test_指代消解把最近文件传给Agent(monkeypatch):
    """两轮对话：先记住文件名，再说「它」时应把该文件名传给 Agent。"""
    monkeypatch.setattr(
        orchestrator, "run_agent",
        lambda text, last_file=None, history=None: {
            "result": "已保存", "confirming": False, "intent": "save_file",
            "args": {"filename": "a.txt"}, "history": [],
        },
    )
    orchestrator.run_text("保存 a.txt", session_id="s1")
    assert orchestrator.get_session("s1").last_file == "a.txt"

    captured = {}

    def fake(text, last_file=None, history=None):
        captured["last_file"] = last_file
        return {
            "result": "内容如下", "confirming": False, "intent": "read_file",
            "args": {"filename": last_file}, "history": [],
        }

    monkeypatch.setattr(orchestrator, "run_agent", fake)
    out = orchestrator.run_text("读一下它", session_id="s1")
    assert captured["last_file"] == "a.txt"
    assert out["result"] == "内容如下"
