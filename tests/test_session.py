"""session 会话记忆的单元测试（多轮上下文 / 待办状态 / 历史裁剪）。

session 是模块级全局字典，由 conftest 的 _reset_sessions fixture 在每个测试前后清空，
因此这里各用例互相隔离，不会串号。
"""
from agent import session


def test_新会话初始状态():
    s = session.get_session("s1")
    assert s.session_id == "s1"
    assert s.last_file is None
    assert s.pending is None
    assert session.get_history("s1") == []


def test_同一id复用会话():
    s1 = session.get_session("s1")
    s1.last_file = "a.txt"
    s2 = session.get_session("s1")
    assert s2 is s1
    assert s2.last_file == "a.txt"


def test_不同会话互不干扰():
    session.remember_file("s1", "a.txt")
    session.remember_file("s2", "b.txt")
    assert session.get_session("s1").last_file == "a.txt"
    assert session.get_session("s2").last_file == "b.txt"


def test_记住文件更新last_file():
    session.remember_file("s1", "a.txt")
    session.remember_file("s1", "b.txt")
    assert session.get_session("s1").last_file == "b.txt"


def test_记住文件写入历史():
    session.remember_file("s1", "a.txt")
    session.remember_file("s1", "b.txt")
    s = session.get_session("s1")
    assert [h["filename"] for h in s.history] == ["a.txt", "b.txt"]


def test_文件历史只保留最近5条():
    for i in range(8):
        session.remember_file("s1", f"f{i}.txt")
    s = session.get_session("s1")
    assert len(s.history) == 5
    assert [h["filename"] for h in s.history] == [f"f{i}.txt" for i in range(3, 8)]


def test_设置与读取待办():
    pending = {"type": "confirm", "intent": "delete_file", "args": {"filename": "a.txt"}}
    session.set_pending("s1", pending)
    assert session.get_pending("s1") == pending


def test_无待办返回None():
    assert session.get_pending("s1") is None


def test_清空待办():
    session.set_pending("s1", {"type": "confirm", "intent": "delete_file"})
    session.clear_pending("s1")
    assert session.get_pending("s1") is None


def test_重置会话清空全部记忆():
    session.remember_file("s1", "a.txt")
    session.set_pending("s1", {"type": "confirm"})
    session.append_history("s1", "user", "删掉它")
    session.reset_session("s1")

    s = session.get_session("s1")
    assert s.last_file is None
    assert s.pending is None
    assert session.get_history("s1") == []


def test_追加对话历史():
    session.append_history("s1", "user", "保存 a.txt")
    session.append_history("s1", "assistant", "已保存")
    assert session.get_history("s1") == [
        {"role": "user", "content": "保存 a.txt"},
        {"role": "assistant", "content": "已保存"},
    ]


def test_对话历史只保留最近12条():
    for i in range(15):
        session.append_history("s1", "user", f"第{i}轮")
    history = session.get_history("s1")
    assert len(history) == 12
    assert history[0]["content"] == "第3轮"
    assert history[-1]["content"] == "第14轮"


def test_历史返回副本不影响内部():
    session.append_history("s1", "user", "原始")
    history = session.get_history("s1")
    history.append({"role": "user", "content": "外部追加"})
    assert len(session.get_history("s1")) == 1
