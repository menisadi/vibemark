from pathlib import Path

import pytest
import typer
from typer.testing import CliRunner

from vibemark.cli import (
    DEFAULT_EXCLUDES,
    DEFAULT_EXTENSIONS,
    FileProgress,
    app,
    count_loc,
    is_excluded,
    load_excludes,
    load_extensions,
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


def test_load_extensions_missing_state(tmp_path: Path) -> None:
    assert load_extensions(tmp_path) == DEFAULT_EXTENSIONS


def test_saved_excludes_applied_to_scan(tmp_path: Path) -> None:
    (tmp_path / "keep.py").write_text("print('keep')\n", encoding="utf-8")
    skip_dir = tmp_path / "skip"
    skip_dir.mkdir()
    (skip_dir / "ignore.py").write_text("print('skip')\n", encoding="utf-8")

    save_state(tmp_path, {}, excludes=["skip/*"])

    scan(root=tmp_path, loc_mode="physical", exclude=None, ext=None)

    items = load_state(tmp_path)
    assert "keep.py" in items
    assert "skip/ignore.py" not in items


def test_saved_extensions_applied_to_scan(tmp_path: Path) -> None:
    (tmp_path / "keep.js").write_text("console.log('keep')\n", encoding="utf-8")
    (tmp_path / "skip.py").write_text("print('skip')\n", encoding="utf-8")

    save_state(tmp_path, {}, extensions=["js"])

    scan(root=tmp_path, loc_mode="physical", exclude=None, ext=None)

    items = load_state(tmp_path)
    assert "keep.js" in items
    assert "skip.py" not in items


def test_version_flag_prints_version() -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.output


def test_exclude_subcommands_add_and_list(tmp_path: Path) -> None:
    add_result = runner.invoke(
        app, ["exclude", "add", "skip/*", "--root", str(tmp_path)]
    )
    assert add_result.exit_code == 0
    assert load_excludes(tmp_path) == ["skip/*"]

    list_result = runner.invoke(app, ["exclude", "list", "--root", str(tmp_path)])
    assert list_result.exit_code == 0
    assert "skip/*" in list_result.output


def test_exclude_legacy_command_still_works(tmp_path: Path) -> None:
    result = runner.invoke(app, ["exclude-add", "skip/*", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert load_excludes(tmp_path) == ["skip/*"]


def test_ext_subcommands_add_and_list(tmp_path: Path) -> None:
    add_result = runner.invoke(app, ["ext", "add", "js", "--root", str(tmp_path)])
    assert add_result.exit_code == 0
    assert load_extensions(tmp_path) == ["py", "js"]

    list_result = runner.invoke(app, ["ext", "list", "--root", str(tmp_path)])
    assert list_result.exit_code == 0
    assert "py" in list_result.output
    assert "js" in list_result.output


def test_ext_legacy_command_still_works(tmp_path: Path) -> None:
    result = runner.invoke(app, ["ext-add", "js", "--root", str(tmp_path)])
    assert result.exit_code == 0
    assert load_extensions(tmp_path) == ["py", "js"]


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


def test_update_handles_removed_changed_and_new_files(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("print('a')\n", encoding="utf-8")
    (tmp_path / "b.py").write_text("print('b')\n", encoding="utf-8")
    scan(root=tmp_path, loc_mode="physical", exclude=None, ext=None)

    items = load_state(tmp_path)
    items["a.py"].read_loc = 1
    save_state(tmp_path, items)

    (tmp_path / "a.py").write_text("print('a')\nprint('a2')\n", encoding="utf-8")
    (tmp_path / "b.py").unlink()
    (tmp_path / "c.py").write_text("print('c')\n", encoding="utf-8")

    result = runner.invoke(
        app,
        ["update", "--root", str(tmp_path)],
        input="y\nn\n",
    )
    assert result.exit_code == 0

    updated = load_state(tmp_path)
    assert "b.py" not in updated
    assert "c.py" in updated
    assert updated["a.py"].total_loc == 2
    assert updated["a.py"].read_loc == 1


def test_stats_all_shows_all_remaining(tmp_path: Path) -> None:
    items = {
        "a.py": FileProgress("a.py", total_loc=10, read_loc=0, mtime_ns=0),
        "b.py": FileProgress("b.py", total_loc=8, read_loc=3, mtime_ns=0),
        "done.py": FileProgress("done.py", total_loc=5, read_loc=5, mtime_ns=0),
    }
    save_state(tmp_path, items)

    result = runner.invoke(app, ["stats", "--root", str(tmp_path), "--all"])

    assert result.exit_code == 0
    assert "All remaining" in result.output
    assert "a.py" in result.output
    assert "b.py" in result.output
    assert "done.py" not in result.output


def test_stats_top_must_be_positive_without_all(tmp_path: Path) -> None:
    items = {
        "a.py": FileProgress("a.py", total_loc=10, read_loc=0, mtime_ns=0),
    }
    save_state(tmp_path, items)

    result = runner.invoke(app, ["stats", "--root", str(tmp_path), "--top", "0"])

    assert result.exit_code != 0
    assert "--top must be > 0 unless --all is provided." in result.output


def test_stats_no_table_shows_totals_only(tmp_path: Path) -> None:
    items = {
        "a.py": FileProgress("a.py", total_loc=10, read_loc=0, mtime_ns=0),
        "b.py": FileProgress("b.py", total_loc=8, read_loc=3, mtime_ns=0),
    }
    save_state(tmp_path, items)

    result = runner.invoke(app, ["stats", "--root", str(tmp_path), "--no-table"])

    assert result.exit_code == 0
    assert "Total:" in result.output
    assert "Top 15 remaining" not in result.output
    assert "All remaining" not in result.output
    assert "a.py" not in result.output
    assert "b.py" not in result.output


def test_stats_no_table_allows_nonpositive_top(tmp_path: Path) -> None:
    items = {
        "a.py": FileProgress("a.py", total_loc=10, read_loc=0, mtime_ns=0),
    }
    save_state(tmp_path, items)

    result = runner.invoke(
        app, ["stats", "--root", str(tmp_path), "--top", "0", "--no-table"]
    )

    assert result.exit_code == 0
    assert "Total:" in result.output
