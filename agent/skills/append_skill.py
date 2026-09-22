import os

from agent.common import OUTPUT_DIR
from agent.paths import safe_output_path
from agent.skill_registry import register


@register(
    intent="append_file",
    description="在已有文件末尾追加内容（对应：追加、加上、补充、在...后面加）",
    fields={"filename": "文件名", "content": "要追加的内容"},
    required=["filename", "content"],
)
def execute(args: dict) -> str:
    """在 output 目录下的指定文件末尾追加内容；文件不存在则新建。"""
    filename = args.get("filename", "untitled.txt")
    content = args.get("content", "")

    try:
        path = safe_output_path(filename)
    except ValueError as e:
        return str(e)

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    existed = path.exists()

    # 追加前确保另起一行：若原文件末尾没有换行符，先补一个，避免直接贴到最后一行末尾
    need_newline = False
    if existed and path.stat().st_size > 0:
        with open(path, "rb") as f:
            f.seek(-1, os.SEEK_END)
            need_newline = f.read(1) != b"\n"

    with open(path, "a", encoding="utf-8") as f:
        if need_newline:
            f.write("\n")
        f.write(content + "\n")

    if existed:
        return f"已在 {path} 末尾追加内容"
    return f"文件不存在，已新建 {path} 并写入内容"
