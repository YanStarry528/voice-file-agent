"""safe_output_path 路径安全校验的单元测试。"""
import pytest

from agent.paths import safe_output_path


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
