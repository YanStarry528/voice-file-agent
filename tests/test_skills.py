"""各 skill 文件操作的单元测试（在隔离的临时输出目录中运行）。"""
from agent.skill_registry import dispatch, needs_confirm, required_fields


def test_save_file_写入内容(isolated_output_dir):
    result = dispatch("save_file", {"filename": "a.txt", "content": "hello"})
    assert (isolated_output_dir / "a.txt").read_text(encoding="utf-8") == "hello"
    assert "已保存" in result


def test_append_file_追加且自动换行(isolated_output_dir):
    (isolated_output_dir / "a.txt").write_text("第一行", encoding="utf-8")
    dispatch("append_file", {"filename": "a.txt", "content": "第二行"})
    assert (isolated_output_dir / "a.txt").read_text(encoding="utf-8") == "第一行\n第二行\n"


def test_rename_file(isolated_output_dir):
    (isolated_output_dir / "old.txt").write_text("x", encoding="utf-8")
    dispatch("rename_file", {"filename": "old.txt", "new_name": "new.txt"})
    assert (isolated_output_dir / "new.txt").exists()
    assert not (isolated_output_dir / "old.txt").exists()


def test_delete_file(isolated_output_dir):
    (isolated_output_dir / "a.txt").write_text("x", encoding="utf-8")
    dispatch("delete_file", {"filename": "a.txt"})
    assert not (isolated_output_dir / "a.txt").exists()


def test_save_file_拒绝路径穿越(isolated_output_dir):
    result = dispatch("save_file", {"filename": "../evil.txt", "content": "x"})
    assert "拒绝" in result
    assert not (isolated_output_dir.parent / "evil.txt").exists()


def test_delete_需要二次确认():
    assert needs_confirm("delete_file") is True
    assert needs_confirm("save_file") is False


def test_required_fields():
    assert required_fields("append_file") == ["filename", "content"]


def test_未注册意图优雅降级():
    assert "没有识别出" in dispatch("nonexistent", {})
