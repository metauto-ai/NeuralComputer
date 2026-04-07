#!/usr/bin/env python3
"""Generate basic-shell VHS tapes with consistent metadata blocks.

The generator focuses on beginner-friendly commands (pwd, whoami, date, etc.) so
that the resulting tapes can bias datasets towards the `Basic` class. Each tape
includes the canonical VHS documentation header, theme settings, and a short
sequence of typed commands.

Example:
    python engine/cli/vhs/generators/basic.py \
        --count 1000 --output-dir engine/cli/vhs/generated/basic_commands
"""

from __future__ import annotations

import argparse
import math
import random
import shlex
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

from _common import (
    DEFAULT_ID_WIDTH,
    DEFAULT_START_INDEX,
    TapeIdAllocator,
    TapeMetadata,
    ensure_output_dir,
    render_tape,
)


@dataclass(frozen=True)
class CommandSpec:
    text: str
    description: str


def default_command_specs() -> list[CommandSpec]:
    commands: list[CommandSpec] = []
    static_pairs: Sequence[tuple[str, str]] = (
        ("pwd", "print the current working directory"),
        ("whoami", "show the active user"),
        ("date", "display the current date and time"),
        ("date +%Y-%m-%d", "show the date in ISO format"),
        ("date +%H:%M:%S", "report the current clock time"),
        ("date +%A", "print the day of the week"),
        ("date +%V", "show the ISO week number"),
        ("uname -a", "summarise kernel and system details"),
        ("uname -r", "show the kernel release"),
        ("uname -s", "identify the operating system"),
        ("uptime", "summarise how long the system has been running"),
        ("hostname", "output the machine hostname"),
        ("cal", "print the current month's calendar"),
        ("echo Current directory: $PWD", "label the working directory"),
        ("echo User: $USER", "label the active user"),
        ("echo Shell: $SHELL", "show the shell executable path"),
        ("echo Home: $HOME", "report the home directory"),
        ("echo PATH: $PATH", "echo the PATH variable"),
        ("echo Bash version: $BASH_VERSION", "report the bash version"),
        ("echo Shell PID: $$", "display the current shell PID"),
        ("echo Random number: $RANDOM", "emit a random number"),
        ("echo Last status: $?", "print the exit status of the last command"),
        ("echo Locale: $LANG", "display the LANG setting"),
        ("echo Editor: $EDITOR", "show the EDITOR preference"),
        ("echo History size: $HISTSIZE", "report the history size"),
        ("echo LC_ALL: $LC_ALL", "show the LC_ALL setting"),
        ("echo Login shell: $0", "reveal the current shell name"),
        ("echo Neural Computer basic sequence", "print a descriptive banner"),
        ("echo Learning shell basics", "state the goal of the demo"),
        ("echo Hello from the training set", "emit a friendly message"),
        ("echo Basic command practice", "highlight the learning context"),
        ("id", "summarise the current identity"),
        ("id -u", "display the numeric user ID"),
        ("id -g", "display the numeric group ID"),
        ("who", "list logged-in users"),
        ("groups", "list group memberships"),
        ("type pwd", "show how the shell resolves pwd"),
        ("type echo", "show how the shell resolves echo"),
        ("help cd", "open bash help for cd"),
        ("help alias", "open bash help for alias"),
        ("printenv", "dump all environment variables"),
        ("printenv SHELL", "print the shell variable"),
        ("printenv PATH", "print the PATH environment variable"),
        ("printenv HOME", "print the home directory"),
        ("env | head -n 5", "preview leading environment entries"),
        ("true", "run the no-op builtin"),
        ("false", "demonstrate the false builtin"),
    )
    for text, description in static_pairs:
        commands.append(CommandSpec(text=text, description=description))
    return commands


def escape_for_instruction(text: str) -> str:
    return text.replace("\\", "\\\\").replace('"', '\\"')


def escape_for_type(text: str) -> str:
    return text.replace("\\", "\\\\").replace('"', '\\"')


def build_instruction(commands: Sequence[CommandSpec]) -> str:
    fragments = [f"runs `{spec.text}` to {spec.description}" for spec in commands]
    if len(fragments) == 1:
        core = fragments[0]
    elif len(fragments) == 2:
        core = " and ".join(fragments)
    else:
        core = ", ".join(fragments[:-1]) + f", then {fragments[-1]}"
    return (
        "The demonstration "
        + core
        + ", keeping the focus on basic shell behaviour before hiding the prompt."
    )


def events_for_length(length: int) -> int:
    return 3 * length + 3


def visual_complexity(length: int) -> int:
    return max(8, 10 + length * 6)


SHELL_BUILTINS = {
    ".",
    ":",
    "alias",
    "bg",
    "bind",
    "break",
    "builtin",
    "cd",
    "command",
    "compgen",
    "complete",
    "compopt",
    "continue",
    "declare",
    "dirs",
    "disown",
    "echo",
    "enable",
    "eval",
    "exec",
    "exit",
    "export",
    "false",
    "fc",
    "fg",
    "getopts",
    "hash",
    "help",
    "history",
    "jobs",
    "kill",
    "let",
    "local",
    "logout",
    "mapfile",
    "popd",
    "printf",
    "pushd",
    "pwd",
    "read",
    "readarray",
    "return",
    "set",
    "shift",
    "shopt",
    "source",
    "suspend",
    "test",
    "times",
    "trap",
    "true",
    "type",
    "typeset",
    "ulimit",
    "umask",
    "unalias",
    "unset",
    "wait",
}


def extract_requires(commands: Sequence[CommandSpec]) -> list[str]:
    seen = {"bash"}
    ordered = ["bash"]
    for spec in commands:
        for segment in spec.text.split("|"):
            try:
                parts = shlex.split(segment)
            except ValueError:
                continue
            if not parts:
                continue
            token = parts[0]
            if token in SHELL_BUILTINS or token in seen:
                continue
            ordered.append(token)
            seen.add(token)
    return ordered


def build_tape(
    tape_id: str,
    commands: Sequence[CommandSpec],
    output_name: str | None = None,
) -> str:
    instruction = escape_for_instruction(build_instruction(commands))
    events = events_for_length(len(commands))
    complexity = visual_complexity(len(commands))
    requires = extract_requires(commands)

    body: list[str] = ["Sleep 180ms"]
    for spec in commands:
        escaped = escape_for_type(spec.text)
        body.append(f'Type "{escaped}"')
        body.append("Sleep 120ms")
        body.append("Enter")
        body.append("Sleep 400ms")
    body.append("Sleep 400ms")
    body.append("Hide")

    metadata = TapeMetadata(
        tape_id=tape_id,
        instruction=instruction,
        active_classes={"Basic": True},
        level=1,
        interactive=False,
        events=events,
        visual_complexity=complexity,
        requires=requires,
        body_lines=body,
        output_name=output_name,
    )
    return render_tape(metadata)


def generate_sequences(
    specs: Sequence[CommandSpec],
    count: int,
    min_length: int,
    max_length: int,
    rng: random.Random,
) -> list[list[CommandSpec]]:
    if min_length < 1 or max_length < min_length:
        raise ValueError("Invalid sequence length bounds")
    if len(specs) < max_length:
        raise ValueError("Not enough command specs to sample without repetition")

    max_unique = sum(math.comb(len(specs), r) for r in range(min_length, max_length + 1))
    if count > max_unique:
        raise ValueError(
            f"Requested {count} tapes but only {max_unique} unique sequences available"
        )

    sequences: list[list[CommandSpec]] = []
    seen: set[tuple[int, ...]] = set()
    attempts = 0
    max_attempts = count * 20

    while len(sequences) < count:
        attempts += 1
        if attempts > max_attempts:
            raise RuntimeError("Exceeded attempt budget while building unique sequences")
        length = rng.randint(min_length, max_length)
        chosen = rng.sample(range(len(specs)), length)
        key = tuple(sorted(chosen)) + (length,)
        if key in seen:
            continue
        seen.add(key)
        sequences.append([specs[index] for index in chosen])

    return sequences


def write_tapes(
    output_dir: Path,
    sequences: Sequence[Sequence[CommandSpec]],
    allocator: TapeIdAllocator,
) -> list[Path]:
    ensure_output_dir(output_dir)
    created: list[Path] = []
    for commands in sequences:
        tape_id, output_name = allocator.next()
        destination = output_dir / f"{tape_id}.tape"
        destination.write_text(
            build_tape(tape_id, commands, output_name=output_name),
            encoding="utf-8",
        )
        created.append(destination)
    return created


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, default=1000, help="How many tapes to generate")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("engine/cli/vhs/generated/basic_commands"),
        help="Directory for the generated tapes",
    )
    parser.add_argument("--min-length", type=int, default=1, help="Minimum commands per tape")
    parser.add_argument("--max-length", type=int, default=3, help="Maximum commands per tape")
    parser.add_argument("--seed", type=int, default=2024, help="Random seed for reproducibility")
    parser.add_argument("--prefix", default="sft", help="ID prefix for generated tapes")
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
    if args.count <= 0:
        raise SystemExit("--count must be positive")

    rng = random.Random(args.seed)
    specs = default_command_specs()
    sequences = generate_sequences(
        specs=specs,
        count=args.count,
        min_length=args.min_length,
        max_length=args.max_length,
        rng=rng,
    )
    allocator = TapeIdAllocator(
        prefix=args.prefix,
        start_index=args.start_index,
        width=args.id_width,
    )
    created_paths = write_tapes(
        output_dir=args.output_dir,
        sequences=sequences,
        allocator=allocator,
    )
    print("Generated tapes:")
    for path in created_paths:
        print(f" - {path}")

    print(f"Next available index: {allocator.next_index}")


if __name__ == "__main__":
    main()
