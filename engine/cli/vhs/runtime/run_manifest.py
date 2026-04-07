#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import os
import re
import shlex
import shutil
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

DockerPath = str

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = next((p for p in [SCRIPT_DIR, *SCRIPT_DIR.parents] if (p / "main.py").is_file()), None)
if REPO_ROOT is None:
    raise SystemExit("Could not locate repo root (expected to find main.py in parent directories).")

VHS_ROOT = REPO_ROOT / "engine" / "cli" / "vhs"
DEFAULT_MANIFEST = VHS_ROOT / "manifest.jsonl"
DEFAULT_OUTPUTS = VHS_ROOT / "outputs"


def resolve_docker_bin() -> str:
    docker_bin = shutil.which("docker")
    if docker_bin:
        return docker_bin

    docker_desktop_bin = Path("/Applications/Docker.app/Contents/Resources/bin/docker")
    if docker_desktop_bin.is_file():
        return str(docker_desktop_bin)

    raise FileNotFoundError("docker")


DOCKER_BIN = resolve_docker_bin()

@dataclass
class TapeEntry:
    tape_id: str
    rel_path: str
    output_name: str
    runtime_mode: str
    manifest_line: int
    host_path: Path | None = None
    container_rel_path: str | None = None

    def tape_path_container(self) -> str:
        rel_path = self.container_rel_path or self.rel_path
        return f"/tapes/{rel_path}"


def determine_tapes_root(entries: Iterable[TapeEntry]) -> Path:
    host_paths = [entry.host_path for entry in entries if entry.host_path is not None]
    if not host_paths:
        raise ValueError("No host paths available to determine tapes root")
    return Path(os.path.commonpath([str(path.parent) for path in host_paths]))


def load_manifest(manifest_path: Path) -> list[TapeEntry]:
    entries: list[TapeEntry] = []
    with manifest_path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            data = json.loads(line)
            if len(data) != 1:
                raise ValueError(f"Manifest line {line_no} must contain a single root key")
            tape_id, payload = next(iter(data.items()))
            rel_path = payload["path"]
            output_name = payload.get("output") or f"{tape_id}.mp4"
            runtime_mode = payload.get("runtime_mode", "shared")
            entries.append(
                TapeEntry(
                    tape_id=tape_id,
                    rel_path=rel_path,
                    output_name=output_name,
                    runtime_mode=runtime_mode,
                    manifest_line=line_no,
                )
            )
    return entries


def ensure_dirs(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def run_docker(cmd: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, text=True, check=check)


def run_shared(
    entries: Iterable[TapeEntry],
    *,
    image: str,
    manifest_root: Path,
    outputs_dir: Path,
    include_legacy: bool,
    max_parallel: int,
    platform: str | None,
    tracker: "ProgressTracker",
) -> bool:
    entries = list(entries)
    if not entries:
        return True

    BASE_CHUNK_SIZE = 200
    MAX_SHARED_CONCURRENCY = 200
    desired_workers = max(1, min(max_parallel, len(entries)))
    if desired_workers > 1:
        max_chunk_for_concurrency = max(1, MAX_SHARED_CONCURRENCY // desired_workers)
        chunk_size = max(
            1,
            min(
                BASE_CHUNK_SIZE,
                max_chunk_for_concurrency,
                math.ceil(len(entries) / desired_workers),
            ),
        )
    else:
        chunk_size = min(BASE_CHUNK_SIZE, len(entries)) or 1

    chunks: list[list[TapeEntry]] = [
        entries[i : i + chunk_size] for i in range(0, len(entries), chunk_size)
    ]

    if not chunks:
        return True

    allowed_workers = max(1, MAX_SHARED_CONCURRENCY // chunk_size)
    num_workers = max(1, min(max_parallel, len(chunks), desired_workers, allowed_workers))
    if num_workers > 1:
        print(
            f"[INFO] Running shared entries with up to {num_workers} parallel workers",
            flush=True,
        )

    def run_shared_batch(batch_entries: list[TapeEntry], label: str) -> bool:
        shell_lines = [
            "set -euo pipefail",
            "TAPE_TIMEOUT=60",
            "status=0",
            f'printf "=== {label} ({len(batch_entries)} tapes)\\n"',
            "process_tape() {",
            "  local tape=$1",
            "  local output=$2",
            "  local name=$3",
            "  if [ -f \"$VHS_OUTPUT_DIR/$output\" ]; then",
            "    printf '>>> %s (skip existing)\\n' \"$name\"",
            "    return",
            "  fi",
            "  printf '>>> running %s\\n' \"$name\"",
            "  if timeout \"${TAPE_TIMEOUT}s\" vhs -q -o \"$VHS_OUTPUT_DIR/$output\" \"$tape\"; then",
            "    printf '    OK  -> %s/%s\\n' \"$VHS_OUTPUT_DIR\" \"$output\"",
            "  else",
            "    printf '    FAIL -> %s\\n' \"$tape\" 1>&2",
            "    status=1",
            "  fi",
            "}",
        ]

        for entry in batch_entries:
            shell_lines.append(
                f"process_tape {shlex.quote(entry.tape_path_container())} "
                f"{shlex.quote(entry.output_name)} {shlex.quote(entry.tape_id)}"
            )

        shell_lines.append("exit $status")
        script = "\n".join(shell_lines)

        cmd: list[str] = [DOCKER_BIN, "run"]
        if platform:
            cmd += ["--platform", platform]
        cmd += [
            "--rm",
            "-v",
            f"{manifest_root}:/tapes:ro",
            "-v",
            f"{outputs_dir}:/workspace/output",
            "-e",
            "VHS_OUTPUT_DIR=/workspace/output",
        ]
        if not include_legacy:
            cmd += ["-e", "NC_INCLUDE_VHS_FIXTURES=0"]
        cmd += [image, "bash", "-lc", script]

        print(f"[INFO] Starting shared batch {label}", flush=True)
        result = run_docker(cmd, check=False)
        if result.returncode != 0:
            print(
                f"[WARN] Shared batch {label} exited with non-zero status",
                flush=True,
            )
            return False
        return True

    if len(chunks) == 1:
        success = run_shared_batch(chunks[0], "shared-worker-1")
        tracker.advance(len(chunks[0]))
        return success

    ok = True
    worker_count = min(num_workers, len(chunks))
    with ThreadPoolExecutor(max_workers=worker_count) as pool:
        futures = {
            pool.submit(run_shared_batch, chunk, f"shared-worker-{idx + 1}"): tuple(chunk)
            for idx, chunk in enumerate(chunks)
        }
        for future in as_completed(futures):
            batch_entries = futures[future]
            if not future.result():
                ok = False
            tracker.advance(len(batch_entries))
    return ok


def run_isolated(
    entries: Iterable[TapeEntry],
    *,
    image: str,
    manifest_root: Path,
    outputs_dir: Path,
    include_legacy: bool,
    max_parallel: int,
    platform: str | None,
    tracker: "ProgressTracker",
) -> bool:
    entries = list(entries)
    if not entries:
        return True

    def process_entry(entry: TapeEntry) -> bool:
        host_output = outputs_dir / entry.output_name
        if host_output.exists():
            print(f">>> {entry.tape_id} (skip existing)")
            return True
        print(f">>> running {entry.tape_id} (isolated)")
        base_cmd: list[str] = [DOCKER_BIN, "create"]
        if platform:
            base_cmd += ["--platform", platform]
        base_cmd += [
            "-v",
            f"{manifest_root}:/tapes:ro",
            "-v",
            f"{outputs_dir}:/workspace/output",
            "-e",
            "VHS_OUTPUT_DIR=/workspace/output",
        ]
        if not include_legacy:
            base_cmd += ["-e", "NC_INCLUDE_VHS_FIXTURES=0"]
        cmd_str = "timeout 60s vhs -q -o {output} {tape}".format(
            output=shlex.quote(f"/workspace/output/{entry.output_name}"),
            tape=shlex.quote(entry.tape_path_container()),
        )
        base_cmd += [image, "bash", "-lc", cmd_str]

        cid: str | None = None
        try:
            cid = subprocess.check_output(base_cmd, text=True).strip()
        except subprocess.CalledProcessError as exc:
            print(
                f"    FAIL -> {entry.rel_path} (docker create error: {exc})",
                flush=True,
            )
            return False

        try:
            result = run_docker([DOCKER_BIN, "start", "-a", cid], check=False)
            if result.returncode != 0:
                print(f"    FAIL -> {entry.rel_path}", flush=True)
                return False
            if host_output.exists():
                print(f"    OK  -> {host_output}")
                return True
            print(f"    WARN no output produced for {entry.rel_path}")
            return False
        finally:
            if cid:
                run_docker([DOCKER_BIN, "rm", "-f", cid], check=False)

    num_workers = max(1, min(max_parallel, len(entries)))
    if num_workers > 1:
        print(
            f"[INFO] Running isolated entries with up to {num_workers} parallel workers",
            flush=True,
        )

    if num_workers == 1:
        ok = True
        for entry in entries:
            if not process_entry(entry):
                ok = False
            tracker.advance(1)
        return ok

    ok = True
    with ThreadPoolExecutor(max_workers=num_workers) as pool:
        futures = {pool.submit(process_entry, entry): entry for entry in entries}
        for future in as_completed(futures):
            if not future.result():
                ok = False
            tracker.advance(1)
    return ok


class ProgressTracker:
    def __init__(self, total: int) -> None:
        self.total = total
        self.completed = 0
        self.start_time = time.time()

    def advance(self, count: int) -> None:
        if count <= 0 or self.total == 0:
            return
        self.completed += count
        elapsed = time.time() - self.start_time
        remaining = self.total - self.completed
        if self.completed == 0:
            return
        rate = elapsed / self.completed
        eta = remaining * rate
        print(
            f"[ETA] {self.completed}/{self.total} done | elapsed {elapsed:.1f}s | remaining ~{eta:.1f}s",
            flush=True,
        )


def determine_parallelism(requested: int | None) -> int:
    if requested is not None:
        if requested < 1:
            raise ValueError("--max-parallel must be at least 1")
        return requested

    cpu_count = os.cpu_count() or 1
    try:
        import psutil  # type: ignore
    except ImportError:
        psutil = None  # type: ignore

    if psutil is not None:
        total_memory_gb = psutil.virtual_memory().total / (1024**3)
        reserve_gb = 4
        per_worker_gb = 2
        available_for_workers = max(total_memory_gb - reserve_gb, per_worker_gb)
        max_by_memory = max(1, int(available_for_workers // per_worker_gb))
    else:
        max_by_memory = cpu_count

    max_by_cpu = max(1, cpu_count - 1)
    return max(1, min(max_by_memory, max_by_cpu, 8))


def main() -> None:
    parser = argparse.ArgumentParser(description="Record VHS tapes from manifest")
    parser.add_argument(
        "manifest",
        default=str(DEFAULT_MANIFEST),
        nargs="?",
        help="Path to manifest JSONL",
    )
    parser.add_argument(
        "--image",
        default="neural-vhs",
        help="Docker image name (default: neural-vhs)",
    )
    parser.add_argument(
        "--outputs",
        default=str(DEFAULT_OUTPUTS),
        help="Directory to store mp4 outputs",
    )
    parser.add_argument(
        "--include-legacy-fixtures",
        action="store_true",
        help="Keep legacy /tmp/vhs_* fixtures (default)",
    )
    parser.add_argument(
        "--no-legacy-fixtures",
        dest="include_legacy_fixtures",
        action="store_false",
        help="Disable legacy /tmp/vhs_* fixture files",
    )
    parser.set_defaults(include_legacy_fixtures=True)
    parser.add_argument(
        "--max-parallel",
        type=int,
        default=None,
        help="Maximum number of Docker runs to execute concurrently (default: auto)",
    )
    parser.add_argument(
        "--reverse",
        action="store_true",
        help="Process manifest entries in reverse order",
    )
    parser.add_argument(
        "--platform",
        default="native",
        help=(
            "Docker platform value (e.g. linux/arm64). Use 'native' to omit the flag "
            "and rely on host defaults (default: native)."
        ),
    )

    args = parser.parse_args()
    manifest_path = Path(args.manifest).resolve()
    outputs_dir = Path(args.outputs).resolve()
    ensure_dirs(outputs_dir)

    entries = load_manifest(manifest_path)
    if args.reverse:
        entries.reverse()
    manifest_root = manifest_path.parent.resolve()

    platform_arg = args.platform.strip()
    platform_value = None if not platform_arg or platform_arg.lower() == "native" else platform_arg
    platform_label = platform_value or "native"

    parallel_workers = determine_parallelism(args.max_parallel)
    print(
        f"[INFO] Using up to {parallel_workers} parallel workers | docker platform: {platform_label}",
        flush=True,
    )

    shared_entries: list[TapeEntry] = []
    isolated_entries: list[TapeEntry] = []

    valid_entries: list[TapeEntry] = []
    for entry in entries:
        tape_abs = (manifest_root / entry.rel_path).resolve()
        if not tape_abs.exists():
            print(
                f"[WARN] Tape file missing ({entry.rel_path}) from manifest line {entry.manifest_line}",
                flush=True,
            )
            continue
        entry.host_path = tape_abs
        valid_entries.append(entry)

    if not valid_entries:
        raise SystemExit("No valid tape entries found in manifest")

    tapes_root = determine_tapes_root(valid_entries)
    for entry in valid_entries:
        assert entry.host_path is not None
        entry.container_rel_path = str(entry.host_path.relative_to(tapes_root))

    for entry in valid_entries:
        host_output = outputs_dir / entry.output_name
        mode = entry.runtime_mode
        became_shared = False
        if mode == "isolated":
            tape_text = entry.host_path.read_text(encoding="utf-8")
            if re.search(r"^Type \"python\"\s*$", tape_text, re.MULTILINE):
                mode = "shared"
                became_shared = True
        target_list = shared_entries if mode == "shared" else isolated_entries
        if host_output.exists():
            continue
        target_list.append(entry)
        if became_shared:
            print(f"[INFO] Promoted {entry.tape_id} to shared (plain python)")

    total_pending = len(shared_entries) + len(isolated_entries)
    tracker = ProgressTracker(total_pending)
    if total_pending:
        print(f"[INFO] Pending tapes: {total_pending}", flush=True)

    ok_shared = run_shared(
        shared_entries,
        image=args.image,
        manifest_root=tapes_root,
        outputs_dir=outputs_dir,
        include_legacy=args.include_legacy_fixtures,
        max_parallel=parallel_workers,
        platform=platform_value,
        tracker=tracker,
    )

    ok_isolated = run_isolated(
        isolated_entries,
        image=args.image,
        manifest_root=tapes_root,
        outputs_dir=outputs_dir,
        include_legacy=args.include_legacy_fixtures,
        max_parallel=parallel_workers,
        platform=platform_value,
        tracker=tracker,
    )

    if not (ok_shared and ok_isolated):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
