#!/usr/bin/env python3
"""Generate text-processing pipeline tapes for VHS."""

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


PIPELINES = [
    {
        "commands": [
            "printf '%s\\n' 'a,1' 'b,2' 'c,3' > sample.csv",
            "cat sample.csv",
            "column -t -s',' sample.csv",
            "rm sample.csv",
        ],
        "description": "format a csv with column -t",
    },
    {
        "commands": [
            "seq 1 12 | paste -d',' - - - - > grid.txt",
            "cat grid.txt",
            "awk -F',' '{print $1,$3}' grid.txt",
            "rm grid.txt",
        ],
        "description": "generate numeric grid and extract columns",
    },
    {
        "commands": [
            "echo 'error:disk full' > logs.txt",
            "echo 'info:ok' >> logs.txt",
            "echo 'warning:high load' >> logs.txt",
            "grep -i 'error' logs.txt",
            "sed 's/:/ -> /' logs.txt",
            "rm logs.txt",
        ],
        "description": "scan a log and rewrite separators",
    },
    {
        "commands": [
            "printf '%s\\n' alpha beta Gamma > words.txt",
            "sort -f words.txt",
            "uniq -c words.txt",
            "rm words.txt",
        ],
        "description": "sort words case-insensitively",
    },
    {
        "commands": [
            "printf '%s\\n' '{\"value\": 42, \"unit\": \"ms\"}' > data.json",
            "jq '.' data.json",
            "python -c \"import json; print(json.load(open('data.json'))['value'] * 2)\"",
            "rm data.json",
        ],
        "description": "inspect json with jq and python",
    },
]


def build_body(commands: List[str]) -> List[str]:
    body: List[str] = ["Sleep 1000ms"]
    for cmd in commands:
        body.append(f'Type "{cmd}"')
        body.append("Enter")
        body.append("Sleep 1000ms")
    body.append("Sleep 1000ms")
    return body


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, default=10000)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("engine/cli/vhs/generated/text_pipeline"),
    )
    parser.add_argument("--seed", type=int, default=2028)
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
        recipe = rng.choice(PIPELINES)
        tape_id, output_name = allocator.next()
        metadata = TapeMetadata(
            tape_id=tape_id,
            instruction=(
                "Runs a quick text-processing pipeline to "
                + recipe["description"]
            ).replace('"', '\\"'),
            active_classes={"Text": True, "Basic": True},
            level=2,
            interactive=False,
            events=4 * len(recipe["commands"]) + 2,
            visual_complexity=48,
            requires=["bash", "jq", "awk"],
            body_lines=build_body(list(recipe["commands"])),
            output_name=output_name,
        )
        destination = args.output_dir / f"{tape_id}.tape"
        destination.write_text(render_tape(metadata), encoding="utf-8")
        created.append(destination)

    print(f"Generated {len(created)} tapes")
    print(f"Next available index: {allocator.next_index}")


if __name__ == "__main__":
    main()
