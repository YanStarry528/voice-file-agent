import os

from agent.common import OUTPUT_DIR
from agent.skill_registry import register


@register(
    intent="search_files",
    description="按关键词搜索文件（对应：搜索、查找、找一下、哪些文件里有、有没有包含…的文件）",
    fields={"keyword": "要搜索的关键词"},
)
def execute(args: dict) -> str:
    """在 output 目录下搜索文件名或内容包含关键词的文件。"""
    keyword = (args.get("keyword") or "").strip()
    if not keyword:
        return "请指定要搜索的关键词。"

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    matched = []
    for name in sorted(os.listdir(OUTPUT_DIR)):
        path = OUTPUT_DIR / name
        if not path.is_file():
            continue

        # 先看文件名是否命中；未命中再尝试读内容匹配（忽略无法解码的二进制字节）
        hit = keyword.lower() in name.lower()
        if not hit:
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            hit = keyword in text
        if hit:
            matched.append(name)

    if not matched:
        return f"没有找到包含「{keyword}」的文件。"
    return f"找到 {len(matched)} 个相关文件：\n" + "\n".join(f"- {n}" for n in matched)
