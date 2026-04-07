#!/usr/bin/env python3
"""Ensure every VHS `Type` string properly escapes internal double quotes."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable

PREFIX = 'Type "'


def split_type_line(line: str) -> tuple[str, str, str] | None:
    if not line.startswith(PREFIX):
        return None
    i = len(line) - 1
    closing_index = -1
    while i >= len(PREFIX):
        if line[i] == '"':
            backslash_count = 0
            j = i - 1
            while j >= len(PREFIX) and line[j] == '\\':
                backslash_count += 1
                j -= 1
            if backslash_count % 2 == 0:
                closing_index = i
                break
        i -= 1
    if closing_index == -1:
        return None
    content = line[len(PREFIX):closing_index]
    remainder = line[closing_index + 1 :]
    return PREFIX, content, remainder


def normalize_content(content: str) -> tuple[str, bool]:
    normalized: list[str] = []
    changed = False
    escape = False
    for ch in content:
        if escape:
            normalized.append(ch)
            escape = False
            continue
        if ch == '\\':
            normalized.append(ch)
            escape = True
            continue
        if ch == '"':
            normalized.append('\\"')
            changed = True
        else:
            normalized.append(ch)
    return ''.join(normalized), changed


def normalize_type_line(line: str) -> tuple[str, bool]:
    split = split_type_line(line)
    if split is None:
        return line, False
    prefix, content, remainder = split
    normalized_content, changed = normalize_content(content)
    if not changed:
        return line, False
    return prefix + normalized_content + '"' + remainder, True


def process_file(path: Path, write: bool) -> bool:
    original = path.read_text(encoding="utf-8")
    parts: list[str] = []
    changed = False
    for line in original.splitlines(keepends=True):
        has_newline = line.endswith('\n')
        body = line[:-1] if has_newline else line
        normalized, line_changed = normalize_type_line(body)
        if has_newline:
            normalized += '\n'
        parts.append(normalized)
        if line_changed:
            changed = True
    if changed and write:
        path.write_text(''.join(parts), encoding="utf-8")
    return changed


def collect_paths(paths: Iterable[Path]) -> list[Path]:
    collected: list[Path] = []
    for path in paths:
        if path.is_dir():
            collected.extend(sorted(path.rglob('*.tape')))
        else:
            collected.append(path)
    return collected


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('paths', nargs='+', type=Path)
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    changed = 0
    for path in collect_paths(args.paths):
        if process_file(path, write=not args.dry_run):
            changed += 1
    if args.dry_run:
        print(f"[DRY-RUN] Would update {changed} file(s)")
    else:
        print(f"Updated {changed} file(s)")


if __name__ == '__main__':
    main()
