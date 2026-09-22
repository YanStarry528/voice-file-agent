import os

from agent.common import OUTPUT_DIR
from agent.skill_registry import register


@register(
    intent="count_words",
    description="统计某个文件的字数与行数（对应：有多少字、多少行、字数、统计一下）",
    fields={"filename": "文件名"},
)
def execute(args: dict) -> str:
    """统计 output 目录下指定文件的字数（非空白字符）与行数。"""
    filename = args.get("filename", "")
    safe_name = os.path.basename(filename)

    if not safe_name:
        return "请指定要统计的文件名。"

    path = OUTPUT_DIR / safe_name

    if not path.exists():
        return f"文件 {safe_name} 不存在"
    if path.is_dir():
        return f"{safe_name} 是一个目录，不是文件"

    text = path.read_text(encoding="utf-8", errors="ignore")
    word_count = len("".join(text.split()))  # 去掉所有空白后的字符数
    line_count = len(text.splitlines())

    return f"{safe_name} 共 {word_count} 字、{line_count} 行。"
