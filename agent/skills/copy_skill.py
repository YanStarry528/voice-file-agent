import shutil

from agent.paths import resolve_output_file
from agent.skill_registry import register


@register(
    intent="copy_file",
    description=(
        "复制一份文件到新名字（对应：复制、拷贝、复制一份、另存一份；"
        "注意：只复制，原件保留；改名字但不保留原件属于 rename_file）"
    ),
    fields={"filename": "要复制的原文件名", "new_name": "复制后的新文件名"},
)
def execute(args: dict) -> str:
    """复制 output 目录下的文件到新名字，原件保留。

    新名字没带后缀时自动补 .txt；目标已存在时拒绝，避免覆盖已有文件。
    """
    old_name = args.get("filename", "")
    new_name = args.get("new_name", "")

    if not old_name.strip():
        return "请指定要复制的原文件名。"
    if not new_name.strip():
        return "请指定复制后的新文件名。"

    try:
        src = resolve_output_file(old_name)
        dst = resolve_output_file(new_name)
    except ValueError as e:
        return str(e)

    if not src.exists():
        return f"文件 {old_name} 不存在"
    if src.is_dir():
        return f"{old_name} 是一个目录，不是文件"
    if dst.exists():
        return f"文件 {dst.name} 已存在，未做改动（避免覆盖已有文件）"

    # 目标可能在子目录里（如「归档/副本.txt」），先确保父目录存在
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return f"已复制 {src.name} 为 {dst.name}"
