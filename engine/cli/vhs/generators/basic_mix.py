#!/usr/bin/env python3
"""Generate shuffled basic shell command sequences for VHS tapes."""

from __future__ import annotations

import argparse
import random
from pathlib import Path
from typing import Iterable, List, Sequence

from _common import (
    DEFAULT_ID_WIDTH,
    DEFAULT_START_INDEX,
    TapeIdAllocator,
    TapeMetadata,
    ensure_output_dir,
    render_tape,
)


BASIC_COMMANDS: Sequence[tuple[str, str]] = (
    ("pwd", "prints the current working directory"),
    ("whoami", "shows the active user"),
    ("uname -r", "reports the kernel release"),
    ("uname -sm", "summarises os and architecture"),
    ("date '+%F %T'", "displays date and time"),
    ("hostname", "shows the system hostname"),
    ("echo $SHELL", "echoes the shell in use"),
    ("echo PATH=$PATH", "prints the PATH variable"),
    ("echo LANG=$LANG", "shows the locale"),
    ("id", "summarises user/group ids"),
    ("ls -1", "lists directory entries line by line"),
    ("ls -lh", "lists files with sizes"),
    ("ls -a", "includes hidden files"),
    ("df -h", "prints disk usage"),
    ("free -h", "shows memory usage"),
    ("uptime", "reports system uptime"),
    ("printenv | head -n 5", "previews environment variables"),
    ("env | sort | head -n 6", "shows sorted env vars"),
    ("alias | head -n 5", "displays configured aliases"),
    ("type ls", "shows how ls resolves"),
    ("type echo", "shows how echo resolves"),
    ("printf 'HOME=%s\\n' \"$HOME\"", "prints home directory explicitly"),
    ("ls /tmp", "lists /tmp contents"),
    ("ls -d */", "shows directories only"),
)


def build_sequence(rng: random.Random, length: int) -> list[tuple[str, str]]:
    choices = list(BASIC_COMMANDS)
    rng.shuffle(choices)
    return choices[:length]


def build_body(commands: Iterable[str], sleep_ms: int) -> List[str]:
    interval = max(1000, sleep_ms)
    body: List[str] = ["Sleep 1000ms"]
    for cmd in commands:
        body.append(f'Type "{cmd}"')
        body.append("Enter")
        body.append(f"Sleep {interval}ms")
    body.append("Sleep 1000ms")
    return body


def build_instruction(seq: Sequence[tuple[str, str]]) -> str:
    parts = [f"runs `{cmd}` to {desc}" for cmd, desc in seq]
    if len(parts) == 1:
        core = parts[0]
    else:
        core = ", then ".join([", ".join(parts[:-1]), parts[-1]]) if len(parts) > 2 else " and ".join(parts)
    return f"In a quick shell tour the user {core}."


def generate_tapes(
    count: int,
    allocator: TapeIdAllocator,
    output_dir: Path,
    rng: random.Random,
    min_len: int,
    max_len: int,
) -> List[Path]:
    ensure_output_dir(output_dir)
    created: List[Path] = []
    for _ in range(count):
        length = rng.randint(min_len, max_len)
        sequence = build_sequence(rng, length)
        commands = [cmd for cmd, _ in sequence]
        tape_id, output_name = allocator.next()
        metadata = TapeMetadata(
            tape_id=tape_id,
            instruction=build_instruction(sequence).replace('"', '\\"'),
            active_classes={"Basic": True},
            level=1,
            interactive=False,
            events=4 * len(commands) + 2,
            visual_complexity=32 + len(commands) * 3,
            requires=["bash"],
            body_lines=build_body(commands, sleep_ms=280),
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
        default=Path("engine/cli/vhs/generated/basic_mix"),
    )
    parser.add_argument("--min-length", type=int, default=3)
    parser.add_argument("--max-length", type=int, default=5)
    parser.add_argument("--seed", type=int, default=2026)
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
        min_len=max(1, args.min_length),
        max_len=max(args.min_length, args.max_length),
    )
    print(f"Generated {len(tapes)} tapes")
    print(f"Next available index: {allocator.next_index}")


if __name__ == "__main__":
    main()
