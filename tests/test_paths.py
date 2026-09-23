"""safe_output_path 路径安全校验的单元测试。"""
import pytest

from agent.paths import resolve_output_file, safe_output_path


def test_正常文件名解析到输出目录(isolated_output_dir):
    p = safe_output_path("note.txt")
    assert p == isolated_output_dir / "note.txt"
    assert p.is_absolute()


def test_输出目录内的子目录合法(isolated_output_dir):
    p = safe_output_path("sub/dir/a.txt")
    assert p == isolated_output_dir / "sub" / "dir" / "a.txt"


@pytest.mark.parametrize(
    "bad",
    [
        "../secret.txt",
        "../../escape.txt",
        "/etc/passwd",
        "C:\\Windows\\system32\\config\\SAM",
        "..\\..\\secret.txt",
    ],
)
def test_拒绝路径穿越与绝对路径(isolated_output_dir, bad):
    with pytest.raises(ValueError):
        safe_output_path(bad)


@pytest.mark.parametrize("empty", [None, "", "   "])
def test_空文件名拒绝(empty):
    with pytest.raises(ValueError):
        safe_output_path(empty)


def test_无后缀自动补_txt(isolated_output_dir):
    assert resolve_output_file("会议记录") == isolated_output_dir / "会议记录.txt"


@pytest.mark.parametrize("name", ["note.md", "data.py", "a.txt"])
def test_已有后缀不改写(isolated_output_dir, name):
    assert resolve_output_file(name) == isolated_output_dir / name


def test_无后缀但已存在同名文件则沿用(isolated_output_dir):
    """历史遗留的无后缀文件不应被 .txt 版本取代，否则内容会分裂成两份。"""
    (isolated_output_dir / "会议记录").write_text("x", encoding="utf-8")
    assert resolve_output_file("会议记录") == isolated_output_dir / "会议记录"


def test_无后缀同样拒绝路径穿越(isolated_output_dir):
    with pytest.raises(ValueError):
        resolve_output_file("../evil")
