# vibemark

Track how much code you have actually read, by file and by LOC. `vibemark` scans your
repository for Python files, stores progress in a local state file, and provides
simple commands to update or visualize your reading status.

## Installation

The main way to use vibemark is via PyPI under the `vibemark` package:

- `pipx install vibemark`
- `pip install vibemark`
- `uv tool install vibemark` (recommended)

## Quickstart

- Scan the repo and initialize progress:
  - `vibemark scan`
- Show overall progress and largest remaining files:
  - `vibemark stats`
- Mark a file as fully read:
  - `vibemark done src/vibemark/cli.py`
- Set partial progress for a file:
  - `vibemark set src/vibemark/cli.py 120`
- Exclude a folder for a run (glob):
  - `vibemark scan --exclude "src/vendor/*"`
- Persistently exclude a folder (saved in `.vibemark.json`):
  - `vibemark exclude add "src/vendor/*"`

## More commands

- `vibemark update` re-scan and optionally reset changed files
- `vibemark update --reset-changed yes|no` skip per-file prompts (default: ask)
- `vibemark reset path/to/file.py` mark a file unread
- `vibemark export-md` export a markdown checklist
- `vibemark exclude remove|list|clear`
- `vibemark ext add|remove|list|clear`
- `vibemark --version`

## How it works

`vibemark` looks for `*.py` files under the repo root, applies default exclusions
(e.g., `.git/`, `.venv/`, `build/`), and writes state to `.vibemark.json` in the
root directory. You can add saved exclude globs like `src/vendor/*` or pass
`--exclude` to a single scan. You can also include other extensions via `--ext`
or the `ext-*` commands. Use `vibemark update` to rescan and optionally reset
progress for changed files. For finer control, `scan`/`update` accept `--loc-mode`
(`physical|nonempty`) and `--include-empty`.

## Development

- Run the CLI:
  - `uv run vibemark --help`
- Run tests:
  - `uv run pytest`

## Requirements

- Python 3.13+
- `uv` for running and building from source
