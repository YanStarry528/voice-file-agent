import os

from agent.common import OUTPUT_DIR  # noqa: F401  # 供测试隔离 fixture 注入
from agent.paths import resolve_output_file
from agent.skill_registry import register


@register(
    intent="rename_file",
    description=(
        "把 output 目录下已存在的文件改成另一个名字"
        "（对应：改名为、重命名为、名字改成、名字叫做、把 X 改成 Y；"
        "注意：只用于给已有文件换名字，新建文件属于 save_file）"
    ),
    fields={"filename": "原文件名", "new_name": "新文件名"},
    confirm=False,  # 改名可逆（再改回来即可），不需要二次确认
)
def execute(args: dict) -> str:
    """重命名 output 目录下的文件。目标已存在时拒绝，避免覆盖。

    新名字没带后缀时自动补 .txt，改名后依然是能直接打开的文本文件。
    """
    old_name = args.get("filename", "")
    new_name = args.get("new_name", "")

    if not old_name:
        return "请指定要改名的原文件名。"
    if not new_name:
        return "请指定新的文件名。"
    if old_name == new_name:
        return f"新旧文件名相同（{old_name}），无需修改。"

    try:
        src = resolve_output_file(old_name)
        dst = resolve_output_file(new_name)
    except ValueError as e:
        return str(e)

    if not src.exists():
        return f"文件 {old_name} 不存在"
    if dst.exists():
        return f"文件 {dst.name} 已存在，未做改动（避免覆盖已有文件）"

    os.rename(src, dst)
    return f"已将 {src.name} 改名为 {dst.name}"
