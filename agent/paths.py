"""文件操作的安全路径解析。

所有 skill 对用户提供的文件名，都必须经过 safe_output_path 解析，
把操作严格限定在 output 目录之内，杜绝路径穿越（../、绝对路径、反斜杠等）。

resolve_output_file 在其之上追加了「后缀补全」：语音输入时用户几乎不会说出
「点 t x t」，导致存下来的文件没有后缀、双击打不开，读取时也常常对不上名字。
"""
from pathlib import Path

from agent.common import OUTPUT_DIR

# 用户没说后缀时默认补上的扩展名（文本文件，双击即可打开）
DEFAULT_SUFFIX = ".txt"


def safe_output_path(filename: str) -> Path:
    """把用户提供的文件名安全解析到 OUTPUT_DIR 内的绝对路径。

    用 resolve() 归一化真实路径后做前缀校验，能正确处理：
    - 正斜杠 / 与反斜杠 \\ 两种分隔符（Windows 下 os.path.basename 只认 \\）
    - 相对穿越：../、../../ 等
    - 绝对路径：/etc/passwd、C:\\Windows\\... 等

    只要归一化后的真实路径不在 OUTPUT_DIR 之内，就抛 ValueError 拒绝。
    """
    if filename is None or not str(filename).strip():
        raise ValueError("文件名不能为空")

    root = OUTPUT_DIR.resolve()
    candidate = (OUTPUT_DIR / str(filename)).resolve()

    if candidate != root and root not in candidate.parents:
        raise ValueError(f"拒绝访问 output 目录之外的路径：{filename}")

    return candidate


def resolve_output_file(filename: str) -> Path:
    """在安全校验的基础上解析目标文件，无后缀时自动补 .txt。

    规则：
    1. 已带后缀（如 note.md、data.py）→ 原样使用，绝不擅自改写用户的后缀；
    2. 没带后缀 → 若 output 里已存在同名的历史文件（早期语音创建的无后缀文件），
       继续操作该文件，避免同一个东西分裂成「会议记录」和「会议记录.txt」两份；
    3. 没带后缀且不存在 → 自动补 .txt，保证存下来的文件双击就能打开。

    语音场景下用户只会说「会议记录」，第 3 条是常态；第 2 条保证老文件不丢失。
    """
    path = safe_output_path(filename)

    if path.suffix:
        return path
    if path.is_file():
        return path

    return path.with_name(path.name + DEFAULT_SUFFIX)
