#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path


def iter_tapes(tapes_dir: Path) -> list[Path]:
    return sorted([p for p in tapes_dir.rglob("*.tape") if p.is_file()])


def build_line(
    *,
    tape_path: Path,
    tape_id: str,
    rel_path: str,
    runtime_mode: str,
    output_ext: str,
) -> str:
    payload = {
        "path": rel_path,
        "output": f"{tape_id}.{output_ext}",
        "runtime_mode": runtime_mode,
    }
    return json.dumps({tape_id: payload}, ensure_ascii=False)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a run_manifest-compatible JSONL from .tape files.")
    parser.add_argument(
        "--tapes-dir",
        type=Path,
        required=True,
        help="Directory containing .tape files (scanned recursively).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Manifest JSONL path (default: <tapes-dir>/manifest.jsonl).",
    )
    parser.add_argument(
        "--runtime-mode",
        choices=["shared", "isolated"],
        default="shared",
        help="Default runtime_mode for each entry.",
    )
    parser.add_argument(
        "--output-ext",
        default="mp4",
        help="Video extension to request in output field (default: mp4).",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    tapes_dir = args.tapes_dir.expanduser().resolve()
    if not tapes_dir.exists():
        raise SystemExit(f"tapes-dir not found: {tapes_dir}")

    manifest_path = (args.output or (tapes_dir / "manifest.jsonl")).expanduser().resolve()
    manifest_path.parent.mkdir(parents=True, exist_ok=True)

    tape_paths = iter_tapes(tapes_dir)
    if not tape_paths:
        raise SystemExit(f"No .tape files found under: {tapes_dir}")

    lines: list[str] = []
    for tape_path in tape_paths:
        tape_id = tape_path.stem
        # Keep manifest paths relative to the manifest location.
        rel_path = os.path.relpath(tape_path, manifest_path.parent)
        lines.append(
            build_line(
                tape_path=tape_path,
                tape_id=tape_id,
                rel_path=rel_path,
                runtime_mode=args.runtime_mode,
                output_ext=args.output_ext,
            )
        )

    manifest_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote manifest: {manifest_path} ({len(lines)} entries)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
