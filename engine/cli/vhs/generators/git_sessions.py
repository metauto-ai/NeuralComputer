#!/usr/bin/env python3
"""Generate Git workflow tapes for VHS."""

from __future__ import annotations

import argparse
import random
from pathlib import Path
from typing import List

from _common import (
    DEFAULT_ID_WIDTH,
    DEFAULT_START_INDEX,
    TapeIdAllocator,
    TapeMetadata,
    ensure_output_dir,
    render_tape,
)


SEQUENCES = [
    [
        "repo=$(mktemp -d /tmp/vhs_git_XXXXXX)",
        "cd \"$repo\"",
        "git init -q",
        "echo 'hello' > README.md",
        "git add README.md",
        "git commit -q -m 'init'",
        "git status -sb",
        "rm -rf \"$repo\"",
    ],
    [
        "repo=$(mktemp -d /tmp/vhs_git_XXXXXX)",
        "cd \"$repo\"",
        "git init -q",
        "touch notes.txt",
        "git add notes.txt",
        "git commit -q -m 'Add notes'",
        "git log --oneline",
        "rm -rf \"$repo\"",
    ],
    [
        "repo=$(mktemp -d /tmp/vhs_git_XXXXXX)",
        "cd \"$repo\"",
        "git init -q",
        "printf 'a\\nb\\n' > data.txt",
        "git add data.txt",
        "git commit -q -m 'Add data'",
        "echo 'c' >> data.txt",
        "git diff",
        "rm -rf \"$repo\"",
    ],
    [
        "repo=$(mktemp -d /tmp/vhs_git_XXXXXX)",
        "cd \"$repo\"",
        "git init -q",
        "echo test > file.txt",
        "git add file.txt",
        "git commit -q -m 'Add file'",
        "git branch feature",
        "git branch",
        "rm -rf \"$repo\"",
    ],
    [
        "repo=$(mktemp -d /tmp/vhs_git_XXXXXX)",
        "cd \"$repo\"",
        "git init -q",
        "echo one > numbers.txt",
        "git add numbers.txt",
        "git commit -q -m 'one'",
        "echo two >> numbers.txt",
        "git status -sb",
        "rm -rf \"$repo\"",
    ],
]


def build_body(commands: List[str]) -> List[str]:
    body: List[str] = ["Sleep 1000ms"]
    for cmd in commands:
        body.append(f'Type "{cmd}"')
        body.append("Enter")
        body.append("Sleep 1000ms")
    body.append("Sleep 1000ms")
    return body


def describe(commands: List[str]) -> str:
    highlights = [cmd for cmd in commands if cmd.startswith("git ") or cmd.startswith("echo")]
    return (
        "Demonstrates a mini git session: "
        + ", then ".join(highlights[:5])
        + "."
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, default=10000)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("engine/cli/vhs/generated/git_sessions"),
    )
    parser.add_argument("--seed", type=int, default=2030)
    parser.add_argument("--id-prefix", default="sft")
    parser.add_argument(
        "--start-index",
        type=int,
        default=DEFAULT_START_INDEX,
    )
    parser.add_argument(
        "--id-width",
        type=int,
        default=DEFAULT_ID_WIDTH,
    )
    args = parser.parse_args()

    rng = random.Random(args.seed)
    allocator = TapeIdAllocator(
        prefix=args.id_prefix,
        start_index=args.start_index,
        width=args.id_width,
    )
    ensure_output_dir(args.output_dir)

    created: List[Path] = []
    for _ in range(args.count):
        sequence = list(rng.choice(SEQUENCES))
        tape_id, output_name = allocator.next()
        metadata = TapeMetadata(
            tape_id=tape_id,
            instruction=describe(sequence).replace('"', '\\"'),
            active_classes={"VCS": True, "Basic": True},
            level=2,
            interactive=False,
            events=4 * len(sequence) + 2,
            visual_complexity=46,
            requires=["git", "bash"],
            body_lines=build_body(sequence),
            output_name=output_name,
        )
        destination = args.output_dir / f"{tape_id}.tape"
        destination.write_text(render_tape(metadata), encoding="utf-8")
        created.append(destination)

    print(f"Generated {len(created)} tapes")
    print(f"Next available index: {allocator.next_index}")


if __name__ == "__main__":
    main()
