import os

from agent.common import OUTPUT_DIR
from agent.skill_registry import register


@register(
    intent="read_file",
    description="查看某个文件的内容（对应：看看、读一下、打开、内容是什么）",
    fields={"filename": "文件名"},
)
def execute(args: dict) -> str:
    """读取 output 目录下指定文件的全部内容。"""
    filename = args.get("filename", "")
    safe_name = os.path.basename(filename)

    if not safe_name:
        return "请指定要查看的文件名。"

    path = OUTPUT_DIR / safe_name

    if not path.exists():
        return f"文件 {safe_name} 不存在"
    if path.is_dir():
        return f"{safe_name} 是一个目录，不是文件"

    return path.read_text(encoding="utf-8")
