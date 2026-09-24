import re

from agent.stt_skill import transcribe
from agent.intent_skill import classify, extract_value, complete_args
from agent.skill_registry import (
    discover,
    dispatch,
    required_fields,
    field_labels,
    needs_confirm,
    skill_summary,
)
from agent.session import (
    get_session,
    remember_file,
    get_pending,
    set_pending,
    clear_pending,
    append_history,
    get_history,
)
from agent.tool_calling import run_agent, NeedConfirm

# 启动时扫描并加载所有 skill（新增 skill 只需在 agent/skills/ 下新建文件）
discover()


def _missing_fields(intent: str, args: dict) -> list[str]:
    """返回 intent 下缺失（未提供或为空）的必填字段。"""
    missing = []
    for f in required_fields(intent):
        v = args.get(f)
        if v is None or str(v).strip() == "":
            missing.append(f)
    return missing


def _ask_message(intent: str, field: str) -> str:
    """生成友好的追问文案（用字段的中文说明，而非英文字段名）。

    必须告知「取消」出口：追问期间的新输入都会被当作补充而非新指令，
    用户如果不想继续，需要知道怎么退出。
    """
    label = field_labels(intent).get(field, field)
    return f"请告诉我{label}（直接回复即可；不想继续可回复「取消」）"


_CONFIRM_WORDS = (
    "确认", "确定", "是的", "是", "好的", "好", "可以", "行",
    "执行", "同意", "没问题", "删吧", "删掉吧", "动手", "来吧", "嗯",
    "ok", "okay", "yes", "y",
)
_CANCEL_WORDS = (
    "取消", "算了", "不要", "不用", "别", "不删", "留着", "保留",
    "否", "放弃", "停止", "停下", "反悔", "no", "n",
)

# 犹豫/拿不准：既不是明确取消，也绝不能当成确认（"我也不确定"含"确定"二字）。
# 这类回复一律重问，既不误删，也不替用户做放弃的决定。
_HESITATE_WORDS = ("不确定", "不确认", "还没想好", "再想想", "考虑", "纠结")


def _judge_confirm(text: str) -> str:
    """判断确认环节的回复：'confirm' / 'cancel' / 'unknown'。

    优先级：明确取消 > 犹豫 > 确认。
    - 取消优先于确认：同时命中时按取消处理（宁可误取消，不可误删）；
    - 犹豫优先于确认且不算取消：既不误删，也不替用户做放弃的决定，重问即可。
    """
    t = re.sub(r"[\s，。！？、,.!?~]+", "", (text or "").strip().lower())
    if not t:
        return "unknown"
    if any(w in t for w in _CANCEL_WORDS):
        return "cancel"
    if any(w in t for w in _HESITATE_WORDS):
        return "unknown"
    if any(w in t for w in _CONFIRM_WORDS):
        return "confirm"
    return "unknown"


def _confirm_message(intent: str, args: dict) -> str:
    """生成危险操作的确认问句（说明操作 + 目标文件 + 两个选项）。"""
    parts = [f"即将执行：{skill_summary(intent)}"]
    target = args.get("filename")
    if target:
        parts.append(f"目标文件：{target}")
    tips = "确定要继续吗？回复「确认」执行，回复「取消」放弃。"
    return "；".join(parts) + "。" + tips


def _remember(session_id: str | None, intent: str, args: dict) -> None:
    """回写本次操作涉及的文件名，供下一轮指代消解使用。"""
    if not session_id:
        return
    filename = args.get("filename")
    if filename:
        remember_file(session_id, filename)
    # 改名成功后，"它"应该指向新名字，否则下一轮会指向已经不存在的旧名
    if intent == "rename_file" and args.get("new_name"):
        remember_file(session_id, args["new_name"])


def _run_pipeline(text: str, session_id: str | None) -> dict:
    """文字 → Agent 循环（工具调用）→ 回写。音频/文本两条通道共用。"""
    # ① 上一轮有事没办完？→ 本轮输入当作"补充"或"确认"，不再开启新意图
    if session_id:
        pending = get_pending(session_id)
        if pending:
            if pending.get("type") == "confirm":
                return _handle_confirm(text, session_id, pending)
            return _handle_supplement(text, session_id, pending)

    # ② 取会话上下文：指代消解用的最近文件名 + 多轮对话历史
    last_file = None
    history: list = []
    if session_id:
        last_file = get_session(session_id).last_file
        history = get_history(session_id)

    # ③ 主路径：function calling Agent 循环
    try:
        outcome = run_agent(text, last_file=last_file, history=history)
    except NeedConfirm as nc:
        # 危险操作 → 不立即执行，先征求用户确认
        msg = _confirm_message(nc.intent, nc.params)
        if session_id:
            set_pending(session_id, {"type": "confirm", "intent": nc.intent, "args": nc.params})
            return {"text": text, "intent": {"intent": nc.intent, **nc.params}, "result": msg, "confirming": True}
        # 没有会话就无法等待下一轮确认，安全地不执行
        return {
            "text": text,
            "intent": {"intent": nc.intent, **nc.params},
            "result": "该操作需要二次确认，但当前会话不可用，已取消。",
            "confirming": True,
        }
    except Exception:
        # 网关异常 / 不支持 tools → 回退旧的手写分类路径
        return _run_legacy(text, session_id)

    # ④ 回写：多轮对话历史 + 最近操作的文件名
    if session_id:
        for item in outcome.get("history") or []:
            append_history(session_id, item["role"], item["content"])
    _remember(session_id, outcome.get("intent"), outcome.get("args") or {})

    result = outcome["result"]
    # ask_doc 等带「参考来源」标注的 skill：模型一句话总结时可能把来源省掉，
    # 这里从工具原始返回中把来源行补回去，保证答案可溯源。
    tool_result = outcome.get("tool_result") or ""
    if "参考来源：" in tool_result and "参考来源" not in result:
        source = tool_result.split("参考来源：", 1)[1].strip().splitlines()[0].strip()
        result = f"{result}\n\n参考来源：{source}"

    return {
        "text": text,
        "intent": {"intent": outcome.get("intent"), **(outcome.get("args") or {})},
        "result": result,
        "confirming": outcome.get("confirming", False),
    }


def _run_legacy(text: str, session_id: str | None) -> dict:
    """回退路径：手写 prompt 意图分类 → 执行（网关不支持 tools 时兜底）。"""
    context = None
    if session_id:
        s = get_session(session_id)
        if s.last_file:
            context = f"【上下文】用户最近操作过的文件是：{s.last_file}"

    try:
        intent_data = classify(text, context)
    except Exception as e:
        return {"text": text, "intent": {}, "result": f"意图分类失败：{e}"}

    intent = intent_data.get("intent")

    # 缺必填字段 → 反问并记住待补全意图
    missing = _missing_fields(intent, intent_data)
    if missing:
        if session_id:
            set_pending(session_id, {
                "type": "supplement",
                "intent": intent,
                "args": intent_data,
                "missing": missing,
            })
        return {
            "text": text,
            "intent": intent_data,
            "result": _ask_message(intent, missing[0]),
            "asking": missing[0],
        }

    # 危险操作 → 不立即执行，先征求用户确认
    if needs_confirm(intent):
        msg = _confirm_message(intent, intent_data)
        if session_id:
            set_pending(session_id, {"type": "confirm", "intent": intent, "args": intent_data})
            return {"text": text, "intent": intent_data, "result": msg, "confirming": True}
        return {
            "text": text,
            "intent": intent_data,
            "result": "该操作需要二次确认，但当前会话不可用，已取消。",
            "confirming": True,
        }

    try:
        result = dispatch(intent, intent_data)
    except Exception as e:
        result = f"执行失败：{e}"

    _remember(session_id, intent, intent_data)

    return {"text": text, "intent": intent_data, "result": result}


def _handle_confirm(text: str, session_id: str, pending: dict) -> dict:
    """处理危险操作的确认回复：确认 → 执行；取消 → 放弃；听不懂 → 重问。"""
    intent = pending.get("intent")
    args = pending.get("args", {})
    judged = _judge_confirm(text)

    # ① 含糊回复（含用户临时改口说别的）→ 保持 pending，重申确认问句
    if judged == "unknown":
        return {
            "text": text,
            "intent": {"intent": intent},
            "result": _confirm_message(intent, args),
            "confirming": True,
        }

    clear_pending(session_id)

    # ② 取消 → 直接放弃，不触碰文件
    if judged == "cancel":
        return {"text": text, "intent": {"intent": "cancel"}, "result": "已取消本次操作。"}

    # ③ 确认 → 真正执行
    try:
        result = dispatch(intent, args)
    except Exception as e:
        result = f"执行失败：{e}"

    _remember(session_id, intent, args)

    return {"text": text, "intent": {"intent": intent, **args}, "result": result}


def _handle_supplement(text: str, session_id: str, pending: dict) -> dict:
    """处理补充回复：LLM 补全参数 → 合并 → 再检测 → 执行。"""
    intent = pending["intent"]
    args = pending.get("args", {})
    missing = pending.get("missing", [])

    # 异常兜底：没有待补字段，清空后按正常流程处理
    if not missing:
        clear_pending(session_id)
        return _run_pipeline(text, session_id)

    field_name = missing[0]

    # ① 优先用 LLM 补全（理解任意说法 + 支持取消）；调用失败则退回规则清洗
    try:
        completed = complete_args(intent, args, field_name, text)
    except Exception:
        completed = None

    if completed is None:
        completed = {field_name: extract_value(text)}
    elif completed.get("intent") == "cancel":
        # ② 用户临时取消
        clear_pending(session_id)
        return {"text": text, "intent": {"intent": "cancel"}, "result": "已取消该操作。"}

    # ③ 合并：以已收集参数为基础，LLM 返回的非空值才覆盖（防止丢字段）
    merged = {"intent": intent, **args}
    for k, v in completed.items():
        if k == "intent":
            continue
        if v is not None and str(v).strip() != "":
            merged[k] = v

    # ④ 重新检测剩余必填字段
    remaining = _missing_fields(intent, merged)
    if remaining:
        pending["args"] = merged
        pending["missing"] = remaining
        return {
            "text": text,
            "intent": {"intent": intent},
            "result": _ask_message(intent, remaining[0]),
            "asking": remaining[0],
        }

    # ⑤ 齐全 → 执行
    clear_pending(session_id)
    try:
        result = dispatch(intent, merged)
    except Exception as e:
        result = f"执行失败：{e}"

    _remember(session_id, intent, merged)

    return {"text": text, "intent": merged, "result": result}


def run(audio_data: bytes, audio_name: str = "audio.wav", session_id: str | None = None) -> dict:
    """音频通道：语音转文字 → 意图 → 执行。"""
    try:
        text = transcribe(audio_data, audio_name)
    except Exception as e:
        return {"text": "", "intent": {}, "result": f"语音识别失败：{e}"}
    return _run_pipeline(text, session_id)


def run_text(text: str, session_id: str | None = None) -> dict:
    """文本通道：跳过语音识别，文字直接走意图 → 执行。"""
    text = (text or "").strip()
    if not text:
        return {"text": "", "intent": {}, "result": "请输入指令内容。"}
    return _run_pipeline(text, session_id)
