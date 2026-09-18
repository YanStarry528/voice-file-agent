"""可插拔 skill 注册中心。

约定：每个 skill 是 agent/skills/ 下的一个 .py 文件，用 @register 装饰器
注册一个 execute(args: dict) -> str 函数。新增 skill 只需新建一个文件，
无需修改 orchestrator 或意图分类器。
"""
import importlib
from pathlib import Path
from typing import Callable

_REGISTRY: dict[str, dict] = {}


def register(intent: str, description: str, fields: dict[str, str] | None = None):
    """把函数注册为一个可执行 skill。

    intent:      意图标识（意图分类器输出的 intent 值）
    description: 一句话说明 + 触发词提示，用于自动生成分类器 prompt
    fields:      该操作需要的参数字段（字段名 -> 说明），无参数传 None
    """
    def deco(fn: Callable[[dict], str]):
        _REGISTRY[intent] = {
            "intent": intent,
            "description": description,
            "fields": fields or {},
            "fn": fn,
        }
        return fn
    return deco


def all_skills() -> list[dict]:
    """返回所有已注册 skill 的元信息（用于生成意图分类 prompt）。"""
    return list(_REGISTRY.values())


def dispatch(intent: str, args: dict) -> str:
    """根据意图调用对应 skill，返回执行结果字符串。"""
    info = _REGISTRY.get(intent)
    if info is None:
        return "没有识别出可执行的操作。"
    return info["fn"](args or {})


def discover() -> None:
    """扫描 agent/skills/ 目录，import 所有 skill 文件以触发注册。"""
    skills_dir = Path(__file__).resolve().parent / "skills"
    for p in sorted(skills_dir.glob("*.py")):
        if p.name == "__init__.py":
            continue
        importlib.import_module(f"agent.skills.{p.stem}")
