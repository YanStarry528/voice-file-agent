import os

from agent.common import OUTPUT_DIR  # noqa: F401  # 供测试隔离 fixture 注入
from agent.paths import resolve_output_file
from agent.skill_registry import register


@register(
    intent="count_words",
    description="统计某个文件的字数与行数（对应：有多少字、多少行、字数、统计一下）",
    fields={"filename": "文件名"},
)
def execute(args: dict) -> str:
    """统计 output 目录下指定文件的字数（非空白字符）与行数。

    文件名没带后缀时，会依次尝试原名与「原名.txt」。
    """
    filename = args.get("filename", "")
    safe_name = os.path.basename(str(filename))

    if not safe_name:
        return "请指定要统计的文件名。"

    try:
        path = resolve_output_file(safe_name)
    except ValueError as e:
        return str(e)

    if not path.exists():
        return f"文件 {safe_name} 不存在"
    if path.is_dir():
        return f"{safe_name} 是一个目录，不是文件"

    text = path.read_text(encoding="utf-8", errors="ignore")
    word_count = len("".join(text.split()))  # 去掉所有空白后的字符数
    line_count = len(text.splitlines())

    return f"{path.name} 共 {word_count} 字、{line_count} 行。"
