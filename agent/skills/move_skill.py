import shutil

from agent.paths import resolve_output_file, safe_output_path
from agent.skill_registry import register


@register(
    intent="move_file",
    description=(
        "把文件移动到指定文件夹（对应：移动、挪到、放进、移到…文件夹；"
        "注意：换位置用这个，只是改名字属于 rename_file）"
    ),
    fields={"filename": "要移动的原文件名", "target_dir": "目标文件夹名"},
)
def execute(args: dict) -> str:
    """把 output 目录下的文件移动到指定子文件夹，目标文件夹不存在则自动创建。"""
    filename = args.get("filename", "")
    target_dir = args.get("target_dir", "")

    if not filename.strip():
        return "请指定要移动的文件名。"
    if not target_dir.strip():
        return "请指定目标文件夹名。"

    try:
        src = resolve_output_file(filename)
        dst_dir = safe_output_path(target_dir)
    except ValueError as e:
        return str(e)

    if not src.exists():
        return f"文件 {filename} 不存在"
    if src.is_dir():
        return f"{filename} 是一个目录，不是文件"

    dst_dir.mkdir(parents=True, exist_ok=True)
    dst = dst_dir / src.name
    if dst.exists():
        return f"目标文件夹里已有同名文件 {src.name}，未做改动"

    shutil.move(str(src), str(dst))
    return f"已将 {src.name} 移动到文件夹 {dst_dir.name}/"
