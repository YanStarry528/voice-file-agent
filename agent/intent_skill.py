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
    lines.append("上下文规则：")
    lines.append("1. 只有当用户提到\"它\"\"他\"\"她\"\"这个文件\"\"刚才那个\"\"上一个文件\"等代词时，")
    lines.append("   （他/她/它与它是同音字，语音输入会随机转成其中一个，视为同一个指代词）")
    lines.append("   才可以用【上下文】中给出的最近操作文件名填充 filename。")
    lines.append("2. 如果用户没有提到任何文件名，filename 必须填空字符串 \"\"：")
    lines.append("   禁止自己编造文件名，也禁止默认使用上下文中的文件名。")
    lines.append("")
    lines.append("请只输出 JSON，不要有任何其他文字。")
    lines.append('如果用户说的不是以上操作，输出：{"intent": "unknown"}')
    return "\n".join(lines)


def classify(text: str, context: str | None = None) -> dict:
    user_content = text
    if context:
        user_content = f"{context}\n{text}"
    response = llm_client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": _build_system_prompt()},
            {"role": "user", "content": user_content},
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


_VALUE_PREFIXES = [
    "文件名叫做", "名字叫做", "文件名叫", "名字叫", "文件名是", "文件名",
    "名字是", "叫做", "就叫", "叫", "是",
]


def extract_value(text: str) -> str:
    """把用户补充的字段值从自然语言里清洗出来（用于缺参数追问后的补充）。"""
    v = (text or "").strip()
    if not v:
        return ""
    # 循环剥离前缀（如"文件名叫做"要先剥"文件名叫"再剥"叫做"）
    changed = True
    while changed:
        changed = False
        for p in _VALUE_PREFIXES:
            if v.startswith(p):
                v = v[len(p):].strip()
                changed = True
                break
    v = re.sub(r"[吧啦呢啊呀哦哈]+$", "", v)
    v = v.strip("，。,.！!？? 　")
    return v.strip()


def complete_args(intent: str, args: dict, missing_field: str, text: str) -> dict:
    """让 LLM 结合已知意图，把用户的补充整理成完整参数 JSON。

    比规则清洗泛化更好：能理解任意说法，且支持用户临时取消。
    """
    system = (
        "你是参数补全助手。用户正在执行一个操作，已收集到部分参数，还缺一个必填字段。\n"
        "请根据用户本轮的补充内容，输出【完整】的参数 JSON。\n"
        "\n"
        "规则：\n"
        "1. intent 和已收集的参数值保持原样，不要修改或删改。\n"
        f"2. 把用户补充的内容整理后填入缺失字段 \"{missing_field}\"，"
        "去掉纯粹的口头前缀（如\"文件名叫\"\"就叫\"\"叫做\"），只保留真正的值。\n"
        "3. 如果用户明确表示取消、放弃、不做了，输出：{\"intent\": \"cancel\"}\n"
        "4. 如果听不出缺失字段的值，该字段填空字符串 \"\"。\n"
        "5. 请只输出 JSON，不要有任何其他文字。\n"
    )
    user_content = (
        f"当前操作 intent：{intent}\n"
        f"已收集参数：{json.dumps(args, ensure_ascii=False)}\n"
        f"缺失字段：{missing_field}\n"
        f"用户补充：{text}"
    )
    response = llm_client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user_content},
        ],
        temperature=0,
    )
    raw = response.choices[0].message.content
    return _parse_json(raw)
