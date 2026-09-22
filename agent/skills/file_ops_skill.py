import os

from agent.common import OUTPUT_DIR
from agent.paths import safe_output_path
from agent.skill_registry import register


@register(
    intent="save_file",
    description="新建或覆盖一个文件（对应：新建、创建、保存）",
    fields={"filename": "文件名", "content": "要保存的内容"},
    required=["filename"],
)
def execute(args: dict) -> str:
    """把内容保存到 output 目录下的指定文件（新建或覆盖）。"""
    filename = args.get("filename", "untitled.txt")
    content = args.get("content", "")

    try:
        path = safe_output_path(filename)
    except ValueError as e:
        return str(e)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

    return f"已保存到 {path}"
