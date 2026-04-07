#!/usr/bin/env python3
"""Generate filesystem workflow tapes (create/list/clean) for VHS."""

from __future__ import annotations

import argparse
import random
from pathlib import Path
from typing import Iterable, List

from _common import (
    DEFAULT_ID_WIDTH,
    DEFAULT_START_INDEX,
    TapeIdAllocator,
    TapeMetadata,
    ensure_output_dir,
    render_tape,
)


WORK_SCRIPTS = [
    [
        "workspace=$(mktemp -d /tmp/vhs_fs_XXXXXX)",
        "cd \"$workspace\"",
        "mkdir -p logs data",
        "touch logs/app.log data/input.txt",
        "ls -R",
        "rm -rf \"$workspace\"",
    ],
    [
        "tmpdir=$(mktemp -d /tmp/vhs_stage_XXXXXX)",
        "cd \"$tmpdir\"",
        "printf '%s\\n' alpha beta gamma > list.txt",
        "cp list.txt backup.txt",
        "mv backup.txt archive.txt",
        "ls -lh",
        "rm -rf \"$tmpdir\"",
    ],
    [
        "basedir=$(mktemp -d /tmp/vhs_tree_XXXXXX)",
        "mkdir -p \"$basedir\"/reports/{daily,weekly,monthly}",
        "find \"$basedir\" -maxdepth 2 -type d | sort",
        "touch \"$basedir\"/reports/daily/summary.txt",
        "ls -R \"$basedir\"/reports",
        "rm -rf \"$basedir\"",
    ],
    [
        "sandbox=$(mktemp -d /tmp/vhs_acl_XXXXXX)",
        "cd \"$sandbox\"",
        "touch notes.md",
        "chmod 640 notes.md",
        "stat --format='%A %n' notes.md",
        "rm -rf \"$sandbox\"",
    ],
    [
        "tmp=$(mktemp -d /tmp/vhs_sync_XXXXXX)",
        "cd \"$tmp\"",
        "for n in {1..3}; do printf 'row %s\\n' \"$n\" >> data.log; done",
        "tail -n 2 data.log",
        "sed -i 's/row/entry/' data.log",
        "cat data.log",
        "rm -rf \"$tmp\"",
    ],
]


def build_body(commands: Iterable[str]) -> List[str]:
    body: List[str] = ["Sleep 1000ms"]
    for cmd in commands:
        body.append(f'Type "{cmd}"')
        body.append("Enter")
        body.append("Sleep 1000ms")
    body.append("Sleep 1000ms")
    return body


def build_instruction(commands: List[str]) -> str:
    summary = [cmd for cmd in commands if not cmd.startswith("tmp=") and "mktemp" not in cmd]
    return (
        "Executes a short filesystem workflow: "
        + ", then ".join(summary[:5])
        + (" and clean-up." if summary else ".")
    )


def generate_tapes(
    count: int,
    allocator: TapeIdAllocator,
    output_dir: Path,
    rng: random.Random,
) -> List[Path]:
    ensure_output_dir(output_dir)
    created: List[Path] = []
    for _ in range(count):
        recipe = list(rng.choice(WORK_SCRIPTS))
        # maybe append listing of tmp to emphasise cleanup variations
        if rng.random() < 0.4:
            recipe.insert(-1, "ls")
        tape_id, output_name = allocator.next()
        metadata = TapeMetadata(
            tape_id=tape_id,
            instruction=build_instruction(recipe).replace('"', '\\"'),
            active_classes={"Files": True, "Basic": True},
            level=2,
            interactive=False,
            events=4 * len(recipe) + 2,
            visual_complexity=44,
            requires=["bash", "find", "stat"],
            body_lines=build_body(recipe),
            output_name=output_name,
        )
        destination = output_dir / f"{tape_id}.tape"
        destination.write_text(render_tape(metadata), encoding="utf-8")
        created.append(destination)
    return created


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, default=10000)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("engine/cli/vhs/generated/fs_workflows"),
    )
    parser.add_argument("--seed", type=int, default=2027)
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
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rng = random.Random(args.seed)
    allocator = TapeIdAllocator(
        prefix=args.id_prefix,
        start_index=args.start_index,
        width=args.id_width,
    )
    tapes = generate_tapes(
        count=args.count,
        allocator=allocator,
        output_dir=args.output_dir,
        rng=rng,
    )
    print(f"Generated {len(tapes)} tapes")
    print(f"Next available index: {allocator.next_index}")


if __name__ == "__main__":
    main()
