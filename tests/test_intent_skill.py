"""intent_skill 中纯逻辑函数（_parse_json / extract_value）的单元测试。"""
import pytest

from agent.intent_skill import _parse_json, extract_value


def test_解析普通json():
    assert _parse_json('{"intent": "read_file", "filename": "a.txt"}') == {
        "intent": "read_file",
        "filename": "a.txt",
    }


def test_解析markdown代码块包裹():
    raw = '```json\n{"intent": "save_file"}\n```'
    assert _parse_json(raw) == {"intent": "save_file"}


def test_解析前后带废话的json():
    raw = '好的，我理解为：{"intent": "delete_file", "filename": "x.txt"}，马上执行'
    assert _parse_json(raw)["intent"] == "delete_file"


def test_无效json抛错():
    with pytest.raises(ValueError):
        _parse_json("这不是 JSON")


def test_剥离前缀():
    assert extract_value("文件名叫 会议记录.txt") == "会议记录.txt"
    assert extract_value("叫做 todo.txt") == "todo.txt"
    assert extract_value("就叫 笔记") == "笔记"


def test_剥离语气词与标点():
    assert extract_value("报告吧") == "报告"
    assert extract_value("报告。") == "报告"


def test_空值返回空字符串():
    assert extract_value("") == ""
    assert extract_value(None) == ""
