# Changelog

Entries below are compiled from the git log and tags.

## 1.3.5 - 2026-03-17

- Added `vibemark --color` global flag to force ANSI color output when piping (e.g. `vibemark --color stats | less -R`).

## 1.3.4 - 2026-03-17

- Added `vibemark stats --include-done` (`-d`) to also show fully-read files in the output.
- Done files appear at the bottom of the table, rendered in dim text with `0` remaining LOC.
- In CSV/TSV mode, done files are appended as rows with `status=done` and `remaining=0`.

## 1.3.3 - 2026-03-01

- Added `vibemark stats --format csv|tsv` to output remaining-files data as CSV or TSV instead of a Rich table, enabling piping into tools like `qsv`, `duckdb`, `visidata`, and `awk`.
- Summary line is suppressed in CSV/TSV mode to keep stdout clean for piping.
- Output columns: `file`, `status`, `read`, `total`, `remaining`.

## 1.3.2 - 2026-02-25

- Added `vibemark stats --no-table` to print only total progress without the remaining-files table.
- Updated `stats` behavior so `--top` validation is skipped when `--no-table` is used.
- Added CLI tests for totals-only output and `--top 0 --no-table`.

## 1.3.1 - 2026-02-25

- Added `vibemark stats --all` to show the full remaining-files table instead of only top-k rows.
- Kept `--top` behavior for top-k output and added validation to require `--top > 0` unless `--all` is used.
- Added CLI tests covering `stats --all` output and `--top 0` validation behavior.

## 1.3.0 - 2026-02-18

- Grouped persistent exclude commands under `exclude` subcommands:
  - `vibemark exclude add`
  - `vibemark exclude remove`
  - `vibemark exclude list`
  - `vibemark exclude clear`
- Grouped persistent extension commands under `ext` subcommands:
  - `vibemark ext add`
  - `vibemark ext remove`
  - `vibemark ext list`
  - `vibemark ext clear`
- Kept legacy dash-style commands (`exclude-add`, `exclude-remove`, `exclude-list`, `exclude-clear`, `ext-add`, `ext-remove`, `ext-list`, `ext-clear`) as hidden aliases for backward compatibility.
- Updated README examples and added CLI tests for new subcommand paths and legacy alias compatibility.

## 1.2.3 - 2026-02-17

- Removed `dash` interactive dashboard command to keep the interface focused on Unix-style CLI workflows.

## 1.2.2 - 2026-01-26

- Added `update --reset-changed yes|no` to skip per-file prompts.

## 1.2.1 - 2026-01-18

- Added support for other file extensions.
- Added MIT License and documentation updates.
- Fixed `update` prompting reset when no progress exists.
- Fixed `export-md` checkbox rendering for done files.
- Skipped remaining table output when `--top` is 0.
- Added tests and lockfile updates.

## 1.1.4 - 2026-01-04

- Added exclude commands.
- Added version flag and improved CLI help.
- Added `--include-empty` support for scans.
- Docstring cleanup and lint/type fixes.

## 1.0.0 - 2026-01-01

- Initial release as `vibemark`.
- Added testing and formatting.
