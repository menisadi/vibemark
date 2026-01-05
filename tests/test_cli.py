from pathlib import Path

import pytest
import typer
from typer.testing import CliRunner

from vibemark.cli import (
    DEFAULT_EXCLUDES,
    FileProgress,
    app,
    count_loc,
    is_excluded,
    load_excludes,
    load_state,
    normalize_excludes,
    normalize_path_arg,
    save_state,
    scan,
)
from vibemark import __version__

runner = CliRunner()


def test_count_loc_modes(tmp_path: Path) -> None:
    target = tmp_path / "sample.py"
    target.write_text("line1\n\nline3\n", encoding="utf-8")

    assert count_loc(target, mode="physical") == 3
    assert count_loc(target, mode="nonempty") == 2


def test_is_excluded_defaults() -> None:
    assert is_excluded(".git/config", DEFAULT_EXCLUDES)
    assert not is_excluded("src/vibemark/cli.py", DEFAULT_EXCLUDES)


def test_normalize_path_arg(tmp_path: Path) -> None:
    root = tmp_path
    rel_path = "example.py"
    abs_path = (tmp_path / rel_path).resolve()

    assert normalize_path_arg(root, rel_path) == rel_path
    assert normalize_path_arg(root, str(abs_path)) == rel_path

    with pytest.raises(typer.BadParameter):
        normalize_path_arg(root, str(Path("/").resolve()))


def test_normalize_excludes_dedup_posix() -> None:
    globs = ["foo\\bar/*", "foo/bar/*", "", " "]
    assert normalize_excludes(globs) == ["foo/bar/*"]


def test_load_excludes_missing_state(tmp_path: Path) -> None:
    assert load_excludes(tmp_path) == []


def test_saved_excludes_applied_to_scan(tmp_path: Path) -> None:
    (tmp_path / "keep.py").write_text("print('keep')\n", encoding="utf-8")
    skip_dir = tmp_path / "skip"
    skip_dir.mkdir()
    (skip_dir / "ignore.py").write_text("print('skip')\n", encoding="utf-8")

    save_state(tmp_path, {}, excludes=["skip/*"])

    scan(root=tmp_path, loc_mode="physical", exclude=None)

    items = load_state(tmp_path)
    assert "keep.py" in items
    assert "skip/ignore.py" not in items


def test_version_flag_prints_version() -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.output


def test_export_md_marks_completed_with_x(tmp_path: Path) -> None:
    items = {
        "done.py": FileProgress("done.py", total_loc=5, read_loc=5, mtime_ns=0),
        "todo.py": FileProgress("todo.py", total_loc=5, read_loc=0, mtime_ns=0),
    }
    save_state(tmp_path, items)

    result = runner.invoke(app, ["export-md", "--root", str(tmp_path)])

    assert result.exit_code == 0
    assert "- [x] done.py" in result.output
    assert "- [ ] todo.py" in result.output
