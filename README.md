# vibemark

Track how much code you have actually read, by file and by LOC. `vibemark` scans your
repository for Python files, stores progress in a local state file, and provides
simple commands to update or visualize your reading status.

## Quickstart

- Scan the repo and initialize progress:
  - `uv run vibemark scan`
- Show overall progress and largest remaining files:
  - `uv run vibemark stats`
- Mark a file as fully read:
  - `uv run vibemark done src/vibemark/cli.py`
- Set partial progress for a file:
  - `uv run vibemark set src/vibemark/cli.py 120`

## How it works

`vibemark` looks for `*.py` files under the repo root, applies default exclusions
(e.g., `.git/`, `.venv/`, `build/`), and writes state to `.vibemark.json` in the
root directory. Use `vibemark update` to rescan and optionally reset progress for
changed files.

## Development

- Run the CLI:
  - `uv run vibemark --help`
- Run tests:
  - `uv run pytest`

## Requirements

- Python 3.13+
- `uv` for running and building
