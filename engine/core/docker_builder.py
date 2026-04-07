#!/usr/bin/env python3
from __future__ import annotations

from typing import List, Dict, Optional
from pathlib import Path
from dataclasses import dataclass

from .interfaces import CommandBuilder

@dataclass
class DockerBuildOptions:
    """Options for Docker build commands."""
    dockerfile: Path
    context: Path
    tag: str
    platform: Optional[str] = None
    build_args: Dict[str, str] = None
    target: Optional[str] = None

    def __post_init__(self):
        if self.build_args is None:
            self.build_args = {}


@dataclass
class DockerRunOptions:
    """Options for Docker run commands."""
    image: str
    command: List[str] = None
    volumes: Dict[str, str] = None
    environment: Dict[str, str] = None
    ports: Dict[int, int] = None
    platform: Optional[str] = None
    detach: bool = False
    remove: bool = True
    interactive: bool = False
    tty: bool = False
    working_dir: Optional[str] = None
    user: Optional[str] = None
    memory: Optional[str] = None
    name: Optional[str] = None

    def __post_init__(self):
        if self.command is None:
            self.command = []
        if self.volumes is None:
            self.volumes = {}
        if self.environment is None:
            self.environment = {}
        if self.ports is None:
            self.ports = {}


class DockerCommandBuilder(CommandBuilder):
    """Build concrete Docker CLI commands for the current runtime."""

    def build_build_command(self, options: DockerBuildOptions) -> List[str]:
        """Build a Docker build command."""
        cmd = ["docker", "build"]

        platform = options.platform
        if platform and platform != "native":
            cmd.extend(["--platform", platform])

        cmd.extend(["-t", options.tag])

        for key, value in options.build_args.items():
            cmd.extend(["--build-arg", f"{key}={value}"])

        if options.target:
            cmd.extend(["--target", options.target])

        cmd.extend(["-f", str(options.dockerfile)])
        cmd.append(str(options.context))

        return cmd

    def build_run_command(self, options: DockerRunOptions) -> List[str]:
        """Build a Docker run command."""
        cmd = ["docker", "run"]

        if options.remove:
            cmd.append("--rm")
        if options.detach:
            cmd.append("-d")
        if options.interactive:
            cmd.append("-i")
        if options.tty:
            cmd.append("-t")

        platform = options.platform
        if platform and platform != "native":
            cmd.extend(["--platform", platform])

        if options.name:
            cmd.extend(["--name", options.name])

        if options.memory:
            cmd.extend(["-m", options.memory])

        if options.working_dir:
            cmd.extend(["-w", options.working_dir])

        if options.user:
            cmd.extend(["-u", options.user])

        for host_path, container_path in options.volumes.items():
            cmd.extend(["-v", f"{host_path}:{container_path}"])

        for key, value in options.environment.items():
            cmd.extend(["-e", f"{key}={value}"])

        for host_port, container_port in options.ports.items():
            cmd.extend(["-p", f"{host_port}:{container_port}"])

        cmd.append(options.image)
        cmd.extend(options.command)

        return cmd

    def build_command(self, command_type: str = "run", **options) -> List[str]:
        """Compatibility wrapper for older callers.

        Internal code should prefer the explicit build_build_command() and
        build_run_command() entry points.
        """
        if command_type == "build":
            return self.build_build_command(DockerBuildOptions(**options))
        if command_type == "run":
            return self.build_run_command(DockerRunOptions(**options))
        raise ValueError(f"Unknown command type: {command_type}")

    def validate_options(self, command_type: str = "run", **options) -> bool:
        """Compatibility validator for older callers."""
        try:
            if command_type == "build":
                DockerBuildOptions(**options)
            elif command_type == "run":
                DockerRunOptions(**options)
            else:
                return False
            return True
        except (TypeError, ValueError):
            return False
