#!/usr/bin/env python3
"""Generate v7 filesystem-focused VHS tapes with explicit file operations."""

from __future__ import annotations

import argparse
import random
from dataclasses import dataclass
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

WORKSPACE_VARS = ["workspace", "tmpdir", "sandbox", "stage"]
WORKSPACE_PREFIXES = ["v7fs", "v7files", "vhs_stage", "neural_fs"]
BASE_DIRS = ["reports", "notes", "logs", "workspace", "project", "records", "datasets"]
SUBDIR_POOL = [
    "daily",
    "weekly",
    "monthly",
    "incoming",
    "processed",
    "archive",
    "drafts",
    "metrics",
    "2024",
    "2025",
    "snapshots",
]
EXTRA_DIRS = [
    "scratch",
    "attachments",
    "exports",
    "summaries",
]
FILE_PREFIXES = [
    "summary",
    "report",
    "notes",
    "log",
    "status",
    "metrics",
    "todo",
    "outline",
    "review",
    "checkpoint",
]
FILE_EXTENSIONS = ["txt", "md", "log", "csv"]
CONTENT_LINES = [
    "Neural Computer dataset v7",
    "Emphasise filesystem practice",
    "Tracking iterative changes",
    "Use ls around deletions",
    "Printed content for review",
    "Cleanup after inspection",
    "Temporary workspace active",
    "Sample progress markers",
    "Automation keeps pace",
    "Status: ready to archive",
]
LIST_COMMANDS = ["ls", "ls -1", "ls -lh", "ls -R"]
TAILING_COMMANDS = ["tail -n 5", "tail -n 3", "head -n 2", "head -n 3"]
BASE_REQUIRES = {"bash", "mktemp", "mkdir", "ls", "printf", "cat", "rm"}


@dataclass
class Workflow:
    commands: List[str]
    instruction: str
    requires: Sequence[str]


def escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace('"', '\\"')


def format_list(items: Sequence[str]) -> str:
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return ", ".join(items[:-1]) + f", and {items[-1]}"


def parent_path(path: str) -> str:
    parts = path.split("/")
    if len(parts) <= 1:
        return "."
    return "/".join(parts[:-1])


def build_body(commands: Sequence[str]) -> List[str]:
    body: List[str] = ["Sleep 180ms"]
    for command in commands:
        escaped = escape(command)
        body.append(f'Type "{escaped}"')
        body.append("Sleep 120ms")
        body.append("Enter")
        body.append("Sleep 400ms")
    body.append("Sleep 400ms")
    return body


def build_workflow(rng: random.Random) -> Workflow:
    workspace_var = rng.choice(WORKSPACE_VARS)
    workspace_prefix = rng.choice(WORKSPACE_PREFIXES)
    commands: List[str] = []
    commands.append(f"{workspace_var}=$(mktemp -d /tmp/{workspace_prefix}_XXXXXX)")
    commands.append(f'cd "${workspace_var}"')

    base_dir = rng.choice(BASE_DIRS)
    subdir_count = rng.randint(2, 3)
    subdirs = rng.sample(SUBDIR_POOL, subdir_count)

    if rng.random() < 0.5:
        mkdir_target = f"{base_dir}/{{{','.join(subdirs)}}}"
        commands.append(f"mkdir -p {mkdir_target}")
        created_dirs = [f"{base_dir}/{sub}" for sub in subdirs]
    else:
        created_dirs = [f"{base_dir}/{sub}" for sub in subdirs]
        commands.append("mkdir -p " + " ".join(created_dirs))

    if rng.random() < 0.3:
        extra_dir = rng.choice(EXTRA_DIRS)
        commands.append(f"mkdir -p {extra_dir}")
        created_dirs.append(extra_dir)

    list_cmd = rng.choice(LIST_COMMANDS)
    commands.append(f"{list_cmd} {base_dir}")

    target_dir = rng.choice(created_dirs)
    file_base = rng.choice(FILE_PREFIXES)
    extension = rng.choice(FILE_EXTENSIONS)
    file_name = f"{file_base}.{extension}"
    file_path = f"{target_dir}/{file_name}"

    line_count = rng.randint(2, 3)
    lines = rng.sample(CONTENT_LINES, line_count)
    printf_payload = " ".join(f'"{line}"' for line in lines)
    commands.append(f'printf "%s\\n" {printf_payload} > {file_path}')
    commands.append(f"cat {file_path}")
    commands.append(f"ls {target_dir}")

    requires = set(BASE_REQUIRES)

    if rng.random() < 0.5:
        extra_line = rng.choice(CONTENT_LINES)
        commands.append(f'printf "%s\\n" "{extra_line}" >> {file_path}')
        follow_cmd = rng.choice(TAILING_COMMANDS)
        commands.append(f"{follow_cmd} {file_path}")
        requires.add(follow_cmd.split()[0])

    action_choice = rng.random()
    removal_target = file_path
    removal_scope = target_dir
    action_description: str

    if action_choice < 0.33:
        backup_name = f"{file_base}_backup.{extension}"
        backup_path = f"{target_dir}/{backup_name}"
        commands.append(f"cp {file_path} {backup_path}")
        commands.append(f"ls {target_dir}")
        removal_target = backup_path
        requires.add("cp")
        action_description = f"copies the file to {backup_name} and removes the backup"
    elif action_choice < 0.66:
        other_dirs = [d for d in created_dirs if d != target_dir]
        if not other_dirs:
            archive_dir = f"{base_dir}/archive"
            commands.append(f"mkdir -p {archive_dir}")
            created_dirs.append(archive_dir)
            other_dirs = [archive_dir]
        dest_dir = rng.choice(other_dirs)
        archive_name = f"{file_base}_archive.{extension}"
        archive_path = f"{dest_dir}/{archive_name}"
        commands.append(f"mv {file_path} {archive_path}")
        commands.append(f"ls {dest_dir}")
        commands.append(f"cat {archive_path}")
        removal_target = archive_path
        removal_scope = dest_dir
        requires.add("mv")
        action_description = (
            f"moves the file into {dest_dir} as {archive_name} before deleting the archive"
        )
    else:
        drafts_dir = f"{base_dir}/drafts"
        if drafts_dir not in created_dirs:
            commands.append(f"mkdir -p {drafts_dir}")
            created_dirs.append(drafts_dir)
        copy_name = f"{file_base}_notes.{extension}"
        copy_path = f"{drafts_dir}/{copy_name}"
        commands.append(f"cp {file_path} {copy_path}")
        commands.append(f"ls {drafts_dir}")
        removal_target = copy_path
        removal_scope = drafts_dir
        requires.add("cp")
        action_description = (
            f"copies the file into {drafts_dir} for notes and then deletes the copy"
        )

    commands.append(f"rm {removal_target}")
    commands.append(f"ls {removal_scope}")

    commands.append("cd /tmp")
    commands.append(f'rm -rf "${workspace_var}"')

    instruction = (
        "Creates a mktemp workspace, populates "
        f"{base_dir} with {format_list(subdirs)} directories, writes {file_name}, "
        "previews the content, "
        f"{action_description}, lists the directory before and after cleanup, "
        "and removes the temporary workspace."
    )

    requires_list: list[str] = []
    return Workflow(commands=commands, instruction=instruction, requires=requires_list)


def generate_workflows(count: int, rng: random.Random) -> List[Workflow]:
    workflows: List[Workflow] = []
    seen: set[tuple[str, ...]] = set()
    attempts = 0
    max_attempts = count * 10

    while len(workflows) < count:
        attempts += 1
        if attempts > max_attempts:
            raise RuntimeError("Exceeded attempt budget while building unique workflows")
        workflow = build_workflow(rng)
        key = tuple(workflow.commands)
        if key in seen:
            continue
        seen.add(key)
        workflows.append(workflow)
    return workflows


def write_tapes(
    workflows: Sequence[Workflow],
    allocator: TapeIdAllocator,
    output_dir: Path,
) -> List[Path]:
    ensure_output_dir(output_dir)
    created: List[Path] = []
    for workflow in workflows:
        tape_id, output_name = allocator.next()
        metadata = TapeMetadata(
            tape_id=tape_id,
            instruction=escape(workflow.instruction),
            active_classes={"Basic": True, "Files": True},
            level=2,
            interactive=False,
            events=len(workflow.commands) * 3 + 4,
            visual_complexity=50 + len(workflow.commands) * 5,
            requires=workflow.requires,
            body_lines=build_body(workflow.commands) + ["Hide"],
            output_name=output_name,
        )
        destination = output_dir / f"{tape_id}.tape"
        destination.write_text(render_tape(metadata), encoding="utf-8")
        created.append(destination)
    return created


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, default=20000)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("engine/cli/vhs/generated/files_v7"),
    )
    parser.add_argument("--seed", type=int, default=2031)
    parser.add_argument("--id-prefix", default="sft")
    parser.add_argument(
        "--start-index",
        type=int,
        default=120000,
    )
    parser.add_argument(
        "--id-width",
        type=int,
        default=DEFAULT_ID_WIDTH,
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.count <= 0:
        raise SystemExit("--count must be positive")

    rng = random.Random(args.seed)
    workflows = generate_workflows(args.count, rng)
    allocator = TapeIdAllocator(
        prefix=args.id_prefix,
        start_index=args.start_index,
        width=args.id_width,
    )
    created = write_tapes(
        workflows=workflows,
        allocator=allocator,
        output_dir=args.output_dir,
    )
    print(f"Generated {len(created)} tapes")
    print(f"Next available index: {allocator.next_index}")


if __name__ == "__main__":
    main()
