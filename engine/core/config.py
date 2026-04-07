#!/usr/bin/env python3
from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, field


@dataclass
class AsciinemaConfig:
    """Configuration for asciinema operations."""
    default_theme: str = "monokai"
    default_font_size: int = 40
    default_fps_cap: Optional[int] = None
    default_speed: Optional[float] = None
    default_idle_time_limit: Optional[float] = None
    ffmpeg_loglevel: str = "error"
    ffmpeg_params: Dict[str, str] = field(default_factory=lambda: {
        "pix_fmt": "yuv420p",
        "movflags": "faststart"
    })


@dataclass
class VHSConfig:
    """Configuration for VHS operations."""
    default_platform: Optional[str] = None
    default_image_tag: str = "neural-vhs"
    default_runtime_mode: str = "shared"
    default_output_ext: str = "mp4"
    default_max_parallel: Optional[int] = None
    chunk_size: int = 200
    shared_timeout: int = 60
    theme: Dict[str, Any] = field(default_factory=lambda: {
        "background": "#1e1e1e",
        "foreground": "#d4d4d4",
        "cursor": "#ffffff",
        "cursorAccent": "#000000",
        "selection": "#264f78"
    })
    vhs_settings: Dict[str, Any] = field(default_factory=lambda: {
        "width": 1600,
        "height": 900,
        "font_size": 40,
        "typing_speed": "70ms",
        "playback_speed": 1.0,
        "margin": 80,
        "padding": 40,
        "border_radius": 8
    })


@dataclass
class GUIConfig:
    """Configuration for GUI operations."""
    default_image_tag: str = "computer-use-gui:local"
    default_platform: Optional[str] = None
    default_novnc_port: int = 0
    default_screen_width: int = 0
    default_screen_height: int = 0
    default_fps: Optional[int] = None
    default_max_tokens: Optional[int] = None
    default_cursor_theme: str = ""
    default_cursor_size: int = 0
    synthetic_config: Dict[str, Any] = field(default_factory=lambda: {
        "default_count": 1,
        "default_memory_per_worker": "2g",
        "default_screen_width": 1024,
        "default_screen_height": 768,
        "default_duration": 30,
        "default_fps": 15,
        "default_retries": 3,
        "default_image": "synthetic-data-collection:local"
    })


@dataclass
class DockerConfig:
    """Configuration for Docker operations."""
    default_platform: Optional[str] = None
    default_build_args: Dict[str, str] = field(default_factory=dict)
    default_run_args: Dict[str, str] = field(default_factory=dict)


class ConfigurationManager:
    """Project configuration."""

    def __init__(self, repo_root: Optional[Path] = None):
        self.repo_root = repo_root or Path(__file__).resolve().parent.parent

        self.asciinema = AsciinemaConfig()
        self.vhs = VHSConfig()
        self.gui = GUIConfig()
        self.docker = DockerConfig()

        self._load_env_overrides()

    def _load_env_overrides(self) -> None:
        """Load configuration overrides from environment variables."""
        if theme := os.getenv("ASCIINEMA_THEME"):
            self.asciinema.default_theme = theme
        if font_size := os.getenv("ASCIINEMA_FONT_SIZE"):
            self.asciinema.default_font_size = int(font_size)
        if fps_cap := os.getenv("ASCIINEMA_FPS_CAP"):
            self.asciinema.default_fps_cap = int(fps_cap)
        if speed := os.getenv("ASCIINEMA_SPEED"):
            self.asciinema.default_speed = float(speed)
        if idle_limit := os.getenv("ASCIINEMA_IDLE_TIME_LIMIT"):
            self.asciinema.default_idle_time_limit = float(idle_limit)

        if platform := os.getenv("VHS_PLATFORM"):
            self.vhs.default_platform = platform
        if image_tag := os.getenv("VHS_IMAGE_TAG"):
            self.vhs.default_image_tag = image_tag
        if runtime_mode := os.getenv("VHS_RUNTIME_MODE"):
            self.vhs.default_runtime_mode = runtime_mode
        if max_parallel := os.getenv("VHS_MAX_PARALLEL"):
            self.vhs.default_max_parallel = int(max_parallel)

        if gui_image := os.getenv("GUI_IMAGE_TAG"):
            self.gui.default_image_tag = gui_image
        if gui_platform := os.getenv("GUI_PLATFORM"):
            self.gui.default_platform = gui_platform
        if novnc_port := os.getenv("NOVNC_PORT"):
            self.gui.default_novnc_port = int(novnc_port)
        if screen_width := os.getenv("SCREEN_WIDTH"):
            self.gui.default_screen_width = int(screen_width)
        if screen_height := os.getenv("SCREEN_HEIGHT"):
            self.gui.default_screen_height = int(screen_height)
        if cursor_theme := os.getenv("CURSOR_THEME"):
            self.gui.default_cursor_theme = cursor_theme
        if cursor_size := os.getenv("CURSOR_SIZE"):
            self.gui.default_cursor_size = int(cursor_size)

        if docker_platform := os.getenv("DOCKER_PLATFORM"):
            self.docker.default_platform = docker_platform

    def get_default_paths(self) -> Dict[str, Path]:
        """Get default paths for various operations."""
        workspace_root = self.repo_root / "workspace"
        video_root = workspace_root / "videos"
        cligen_general_root = workspace_root / "cligen_general"
        cligen_clean_root = workspace_root / "cligen_clean"
        guiworld_root = workspace_root / "guiworld"

        return {
            "workspace_root": workspace_root,
            "video_root": video_root,
            "cligen_general_root": cligen_general_root,
            "cligen_clean_root": cligen_clean_root,
            "guiworld_root": guiworld_root,
            "asciinema_casts": cligen_general_root / "casts",
            "asciinema_gifs": cligen_general_root / "gifs",
            "asciinema_mp4": video_root / "asciinema",
            "vhs_manifest": cligen_clean_root / "manifest.jsonl",
            "vhs_outputs": video_root / "vhs",
            "vhs_generated": cligen_clean_root / "generated" / "basic",
            "gui_recordings": video_root / "gui",
            "gui_synthetic_raw_data": video_root / "gui_synthetic",
            "dockerfiles": self.repo_root / "engine" / "dockerfiles"
        }

_config_instance: Optional[ConfigurationManager] = None


def get_config(repo_root: Optional[Path] = None) -> ConfigurationManager:
    """Get the global configuration instance."""
    global _config_instance
    if _config_instance is None:
        _config_instance = ConfigurationManager(repo_root)
    return _config_instance
