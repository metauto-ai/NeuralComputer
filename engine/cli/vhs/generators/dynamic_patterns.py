#!/usr/bin/env python3
"""Generate large batches of CLI pattern tapes (monitoring, ASCII art, loops)."""

from __future__ import annotations

import argparse
import random
import shlex
from dataclasses import dataclass
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


@dataclass
class Scenario:
    command: str
    description: str
    requires: List[str]
    post_sleep_ms: int
    level: int
    events: int
    visual_complexity: int


def _base_body(command: str, post_sleep_ms: int) -> List[str]:
    body = [
        "Sleep 1000ms",
        f'Type "{command}"',
        "Enter",
        f"Sleep {max(1000, post_sleep_ms)}ms",
    ]
    return body


def _monitoring_scenarios(count: int, rng: random.Random) -> List[Scenario]:
    inner_commands = [
        "date",
        "df -h",
        "uptime",
        "free -m",
        "cat /proc/loadavg",
        "who",
        "netstat -an | head",
        "sensors",
    ]
    scenarios: List[Scenario] = []
    for _ in range(count):
        inner = rng.choice(inner_commands)
        duration = rng.randint(4, 8)
        interval = rng.choice([1, 2, 3])
        command = f"timeout {duration}s watch -n {interval} {shlex.quote(inner)}"
        requires = ["timeout", "watch"] + inner.split()[0:1]
        scenarios.append(
            Scenario(
                command=command,
                description=(
                    f"Runs `{command}` so the terminal refreshes `{inner}` every {interval}s "
                    f"for about {duration}s, highlighting steady monitoring output."
                ),
                requires=requires,
                post_sleep_ms=(duration + 2) * 1000,
                level=1,
                events=12,
                visual_complexity=48,
            )
        )
    return scenarios


def _sequence_scenarios(count: int, rng: random.Random) -> List[Scenario]:
    templates = [
        "for i in {1..%(limit)d}; do printf \"%%02d %%s\\n\" \"$i\" \"$(printf '#%%.0s' $(seq 1 $i))\"; sleep %(sleep).1f; done",
        "for i in $(seq 1 %(step)d %(limit)d); do printf \"Row %%02d: %%s\\n\" \"$i\" \"$(printf '*%%.0s' $(seq 1 $i))\"; sleep %(sleep).1f; done",
        "for i in $(seq %(limit)d -1 1); do printf \"%%02d |%%*s\\n\" \"$i\" \"$i\" '' | tr ' ' '~'; sleep %(sleep).1f; done",
    ]
    scenarios: List[Scenario] = []
    for _ in range(count):
        template = rng.choice(templates)
        limit = rng.randint(10, 30)
        step = rng.choice([1, 2, 3])
        sleep_time = rng.choice([0.1, 0.2, 0.3, 0.4])
        command = template % {"limit": limit, "step": step, "sleep": sleep_time}
        scenarios.append(
            Scenario(
                command=command,
                description=(
                    "Prints incremental ASCII sequences with controlled sleeps, showing linear "
                    "growth and symmetry patterns line by line."
                ),
                requires=["bash"],
                post_sleep_ms=2000,
                level=1,
                events=16,
                visual_complexity=42,
            )
        )
    return scenarios


def _countdown_scenarios(count: int, rng: random.Random) -> List[Scenario]:
    scenarii = []
    for _ in range(count):
        start = rng.randint(8, 20)
        tempo = rng.choice([0.3, 0.4, 0.5, 0.6])
        command = (
            "seq {start} -1 1 | while read n; do "
            "clear; printf \"T-%02d\\n\" \"$n\"; sleep {tempo}; done"
        ).format(start=start, tempo=tempo)
        scenarii.append(
            Scenario(
                command=command,
                description=(
                    "Simulates a countdown timer that clears the screen then prints T-minus values "
                    "with a consistent beat."
                ),
                requires=["bash"],
                post_sleep_ms=int((start * tempo + 1) * 1000),
                level=1,
                events=18,
                visual_complexity=46,
            )
        )
    for _ in range(count // 4):
        # Insert a tempo-changing variant
        command = (
            "for t in 1 1 0.5 0.5 0.25 0.5 0.5 1; do clear; date +%T; sleep $t; done"
        )
        scenarii.append(
            Scenario(
                command=command,
                description="Runs a tempo-changing beat by printing the current time with varying sleeps.",
                requires=["date"],
                post_sleep_ms=6000,
                level=1,
                events=14,
                visual_complexity=38,
            )
        )
    return scenarii[:count]


def _banner_scenarios(count: int, rng: random.Random) -> List[Scenario]:
    words = [
        "Neural",
        "Physics",
        "Patterns",
        "Training",
        "Demo",
        "Symmetry",
        "Rhythm",
        "Tempo",
    ]
    tools = [
        ("figlet", ["figlet", "figlet -f slant", "figlet -f small"]),
        ("toilet", ["toilet --metal", "toilet -f mono12 --filter border"]),
        ("banner", ["banner"]),
    ]
    scenarios: List[Scenario] = []
    for _ in range(count):
        tool, variants = rng.choice(tools)
        cmd_variant = rng.choice(variants)
        word_cycle = rng.sample(words, k=min(3, len(words)))
        loop_body = " ".join(shlex.quote(word) for word in word_cycle)
        command = (
            f"for word in {loop_body}; do clear; {cmd_variant} \"$word\"; sleep 1; done"
        )
        requires = [tool]
        scenarios.append(
            Scenario(
                command=command,
                description=(
                    "Cycles through banner commands to render large ASCII headings for several words."
                ),
                requires=requires,
                post_sleep_ms=5000,
                level=1,
                events=15,
                visual_complexity=55,
            )
        )
    return scenarios


def _table_scenarios(count: int, rng: random.Random) -> List[Scenario]:
    scenarios: List[Scenario] = []
    for _ in range(count):
        rows = rng.randint(5, 12)
        cols = rng.randint(3, 5)
        seq_cmd = f"seq 1 {rows * cols}"
        dash_flags = " ".join("-" for _ in range(cols))
        command = (
            f"{seq_cmd} | paste -d',' {dash_flags} | column -t -s',' | tee metrics_{rows}x{cols}.txt"
        )
        scenarios.append(
            Scenario(
                command=command,
                description=(
                    "Generates synthetic metrics, aligns them into a table, and archives the output."),
                requires=["seq", "paste", "column", "tee"],
                post_sleep_ms=2000,
                level=2,
                events=12,
                visual_complexity=40,
            )
        )
    return scenarios


def _animation_scenarios(count: int, rng: random.Random) -> List[Scenario]:
    templates = [
        ("timeout {dur}s cmatrix -u {speed} -C {color}", ["cmatrix"], 6000),
        ("timeout {dur}s yes {symbol}", ["yes"], 5000),
        (
            "python - <<'PY'\nimport time\nfor i in range({loops}):\n"
            "    print(f'Frame {{i:02d}} ::' + '>' * (i % 20))\n    time.sleep({sleep})\nPY",
            ["python"],
            4000,
        ),
        (
            'for angle in $(seq 0 30 330); do printf "\\rAngle: %03d" "$angle"; sleep 0.4; done',
            ["bash"],
            4000,
        ),
    ]
    colors = ["green", "magenta", "cyan", "yellow"]
    symbols = ['"⚙"', '"*"', '"#"', '"•"']
    scenarios: List[Scenario] = []
    for _ in range(count):
        template, requires, base_sleep = rng.choice(templates)
        if "cmatrix" in template:
            command = template.format(
                dur=rng.randint(4, 7),
                speed=rng.randint(5, 12),
                color=rng.choice(colors),
            )
        elif "yes" in template:
            command = template.format(
                dur=rng.randint(4, 7),
                symbol=rng.choice(symbols),
            )
        elif "python" in template:
            command = template.format(
                loops=rng.randint(10, 18),
                sleep=rng.choice([0.1, 0.2, 0.25]),
            )
        else:
            command = template
        scenarios.append(
            Scenario(
                command=command,
                description="Produces a looping terminal animation to highlight rhythmic changes.",
                requires=requires,
                post_sleep_ms=base_sleep,
                level=2,
                events=14,
                visual_complexity=52,
            )
        )
    return scenarios


def _write_tapes(
    scenarios: Iterable[Scenario],
    allocator: TapeIdAllocator,
    output_dir: Path,
    rng: random.Random,
) -> List[Path]:
    ensure_output_dir(output_dir)
    created: List[Path] = []
    for scenario in scenarios:
        tape_id, output_name = allocator.next()
        body = _base_body(scenario.command, scenario.post_sleep_ms)
        metadata = TapeMetadata(
            tape_id=tape_id,
            instruction=scenario.description.replace('"', '\\"'),
            active_classes={"Basic": True},
            level=scenario.level,
            interactive=False,
            events=scenario.events,
            visual_complexity=scenario.visual_complexity,
            requires=scenario.requires,
            body_lines=body,
            output_name=output_name,
        )
        destination = output_dir / f"{tape_id}.tape"
        destination.write_text(render_tape(metadata), encoding="utf-8")
        created.append(destination)
    rng.shuffle(created)
    return created


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("engine/cli/vhs/generated/dynamic_patterns"),
        help="Directory for generated tapes",
    )
    parser.add_argument("--monitor-count", type=int, default=5000)
    parser.add_argument("--sequence-count", type=int, default=5000)
    parser.add_argument("--countdown-count", type=int, default=5000)
    parser.add_argument("--banner-count", type=int, default=5000)
    parser.add_argument("--table-count", type=int, default=5000)
    parser.add_argument("--animation-count", type=int, default=5000)
    parser.add_argument("--seed", type=int, default=2025)
    parser.add_argument("--id-prefix", default="sft")
    parser.add_argument(
        "--start-index",
        type=int,
        default=DEFAULT_START_INDEX,
        help="Starting numeric index for tape IDs",
    )
    parser.add_argument(
        "--id-width",
        type=int,
        default=DEFAULT_ID_WIDTH,
        help="Zero padding width for IDs",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rng = random.Random(args.seed)

    total_requested = (
        args.monitor_count
        + args.sequence_count
        + args.countdown_count
        + args.banner_count
        + args.table_count
        + args.animation_count
    )
    print(f"Generating {total_requested:,} tapes...")

    allocator = TapeIdAllocator(
        prefix=args.id_prefix,
        start_index=args.start_index,
        width=args.id_width,
    )

    scenarios: List[Scenario] = []
    scenarios.extend(_monitoring_scenarios(args.monitor_count, rng))
    scenarios.extend(_sequence_scenarios(args.sequence_count, rng))
    scenarios.extend(_countdown_scenarios(args.countdown_count, rng))
    scenarios.extend(_banner_scenarios(args.banner_count, rng))
    scenarios.extend(_table_scenarios(args.table_count, rng))
    scenarios.extend(_animation_scenarios(args.animation_count, rng))

    rng.shuffle(scenarios)

    created = _write_tapes(scenarios, allocator, args.output_dir, rng)
    print(f"Created {len(created)} tapes")
    print(f"Next available index: {allocator.next_index}")


if __name__ == "__main__":
    main()
