"""可插拔 skill 注册中心。

约定：每个 skill 是 agent/skills/ 下的一个 .py 文件，用 @register 装饰器
注册一个 execute(args: dict) -> str 函数。新增 skill 只需新建一个文件，
无需修改 orchestrator 或意图分类器。
"""
import importlib
from pathlib import Path
from typing import Callable

_REGISTRY: dict[str, dict] = {}


def register(
    intent: str,
    description: str,
    fields: dict[str, str] | None = None,
    required: list[str] | None = None,
    confirm: bool = False,
):
    """把函数注册为一个可执行 skill。

    intent:      意图标识（意图分类器输出的 intent 值）
    description: 一句话说明 + 触发词提示，用于自动生成分类器 prompt
    fields:      该操作需要的参数字段（字段名 -> 说明），无参数传 None
    required:    必填字段列表；缺省时默认 fields 的所有 key 都必填
    confirm:     是否为危险操作（执行前需要用户二次确认），默认 False
    """
    def deco(fn: Callable[[dict], str]):
        req = required if required is not None else list((fields or {}).keys())
        _REGISTRY[intent] = {
            "intent": intent,
            "description": description,
            "fields": fields or {},
            "required": req,
            "confirm": confirm,
            "fn": fn,
        }
        return fn
    return deco


def all_skills() -> list[dict]:
    """返回所有已注册 skill 的元信息（用于生成意图分类 prompt）。"""
    return list(_REGISTRY.values())


def required_fields(intent: str) -> list[str]:
    """返回该 intent 的必填字段列表（未注册返回空列表）。"""
    info = _REGISTRY.get(intent)
    if info is None:
        return []
    return info["required"]


def field_labels(intent: str) -> dict[str, str]:
    """返回该 intent 的字段 -> 中文说明映射（用于生成友好的追问文案）。"""
    info = _REGISTRY.get(intent)
    if info is None:
        return {}
    return info["fields"]


def needs_confirm(intent: str) -> bool:
    """该 intent 是否为危险操作（执行前需要用户二次确认）。"""
    info = _REGISTRY.get(intent)
    if info is None:
        return False
    return bool(info["confirm"])


def skill_summary(intent: str) -> str:
    """返回该 skill 的一句话说明（去掉括号内的触发词提示），用于确认文案。"""
    info = _REGISTRY.get(intent)
    if info is None:
        return intent
    return info["description"].split("（")[0].strip()


def build_tools() -> list[dict]:
    """把所有已注册 skill 转成 OpenAI function calling 的 tools 定义。

    每个工具：
    - name 用 intent 标识（模型据此决定调用哪个工具）
    - description 用 skill 的一句话说明
    - parameters 由 fields 展开成 JSON Schema（字段名 -> 说明，均视为字符串）
    """
    tools = []
    for info in _REGISTRY.values():
        props = {}
        for field, label in (info.get("fields") or {}).items():
            props[field] = {"type": "string", "description": label}
        parameters: dict = {"type": "object", "properties": props}
        required = info.get("required") or []
        if required:
            parameters["required"] = required
        tools.append({
            "type": "function",
            "function": {
                "name": info["intent"],
                "description": info["description"],
                "parameters": parameters,
            },
        })
    return tools


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
