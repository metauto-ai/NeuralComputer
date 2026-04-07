#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence


REPO_ROOT = Path(__file__).resolve().parents[2]
CAST_REPAIR_SCRIPT = REPO_ROOT / "cli" / "asciinema" / "tools" / "1_convert_cast_format.py"


class DependencyError(RuntimeError):
    pass


def require_binary(name: str) -> None:
    if shutil.which(name) is None:
        raise DependencyError(f"Missing dependency: {name}")


def run(cmd: Sequence[str]) -> None:
    env = None
    if cmd and Path(cmd[0]).name == "asciinema":
        # Avoid asciinema UTF-8 env parsing issues on localized paths.
        env = dict(os.environ)
        env.pop("_", None)
    subprocess.run(list(cmd), check=True, env=env)


def iter_files(paths: Sequence[Path], suffix: str) -> Iterable[tuple[Path, Path]]:
    """Yield (root, file_path) pairs for files ending with suffix under the given paths."""
    for input_path in paths:
        input_path = input_path.expanduser().resolve()
        if input_path.is_dir():
            for file_path in sorted(input_path.rglob(f"*{suffix}")):
                if file_path.is_file():
                    yield input_path, file_path
            continue
        if input_path.is_file():
            if input_path.name.endswith(suffix):
                yield input_path.parent, input_path
            continue
        raise FileNotFoundError(str(input_path))


def output_path_for(
    file_path: Path,
    *,
    input_root: Path,
    output_root: Path,
    new_suffix: str,
) -> Path:
    rel = file_path.relative_to(input_root)
    return (output_root / rel).with_suffix(new_suffix)


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


@dataclass(frozen=True)
class AggSettings:
    theme: str
    font_size: int
    fps_cap: int | None
    speed: float | None
    idle_time_limit: float | None

    def to_args(self) -> list[str]:
        args = ["--theme", self.theme, "--font-size", str(self.font_size)]
        if self.fps_cap is not None:
            args += ["--fps-cap", str(self.fps_cap)]
        if self.speed is not None:
            args += ["--speed", str(self.speed)]
        if self.idle_time_limit is not None:
            args += ["--idle-time-limit", str(self.idle_time_limit)]
        return args


def cast_to_gif_one(
    cast_path: Path,
    gif_path: Path,
    *,
    settings: AggSettings,
    repair_on_failure: bool,
    overwrite: bool,
) -> None:
    if gif_path.exists() and not overwrite:
        return

    ensure_parent(gif_path)

    def try_render(input_cast: Path) -> None:
        cmd = ["agg", *settings.to_args(), str(input_cast), str(gif_path)]
        run(cmd)
        if not gif_path.exists() or gif_path.stat().st_size == 0:
            raise RuntimeError(f"agg produced empty gif: {gif_path}")

    try:
        try_render(cast_path)
        return
    except Exception:
        if not repair_on_failure:
            raise
        if not CAST_REPAIR_SCRIPT.exists():
            raise

    with tempfile.TemporaryDirectory(prefix="ncdat_engine_cast_fix_") as tmp:
        fixed_cast = Path(tmp) / cast_path.name
        run([sys.executable, str(CAST_REPAIR_SCRIPT), str(cast_path), str(fixed_cast)])
        try_render(fixed_cast)


def gif_to_mp4_one(
    gif_path: Path,
    mp4_path: Path,
    *,
    overwrite: bool,
    ffmpeg_loglevel: str,
) -> None:
    if mp4_path.exists() and not overwrite:
        return

    ensure_parent(mp4_path)

    overwrite_flag = "-y" if overwrite else "-n"
    cmd = [
        "ffmpeg",
        overwrite_flag,
        "-loglevel",
        ffmpeg_loglevel,
        "-i",
        str(gif_path),
        "-movflags",
        "faststart",
        "-pix_fmt",
        "yuv420p",
        "-vf",
        "scale=trunc(iw/2)*2:trunc(ih/2)*2",
        str(mp4_path),
    ]
    run(cmd)
    if not mp4_path.exists() or mp4_path.stat().st_size == 0:
        raise RuntimeError(f"ffmpeg produced empty mp4: {mp4_path}")


def cmd_record(args: argparse.Namespace) -> None:
    require_binary("asciinema")

    output = Path(args.output).expanduser()
    output.parent.mkdir(parents=True, exist_ok=True)

    cmd: list[str] = ["asciinema", "rec"]
    if args.overwrite:
        cmd.append("--overwrite")
    if args.append:
        cmd.append("--append")
    if args.title:
        cmd += ["--title", args.title]
    if args.cols:
        cmd += ["--cols", str(args.cols)]
    if args.rows:
        cmd += ["--rows", str(args.rows)]
    if args.idle_time_limit is not None:
        cmd += ["--idle-time-limit", str(args.idle_time_limit)]
    for env_pair in args.env:
        cmd += ["--env", env_pair]
    if args.command:
        cmd += ["-c", args.command]
    cmd.append(str(output))

    run(cmd)


def cmd_cast_to_gif(args: argparse.Namespace) -> None:
    require_binary("agg")

    output_dir = Path(args.output_dir).expanduser().resolve()
    settings = AggSettings(
        theme=args.theme,
        font_size=args.font_size,
        fps_cap=args.fps_cap,
        speed=args.speed,
        idle_time_limit=args.idle_time_limit,
    )

    inputs = [Path(p) for p in args.inputs]
    work_items: list[tuple[Path, Path, Path]] = []
    for root, cast_path in iter_files(inputs, ".cast"):
        gif_path = output_path_for(
            cast_path,
            input_root=root,
            output_root=output_dir,
            new_suffix=".gif",
        )
        work_items.append((root, cast_path, gif_path))

    if not work_items:
        raise SystemExit("No .cast files found")

    errors: list[str] = []
    for _, cast_path, gif_path in work_items:
        try:
            cast_to_gif_one(
                cast_path,
                gif_path,
                settings=settings,
                repair_on_failure=not args.no_repair,
                overwrite=args.overwrite,
            )
            print(f"[gif] {cast_path} -> {gif_path}")
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{cast_path}: {exc}")

    if errors:
        raise SystemExit("Failed:\n" + "\n".join(f" - {line}" for line in errors))


def cmd_gif_to_mp4(args: argparse.Namespace) -> None:
    require_binary("ffmpeg")

    output_dir = Path(args.output_dir).expanduser().resolve()
    inputs = [Path(p) for p in args.inputs]

    work_items: list[tuple[Path, Path, Path]] = []
    for root, gif_path in iter_files(inputs, ".gif"):
        mp4_path = output_path_for(
            gif_path,
            input_root=root,
            output_root=output_dir,
            new_suffix=".mp4",
        )
        work_items.append((root, gif_path, mp4_path))

    if not work_items:
        raise SystemExit("No .gif files found")

    errors: list[str] = []
    for _, gif_path, mp4_path in work_items:
        try:
            gif_to_mp4_one(
                gif_path,
                mp4_path,
                overwrite=args.overwrite,
                ffmpeg_loglevel=args.ffmpeg_loglevel,
            )
            print(f"[mp4] {gif_path} -> {mp4_path}")
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{gif_path}: {exc}")

    if errors:
        raise SystemExit("Failed:\n" + "\n".join(f" - {line}" for line in errors))


def cmd_cast_to_mp4(args: argparse.Namespace) -> None:
    require_binary("agg")
    require_binary("ffmpeg")

    cast_output_dir = Path(args.gif_dir).expanduser().resolve()
    mp4_output_dir = Path(args.mp4_dir).expanduser().resolve()

    settings = AggSettings(
        theme=args.theme,
        font_size=args.font_size,
        fps_cap=args.fps_cap,
        speed=args.speed,
        idle_time_limit=args.idle_time_limit,
    )

    inputs = [Path(p) for p in args.inputs]

    work_items: list[tuple[Path, Path, Path, Path]] = []
    for root, cast_path in iter_files(inputs, ".cast"):
        gif_path = output_path_for(
            cast_path,
            input_root=root,
            output_root=cast_output_dir,
            new_suffix=".gif",
        )
        mp4_path = output_path_for(
            cast_path,
            input_root=root,
            output_root=mp4_output_dir,
            new_suffix=".mp4",
        )
        work_items.append((root, cast_path, gif_path, mp4_path))

    if not work_items:
        raise SystemExit("No .cast files found")

    errors: list[str] = []
    for _, cast_path, gif_path, mp4_path in work_items:
        try:
            cast_to_gif_one(
                cast_path,
                gif_path,
                settings=settings,
                repair_on_failure=not args.no_repair,
                overwrite=args.overwrite,
            )
            gif_to_mp4_one(
                gif_path,
                mp4_path,
                overwrite=args.overwrite,
                ffmpeg_loglevel=args.ffmpeg_loglevel,
            )
            print(f"[mp4] {cast_path} -> {mp4_path}")
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{cast_path}: {exc}")

    if errors:
        raise SystemExit("Failed:\n" + "\n".join(f" - {line}" for line in errors))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Asciinema cast recording/conversion helper.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    record = sub.add_parser("record", help="Record a terminal session to .cast with asciinema.")
    record.add_argument("--output", required=True, help="Output .cast path.")
    record.add_argument("--command", default="", help="Run command (non-interactive) and record.")
    record.add_argument("--title", default="", help="Recording title.")
    record.add_argument("--cols", type=int, default=0, help="Terminal columns (0 = default).")
    record.add_argument("--rows", type=int, default=0, help="Terminal rows (0 = default).")
    record.add_argument(
        "--idle-time-limit",
        type=float,
        default=None,
        help="Limit recorded idle time (seconds).",
    )
    record.add_argument(
        "--env",
        action="append",
        default=[],
        help="Environment variables to capture (KEY=VALUE). Repeatable.",
    )
    record.add_argument("--overwrite", action="store_true", help="Overwrite output file if exists.")
    record.add_argument("--append", action="store_true", help="Append to existing output file.")
    record.set_defaults(func=cmd_record)

    cast_to_gif = sub.add_parser("cast-to-gif", help="Convert .cast files to .gif using agg.")
    cast_to_gif.add_argument("inputs", nargs="+", help="Input .cast file(s) or directory(ies).")
    cast_to_gif.add_argument("--output-dir", required=True, help="Output directory for .gif files.")
    cast_to_gif.add_argument("--theme", default="monokai", help="agg theme name.")
    cast_to_gif.add_argument("--font-size", type=int, default=40, help="Font size.")
    cast_to_gif.add_argument("--fps-cap", type=int, default=None, help="Max FPS (optional).")
    cast_to_gif.add_argument("--speed", type=float, default=None, help="Playback speed multiplier.")
    cast_to_gif.add_argument(
        "--idle-time-limit",
        type=float,
        default=None,
        help="Limit idle time when rendering (seconds).",
    )
    cast_to_gif.add_argument(
        "--no-repair",
        action="store_true",
        help="Do not attempt to repair broken .cast files on agg failure.",
    )
    cast_to_gif.add_argument("--overwrite", action="store_true", help="Overwrite existing outputs.")
    cast_to_gif.set_defaults(func=cmd_cast_to_gif)

    gif_to_mp4 = sub.add_parser("gif-to-mp4", help="Convert .gif files to .mp4 using ffmpeg.")
    gif_to_mp4.add_argument("inputs", nargs="+", help="Input .gif file(s) or directory(ies).")
    gif_to_mp4.add_argument("--output-dir", required=True, help="Output directory for .mp4 files.")
    gif_to_mp4.add_argument("--overwrite", action="store_true", help="Overwrite existing outputs.")
    gif_to_mp4.add_argument(
        "--ffmpeg-loglevel",
        default="error",
        help="ffmpeg loglevel (quiet|panic|fatal|error|warning|info|verbose).",
    )
    gif_to_mp4.set_defaults(func=cmd_gif_to_mp4)

    cast_to_mp4 = sub.add_parser(
        "cast-to-mp4",
        help="Convert .cast to .mp4 (cast->gif->mp4).",
    )
    cast_to_mp4.add_argument("inputs", nargs="+", help="Input .cast file(s) or directory(ies).")
    cast_to_mp4.add_argument("--gif-dir", required=True, help="Intermediate .gif output directory.")
    cast_to_mp4.add_argument("--mp4-dir", required=True, help="Final .mp4 output directory.")
    cast_to_mp4.add_argument("--theme", default="monokai", help="agg theme name.")
    cast_to_mp4.add_argument("--font-size", type=int, default=40, help="Font size.")
    cast_to_mp4.add_argument("--fps-cap", type=int, default=None, help="Max FPS (optional).")
    cast_to_mp4.add_argument("--speed", type=float, default=None, help="Playback speed multiplier.")
    cast_to_mp4.add_argument(
        "--idle-time-limit",
        type=float,
        default=None,
        help="Limit idle time when rendering (seconds).",
    )
    cast_to_mp4.add_argument(
        "--no-repair",
        action="store_true",
        help="Do not attempt to repair broken .cast files on agg failure.",
    )
    cast_to_mp4.add_argument("--overwrite", action="store_true", help="Overwrite existing outputs.")
    cast_to_mp4.add_argument(
        "--ffmpeg-loglevel",
        default="error",
        help="ffmpeg loglevel (quiet|panic|fatal|error|warning|info|verbose).",
    )
    cast_to_mp4.set_defaults(func=cmd_cast_to_mp4)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        args.func(args)
    except DependencyError as exc:
        print(f"❌ {exc}", file=sys.stderr)
        return 2
    except subprocess.CalledProcessError as exc:
        return exc.returncode or 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
