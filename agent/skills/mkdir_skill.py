from agent.paths import safe_output_path
from agent.skill_registry import register


@register(
    intent="make_dir",
    description="新建一个文件夹（对应：新建文件夹、创建文件夹、建一个目录、建个文件夹）",
    fields={"dirname": "文件夹名"},
)
def execute(args: dict) -> str:
    """在 output 目录下新建一个子文件夹（文件夹名不会自动补后缀）。"""
    dirname = args.get("dirname", "")

    if not dirname.strip():
        return "请指定要新建的文件夹名。"

    try:
        path = safe_output_path(dirname)
    except ValueError as e:
        return str(e)

    if path.exists():
        if path.is_dir():
            return f"文件夹 {dirname} 已存在"
        return f"已存在同名文件 {dirname}，无法创建同名文件夹"

    path.mkdir(parents=True)
    return f"已新建文件夹 {path.name}/"
