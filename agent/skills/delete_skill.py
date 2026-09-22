import os

from agent.common import OUTPUT_DIR
from agent.paths import safe_output_path
from agent.skill_registry import register


@register(
    intent="delete_file",
    description="删除 output 目录下的某个文件（对应：删除、删掉、移除）",
    fields={"filename": "文件名"},
    confirm=True,  # 删除不可逆，执行前需要用户二次确认
)
def execute(args: dict) -> str:
    """删除 output 目录下指定的文件。"""
    filename = args.get("filename", "")

    if not filename or not filename.strip():
        return "请指定要删除的文件名。"

    try:
        path = safe_output_path(filename)
    except ValueError as e:
        return str(e)

    if not path.exists():
        return f"文件 {filename} 不存在"

    os.remove(path)
    return f"已删除 {path}"
