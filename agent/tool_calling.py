"""基于 LLM function calling 的 Agent 循环。

把「一句话归一个类」升级为真正的工具调用循环：

    用户指令 → LLM 决定调用哪个工具 → 执行 → 把结果喂回 LLM
            → 观察后再决定是否继续调用 → 直到任务完成给出总结。

相比旧的手写 prompt → JSON 分类，这里让模型在工具清单里自主决策，
支持复合指令（如「读会议记录，把待办存成 todo.txt」会被拆成多步）。

危险操作（confirm=True 的 skill）不在这里执行：一旦模型要调用，
抛 NeedConfirm 交给 orchestrator 走二次确认流程。
"""
import json

from agent.common import chat
from agent.skill_registry import build_tools, dispatch, needs_confirm

# 单轮最多允许的「思考→调用」往返次数，覆盖绝大多数复合指令
MAX_ROUNDS = 6


class NeedConfirm(Exception):
    """模型试图执行危险操作，但尚未经用户二次确认。

    注意：参数名用 params 而非 args，避免覆盖 BaseException.args。
    """
    def __init__(self, intent: str, params: dict):
        super().__init__(intent)
        self.intent = intent
        self.params = params


def _system_prompt(last_file: str | None) -> str:
    lines = [
        "你是语音文件助手。用户通过语音或文字下达文件操作指令，你需要调用工具来完成。",
        "",
        "规则：",
        "1. 用工具完成文件操作，不要凭空编造文件内容或操作结果。",
        "2. 缺少必要信息（如文件名、要写的内容）时，先用文字追问用户，不要乱填、不要猜。",
        "3. 用户的一句话可能包含多个动作，可以分多步调用工具完成；每次调用后根据返回结果决定下一步。",
        "4. 全部完成后，用一句话向用户总结结果。",
    ]
    if last_file:
        lines.append(
            f"5. 上下文：用户最近操作过的文件是「{last_file}」。"
            "当用户用「它 / 这个文件 / 刚才那个 / 上一个文件」等代词指代时，用这个名字。"
        )
    return "\n".join(lines)


def _assistant_with_tool_calls(msg) -> dict:
    """把 OpenAI 返回的 assistant 消息转成可回传的 dict（保留 tool_calls）。"""
    return {
        "role": "assistant",
        "content": msg.content or "",
        "tool_calls": [
            {
                "id": tc.id,
                "type": "function",
                "function": {"name": tc.function.name, "arguments": tc.function.arguments},
            }
            for tc in msg.tool_calls
        ],
    }


def run_agent(text: str, last_file: str | None = None, history: list[dict] | None = None) -> dict:
    """执行一轮 Agent 循环。

    参数：
        text:      本轮用户输入
        last_file: 最近操作的文件名（用于「它」等指代消解）
        history:   此前多轮对话 [{role, content}]，用于追问补全

    返回：
        {
            "result":    最终给用户看的文本（总结 / 追问 / 错误提示）,
            "confirming": bool,
            "intent":    最后一次工具调用的意图（无工具调用则为 None）,
            "args":      最后一次工具调用的参数（无则为 {}）,
            "history":   本轮新增的对话 [{"role":"user",...},{"role":"assistant",...}],
        }

    可能抛 NeedConfirm（危险操作需二次确认）。
    """
    messages = [{"role": "system", "content": _system_prompt(last_file)}]
    messages.extend(history or [])
    messages.append({"role": "user", "content": text})

    last_intent: str | None = None
    last_args: dict = {}

    for _ in range(MAX_ROUNDS):
        resp = chat(messages=messages, tools=build_tools())
        msg = resp.choices[0].message

        # 没有工具调用 → 是最终回复或追问，直接返回
        if not msg.tool_calls:
            final = (msg.content or "").strip() or "已完成。"
            return {
                "result": final,
                "confirming": False,
                "intent": last_intent,
                "args": last_args,
                "history": [
                    {"role": "user", "content": text},
                    {"role": "assistant", "content": final},
                ],
            }

        # 有工具调用 → 追加 assistant 消息后逐个执行
        messages.append(_assistant_with_tool_calls(msg))
        for tc in msg.tool_calls:
            name = tc.function.name
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}

            # 危险操作 → 抛给 orchestrator 做二次确认
            if needs_confirm(name):
                raise NeedConfirm(name, args)

            result = dispatch(name, args)
            messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})
            last_intent = name
            last_args = args

    # 循环跑满仍未结束（连续调用超过上限），给个明确提示
    return {
        "result": "任务步骤过多，已暂停。请拆分指令后再试。",
        "confirming": False,
        "intent": last_intent,
        "args": last_args,
        "history": [
            {"role": "user", "content": text},
            {"role": "assistant", "content": "任务步骤过多，已暂停。"},
        ],
    }
