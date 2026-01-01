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
  - `vibemark exclude-add "src/vendor/*"`

## How it works

`vibemark` looks for `*.py` files under the repo root, applies default exclusions
(e.g., `.git/`, `.venv/`, `build/`), and writes state to `.vibemark.json` in the
root directory. You can add saved exclude globs like `src/vendor/*` or pass
`--exclude` to a single scan. Use `vibemark update` to rescan and optionally reset
progress for changed files.

## Development

- Run the CLI:
  - `uv run vibemark --help`
- Run tests:
  - `uv run pytest`

## Requirements

- Python 3.13+
- `uv` for running and building from source
