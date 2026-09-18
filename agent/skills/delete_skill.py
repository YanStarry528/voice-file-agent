import os

from agent.common import OUTPUT_DIR
from agent.skill_registry import register


@register(
    intent="delete_file",
    description="删除 output 目录下的某个文件（对应：删除、删掉、移除）",
    fields={"filename": "文件名"},
)
def execute(args: dict) -> str:
    """删除 output 目录下指定的文件。"""
    filename = args.get("filename", "")
    safe_name = os.path.basename(filename)

    if not safe_name:
        return "请指定要删除的文件名。"

    path = OUTPUT_DIR / safe_name

    if not path.exists():
        return f"文件 {safe_name} 不存在"

    os.remove(path)
    return f"已删除 {path}"
