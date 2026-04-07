"""Shared helpers for VHS tape generator scripts."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List
import json

DEFAULT_ID_PREFIX = "sft"
DEFAULT_ID_WIDTH = 6
DEFAULT_START_INDEX = 21764

DOC_BLOCK = """# ---- VHS documentation start (DO NOT CHANGE) ----
#
# Require:
#   Require <string>                Ensure a program is on the $PATH to proceed
#
# Sleep:
#   Sleep <time>                    Sleep for a set amount of <time> in seconds
#
# Type:
#   Type[@<time>] "<characters>"    Type <characters> into the terminal with a
#                                   <time> delay between each character
#
# Keys:
#   Escape[@<time>] [number]        Press the Escape key
#   Backspace[@<time>] [number]     Press the Backspace key
#   Delete[@<time>] [number]        Press the Delete key
#   Insert[@<time>] [number]        Press the Insert key
#   Down[@<time>] [number]          Press the Down key
#   Enter[@<time>] [number]         Press the Enter key
#   Space[@<time>] [number]         Press the Space key
#   Tab[@<time>] [number]           Press the Tab key
#   Left[@<time>] [number]          Press the Left Arrow key
#   Right[@<time>] [number]         Press the Right Arrow key
#   Up[@<time>] [number]            Press the Up Arrow key
#   Down[@<time>] [number]          Press the Down Arrow key
#   PageUp[@<time>] [number]        Press the Page Up key
#   PageDown[@<time>] [number]      Press the Page Down key
#   Ctrl+<key>                      Press the Control key + <key> (e.g. Ctrl+C)
#
# Display:
#   Hide                            Hide the subsequent commands from the output
#   Show                            Show the subsequent commands in the output
# ---- VHS documentation end (DO NOT CHANGE) ----"""

THEME_BLOCK = """# ---- Theme setting start (DO NOT CHANGE) ----
Output {output_name}

{requires_block}# "Catppuccin Mocha (Pure White, Warm Pink Cursor)"
Set Shell "bash"

Set Theme {{
  "name": "Catppuccin Mocha (Pure White, Warm Pink Cursor)",
  "background": "#1e1e2e",
  "foreground": "#ffffff",
  "black": "#45475a",
  "red": "#f38ba8",
  "green": "#a6e3a1",
  "yellow": "#f9e2af",
  "blue": "#89b4fa",
  "purple": "#cba6f7",
  "cyan": "#94e2d5",
  "white": "#ffffff",
  "brightBlack": "#585b70",
  "brightRed": "#f38ba8",
  "brightGreen": "#a6e3a1",
  "brightYellow": "#f9e2af",
  "brightBlue": "#89b4fa",
  "brightPurple": "#cba6f7",
  "brightCyan": "#89dceb",
  "brightWhite": "#ffffff",
  "cursor": "#f5c2e7",
  "cursorAccent": "#1e1e2e",
  "selectionBackground": "#585b70"
}}

Set FontSize 40
Set Width 1600
Set Height 900
Set TypingSpeed 70ms
Set PlaybackSpeed 1
Set Margin 28
Set MarginFill "#0091FF"
Set BorderRadius 25
Set Padding 18
Set LineHeight 1.2
Set LetterSpacing 0.8

# ---- Theme setting end (DO NOT CHANGE) ----"""

ALL_CLASSES: List[str] = [
    "Basic",
    "Files",
    "Text",
    "Process",
    "Network",
    "Package",
    "VCS",
    "Build",
    "Users",
    "Admin",
    "FS",
    "Security",
    "DB",
    "Container",
    "Editors",
    "Exec",
    "Misc",
]


def format_classes(active_flags: dict[str, bool]) -> str:
    """Return the canonical CLASS JSON string ordered by ALL_CLASSES."""
    canonical = {name: False for name in ALL_CLASSES}
    canonical.update(active_flags)
    return json.dumps(canonical, separators=(", ", ": "))


def render_require_lines(requirements: Iterable[str]) -> str:
    uniq = []
    seen = set()
    for item in requirements:
        item = item.strip()
        if not item:
            continue
        if item.lower().startswith("require "):
            item = item.split(" ", 1)[1]
        if item not in seen:
            uniq.append(item)
            seen.add(item)
    if not uniq:
        return ""
    return "\n".join(f"Require {item}" for item in uniq)


@dataclass
class TapeMetadata:
    tape_id: str
    instruction: str
    active_classes: dict[str, bool]
    level: int
    interactive: bool
    events: int
    visual_complexity: int
    requires: Iterable[str]
    body_lines: Iterable[str]
    output_name: str | None = None


def format_tape_id(prefix: str, index: int, width: int = DEFAULT_ID_WIDTH) -> str:
    if index < 0:
        raise ValueError("index must be non-negative")
    if width <= 0:
        raise ValueError("width must be positive")
    return f"{prefix}_{index:0{width}d}"


@dataclass
class TapeIdAllocator:
    prefix: str = DEFAULT_ID_PREFIX
    start_index: int = DEFAULT_START_INDEX
    width: int = DEFAULT_ID_WIDTH

    def __post_init__(self) -> None:
        if self.start_index < 0:
            raise ValueError("start_index must be non-negative")
        if self.width <= 0:
            raise ValueError("width must be positive")
        self._next_index = self.start_index

    def next(self) -> tuple[str, str]:
        tape_id = format_tape_id(self.prefix, self._next_index, self.width)
        output_name = f"{tape_id}.mp4"
        self._next_index += 1
        return tape_id, output_name

    @property
    def next_index(self) -> int:
        return self._next_index


def render_tape(metadata: TapeMetadata) -> str:
    output_name = metadata.output_name or f"{metadata.tape_id}.mp4"
    requires_lines = render_require_lines(metadata.requires)
    requires_block = f"{requires_lines}\n\n" if requires_lines else "\n"
    parts = [
        DOC_BLOCK,
        "",
        f"# ID: {metadata.tape_id}",
        f"# INSTRUCTION: {metadata.instruction}",
        f"# CLASS: {format_classes(metadata.active_classes)}",
        f"# LEVEL: {metadata.level}",
        f"# INTERACTIVE: {str(metadata.interactive).lower()}",
        f"# EVENTS: {metadata.events}",
        f"# VISUAL_COMPLEXITY: {metadata.visual_complexity}",
        "",
        THEME_BLOCK.format(output_name=output_name, requires_block=requires_block),
        "",
    ]
    body_lines = list(metadata.body_lines)
    parts.extend(body_lines)
    if body_lines:
        last = body_lines[-1].strip()
        if last != "Hide":
            parts.append("Hide")
    parts.append("")
    return "\n".join(parts)


def ensure_output_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
