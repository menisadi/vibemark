from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
import tomllib


def _read_pyproject_version() -> str:
    root = Path(__file__).resolve().parents[2]
    pyproject = root / "pyproject.toml"
    if not pyproject.exists():
        return "0+unknown"
    try:
        data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    except Exception:
        return "0+unknown"
    project = data.get("project", {})
    if isinstance(project, dict):
        value = project.get("version")
        if isinstance(value, str) and value.strip():
            return value
    return "0+unknown"


def get_version() -> str:
    try:
        return version("vibemark")
    except PackageNotFoundError:
        return _read_pyproject_version()


__version__ = get_version()
