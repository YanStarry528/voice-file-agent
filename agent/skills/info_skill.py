from datetime import datetime

from agent.paths import resolve_output_file
from agent.skill_registry import register


def _human_size(num: float) -> str:
    """把字节数转成易读的 B / KB / MB 文本。"""
    size = float(num)
    if size < 1024:
        return f"{size:.0f} B"
    if size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    return f"{size / 1024 / 1024:.1f} MB"


@register(
    intent="file_info",
    description=(
        "查看文件的大小与最后修改时间（对应：文件多大、有多大了、什么时候改的、"
        "文件信息、修改时间、占用多少空间）"
    ),
    fields={"filename": "文件名"},
)
def execute(args: dict) -> str:
    """查看 output 目录下指定文件的大小（B/KB/MB）与最后修改时间。"""
    filename = args.get("filename", "")

    if not filename.strip():
        return "请指定要查看的文件名。"

    try:
        path = resolve_output_file(filename)
    except ValueError as e:
        return str(e)

    if not path.exists():
        return f"文件 {filename} 不存在"
    if path.is_dir():
        return f"{filename} 是一个目录，不是文件"

    st = path.stat()
    mtime = datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
    return f"{path.name} 大小 {_human_size(st.st_size)}，最后修改于 {mtime}"
