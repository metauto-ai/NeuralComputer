#!/usr/bin/env python3
"""Generate monitoring and network routine tapes for VHS."""

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


SCENARIOS = [
    (
        "timeout 6s watch -n 1 \"date '+%T'; uptime\"",
        "monitors time and uptime briefly",
        ["timeout", "watch", "date", "uptime"],
    ),
    (
        "timeout 6s watch -n 2 \"df -h /\"",
        "repeats df -h to watch disk usage",
        ["timeout", "watch", "df"],
    ),
    (
        "ping -c 3 localhost",
        "pings localhost three times",
        ["ping"],
    ),
    (
        "curl --max-time 4 -I https://example.com || echo offline",
        "performs a quick HTTP HEAD request",
        ["curl"],
    ),
    (
        "dig +short example.com",
        "resolves example.com using dig",
        ["dig"],
    ),
    (
        "netstat -tuln | head -n 5",
        "inspects listening sockets",
        ["netstat"],
    ),
    (
        "sensors | head -n 8",
        "prints sensor readings",
        ["sensors"],
    ),
    (
        "ss -tuna | head -n 5",
        "lists TCP/UDP sockets",
        ["ss"],
    ),
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
        default=Path("engine/cli/vhs/generated/monitoring_network"),
    )
    parser.add_argument("--seed", type=int, default=2029)
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
        first, second = rng.sample(SCENARIOS, k=2)
        commands = [first[0], second[0]]
        requires = sorted(set(first[2] + second[2]))
        instruction = (
            f"Runs `{commands[0]}` and `{commands[1]}` to "
            f"{first[1]} and {second[1]}."
        ).replace('"', '\\"')
        tape_id, output_name = allocator.next()
        metadata = TapeMetadata(
            tape_id=tape_id,
            instruction=instruction,
            active_classes={"Network": True, "Process": True},
            level=2,
            interactive=False,
            events=10,
            visual_complexity=40,
            requires=requires,
            body_lines=build_body(commands),
            output_name=output_name,
        )
        destination = args.output_dir / f"{tape_id}.tape"
        destination.write_text(render_tape(metadata), encoding="utf-8")
        created.append(destination)

    print(f"Generated {len(created)} tapes")
    print(f"Next available index: {allocator.next_index}")


if __name__ == "__main__":
    main()
