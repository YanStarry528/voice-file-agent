import json
import re

from agent.common import llm_client, LLM_MODEL
from agent.skill_registry import all_skills


def _build_system_prompt() -> str:
    """根据已注册的 skill 动态生成意图分类 prompt。"""
    lines = [
        "你是一个意图分类器。用户会说一句话，你需要判断他想要做什么。",
        "",
        "目前支持以下操作：",
        "",
    ]
    for i, s in enumerate(all_skills(), 1):
        lines.append(f"{i}. {s['intent']}：{s['description']}")
        if s["fields"]:
            fields = ", ".join(f'"{k}": "{v}"' for k, v in s["fields"].items())
            lines.append(f"   输出格式：{{\"intent\": \"{s['intent']}\", {fields}}}")
        else:
            lines.append(f"   输出格式：{{\"intent\": \"{s['intent']}\"}}")
        lines.append("")
    lines.append("请只输出 JSON，不要有任何其他文字。")
    lines.append('如果用户说的不是以上操作，输出：{"intent": "unknown"}')
    return "\n".join(lines)


def classify(text: str) -> dict:
    response = llm_client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": _build_system_prompt()},
            {"role": "user", "content": text},
        ],
        temperature=0,
    )
    raw = response.choices[0].message.content
    return _parse_json(raw)


def _parse_json(raw: str) -> dict:
    """尽量稳健地把模型输出解析成 dict，避免格式轻微偏差就整体崩溃。"""
    raw = (raw or "").strip()
    # 去掉可能的 markdown 代码块标记（```json / ```）
    raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw).strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # 兜底：抽取第一段 {...} 再解析
        m = re.search(r"\{.*\}", raw, re.S)
        if m:
            return json.loads(m.group(0))
        raise
