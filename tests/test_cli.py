from pathlib import Path

import pytest
import typer

from viberead.cli import DEFAULT_EXCLUDES, count_loc, is_excluded, normalize_path_arg


def test_count_loc_modes(tmp_path: Path) -> None:
    target = tmp_path / "sample.py"
    target.write_text("line1\n\nline3\n", encoding="utf-8")

    assert count_loc(target, mode="physical") == 3
    assert count_loc(target, mode="nonempty") == 2


def test_is_excluded_defaults() -> None:
    assert is_excluded(".git/config", DEFAULT_EXCLUDES)
    assert not is_excluded("src/viberead/cli.py", DEFAULT_EXCLUDES)


def test_normalize_path_arg(tmp_path: Path) -> None:
    root = tmp_path
    rel_path = "example.py"
    abs_path = (tmp_path / rel_path).resolve()

    assert normalize_path_arg(root, rel_path) == rel_path
    assert normalize_path_arg(root, str(abs_path)) == rel_path

    with pytest.raises(typer.BadParameter):
        normalize_path_arg(root, str(Path("/").resolve()))
