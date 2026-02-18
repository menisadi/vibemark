#!/usr/bin/env -S uv run
from __future__ import annotations

import builtins
import fnmatch
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple, cast

import typer
from rich.console import Console
from rich.table import Table
from rich.prompt import Confirm
from rich import box

from vibemark import __version__

app = typer.Typer(
    add_completion=False, help="vibemark — track code reading progress by LOC"
)
exclude_app = typer.Typer(help="Manage persistent exclude globs.")
ext_app = typer.Typer(help="Manage persistent scan extensions.")
app.add_typer(exclude_app, name="exclude")
app.add_typer(ext_app, name="ext")
console = Console()

STATE_FILENAME = ".vibemark.json"

DEFAULT_EXCLUDES = [
    ".git/*",
    ".venv/*",
    "venv/*",
    "__pycache__/*",
    ".mypy_cache/*",
    ".pytest_cache/*",
    "build/*",
    "dist/*",
    ".ruff_cache/*",
    ".tox/*",
]

DEFAULT_EXTENSIONS = ["py"]


def is_excluded(rel: str, exclude_globs: List[str]) -> bool:
    rel = rel.replace("\\", "/")
    return any(fnmatch.fnmatch(rel, g) for g in exclude_globs)


def count_loc(path: Path, mode: str = "physical") -> int:
    """
    mode:
      - physical: count all lines
      - nonempty: count non-empty lines
    (Easy to add "sloc" later: ignore comments/blank lines)
    """
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return 0
    lines = text.splitlines()
    if mode == "nonempty":
        return sum(1 for ln in lines if ln.strip())
    return len(lines)


def coerce_int(value: object) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return 0
    return 0


@dataclass
class FileProgress:
    path: str
    total_loc: int
    read_loc: int
    mtime_ns: int

    @property
    def status(self) -> str:
        if self.read_loc <= 0:
            return "unread"
        if self.read_loc >= self.total_loc:
            return "done"
        return "partial"

    def clamp(self) -> None:
        if self.total_loc < 0:
            self.total_loc = 0
        if self.read_loc < 0:
            self.read_loc = 0
        if self.read_loc > self.total_loc:
            self.read_loc = self.total_loc


def state_path(root: Path) -> Path:
    return root / STATE_FILENAME


def load_state_payload(root: Path) -> Dict[str, object]:
    p = state_path(root)
    if not p.exists():
        return {
            "version": 1,
            "files": {},
            "excludes": [],
            "extensions": DEFAULT_EXTENSIONS,
        }
    return json.loads(p.read_text(encoding="utf-8"))


def load_state(root: Path) -> Dict[str, FileProgress]:
    raw = load_state_payload(root)
    files = raw.get("files", {})
    if not isinstance(files, dict):
        return {}
    out: Dict[str, FileProgress] = {}
    for rel, meta in files.items():
        if not isinstance(rel, str):
            continue
        if not isinstance(meta, dict):
            continue
        meta_dict = cast(dict[str, object], meta)
        out[rel] = FileProgress(
            path=rel,
            total_loc=coerce_int(meta_dict.get("total_loc", 0)),
            read_loc=coerce_int(meta_dict.get("read_loc", 0)),
            mtime_ns=coerce_int(meta_dict.get("mtime_ns", 0)),
        )
        out[rel].clamp()
    return out


def normalize_exclude_glob(glob: str) -> str:
    return glob.strip().replace("\\", "/")


def normalize_excludes(globs: List[str]) -> List[str]:
    seen = builtins.set()
    normalized: List[str] = []
    for glob in globs:
        norm = normalize_exclude_glob(glob)
        if norm and norm not in seen:
            normalized.append(norm)
            seen.add(norm)
    return normalized


def normalize_extension(ext: str) -> str:
    return ext.strip().lstrip(".").lower()


def normalize_extensions(exts: List[str]) -> List[str]:
    seen = builtins.set()
    normalized: List[str] = []
    for ext in exts:
        norm = normalize_extension(ext)
        if norm and norm not in seen:
            normalized.append(norm)
            seen.add(norm)
    return normalized


def load_excludes(root: Path) -> List[str]:
    raw = load_state_payload(root)
    excludes = raw.get("excludes", [])
    if not isinstance(excludes, list):
        return []
    return normalize_excludes([str(g) for g in excludes])


def load_extensions(root: Path) -> List[str]:
    raw = load_state_payload(root)
    exts = raw.get("extensions", [])
    if not isinstance(exts, list):
        return DEFAULT_EXTENSIONS
    normalized = normalize_extensions([str(ext) for ext in exts])
    return normalized or DEFAULT_EXTENSIONS


def save_state(
    root: Path,
    items: Dict[str, FileProgress],
    excludes: Optional[List[str]] = None,
    extensions: Optional[List[str]] = None,
) -> None:
    p = state_path(root)
    if excludes is None:
        excludes = load_excludes(root)
    if extensions is None:
        extensions = load_extensions(root)
    files = {
        rel: {
            "total_loc": fp.total_loc,
            "read_loc": fp.read_loc,
            "mtime_ns": fp.mtime_ns,
        }
        for rel, fp in sorted(items.items(), key=lambda kv: kv[0])
    }
    payload = {
        "version": 1,
        "files": files,
        "excludes": normalize_excludes(excludes),
        "extensions": normalize_extensions(extensions),
    }
    p.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def scan_repo(
    root: Path,
    exclude: List[str],
    loc_mode: str,
    include_empty: bool,
    extensions: List[str],
) -> Dict[str, Tuple[int, int]]:
    """
    Returns mapping rel_path -> (total_loc, mtime_ns)
    """
    results: Dict[str, Tuple[int, int]] = {}
    normalized_exts = normalize_extensions(extensions)
    if not normalized_exts:
        return results
    for ext in normalized_exts:
        for path in root.rglob(f"*.{ext}"):
            if not path.is_file():
                continue
            rel = path.relative_to(root).as_posix()
            if is_excluded(rel, exclude):
                continue
            st = path.stat()
            total = count_loc(path, mode=loc_mode)
            if not include_empty and total == 0:
                continue
            results[rel] = (total, st.st_mtime_ns)
    return results


def totals(items: Dict[str, FileProgress]) -> Tuple[int, int]:
    total = sum(fp.total_loc for fp in items.values())
    read = sum(fp.read_loc for fp in items.values())
    return total, read


def render_table(items: Dict[str, FileProgress], limit: int = 200) -> Table:
    t = Table(title="vibemark", box=box.SIMPLE_HEAVY)
    t.add_column("#", style="dim", width=4, justify="right")
    t.add_column("Status", width=8)
    t.add_column("Read", justify="right", width=12)
    t.add_column("LOC", justify="right", width=8)
    t.add_column("File", overflow="fold")

    rows = sorted(
        items.values(),
        key=lambda fp: (fp.status != "unread", fp.status != "partial", fp.path),
    )
    for i, fp in enumerate(rows[:limit], start=1):
        status = {
            "unread": "[dim]unread[/dim]",
            "partial": "[yellow]partial[/yellow]",
            "done": "[green]done[/green]",
        }[fp.status]
        read_str = f"{fp.read_loc}/{fp.total_loc}"
        t.add_row(str(i), status, read_str, str(fp.total_loc), fp.path)
    return t


def resolve_root(root: Optional[Path]) -> Path:
    r = root or Path.cwd()
    r = r.resolve()
    if not r.exists():
        raise typer.BadParameter(f"Root does not exist: {r}")
    return r


def _version_callback(value: bool) -> None:
    if value:
        console.print(__version__)
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        False,
        "--version",
        "-v",
        help="Show the vibemark version and exit",
        is_eager=True,
        callback=_version_callback,
    ),
) -> None:
    """
    vibemark — track code reading progress by LOC
    """
    return None


@app.command()
def scan(
    root: Optional[Path] = typer.Option(None, help="Repo root (default: cwd)"),
    loc_mode: str = typer.Option("physical", help="LOC mode: physical|nonempty"),
    exclude: List[str] = typer.Option(
        None,
        "--exclude",
        help="Exclude glob for this run (repeatable), e.g. src/pkg/*",
    ),
    ext: List[str] = typer.Option(
        None,
        "--ext",
        help="Include file extension(s) for scan (repeatable), e.g. py",
    ),
    include_empty: bool = typer.Option(
        False, "--include-empty", help="Include empty files (0 LOC) in scan"
    ),
) -> None:
    """
    Scan repo for Python files and create/update .vibemark.json
    """
    root = resolve_root(root)
    saved_excludes = load_excludes(root)
    saved_extensions = load_extensions(root)
    ex = DEFAULT_EXCLUDES + saved_excludes + (exclude or [])
    existing = load_state(root)
    extensions = normalize_extensions(ext or saved_extensions)
    if not extensions:
        raise typer.BadParameter("No extensions provided.")
    scanned = scan_repo(
        root,
        ex,
        loc_mode=loc_mode,
        include_empty=include_empty,
        extensions=extensions,
    )

    # Add/update scanned files, keep read_loc if present
    new_state: Dict[str, FileProgress] = {}
    for rel, (total_loc, mtime_ns) in scanned.items():
        prev = existing.get(rel)
        read_loc = prev.read_loc if prev else 0
        fp = FileProgress(rel, total_loc, read_loc, mtime_ns)
        fp.clamp()
        new_state[rel] = fp

    save_state(root, new_state, excludes=saved_excludes, extensions=extensions)
    total, read = totals(new_state)
    console.print(
        f"[green]Scanned[/green] {len(new_state)} files. Total {read}/{total} LOC read."
    )


@app.command()
def stats(
    root: Optional[Path] = typer.Option(None, help="Repo root (default: cwd)"),
    top: int = typer.Option(15, help="Show top N remaining by LOC"),
) -> None:
    """
    Show total progress and largest remaining files.
    """
    root = resolve_root(root)
    items = load_state(root)
    if not items:
        console.print("[yellow]No state found. Run[/yellow] vibemark scan")
        raise typer.Exit(1)

    total, read = totals(items)
    pct = (read / total * 100.0) if total else 0.0
    console.print(
        f"Total: [bold]{read}/{total}[/bold] LOC read  ([bold]{pct:.1f}%[/bold])"
    )

    if top <= 0:
        return

    remaining = sorted(
        (fp for fp in items.values() if fp.read_loc < fp.total_loc),
        key=lambda fp: (fp.total_loc - fp.read_loc),
        reverse=True,
    )[:top]

    t = Table(title=f"Top {top} remaining", box=box.SIMPLE)
    t.add_column("Remaining", justify="right")
    t.add_column("Read", justify="right")
    t.add_column("LOC", justify="right")
    t.add_column("File", overflow="fold")
    for fp in remaining:
        rem = fp.total_loc - fp.read_loc
        t.add_row(str(rem), f"{fp.read_loc}/{fp.total_loc}", str(fp.total_loc), fp.path)
    console.print(t)


def require_state(root: Path) -> Dict[str, FileProgress]:
    items = load_state(root)
    if not items:
        console.print("[yellow]No state found. Run[/yellow] vibemark scan")
        raise typer.Exit(1)
    return items


def normalize_path_arg(root: Path, p: str) -> str:
    # Accept either relative paths or absolute paths under root
    path = Path(p)
    if path.is_absolute():
        try:
            rel = path.resolve().relative_to(root).as_posix()
        except Exception:
            raise typer.BadParameter(f"Path must be under root: {root}")
        return rel
    return path.as_posix().replace("\\", "/")


@exclude_app.command("add")
def exclude_add(
    globs: List[str] = typer.Argument(..., help="Exclude glob(s), e.g. src/pkg/*"),
    root: Optional[Path] = typer.Option(None, help="Repo root (default: cwd)"),
) -> None:
    """
    Add persistent exclude globs saved in .vibemark.json
    """
    root = resolve_root(root)
    items = load_state(root)
    excludes = load_excludes(root)
    to_add = normalize_excludes(globs)
    if not to_add:
        raise typer.BadParameter("No excludes provided.")
    new_excludes = normalize_excludes(excludes + to_add)
    added = [glob for glob in new_excludes if glob not in excludes]
    save_state(root, items, excludes=new_excludes)
    if added:
        console.print("[green]Added excludes:[/green]")
        for glob in added:
            console.print(f"- {glob}")
    else:
        console.print("[yellow]No new excludes added.[/yellow]")


@exclude_app.command("remove")
def exclude_remove(
    globs: List[str] = typer.Argument(..., help="Exclude glob(s), e.g. src/pkg/*"),
    root: Optional[Path] = typer.Option(None, help="Repo root (default: cwd)"),
) -> None:
    """
    Remove persistent exclude globs from .vibemark.json
    """
    root = resolve_root(root)
    items = load_state(root)
    excludes = load_excludes(root)
    to_remove = builtins.set(normalize_excludes(globs))
    if not to_remove:
        raise typer.BadParameter("No excludes provided.")
    removed = [glob for glob in excludes if glob in to_remove]
    new_excludes = [glob for glob in excludes if glob not in to_remove]
    save_state(root, items, excludes=new_excludes)
    if removed:
        console.print("[green]Removed excludes:[/green]")
        for glob in removed:
            console.print(f"- {glob}")
    else:
        console.print("[yellow]No matching excludes found.[/yellow]")


@exclude_app.command("list")
def exclude_list(
    root: Optional[Path] = typer.Option(None, help="Repo root (default: cwd)"),
) -> None:
    """
    List default and saved exclude globs.
    """
    root = resolve_root(root)
    saved = load_excludes(root)
    console.print("[bold]Default excludes[/bold]")
    for glob in DEFAULT_EXCLUDES:
        console.print(f"- {glob}")
    console.print("\n[bold]Saved excludes[/bold]")
    if not saved:
        console.print("(none)")
        return
    for glob in saved:
        console.print(f"- {glob}")


@exclude_app.command("clear")
def exclude_clear(
    root: Optional[Path] = typer.Option(None, help="Repo root (default: cwd)"),
) -> None:
    """
    Clear all saved exclude globs.
    """
    root = resolve_root(root)
    items = load_state(root)
    save_state(root, items, excludes=[])
    console.print("[green]Cleared saved excludes.[/green]")


@app.command("exclude-add", hidden=True)
def exclude_add_legacy(
    globs: List[str] = typer.Argument(..., help="Exclude glob(s), e.g. src/pkg/*"),
    root: Optional[Path] = typer.Option(None, help="Repo root (default: cwd)"),
) -> None:
    exclude_add(globs=globs, root=root)


@app.command("exclude-remove", hidden=True)
def exclude_remove_legacy(
    globs: List[str] = typer.Argument(..., help="Exclude glob(s), e.g. src/pkg/*"),
    root: Optional[Path] = typer.Option(None, help="Repo root (default: cwd)"),
) -> None:
    exclude_remove(globs=globs, root=root)


@app.command("exclude-list", hidden=True)
def exclude_list_legacy(
    root: Optional[Path] = typer.Option(None, help="Repo root (default: cwd)"),
) -> None:
    exclude_list(root=root)


@app.command("exclude-clear", hidden=True)
def exclude_clear_legacy(
    root: Optional[Path] = typer.Option(None, help="Repo root (default: cwd)"),
) -> None:
    exclude_clear(root=root)


@ext_app.command("add")
def ext_add(
    exts: List[str] = typer.Argument(..., help="Extensions to include, e.g. py md"),
    root: Optional[Path] = typer.Option(None, help="Repo root (default: cwd)"),
) -> None:
    """
    Add persistent file extensions for scans.
    """
    root = resolve_root(root)
    items = load_state(root)
    extensions = load_extensions(root)
    to_add = normalize_extensions(exts)
    if not to_add:
        raise typer.BadParameter("No extensions provided.")
    new_extensions = normalize_extensions(extensions + to_add)
    added = [ext for ext in new_extensions if ext not in extensions]
    save_state(root, items, extensions=new_extensions)
    if added:
        console.print("[green]Added extensions:[/green]")
        for ext in added:
            console.print(f"- {ext}")
    else:
        console.print("[yellow]No new extensions added.[/yellow]")


@ext_app.command("remove")
def ext_remove(
    exts: List[str] = typer.Argument(..., help="Extensions to remove, e.g. py md"),
    root: Optional[Path] = typer.Option(None, help="Repo root (default: cwd)"),
) -> None:
    """
    Remove persistent file extensions for scans.
    """
    root = resolve_root(root)
    items = load_state(root)
    extensions = load_extensions(root)
    to_remove = builtins.set(normalize_extensions(exts))
    if not to_remove:
        raise typer.BadParameter("No extensions provided.")
    removed = [ext for ext in extensions if ext in to_remove]
    new_extensions = [ext for ext in extensions if ext not in to_remove]
    if not new_extensions:
        raise typer.BadParameter("At least one extension is required.")
    save_state(root, items, extensions=new_extensions)
    if removed:
        console.print("[green]Removed extensions:[/green]")
        for ext in removed:
            console.print(f"- {ext}")
    else:
        console.print("[yellow]No matching extensions found.[/yellow]")


@ext_app.command("list")
def ext_list(
    root: Optional[Path] = typer.Option(None, help="Repo root (default: cwd)"),
) -> None:
    """
    List saved file extensions used for scans.
    """
    root = resolve_root(root)
    extensions = load_extensions(root)
    console.print("[bold]Extensions used for scan[/bold]")
    for ext in extensions:
        console.print(f"- {ext}")


@ext_app.command("clear")
def ext_clear(
    root: Optional[Path] = typer.Option(None, help="Repo root (default: cwd)"),
) -> None:
    """
    Reset extensions to the default list.
    """
    root = resolve_root(root)
    items = load_state(root)
    save_state(root, items, extensions=DEFAULT_EXTENSIONS)
    console.print("[green]Reset extensions to defaults.[/green]")


@app.command("ext-add", hidden=True)
def ext_add_legacy(
    exts: List[str] = typer.Argument(..., help="Extensions to include, e.g. py md"),
    root: Optional[Path] = typer.Option(None, help="Repo root (default: cwd)"),
) -> None:
    ext_add(exts=exts, root=root)


@app.command("ext-remove", hidden=True)
def ext_remove_legacy(
    exts: List[str] = typer.Argument(..., help="Extensions to remove, e.g. py md"),
    root: Optional[Path] = typer.Option(None, help="Repo root (default: cwd)"),
) -> None:
    ext_remove(exts=exts, root=root)


@app.command("ext-list", hidden=True)
def ext_list_legacy(
    root: Optional[Path] = typer.Option(None, help="Repo root (default: cwd)"),
) -> None:
    ext_list(root=root)


@app.command("ext-clear", hidden=True)
def ext_clear_legacy(
    root: Optional[Path] = typer.Option(None, help="Repo root (default: cwd)"),
) -> None:
    ext_clear(root=root)


@app.command()
def set(
    path: str = typer.Argument(
        ..., help="File path (relative to root or absolute under root)"
    ),
    read_loc: int = typer.Argument(..., help="How many LOC you read in this file"),
    root: Optional[Path] = typer.Option(None, help="Repo root (default: cwd)"),
) -> None:
    """
    Set partial progress for a file.
    """
    root = resolve_root(root)
    items = require_state(root)
    rel = normalize_path_arg(root, path)
    if rel not in items:
        raise typer.BadParameter(f"Unknown file: {rel} (did you scan?)")
    items[rel].read_loc = read_loc
    items[rel].clamp()
    save_state(root, items)
    console.print(f"Updated {rel}: {items[rel].read_loc}/{items[rel].total_loc}")


@app.command()
def done(
    path: str = typer.Argument(...),
    root: Optional[Path] = typer.Option(None),
) -> None:
    """
    Mark a file as fully read.
    """
    root = resolve_root(root)
    items = require_state(root)
    rel = normalize_path_arg(root, path)
    if rel not in items:
        raise typer.BadParameter(f"Unknown file: {rel} (did you scan?)")
    items[rel].read_loc = items[rel].total_loc
    save_state(root, items)
    console.print(f"[green]Done[/green] {rel}")


@app.command()
def reset(
    path: str = typer.Argument(...),
    root: Optional[Path] = typer.Option(None),
) -> None:
    """
    Reset a file's progress to unread.
    """
    root = resolve_root(root)
    items = require_state(root)
    rel = normalize_path_arg(root, path)
    if rel not in items:
        raise typer.BadParameter(f"Unknown file: {rel} (did you scan?)")
    items[rel].read_loc = 0
    save_state(root, items)
    console.print(f"Reset {rel}")


@app.command()
def update(
    root: Optional[Path] = typer.Option(None, help="Repo root (default: cwd)"),
    loc_mode: str = typer.Option("physical", help="LOC mode: physical|nonempty"),
    exclude: List[str] = typer.Option(
        None, "--exclude", help="Exclude glob for this run (repeatable)"
    ),
    ext: List[str] = typer.Option(
        None,
        "--ext",
        help="Include file extension(s) for scan (repeatable), e.g. py",
    ),
    include_empty: bool = typer.Option(
        False, "--include-empty", help="Include empty files (0 LOC) in scan"
    ),
    reset_changed: str = typer.Option(
        "ask",
        "--reset-changed",
        help="Reset progress for changed files: ask|yes|no",
    ),
) -> None:
    """
    Re-scan and detect modified files.
    """
    root = resolve_root(root)
    reset_changed = reset_changed.lower()
    if reset_changed not in {"ask", "yes", "no"}:
        raise typer.BadParameter("Invalid --reset-changed value. Use ask, yes, or no.")
    saved_excludes = load_excludes(root)
    saved_extensions = load_extensions(root)
    ex = DEFAULT_EXCLUDES + saved_excludes + (exclude or [])
    items = require_state(root)
    extensions = normalize_extensions(ext or saved_extensions)
    if not extensions:
        raise typer.BadParameter("No extensions provided.")
    scanned = scan_repo(
        root,
        ex,
        loc_mode=loc_mode,
        include_empty=include_empty,
        extensions=extensions,
    )

    changed: List[Tuple[str, FileProgress, int, int]] = []
    removed: List[str] = []

    for rel, fp in items.items():
        if rel not in scanned:
            removed.append(rel)
            continue
        new_total, new_mtime = scanned[rel]
        if (new_total != fp.total_loc) or (new_mtime != fp.mtime_ns):
            changed.append((rel, fp, new_total, new_mtime))

    # Handle removed files
    if removed:
        console.print(f"[yellow]{len(removed)} files disappeared from scan.[/yellow]")
        if Confirm.ask("Remove them from vibemark state?", default=False):
            for rel in removed:
                items.pop(rel, None)

    # Handle changed files
    if not changed:
        console.print("[green]No changes detected.[/green]")
    else:
        console.print(f"[yellow]{len(changed)} files changed.[/yellow]")
        for rel, fp, new_total, new_mtime in sorted(changed, key=lambda x: x[0]):
            console.print(f"\n[bold]{rel}[/bold]")
            console.print(f"  was: {fp.read_loc}/{fp.total_loc}  now LOC: {new_total}")
            if fp.read_loc > 0:
                should_reset = reset_changed == "yes"
                if reset_changed == "ask":
                    should_reset = Confirm.ask(
                        "Reset progress for this file?", default=False
                    )
                if should_reset:
                    fp.read_loc = 0
            # Always update metadata & clamp
            fp.total_loc = new_total
            fp.mtime_ns = new_mtime
            fp.clamp()

    # Add any new files
    new_files = [rel for rel in scanned.keys() if rel not in items]
    if new_files:
        console.print(
            f"\n[cyan]{len(new_files)} new files found.[/cyan] Adding as unread."
        )
        for rel in new_files:
            total, mtime = scanned[rel]
            items[rel] = FileProgress(rel, total, 0, mtime)

    save_state(
        root,
        items,
        excludes=saved_excludes,
        extensions=extensions,
    )
    total, read = totals(items)
    console.print(f"\nSaved. Total {read}/{total} LOC read.")


@app.command()
def export_md(
    root: Optional[Path] = typer.Option(None, help="Repo root (default: cwd)"),
    header: str = typer.Option("## Review", help="Markdown header title"),
) -> None:
    """
    Export a markdown checklist
    """
    root = resolve_root(root)
    items = require_state(root)

    lines = [header, ""]
    rows = sorted(items.values(), key=lambda fp: fp.path)
    for fp in rows:
        checked = "x" if fp.status == "done" else " "
        extra = ""
        if fp.status == "partial":
            extra = f"  ({fp.read_loc}/{fp.total_loc} read)"
        lines.append(f"- [{checked}] {fp.path}  {fp.total_loc} LOC{extra}")

    console.print("\n".join(lines), markup=False)


if __name__ == "__main__":
    app()
