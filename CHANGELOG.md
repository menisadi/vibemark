# Changelog

Entries below are compiled from the git log and tags.

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
