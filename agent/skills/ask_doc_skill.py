"""本地文档问答 skill（轻量 RAG）：在 output 目录下检索相关片段，交给 LLM 回答。

这是「检索增强生成（RAG）」的最小可用实现，三个设计取舍：

1. **实时切分、不落盘**：每次提问都按 output 目录的当前内容重新切段检索。
   好处是文件增删改立刻生效，不会出现「索引还在、文件已被删」的脏数据，
   也就不需要维护索引一致性的额外代码；代价只是多读一遍文件，
   本项目面向的是个人 KB 级文档，这个代价可以忽略。
   真到文档规模涨上来时，只需替换 _retrieve 为向量检索，上层不用动。

2. **检索用中文字符 bigram 重合度打分**：中文没有空格，bigram（二字滑窗）
   是零依赖的检索单元——不必引入 jieba 之类的分词库，也能覆盖短语级匹配。
   打分用「问题 bigram 的覆盖率」，避免长段落靠字数取胜。

3. **生成阶段严格限定只依据片段回答并注明来源**，检索不到就直接说没找到，
   杜绝模型脱离文档编造（与会议纪要 skill 的防虚构约束一致）。
"""
import os
import re

from agent.common import OUTPUT_DIR, chat
from agent.skill_registry import register

# 参与问答的文档后缀（语音场景产出的是 txt，md 也一并支持）
DOC_SUFFIXES = (".txt", ".md")

# 单段最大字符数；超长段落按此长度滑动切分
CHUNK_SIZE = 200
# 滑动步长（小于 CHUNK_SIZE，段与段之间保留重叠，避免把一句话切断）
CHUNK_STEP = 150
# 交给 LLM 的最大片段数
TOP_K = 3


def _bigrams(text: str) -> set[str]:
    """把文本切成字符二元组集合（中文无空格，bigram 是最轻量的检索单元）。"""
    t = re.sub(r"\s+", "", text)
    if not t:
        return set()
    if len(t) < 2:
        return {t}
    return {t[i:i + 2] for i in range(len(t) - 1)}


def _split_chunks(text: str) -> list[str]:
    """按段落切段，超长段落再按滑动窗口细分。"""
    chunks = []
    for para in re.split(r"\n\s*\n", text):
        para = para.strip()
        if not para:
            continue
        if len(para) <= CHUNK_SIZE:
            chunks.append(para)
            continue
        start = 0
        while start < len(para):
            chunks.append(para[start:start + CHUNK_SIZE])
            start += CHUNK_STEP
    return chunks


def _collect_chunks() -> list[tuple[str, int, str]]:
    """遍历 output 目录下的文档，返回 [(文件名, 段序号, 段落文本)]。"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    chunks = []
    for name in sorted(os.listdir(OUTPUT_DIR)):
        path = OUTPUT_DIR / name
        if not path.is_file() or path.suffix.lower() not in DOC_SUFFIXES:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for idx, chunk in enumerate(_split_chunks(text), start=1):
            chunks.append((name, idx, chunk))
    return chunks


def _retrieve(question: str, chunks: list[tuple[str, int, str]]) -> list[tuple[str, int, str]]:
    """按 bigram 覆盖率给段落打分，返回分数最高的 TOP_K 段（完全没有重合的段落直接淘汰）。"""
    q_bigrams = _bigrams(question)

    scored = []
    for name, idx, text in chunks:
        shared = len(q_bigrams & _bigrams(text))
        if shared == 0:
            continue
        # 覆盖率 = 命中的问题 bigram 数 / 问题 bigram 总数，避免长段落靠字数取胜
        scored.append((shared / max(1, len(q_bigrams)), name, idx, text))

    # 同分时按文件名、段序号排序，保证结果稳定可复现
    scored.sort(key=lambda item: (-item[0], item[1], item[2]))
    return [(name, idx, text) for _, name, idx, text in scored[:TOP_K]]


def _ask(question: str, hits: list[tuple[str, int, str]]) -> str:
    """把检索到的片段连同问题交给 LLM，返回带来源标注的回答。"""
    system = (
        "你是文档问答助手。请只依据用户提供的文档片段回答用户的问题。\n"
        "规则：\n"
        "1. 只能使用片段中出现的信息，严禁编造或引入片段之外的内容；\n"
        "2. 片段中没有答案时，直接回答「在文档中没有找到相关信息」；\n"
        "3. 用简洁的中文回答，并在句末注明来源文件名，例如「（来源：会议记录3.txt）」。"
    )
    snippets = "\n\n".join(f"[{name} 第{idx}段]\n{text}" for name, idx, text in hits)

    resp = chat(
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": f"文档片段：\n{snippets}\n\n问题：{question}"},
        ],
    )
    return (resp.choices[0].message.content or "").strip()


@register(
    intent="ask_doc",
    description=(
        "基于 output 目录下的文档回答问题"
        "（对应：问一下、文档里怎么说的、查一下文档、关于…是怎么说的、…是什么时候）"
    ),
    fields={"question": "要问的问题"},
)
def execute(args: dict) -> str:
    """检索 output 目录下的文档片段 → LLM 基于片段回答 → 附上参考来源。"""
    question = str(args.get("question") or "").strip()
    if not question:
        return "请告诉我你想问什么。"

    chunks = _collect_chunks()
    if not chunks:
        return "output 目录下还没有可以问答的文档（.txt / .md）。"

    hits = _retrieve(question, chunks)
    if not hits:
        return f"在文档里没有找到与「{question}」相关的内容。"

    answer = _ask(question, hits)
    sources = "、".join(f"{name} 第{idx}段" for name, idx, _ in hits)
    return f"{answer}\n\n参考来源：{sources}"
