"""文件操作的安全路径解析。

所有 skill 对用户提供的文件名，都必须经过 safe_output_path 解析，
把操作严格限定在 output 目录之内，杜绝路径穿越（../、绝对路径、反斜杠等）。
"""
from pathlib import Path

from agent.common import OUTPUT_DIR


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
