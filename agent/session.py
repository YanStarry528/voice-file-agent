"""会话记忆管理。

MVP：只记一个槽位 last_file（最近一次文件操作涉及的文件名），
用于把"它 / 这个文件 / 刚才那个文件"等指代解析成真实文件名。
"""

from collections import deque
from dataclasses import dataclass, field

_SESSIONS: dict[str, "Session"] = {}


@dataclass
class Session:
    session_id: str
    last_file: str | None = None           # 最近一次文件操作的文件名
    history: deque = field(default_factory=lambda: deque(maxlen=5))  # 最近几轮文件操作（供后续多轮上下文扩展）
    messages: list = field(default_factory=list)  # 多轮对话历史 [{role, content}]，供 function calling 追问补全
    pending: dict | None = None            # 待办事项，两种类型：
                                           #   {"type":"supplement", "intent", "args", "missing":[...]}  缺参数，等待用户补充
                                           #   {"type":"confirm",     "intent", "args"}                 危险操作，等待用户确认


def get_session(session_id: str) -> Session:
    """按 session_id 取会话，不存在则新建。"""
    if session_id not in _SESSIONS:
        _SESSIONS[session_id] = Session(session_id=session_id)
    return _SESSIONS[session_id]


def remember_file(session_id: str, filename: str) -> None:
    """记录一次文件操作涉及的文件名，更新 last_file 并写入历史。"""
    s = get_session(session_id)
    s.last_file = filename
    s.history.append({"filename": filename})


def set_pending(session_id: str, pending: dict) -> None:
    """记录待补全的意图（缺参数反问后等待用户补充）。"""
    get_session(session_id).pending = pending


def get_pending(session_id: str) -> dict | None:
    """取当前待补全的意图，无则返回 None。"""
    return get_session(session_id).pending


def clear_pending(session_id: str) -> None:
    """清空待补全意图（补全完成或取消后调用）。"""
    get_session(session_id).pending = None


def reset_session(session_id: str) -> None:
    """清空某个会话的记忆（用于前端"新对话"）。"""
    _SESSIONS.pop(session_id, None)


def append_history(session_id: str, role: str, content: str) -> None:
    """向会话追加一轮对话记录，用于多轮追问补全。

    只保留最近几轮，避免历史无限增长、拖长每次请求。
    """
    s = get_session(session_id)
    s.messages.append({"role": role, "content": content})
    if len(s.messages) > 12:
        s.messages = s.messages[-12:]


def get_history(session_id: str) -> list[dict]:
    """返回会话的对话历史副本（无会话则空列表）。"""
    s = get_session(session_id)
    return list(s.messages)
