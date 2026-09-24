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


def test_save_file_无后缀自动补_txt(isolated_output_dir):
    dispatch("save_file", {"filename": "会议记录", "content": "今天开了产品会"})
    assert (isolated_output_dir / "会议记录.txt").read_text(encoding="utf-8") == "今天开了产品会"


def test_save_file_保留用户指定的后缀(isolated_output_dir):
    dispatch("save_file", {"filename": "note.md", "content": "# 标题"})
    assert (isolated_output_dir / "note.md").exists()
    assert not (isolated_output_dir / "note.md.txt").exists()


def test_read_file_无后缀能读到_txt(isolated_output_dir):
    (isolated_output_dir / "会议记录.txt").write_text("内容", encoding="utf-8")
    assert dispatch("read_file", {"filename": "会议记录"}) == "内容"


def test_read_file_兼容历史无后缀文件(isolated_output_dir):
    (isolated_output_dir / "会议记录").write_text("老文件", encoding="utf-8")
    assert dispatch("read_file", {"filename": "会议记录"}) == "老文件"


def test_append_无后缀不分裂文件(isolated_output_dir):
    """已有无后缀文件时继续追加它，而不是新建一个 .txt 副本。"""
    (isolated_output_dir / "会议记录").write_text("第一行", encoding="utf-8")
    dispatch("append_file", {"filename": "会议记录", "content": "第二行"})
    assert not (isolated_output_dir / "会议记录.txt").exists()
    assert (isolated_output_dir / "会议记录").read_text(encoding="utf-8") == "第一行\n第二行\n"


def test_count_words_无后缀(isolated_output_dir):
    (isolated_output_dir / "会议记录.txt").write_text("你好 世界", encoding="utf-8")
    result = dispatch("count_words", {"filename": "会议记录"})
    assert "4 字" in result
    assert "会议记录.txt" in result


def test_delete_file_无后缀(isolated_output_dir):
    (isolated_output_dir / "会议记录.txt").write_text("x", encoding="utf-8")
    dispatch("delete_file", {"filename": "会议记录"})
    assert not (isolated_output_dir / "会议记录.txt").exists()


def test_rename_file_新名无后缀补_txt(isolated_output_dir):
    (isolated_output_dir / "old.txt").write_text("x", encoding="utf-8")
    result = dispatch("rename_file", {"filename": "old", "new_name": "会议纪要"})
    assert (isolated_output_dir / "会议纪要.txt").exists()
    assert "会议纪要.txt" in result


# ===== 方向三：文件类 skill（复制 / 移动 / 新建文件夹 / 文件信息） =====


def test_copy_file(isolated_output_dir):
    (isolated_output_dir / "a.txt").write_text("hello", encoding="utf-8")
    result = dispatch("copy_file", {"filename": "a.txt", "new_name": "b.txt"})
    assert (isolated_output_dir / "b.txt").read_text(encoding="utf-8") == "hello"
    assert (isolated_output_dir / "a.txt").exists()  # 原件保留
    assert "已复制" in result


def test_copy_file_新名无后缀补_txt(isolated_output_dir):
    (isolated_output_dir / "a.txt").write_text("x", encoding="utf-8")
    dispatch("copy_file", {"filename": "a.txt", "new_name": "副本"})
    assert (isolated_output_dir / "副本.txt").exists()


def test_copy_file_目标已存在拒绝(isolated_output_dir):
    (isolated_output_dir / "a.txt").write_text("old", encoding="utf-8")
    (isolated_output_dir / "b.txt").write_text("new", encoding="utf-8")
    result = dispatch("copy_file", {"filename": "a.txt", "new_name": "b.txt"})
    assert "已存在" in result
    assert (isolated_output_dir / "b.txt").read_text(encoding="utf-8") == "new"


def test_copy_file_源不存在(isolated_output_dir):
    result = dispatch("copy_file", {"filename": "没有.txt", "new_name": "b.txt"})
    assert "不存在" in result


def test_move_file(isolated_output_dir):
    (isolated_output_dir / "a.txt").write_text("hello", encoding="utf-8")
    result = dispatch("move_file", {"filename": "a.txt", "target_dir": "归档"})
    assert (isolated_output_dir / "归档" / "a.txt").read_text(encoding="utf-8") == "hello"
    assert not (isolated_output_dir / "a.txt").exists()
    assert "移动" in result


def test_move_file_目标已存在同名拒绝(isolated_output_dir):
    (isolated_output_dir / "a.txt").write_text("old", encoding="utf-8")
    (isolated_output_dir / "归档").mkdir()
    (isolated_output_dir / "归档" / "a.txt").write_text("new", encoding="utf-8")
    result = dispatch("move_file", {"filename": "a.txt", "target_dir": "归档"})
    assert "已有" in result
    assert (isolated_output_dir / "a.txt").exists()  # 未移动
    assert (isolated_output_dir / "归档" / "a.txt").read_text(encoding="utf-8") == "new"


def test_make_dir(isolated_output_dir):
    result = dispatch("make_dir", {"dirname": "归档"})
    assert (isolated_output_dir / "归档").is_dir()
    assert "已新建" in result


def test_make_dir_已存在(isolated_output_dir):
    (isolated_output_dir / "归档").mkdir()
    result = dispatch("make_dir", {"dirname": "归档"})
    assert "已存在" in result


def test_file_info(isolated_output_dir):
    (isolated_output_dir / "a.txt").write_text("hello world", encoding="utf-8")
    result = dispatch("file_info", {"filename": "a.txt"})
    assert "11 B" in result
    assert "最后修改于" in result


def test_file_info_不存在(isolated_output_dir):
    result = dispatch("file_info", {"filename": "没有.txt"})
    assert "不存在" in result


# ===== 方向三：待办清单 skill（记待办 / 列待办 / 标记完成） =====


def test_add_todo_记一条(isolated_output_dir):
    result = dispatch("add_todo", {"content": "明天交周报"})
    assert "已记下" in result
    assert (isolated_output_dir / "todo.txt").read_text(encoding="utf-8") == "[ ] 明天交周报\n"


def test_add_todo_追加不覆盖(isolated_output_dir):
    (isolated_output_dir / "todo.txt").write_text("[ ] 第一条\n", encoding="utf-8")
    dispatch("add_todo", {"content": "第二条"})
    text = (isolated_output_dir / "todo.txt").read_text(encoding="utf-8")
    assert "[ ] 第一条" in text
    assert "[ ] 第二条" in text


def test_add_todo_空内容(isolated_output_dir):
    result = dispatch("add_todo", {"content": ""})
    assert "待办内容" in result


def test_list_todo_空清单(isolated_output_dir):
    result = dispatch("list_todo", {})
    assert "还没有" in result


def test_list_todo_有内容(isolated_output_dir):
    (isolated_output_dir / "todo.txt").write_text("[ ] 买牛奶\n[x] 回复邮件\n", encoding="utf-8")
    result = dispatch("list_todo", {})
    assert "买牛奶" in result
    assert "回复邮件" in result
    assert "1 条待办" in result


def test_done_todo_标记完成(isolated_output_dir):
    (isolated_output_dir / "todo.txt").write_text("[ ] 买牛奶\n[ ] 交周报\n", encoding="utf-8")
    result = dispatch("done_todo", {"content": "买牛奶"})
    text = (isolated_output_dir / "todo.txt").read_text(encoding="utf-8")
    assert "[x] 买牛奶" in text
    assert "[ ] 交周报" in text
    assert "标记为完成" in result


def test_done_todo_找不到(isolated_output_dir):
    (isolated_output_dir / "todo.txt").write_text("[ ] 买牛奶\n", encoding="utf-8")
    result = dispatch("done_todo", {"content": "不存在的事"})
    assert "没有找到" in result


# ===== 方向三：会议纪要整理 skill（依赖 LLM，需 mock chat） =====


def _fake_llm_response(content):
    from types import SimpleNamespace

    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))]
    )


def test_summarize_meeting_生成纪要(monkeypatch, isolated_output_dir):
    import agent.skills.meeting_summary_skill as meeting_skill

    (isolated_output_dir / "会议记录.txt").write_text(
        "今天讨论发布计划，决定周五上线，小王负责测试。", encoding="utf-8"
    )
    monkeypatch.setattr(
        meeting_skill, "chat", lambda **kw: _fake_llm_response("## 会议主题\n发布计划")
    )
    result = dispatch("summarize_meeting", {"filename": "会议记录"})
    assert "已生成会议纪要" in result
    assert "会议记录_纪要.txt" in result
    assert (
        isolated_output_dir / "会议记录_纪要.txt"
    ).read_text(encoding="utf-8") == "## 会议主题\n发布计划"


def test_summarize_meeting_文件不存在(isolated_output_dir):
    result = dispatch("summarize_meeting", {"filename": "没有.txt"})
    assert "不存在" in result


def test_summarize_meeting_空文件(isolated_output_dir):
    (isolated_output_dir / "a.txt").write_text("   ", encoding="utf-8")
    result = dispatch("summarize_meeting", {"filename": "a.txt"})
    assert "空的" in result


def test_summarize_meeting_空文件名(isolated_output_dir):
    result = dispatch("summarize_meeting", {"filename": ""})
    assert "请指定" in result
