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


def test_search_files_按内容命中(isolated_output_dir):
    (isolated_output_dir / "a.txt").write_text("今天的会议纪要", encoding="utf-8")
    (isolated_output_dir / "b.txt").write_text("购物清单", encoding="utf-8")
    result = dispatch("search_files", {"keyword": "会议"})
    assert "a.txt" in result
    assert "b.txt" not in result


def test_search_files_按文件名命中(isolated_output_dir):
    (isolated_output_dir / "会议.txt").write_text("随便写点", encoding="utf-8")
    result = dispatch("search_files", {"keyword": "会议"})
    assert "会议.txt" in result


def test_search_files_无命中(isolated_output_dir):
    (isolated_output_dir / "a.txt").write_text("hello", encoding="utf-8")
    result = dispatch("search_files", {"keyword": "不存在"})
    assert "没有找到" in result


def test_count_words(isolated_output_dir):
    (isolated_output_dir / "a.txt").write_text("你好 世界", encoding="utf-8")
    result = dispatch("count_words", {"filename": "a.txt"})
    assert "4 字" in result
    assert "1 行" in result


def test_count_words_多行(isolated_output_dir):
    (isolated_output_dir / "a.txt").write_text("第一行\n第二行\n", encoding="utf-8")
    result = dispatch("count_words", {"filename": "a.txt"})
    assert "6 字" in result
    assert "2 行" in result


def test_count_words_文件不存在(isolated_output_dir):
    result = dispatch("count_words", {"filename": "没有.txt"})
    assert "不存在" in result
