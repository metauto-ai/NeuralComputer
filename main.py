#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

from engine.core.config import get_config
from engine.core.cli_handlers import CLIHandlers

REPO_ROOT = Path(__file__).resolve().parent


handlers = CLIHandlers(REPO_ROOT)
config = get_config(REPO_ROOT)


def cli_asciinema(args: argparse.Namespace) -> None:
    handlers.cli_asciinema(args)


def cli_vhs_build(args: argparse.Namespace) -> None:
    handlers.cli_vhs_build(args)


def cli_vhs_run_manifest(args: argparse.Namespace) -> None:
    handlers.cli_vhs_run_manifest(args)


def cli_vhs_generate_basic(args: argparse.Namespace) -> None:
    handlers.cli_vhs_generate_basic(args)


def cli_vhs_make_manifest(args: argparse.Namespace) -> None:
    handlers.cli_vhs_make_manifest(args)


def gui_build(args: argparse.Namespace) -> None:
    handlers.gui_build(args)


def gui_run(args: argparse.Namespace) -> None:
    handlers.gui_run(args)


def gui_run_parallel(args: argparse.Namespace) -> None:
    handlers.gui_run_parallel(args)


def gui_synthetic(args: argparse.Namespace) -> None:
    handlers.gui_synthetic(args)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="NCDataEngine unified data-generation entrypoint.")
    sub = parser.add_subparsers(dest="engine", required=True)

    default_paths = config.get_default_paths()

    cli = sub.add_parser(
        "cligen",
        aliases=["cli"],
        help="Cligen video data engine (asciinema/vhs).",
    )
    cli_sub = cli.add_subparsers(dest="cli_engine", required=True)

    asciinema = cli_sub.add_parser("asciinema", help="Record/convert asciinema casts (.cast).")
    asciinema_sub = asciinema.add_subparsers(dest="action", required=True)

    asciinema_record = asciinema_sub.add_parser("record", help="Record a terminal session to .cast.")
    asciinema_record.add_argument(
        "--output",
        default="",
        help=(
            "Output .cast path. "
            "If omitted, auto-generates under workspace/cligen_general/casts."
        ),
    )
    asciinema_record.add_argument("--command", default="", help="Run a command and record it.")
    asciinema_record.add_argument("--title", default="", help="Recording title.")
    asciinema_record.add_argument("--cols", type=int, default=0, help="Terminal columns.")
    asciinema_record.add_argument("--rows", type=int, default=0, help="Terminal rows.")
    asciinema_record.add_argument(
        "--idle-time-limit",
        type=float,
        default=None,
        help="Limit recorded idle time (seconds).",
    )
    asciinema_record.add_argument(
        "--env",
        action="append",
        default=[],
        help="Environment variables to capture (KEY=VALUE). Repeatable.",
    )
    asciinema_record.add_argument("--overwrite", action="store_true", help="Overwrite output file.")
    asciinema_record.add_argument("--append", action="store_true", help="Append to existing file.")
    asciinema_record.set_defaults(func=cli_asciinema)

    asciinema_cast_to_gif = asciinema_sub.add_parser(
        "cast-to-gif", help="Convert .cast files to .gif (agg)."
    )
    asciinema_cast_to_gif.add_argument("inputs", nargs="+", help="Input .cast file(s)/dir(s).")
    asciinema_cast_to_gif.add_argument(
        "--output-dir",
        type=Path,
        default=default_paths["asciinema_gifs"],
        help="Output directory for .gif files.",
    )
    asciinema_cast_to_gif.add_argument("--theme", default=config.asciinema.default_theme, help="agg theme.")
    asciinema_cast_to_gif.add_argument("--font-size", type=int, default=config.asciinema.default_font_size, help="Font size.")
    asciinema_cast_to_gif.add_argument("--fps-cap", type=int, default=None, help="Max FPS.")
    asciinema_cast_to_gif.add_argument("--speed", type=float, default=None, help="Speed multiplier.")
    asciinema_cast_to_gif.add_argument(
        "--idle-time-limit",
        type=float,
        default=None,
        help="Limit idle time (seconds) when rendering.",
    )
    asciinema_cast_to_gif.add_argument(
        "--no-repair",
        action="store_true",
        help="Do not attempt auto-repair on broken .cast files.",
    )
    asciinema_cast_to_gif.add_argument("--overwrite", action="store_true", help="Overwrite outputs.")
    asciinema_cast_to_gif.set_defaults(func=cli_asciinema)

    asciinema_gif_to_mp4 = asciinema_sub.add_parser(
        "gif-to-mp4", help="Convert .gif files to .mp4 (ffmpeg)."
    )
    asciinema_gif_to_mp4.add_argument("inputs", nargs="+", help="Input .gif file(s)/dir(s).")
    asciinema_gif_to_mp4.add_argument(
        "--output-dir",
        type=Path,
        default=default_paths["asciinema_mp4"],
        help="Output directory for .mp4 files.",
    )
    asciinema_gif_to_mp4.add_argument("--overwrite", action="store_true", help="Overwrite outputs.")
    asciinema_gif_to_mp4.add_argument(
        "--ffmpeg-loglevel",
        default=config.asciinema.ffmpeg_loglevel,
        help="ffmpeg loglevel (quiet|panic|fatal|error|warning|info|verbose).",
    )
    asciinema_gif_to_mp4.set_defaults(func=cli_asciinema)

    asciinema_cast_to_mp4 = asciinema_sub.add_parser(
        "cast-to-mp4", help="Convert .cast -> .gif -> .mp4."
    )
    asciinema_cast_to_mp4.add_argument("inputs", nargs="+", help="Input .cast file(s)/dir(s).")
    asciinema_cast_to_mp4.add_argument(
        "--gif-dir",
        type=Path,
        default=default_paths["asciinema_gifs"],
        help="GIF dir.",
    )
    asciinema_cast_to_mp4.add_argument(
        "--mp4-dir",
        type=Path,
        default=default_paths["asciinema_mp4"],
        help="MP4 dir.",
    )
    asciinema_cast_to_mp4.add_argument("--theme", default=config.asciinema.default_theme, help="agg theme.")
    asciinema_cast_to_mp4.add_argument("--font-size", type=int, default=config.asciinema.default_font_size, help="Font size.")
    asciinema_cast_to_mp4.add_argument("--fps-cap", type=int, default=None, help="Max FPS.")
    asciinema_cast_to_mp4.add_argument("--speed", type=float, default=None, help="Speed multiplier.")
    asciinema_cast_to_mp4.add_argument(
        "--idle-time-limit",
        type=float,
        default=None,
        help="Limit idle time (seconds) when rendering.",
    )
    asciinema_cast_to_mp4.add_argument(
        "--no-repair",
        action="store_true",
        help="Do not attempt auto-repair on broken .cast files.",
    )
    asciinema_cast_to_mp4.add_argument("--overwrite", action="store_true", help="Overwrite outputs.")
    asciinema_cast_to_mp4.add_argument(
        "--ffmpeg-loglevel",
        default=config.asciinema.ffmpeg_loglevel,
        help="ffmpeg loglevel (quiet|panic|fatal|error|warning|info|verbose).",
    )
    asciinema_cast_to_mp4.set_defaults(func=cli_asciinema)

    vhs = cli_sub.add_parser("vhs", help="Generate mp4 from VHS .tape scripts.")
    vhs_sub = vhs.add_subparsers(dest="vhs_action", required=True)

    vhs_build = vhs_sub.add_parser("build-image", help="Build the neural-vhs Docker image.")
    vhs_build.add_argument("--platform", default=config.vhs.default_platform, help="Docker build platform.")
    vhs_build.add_argument("--tag", default=config.vhs.default_image_tag, help="Docker image tag.")
    vhs_build.set_defaults(func=cli_vhs_build)

    vhs_run = vhs_sub.add_parser("run-manifest", help="Run a manifest JSONL and produce mp4 outputs.")
    vhs_run.add_argument(
        "--manifest",
        type=Path,
        default=default_paths["vhs_manifest"],
        help="Manifest JSONL path.",
    )
    vhs_run.add_argument(
        "--outputs",
        type=Path,
        default=default_paths["vhs_outputs"],
        help="Output directory for mp4 files.",
    )
    vhs_run.add_argument("--image", default=config.vhs.default_image_tag, help="Docker image name.")
    vhs_run.add_argument(
        "--platform",
        default=config.vhs.default_platform,
        help="Docker platform (use 'native' to omit in run_manifest).",
    )
    vhs_run.add_argument("--reverse", action="store_true", help="Process manifest in reverse order.")
    vhs_run.add_argument("--max-parallel", type=int, default=None, help="Max parallel docker jobs.")
    vhs_run.add_argument(
        "--no-legacy-fixtures",
        action="store_true",
        help="Disable legacy /tmp/vhs_* fixture files.",
    )
    vhs_run.set_defaults(func=cli_vhs_run_manifest)

    vhs_gen = vhs_sub.add_parser(
        "generate-basic",
        help="Batch-generate .tape files (basic shell commands preset).",
    )
    vhs_gen.add_argument("--count", type=int, default=1000, help="How many tapes to generate.")
    vhs_gen.add_argument(
        "--output-dir",
        type=Path,
        default=default_paths["vhs_generated"],
        help="Output directory for generated .tape files.",
    )
    vhs_gen.add_argument("--min-length", type=int, default=1, help="Min commands per tape.")
    vhs_gen.add_argument("--max-length", type=int, default=3, help="Max commands per tape.")
    vhs_gen.add_argument("--seed", type=int, default=2024, help="Random seed.")
    vhs_gen.add_argument("--prefix", default="demo", help="Tape ID prefix.")
    vhs_gen.add_argument("--start-index", type=int, default=0, help="Starting index for IDs.")
    vhs_gen.add_argument("--id-width", type=int, default=6, help="Zero-pad width for IDs.")
    vhs_gen.set_defaults(func=cli_vhs_generate_basic)

    vhs_manifest = vhs_sub.add_parser(
        "make-manifest",
        help="Create a run_manifest-compatible manifest.jsonl from a tapes directory.",
    )
    vhs_manifest.add_argument(
        "--tapes-dir",
        type=Path,
        default=default_paths["vhs_generated"],
        help="Directory of .tape files.",
    )
    vhs_manifest.add_argument("--output", type=Path, default=None, help="Manifest JSONL path.")
    vhs_manifest.add_argument(
        "--runtime-mode",
        choices=["shared", "isolated"],
        default=config.vhs.default_runtime_mode,
        help="Default runtime_mode for each entry.",
    )
    vhs_manifest.add_argument("--output-ext", default=config.vhs.default_output_ext, help="Output video extension.")
    vhs_manifest.set_defaults(func=cli_vhs_make_manifest)

    gui = sub.add_parser(
        "guiworld",
        aliases=["gui"],
        help="GUIWorld video data engine (desktop container + recorder).",
    )
    gui_sub = gui.add_subparsers(dest="gui_action", required=True)

    gui_build_p = gui_sub.add_parser("build-image", help="Build the computer-use-gui Docker image.")
    gui_build_p.add_argument("--tag", default=config.gui.default_image_tag, help="Docker image tag.")
    gui_build_p.add_argument("--platform", default=None, help="Optional docker build platform.")
    gui_build_p.set_defaults(func=gui_build)

    gui_run_p = gui_sub.add_parser("run", help="Run a single instruction with recording (noVNC).")
    gui_run_p.add_argument("--instruction", default="", help="Instruction text.")
    gui_run_p.add_argument("--model", default="", help="Anthropic model name.")
    gui_run_p.add_argument("--fps", type=int, default=config.gui.default_fps, help="Recording FPS.")
    gui_run_p.add_argument("--max-tokens", type=int, default=config.gui.default_max_tokens, help="Max tokens per model call.")
    gui_run_p.add_argument(
        "--docker-platform",
        default=config.gui.default_platform,
        help="Set DOCKER_PLATFORM for the GUI runtime (e.g. linux/amd64, linux/arm64).",
    )
    gui_run_p.add_argument("--novnc-port", type=int, default=config.gui.default_novnc_port, help="Expose noVNC on this port.")
    gui_run_p.add_argument("--screen-width", type=int, default=config.gui.default_screen_width, help="Virtual screen width.")
    gui_run_p.add_argument("--screen-height", type=int, default=config.gui.default_screen_height, help="Virtual screen height.")
    gui_run_p.add_argument(
        "--recordings-dir",
        default="",
        help="Host directory to store recordings (default: workspace/videos/gui).",
    )
    gui_run_p.add_argument(
        "--wallpaper",
        default="",
        help="Optional host path to a wallpaper image to mount into the container.",
    )
    gui_run_p.add_argument(
        "--cursor-theme",
        default=config.gui.default_cursor_theme,
        help="Cursor theme name inside the container (e.g. Adwaita).",
    )
    gui_run_p.add_argument(
        "--cursor-size",
        type=int,
        default=config.gui.default_cursor_size,
        help="Cursor size inside the container (e.g. 24, 32, 48).",
    )
    gui_run_p.set_defaults(func=gui_run)

    gui_parallel_p = gui_sub.add_parser(
        "run-parallel", help="Run the bundled parallel GUI instruction set."
    )
    gui_parallel_p.set_defaults(func=gui_run_parallel)

    gui_syn_p = gui_sub.add_parser(
        "synthetic",
        help="Generate synthetic GUI trajectories (default: workspace/videos/gui_synthetic/*).",
    )
    gui_syn_p.add_argument("--count", type=int, default=config.gui.synthetic_config["default_count"], help="How many trajectories to generate.")
    gui_syn_p.add_argument(
        "--max-workers",
        type=int,
        default=None,
        help="Max parallel workers (default: auto).",
    )
    gui_syn_p.add_argument(
        "--memory-per-worker",
        default=config.gui.synthetic_config["default_memory_per_worker"],
        help="Docker memory limit per worker container (default: 2g).",
    )
    gui_syn_p.add_argument(
        "--screen-width",
        type=int,
        default=config.gui.synthetic_config["default_screen_width"],
        help="Virtual screen width inside the container.",
    )
    gui_syn_p.add_argument(
        "--screen-height",
        type=int,
        default=config.gui.synthetic_config["default_screen_height"],
        help="Virtual screen height inside the container.",
    )
    gui_syn_p.add_argument("--duration", type=int, default=config.gui.synthetic_config["default_duration"], help="Seconds per trajectory.")
    gui_syn_p.add_argument("--fps", type=int, default=config.gui.synthetic_config["default_fps"], help="Recording FPS.")
    gui_syn_p.add_argument("--retries", type=int, default=config.gui.synthetic_config["default_retries"], help="Max retries per trajectory.")
    gui_syn_p.add_argument(
        "--image",
        default=config.gui.synthetic_config["default_image"],
        help="Base Docker image for synthetic runs.",
    )
    gui_syn_p.set_defaults(func=gui_synthetic)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        args.func(args)
    except subprocess.CalledProcessError as exc:
        return exc.returncode or 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
