import os

from agent.common import OUTPUT_DIR
from agent.skill_registry import register


@register(
    intent="list_files",
    description="列出 output 目录下的文件（对应：有哪些文件、列出文件、看看目录）",
    fields=None,
)
def execute(args: dict) -> str:
    """列出 output 目录下的所有文件，返回便于展示的字符串。"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    files = sorted(os.listdir(OUTPUT_DIR))

    if not files:
        return "output 目录当前是空的。"

    lines = [f"- {name}" for name in files]
    return f"output 目录下共有 {len(files)} 个文件：\n" + "\n".join(lines)
