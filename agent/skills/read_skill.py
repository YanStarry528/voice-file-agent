import os

from agent.common import OUTPUT_DIR  # noqa: F401  # 供测试隔离 fixture 注入
from agent.paths import resolve_output_file
from agent.skill_registry import register


@register(
    intent="read_file",
    description="查看某个文件的内容（对应：看看、读一下、打开、内容是什么）",
    fields={"filename": "文件名"},
)
def execute(args: dict) -> str:
    """读取 output 目录下指定文件的全部内容。

    文件名没带后缀时，会依次尝试原名与「原名.txt」，
    因此语音说的「会议记录」也能读到实际存储的「会议记录.txt」。
    """
    filename = args.get("filename", "")
    safe_name = os.path.basename(str(filename))

    if not safe_name:
        return "请指定要查看的文件名。"

    try:
        path = resolve_output_file(safe_name)
    except ValueError as e:
        return str(e)

    if not path.exists():
        return f"文件 {safe_name} 不存在"
    if path.is_dir():
        return f"{safe_name} 是一个目录，不是文件"

    return path.read_text(encoding="utf-8")
