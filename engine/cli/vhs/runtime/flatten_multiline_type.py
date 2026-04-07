#!/usr/bin/env python3
"""Flatten multi-line VHS `Type` commands into single-line equivalents."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable


def count_unescaped_quotes(text: str) -> int:
    total = 0
    escape = False
    for ch in text:
        if escape:
            escape = False
            continue
        if ch == "\\":
            escape = True
            continue
        if ch == '"':
            total += 1
    return total


def extract_type_block(lines: list[str], start_index: int) -> tuple[list[str], int]:
    buffer: list[str] = [lines[start_index]]
    total_quotes = count_unescaped_quotes(lines[start_index])
    index = start_index
    while total_quotes % 2 == 1:
        index += 1
        if index >= len(lines):
            raise ValueError("Unterminated Type string literal encountered")
        buffer.append(lines[index])
        total_quotes += count_unescaped_quotes(lines[index])
    return buffer, index


def unescape_line_prefix(line: str) -> str:
    if not line.startswith('Type "'):
        raise ValueError("Line does not start with Type \"")
    return line[len('Type "') :]


def strip_trailing_quote(line: str) -> str:
    if line.endswith('"') and not line.endswith('\\"'):
        return line[:-1]
    return line


def decode_block(block_lines: list[str]) -> list[str]:
    parts: list[str] = []
    for idx, raw_line in enumerate(block_lines):
        if idx == 0:
            piece = unescape_line_prefix(raw_line)
        else:
            piece = raw_line
        if idx == len(block_lines) - 1:
            piece = strip_trailing_quote(piece)
        parts.append(piece)
    joined = "\n".join(parts)
    return joined.split("\n")


def needs_flatten(block_lines: list[str]) -> bool:
    if len(block_lines) == 1:
        return False
    joined = "\n".join(block_lines)
    return "\n" in joined


def escape_for_type(text: str) -> str:
    text = text.replace("\\", "\\\\")
    text = text.replace('"', '\\"')
    return text


def flatten_tape(content: str) -> tuple[str, bool]:
    lines = content.splitlines()
    output: list[str] = []
    i = 0
    skip_next_enter = False
    changed = False

    while i < len(lines):
        line = lines[i]
        if line.startswith('Type "'):
            block, end_index = extract_type_block(lines, i)
            if needs_flatten(block):
                decoded_lines = decode_block(block)
                for decoded in decoded_lines:
                    escaped = escape_for_type(decoded)
                    output.append(f'Type "{escaped}"')
                    output.append('Enter')
                skip_next_enter = True
                changed = True
                i = end_index + 1
                continue
            else:
                output.append(line)
                i += 1
                continue
        if skip_next_enter and line.strip() == 'Enter':
            skip_next_enter = False
            i += 1
            continue
        skip_next_enter = False
        output.append(line)
        i += 1

    result = "\n".join(output)
    if content.endswith("\n"):
        result += "\n"
    return result, changed


def process_files(paths: Iterable[Path], write: bool) -> int:
    total_changed = 0
    for path in paths:
        original = path.read_text(encoding="utf-8")
        updated, changed = flatten_tape(original)
        if not changed:
            continue
        total_changed += 1
        if write:
            path.write_text(updated, encoding="utf-8")
    return total_changed


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "paths",
        nargs="+",
        type=Path,
        help="Tape files or directories to process",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show how many files would change without writing",
    )
    args = parser.parse_args()

    resolved: list[Path] = []
    for path in args.paths:
        if path.is_dir():
            resolved.extend(sorted(path.rglob("*.tape")))
        else:
            resolved.append(path)

    changed = process_files(resolved, write=not args.dry_run)
    if args.dry_run:
        print(f"[DRY-RUN] Would update {changed} file(s)")
    else:
        print(f"Updated {changed} file(s)")


if __name__ == "__main__":
    main()
