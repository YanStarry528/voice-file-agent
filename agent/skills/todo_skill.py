"""待办清单 skill：记待办、列待办、标记完成。

三个操作共享 output/todo.txt 一个数据文件，每条占一行：
    [ ] 待办内容        # 未完成
    [x] 待办内容        # 已完成
"""
from agent.paths import resolve_output_file
from agent.skill_registry import register

# 待办清单统一存放在这一个文件里
TODO_FILE = "todo.txt"


def _todo_path():
    """返回待办清单文件的绝对路径（在 output 目录内，经安全校验）。"""
    return resolve_output_file(TODO_FILE)


@register(
    intent="add_todo",
    description="记一条待办事项（对应：记个待办、添加待办、帮我记一下、待办清单加一条）",
    fields={"content": "待办事项内容"},
)
def add_todo(args: dict) -> str:
    """往待办清单里追加一条待办。"""
    content = str(args.get("content", "")).strip()
    if not content:
        return "请说清要记的待办内容。"

    path = _todo_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(f"[ ] {content}\n")
    return f"已记下待办：{content}"


@register(
    intent="list_todo",
    description="列出所有待办事项（对应：我的待办、待办清单、还有哪些事没做、看看待办）",
    fields=None,
)
def list_todo(args: dict) -> str:
    """列出待办清单（未完成 + 已完成）。"""
    path = _todo_path()
    if not path.exists():
        return "还没有记下任何待办。"

    lines = path.read_text(encoding="utf-8").splitlines()
    pending = [line[4:] for line in lines if line.startswith("[ ]")]
    done = [line[4:] for line in lines if line.startswith("[x]")]

    if not pending and not done:
        return "还没有记下任何待办。"

    parts = []
    if pending:
        numbered = "\n".join(f"{i}. {t}" for i, t in enumerate(pending, 1))
        parts.append(f"还有 {len(pending)} 条待办：\n{numbered}")
    if done:
        finished = "\n".join(f"- {t}" for t in done)
        parts.append(f"已完成 {len(done)} 条：\n{finished}")
    return "\n\n".join(parts)


@register(
    intent="done_todo",
    description="把某条待办标记为已完成（对应：做完了、完成了、标记完成、办好了）",
    fields={"content": "要标记完成的待办内容（说关键词即可）"},
)
def done_todo(args: dict) -> str:
    """把包含指定关键词的未完成待办标记为已完成。"""
    content = str(args.get("content", "")).strip()
    if not content:
        return "请说要标记完成哪条待办。"

    path = _todo_path()
    if not path.exists():
        return "还没有记下任何待办。"

    lines = path.read_text(encoding="utf-8").splitlines()
    matched = 0
    new_lines = []
    for line in lines:
        if line.startswith("[ ]") and content in line[4:]:
            new_lines.append("[x]" + line[3:])
            matched += 1
        else:
            new_lines.append(line)

    if matched == 0:
        return f"没有找到包含「{content}」的待办。"

    path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    return f"已把 {matched} 条待办标记为完成：{content}"
