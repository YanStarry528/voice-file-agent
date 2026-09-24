"""会议纪要整理 skill：读取会议记录文件，调用 LLM 整理成结构化纪要。

这是第一个「依赖 LLM」的 skill（此前的 skill 都是纯本地文件操作）：
execute 内部调用 common.chat，把原始会议记录整理成结构化纪要，
并另存为「原文件名_纪要.txt」，同时返回纪要全文供页面展示。
"""
from agent.common import chat
from agent.paths import resolve_output_file
from agent.skill_registry import register


def _summarize(content: str) -> str:
    """调用 LLM 把原始会议记录整理成结构化纪要（markdown）。"""
    system = (
        "你是会议纪要整理助手。请把用户提供的会议记录整理成一份简洁、结构化的会议纪要。\n"
        "只依据用户消息中的会议记录原文整理，严禁引入原文中不存在的信息。\n"
        "按以下结构输出（用 markdown）：\n"
        "## 会议主题\n一句话概括本次会议。\n"
        "## 关键结论\n分点列出，每条一行，以 - 开头。\n"
        "## 待办事项\n分点列出，每条一行，以 - 开头；没有待办就写「无」。\n"
        "直接输出纪要内容，不要任何多余的解释或开场白。"
    )
    resp = chat(
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": content},
        ],
    )
    return (resp.choices[0].message.content or "").strip()


@register(
    intent="summarize_meeting",
    description="把会议记录整理成结构化纪要（对应：整理会议纪要、生成会议纪要、总结会议、把会议记录整理一下）",
    fields={"filename": "要整理的会议记录文件名"},
)
def execute(args: dict) -> str:
    """读取会议记录 → LLM 整理 → 另存为「原文件名_纪要.txt」并返回纪要全文。"""
    filename = str(args.get("filename", "")).strip()
    if not filename:
        return "请指定要整理的会议记录文件名。"

    try:
        path = resolve_output_file(filename)
    except ValueError as e:
        return str(e)

    if not path.exists():
        return f"文件 {filename} 不存在"
    if path.is_dir():
        return f"{filename} 是一个目录，不是文件"

    content = path.read_text(encoding="utf-8", errors="ignore").strip()
    if not content:
        return f"文件 {path.name} 是空的，没有内容可整理。"

    summary = _summarize(content)

    out_path = path.with_name(path.stem + "_纪要.txt")
    out_path.write_text(summary, encoding="utf-8")

    return f"已生成会议纪要，保存到「{out_path.name}」：\n\n{summary}"
