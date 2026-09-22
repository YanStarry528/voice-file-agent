"""pytest 全局配置。

- 位于项目根，确保 pytest 把项目根加入 sys.path，使 `from agent...` 可导入。
- 提供隔离输出目录 fixture：每个测试把各模块绑定的 OUTPUT_DIR 指向独立临时目录，
  避免测试之间互相污染，也避免误操作真实的 output/ 目录。
"""
import importlib

import pytest

from agent.skill_registry import discover

# 所有通过 `from agent.common import OUTPUT_DIR` 绑定了目录引用的模块。
# safe_output_path 及各 skill 内部使用的都是这些模块级绑定，需一并替换。
_OUTPUT_DIR_MODULES = [
    "agent.paths",
    "agent.skills.file_ops_skill",
    "agent.skills.append_skill",
    "agent.skills.rename_skill",
    "agent.skills.delete_skill",
    "agent.skills.read_skill",
    "agent.skills.list_skill",
]


@pytest.fixture(scope="session", autouse=True)
def _load_skills():
    """确保所有 skill 已通过 @register 注册进注册中心（只需一次）。"""
    discover()


@pytest.fixture(autouse=True)
def isolated_output_dir(tmp_path, monkeypatch):
    """把每个模块的 OUTPUT_DIR 统一指向当前测试的临时目录。"""
    for mod_name in _OUTPUT_DIR_MODULES:
        mod = importlib.import_module(mod_name)
        monkeypatch.setattr(mod, "OUTPUT_DIR", tmp_path)
    return tmp_path
