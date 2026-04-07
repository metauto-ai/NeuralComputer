#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from .config import get_config
from .docker_builder import DockerCommandBuilder, DockerBuildOptions


class CLIHandlers:
    """CLI handlers."""

    def __init__(self, repo_root: Path):
        self.repo_root = repo_root
        self.config = get_config(repo_root)
        self.docker_builder = DockerCommandBuilder()

    def run(self, cmd: List[str], *, cwd: Optional[Path] = None,
            env: Optional[Dict[str, str]] = None) -> None:
        """Run a command."""
        subprocess.run(
            cmd,
            cwd=str(cwd) if cwd else None,
            env=env,
            check=True,
        )

    @staticmethod
    def _append_option(cmd: List[str], flag: str, value: object, *, include: bool = True) -> None:
        """Append a CLI option when include=True."""
        if include:
            cmd += [flag, str(value)]

    @staticmethod
    def _append_flag(cmd: List[str], flag: str, enabled: bool) -> None:
        """Append a boolean CLI flag when enabled=True."""
        if enabled:
            cmd.append(flag)

    @staticmethod
    def _append_repeated_option(cmd: List[str], flag: str, values: List[str]) -> None:
        """Append a repeatable option for every value in values."""
        for value in values:
            cmd += [flag, value]

    def _python_command(self, script_path: Path, *script_args: str) -> List[str]:
        """Build a Python command."""
        return [sys.executable, str(script_path), *script_args]

    def _run_python_script(self, relative_script: Path, script_args: List[str]) -> None:
        """Run a repository-relative python script."""
        script = self.repo_root / relative_script
        cmd = self._python_command(script, *script_args)
        self.run(cmd, cwd=self.repo_root)

    def _run_shell_script(
        self,
        relative_script: Path,
        script_args: Optional[List[str]] = None,
        *,
        env: Optional[Dict[str, str]] = None,
    ) -> None:
        """Run a repository-relative shell script."""
        script = self.repo_root / relative_script
        cmd = ["bash", str(script)]
        if script_args:
            cmd += script_args
        self.run(cmd, cwd=self.repo_root, env=env)

    def _build_docker_image(self, dockerfile_name: str, tag: str, platform: Optional[str]) -> None:
        """Build a Docker image from engine/dockerfiles."""
        dockerfile = self.repo_root / "engine" / "dockerfiles" / dockerfile_name
        build_options = DockerBuildOptions(
            dockerfile=dockerfile,
            context=self.repo_root,
            tag=tag,
            platform=platform,
        )
        cmd = self.docker_builder.build_build_command(build_options)
        self.run(cmd, cwd=self.repo_root)

    def _append_asciinema_render_options(self, cmd: List[str], args: argparse.Namespace) -> None:
        """Append shared render options for cast-to-gif / cast-to-mp4."""
        self._append_option(cmd, "--theme", args.theme)
        self._append_option(cmd, "--font-size", args.font_size)
        self._append_option(cmd, "--fps-cap", args.fps_cap, include=args.fps_cap is not None)
        self._append_option(cmd, "--speed", args.speed, include=args.speed is not None)
        self._append_option(
            cmd,
            "--idle-time-limit",
            args.idle_time_limit,
            include=args.idle_time_limit is not None,
        )
        self._append_flag(cmd, "--no-repair", args.no_repair)

    def cli_asciinema(self, args: argparse.Namespace) -> None:
        """Handle asciinema CLI operations."""
        script = self.repo_root / "engine" / "cli" / "asciinema" / "asciinema_engine.py"
        cmd = self._python_command(script, args.action)
        default_paths = self.config.get_default_paths()

        if args.action == "record":
            if args.output:
                output_path = Path(args.output).expanduser().resolve()
            else:
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_path = default_paths["asciinema_casts"] / f"record_{ts}.cast"
            self._append_option(cmd, "--output", output_path)
            self._append_option(cmd, "--command", args.command, include=bool(args.command))
            self._append_option(cmd, "--title", args.title, include=bool(args.title))
            self._append_option(cmd, "--cols", args.cols, include=bool(args.cols))
            self._append_option(cmd, "--rows", args.rows, include=bool(args.rows))
            self._append_option(
                cmd,
                "--idle-time-limit",
                args.idle_time_limit,
                include=args.idle_time_limit is not None,
            )
            self._append_repeated_option(cmd, "--env", args.env)
            self._append_flag(cmd, "--overwrite", args.overwrite)
            self._append_flag(cmd, "--append", args.append)

        elif args.action == "cast-to-gif":
            cmd += args.inputs
            output_dir = Path(args.output_dir).expanduser().resolve()
            self._append_option(cmd, "--output-dir", output_dir)
            self._append_asciinema_render_options(cmd, args)
            self._append_flag(cmd, "--overwrite", args.overwrite)

        elif args.action == "gif-to-mp4":
            cmd += args.inputs
            output_dir = Path(args.output_dir).expanduser().resolve()
            self._append_option(cmd, "--output-dir", output_dir)
            self._append_option(cmd, "--ffmpeg-loglevel", args.ffmpeg_loglevel)
            self._append_flag(cmd, "--overwrite", args.overwrite)

        elif args.action == "cast-to-mp4":
            cmd += args.inputs
            gif_dir = Path(args.gif_dir).expanduser().resolve()
            mp4_dir = Path(args.mp4_dir).expanduser().resolve()
            self._append_option(cmd, "--gif-dir", gif_dir)
            self._append_option(cmd, "--mp4-dir", mp4_dir)
            self._append_asciinema_render_options(cmd, args)
            self._append_option(cmd, "--ffmpeg-loglevel", args.ffmpeg_loglevel)
            self._append_flag(cmd, "--overwrite", args.overwrite)

        self.run(cmd, cwd=self.repo_root)

    def cli_vhs_build(self, args: argparse.Namespace) -> None:
        """Build the VHS image."""
        self._build_docker_image("vhs.Dockerfile", args.tag, args.platform)

    def cli_vhs_run_manifest(self, args: argparse.Namespace) -> None:
        """Run VHS manifest."""
        cmd = [
            str(args.manifest),
            "--image",
            args.image,
            "--outputs",
            str(args.outputs),
        ]
        self._append_option(cmd, "--platform", args.platform, include=args.platform is not None)
        self._append_flag(cmd, "--reverse", args.reverse)
        self._append_option(
            cmd,
            "--max-parallel",
            args.max_parallel,
            include=args.max_parallel is not None,
        )
        self._append_flag(cmd, "--no-legacy-fixtures", args.no_legacy_fixtures)
        self._run_python_script(Path("engine/cli/vhs/runtime/run_manifest.py"), cmd)

    def cli_vhs_generate_basic(self, args: argparse.Namespace) -> None:
        """Generate basic VHS tapes."""
        output_dir = Path(args.output_dir).expanduser().resolve()
        cmd = [
            "--count",
            str(args.count),
            "--output-dir",
            str(output_dir),
            "--min-length",
            str(args.min_length),
            "--max-length",
            str(args.max_length),
            "--seed",
            str(args.seed),
            "--prefix",
            args.prefix,
            "--start-index",
            str(args.start_index),
            "--id-width",
            str(args.id_width),
        ]
        self._run_python_script(Path("engine/cli/vhs/generators/basic.py"), cmd)

    def cli_vhs_make_manifest(self, args: argparse.Namespace) -> None:
        """Make VHS manifest."""
        tapes_dir = Path(args.tapes_dir).expanduser().resolve()
        cmd = [
            "--tapes-dir",
            str(tapes_dir),
            "--runtime-mode",
            args.runtime_mode,
            "--output-ext",
            args.output_ext,
        ]
        if args.output:
            self._append_option(cmd, "--output", Path(args.output).expanduser().resolve())
        self._run_python_script(Path("engine/cli/vhs/runtime/make_manifest.py"), cmd)

    def gui_build(self, args: argparse.Namespace) -> None:
        """Build the GUI image."""
        self._build_docker_image("gui.Dockerfile", args.tag, args.platform)

    def gui_run(self, args: argparse.Namespace) -> None:
        """Run GUI session."""
        script_args: List[str] = []
        self._append_option(script_args, "--instruction", args.instruction, include=bool(args.instruction))
        self._append_option(script_args, "--model", args.model, include=bool(args.model))
        self._append_option(script_args, "--fps", args.fps, include=args.fps is not None)
        self._append_option(
            script_args,
            "--max-tokens",
            args.max_tokens,
            include=args.max_tokens is not None,
        )

        env = os.environ.copy()
        gui_config = self.config.gui

        if args.docker_platform:
            env["DOCKER_PLATFORM"] = args.docker_platform

        if args.novnc_port or gui_config.default_novnc_port:
            env["NOVNC_PORT"] = str(args.novnc_port or gui_config.default_novnc_port)

        if args.screen_width or gui_config.default_screen_width:
            env["SCREEN_WIDTH"] = str(args.screen_width or gui_config.default_screen_width)

        if args.screen_height or gui_config.default_screen_height:
            env["SCREEN_HEIGHT"] = str(args.screen_height or gui_config.default_screen_height)

        default_recordings = self.config.get_default_paths()["gui_recordings"]
        recordings_dir = Path(args.recordings_dir).expanduser() if args.recordings_dir else default_recordings
        env["RECORDINGS_DIR"] = str(recordings_dir.resolve())
        if args.wallpaper:
            env["WALLPAPER_HOST_PATH"] = str(Path(args.wallpaper).expanduser().resolve())
            env["WALLPAPER_PATH"] = "/home/computeruse/wallpaper.png"

        cursor_theme = args.cursor_theme or gui_config.default_cursor_theme
        cursor_size = args.cursor_size or gui_config.default_cursor_size

        if cursor_theme:
            env["CURSOR_THEME"] = cursor_theme
        if cursor_size:
            env["CURSOR_SIZE"] = str(cursor_size)

        self._run_shell_script(Path("engine/gui/runtime/run.sh"), script_args, env=env)

    def gui_run_parallel(self, args: argparse.Namespace) -> None:
        """Run GUI in parallel mode."""
        self._run_shell_script(Path("engine/gui/runtime/run_parallel.sh"))

    def gui_synthetic(self, args: argparse.Namespace) -> None:
        """Generate synthetic GUI data."""
        cmd: List[str] = []

        synthetic_config = self.config.gui.synthetic_config

        self._append_option(cmd, "--count", args.count)
        self._append_option(cmd, "--memory-per-worker", args.memory_per_worker)
        self._append_option(cmd, "--screen-width", args.screen_width)
        self._append_option(cmd, "--screen-height", args.screen_height)
        self._append_option(cmd, "--duration", args.duration)
        self._append_option(cmd, "--fps", args.fps)
        self._append_option(cmd, "--retries", args.retries)
        self._append_option(
            cmd,
            "--max-workers",
            args.max_workers,
            include=args.max_workers is not None,
        )

        image = args.image or synthetic_config.get("default_image", "synthetic-data-collection:local")
        self._append_option(cmd, "--image", image)

        env = os.environ.copy()
        env.setdefault(
            "SYNTH_OUTPUT_DIR",
            str(self.config.get_default_paths()["gui_synthetic_raw_data"].resolve()),
        )
        self._run_shell_script(Path("engine/gui/runtime/run_synthetic.sh"), cmd, env=env)
