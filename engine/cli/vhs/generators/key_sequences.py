#!/usr/bin/env python3
"""Generate typing-focused VHS tapes (letters and terminal words)."""

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


def _escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace('"', '\\"')


def _build_body(sequence: Sequence[str], pause_ms: int) -> List[str]:
    body: List[str] = ["Sleep 300ms"]
    for char in sequence:
        escaped = _escape(char)
        body.append(f'Type "{escaped}"')
        body.append(f"Sleep {pause_ms}ms")
    body.append("Enter")
    body.append("Sleep 500ms")
    return body


def _events(length: int) -> int:
    return max(6, 2 * length + 4)


def _visual_complexity(length: int) -> int:
    return max(8, 5 + length * 2)


def _create_tape(
    tape_id: str,
    output_name: str,
    sequence: str,
    instruction_template: str,
    pause_ms: int,
) -> str:
    instruction = instruction_template.format(sequence=sequence, spaced=" ".join(sequence))
    metadata = TapeMetadata(
        tape_id=tape_id,
        instruction=_escape(instruction),
        active_classes={"Basic": True},
        level=1,
        interactive=False,
        events=_events(len(sequence)),
        visual_complexity=_visual_complexity(len(sequence)),
        requires=["bash"],
        body_lines=_build_body(sequence, pause_ms),
        output_name=output_name,
    )
    return render_tape(metadata)


def _write_batch(
    sequences: Iterable[str],
    output_dir: Path,
    allocator: TapeIdAllocator,
    instruction_template: str,
    pause_range: tuple[int, int],
) -> List[Path]:
    ensure_output_dir(output_dir)
    created: List[Path] = []
    for sequence in sequences:
        pause_ms = random.randint(*pause_range)
        tape_id, output_name = allocator.next()
        tape_text = _create_tape(tape_id, output_name, sequence, instruction_template, pause_ms)
        destination = output_dir / f"{tape_id}.tape"
        destination.write_text(tape_text + "\n", encoding="utf-8")
        created.append(destination)
    return created


def _random_letter_sequences(
    count: int,
    minimum: int,
    maximum: int,
    alphabet: str = "abcdefghijklmnopqrstuvwxyz",
) -> List[str]:
    return [
        "".join(random.choice(alphabet) for _ in range(random.randint(minimum, maximum)))
        for _ in range(count)
    ]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--letters-count", type=int, default=0, help="How many random letter tapes to create")
    parser.add_argument("--letters-min", type=int, default=2, help="Minimum length for letter sequences")
    parser.add_argument("--letters-max", type=int, default=10, help="Maximum length for letter sequences")
    parser.add_argument(
        "--letters-dir",
        type=Path,
        default=Path("engine/cli/vhs/generated/letters"),
        help="Output directory for letter tapes",
    )
    parser.add_argument(
        "--words",
        nargs="*",
        default=[],
        help="Terminal words to type (each becomes one tape)",
    )
    parser.add_argument(
        "--words-file",
        type=Path,
        help="Optional file with newline-separated sequences to type",
    )
    parser.add_argument(
        "--words-dir",
        type=Path,
        default=Path("engine/cli/vhs/generated/words"),
        help="Output directory for word tapes",
    )
    parser.add_argument(
        "--pause-range",
        default="140,260",
        help="Comma-separated min,max pause (ms) between keystrokes",
    )
    parser.add_argument("--seed", type=int, help="Random seed for reproducibility")
    parser.add_argument("--id-prefix", default="sft", help="Prefix for generated tape IDs")
    parser.add_argument(
        "--start-index",
        type=int,
        default=DEFAULT_START_INDEX,
        help="Starting numeric index for tape IDs (inclusive)",
    )
    parser.add_argument(
        "--id-width",
        type=int,
        default=DEFAULT_ID_WIDTH,
        help="Zero-padding width for the numeric portion of tape IDs",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.seed is not None:
        random.seed(args.seed)

    try:
        pause_min, pause_max = (int(part) for part in args.pause_range.split(","))
    except ValueError as exc:
        raise SystemExit(f"Invalid --pause-range '{args.pause_range}': {exc}") from exc

    if pause_min <= 0 or pause_max < pause_min:
        raise SystemExit("Pause range must be positive and min <= max")

    allocator = TapeIdAllocator(prefix=args.id_prefix, start_index=args.start_index, width=args.id_width)

    created_paths: List[Path] = []
    words: List[str] = list(args.words)
    if args.words_file:
        file_text = args.words_file.read_text(encoding="utf-8")
        words.extend([line.strip() for line in file_text.splitlines() if line.strip()])

    if args.letters_count > 0:
        sequences = _random_letter_sequences(args.letters_count, args.letters_min, args.letters_max)
        created_paths.extend(
            _write_batch(
                sequences=sequences,
                output_dir=args.letters_dir,
                allocator=allocator,
                instruction_template=(
                    "Types the lowercase letters '{sequence}' one key at a time with short pauses, "
                    "then sends them at the shell prompt."
                ),
                pause_range=(pause_min, pause_max),
            )
        )

    if words:
        created_paths.extend(
            _write_batch(
                sequences=words,
                output_dir=args.words_dir,
                allocator=allocator,
                instruction_template=(
                    "Types the terminal word '{sequence}' letter by letter with steady pauses so the video"
                    " stays aligned with the caption, then presses Enter."
                ),
                pause_range=(pause_min, pause_max),
            )
        )

    if not created_paths:
        raise SystemExit("Nothing to do: specify --letters-count and/or --words")

    print("Generated tapes:")
    for path in created_paths:
        print(f" - {path}")

    print(f"Next available index: {allocator.next_index}")


if __name__ == "__main__":
    main()
