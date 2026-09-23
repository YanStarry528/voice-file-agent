import os

from agent.common import OUTPUT_DIR
from agent.paths import resolve_output_file
from agent.skill_registry import register


@register(
    intent="save_file",
    description="新建或覆盖一个文件（对应：新建、创建、保存）",
    fields={"filename": "文件名", "content": "要保存的内容"},
    required=["filename"],
)
def execute(args: dict) -> str:
    """把内容保存到 output 目录下的指定文件（新建或覆盖）。

    文件名没带后缀时会自动补 .txt（语音输入不会说出「点 txt」）。
    """
    filename = args.get("filename", "untitled.txt")
    content = args.get("content", "")

    try:
        path = resolve_output_file(filename)
    except ValueError as e:
        return str(e)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

    return f"已保存到 {path}"
