#!/usr/bin/env python3
"""Generate VHS tapes that emphasise keyboard-driven interactions."""

import argparse
import random
from pathlib import Path
from typing import Dict, List, Tuple

from _common import TapeMetadata, ensure_output_dir, render_tape


def sanitize_instruction(text: str) -> str:
    return text.replace("\\", "\\\\").replace('"', '\\"')


def parse_requirements(raw: str) -> List[str]:
    lines = []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        lines.append(line)
    return lines or ["Require bash"]


def estimate_events(body: List[str]) -> int:
    return max(8, len(body) + 6)


def estimate_visual_complexity(body: List[str]) -> int:
    return max(25, 6 * len(body))

def generate_vim_scenarios() -> List[Tuple[str, str, Dict[str, bool], str]]:
    """Generate 200 vim/editor navigation scenarios."""
    scenarios = []
    
    # Basic vim operations
    vim_basics = [
        ("vim hello.txt", "Opening vim and typing text with Insert mode", "Insert mode typing in vim", 
         ["Type \"vim hello.txt\"", "Enter", "Sleep 800ms", "Type \"i\"", "Sleep 300ms", 
          "Type \"Hello World!\"", "Sleep 400ms", "Escape", "Sleep 300ms", "Type \":wq\"", "Enter"]),
        
        ("vim config.py", "Using vim arrow keys for navigation and editing", "Arrow key navigation in vim",
         ["Type \"vim config.py\"", "Enter", "Sleep 800ms", "Type \"i\"", "Sleep 200ms",
          "Type \"# Configuration file\"", "Sleep 300ms", "Escape", "Sleep 200ms",
          "Down 2", "Type \"i\"", "Sleep 200ms", "Type \"debug = True\"", "Sleep 300ms",
          "Escape", "Sleep 200ms", "Type \":wq\"", "Enter"]),
        
        ("vim data.json", "Vim editing with backspace corrections", "Correcting typos in vim",
         ["Type \"vim data.json\"", "Enter", "Sleep 800ms", "Type \"i\"", "Sleep 200ms",
          "Type \"{\\\"namme\\\": \\\"John\\\"}\"", "Sleep 400ms", "Left 8", "Backspace 2",
          "Type \"e\"", "Sleep 300ms", "Escape", "Sleep 200ms", "Type \":wq\"", "Enter"]),
        
        ("vim script.sh", "Using vim search functionality with escape", "Searching in vim",
         ["Type \"vim script.sh\"", "Enter", "Sleep 800ms", "Type \"/echo\"", "Enter",
          "Sleep 400ms", "Type \"n\"", "Sleep 300ms", "Escape", "Sleep 200ms",
          "Type \":q!\"", "Enter"]),
        
        ("vim README.md", "Multi-line editing in vim with arrow navigation", "Multi-line vim editing",
         ["Type \"vim README.md\"", "Enter", "Sleep 800ms", "Type \"i\"", "Sleep 200ms",
          "Type \"# Project\"", "Enter", "Type \"Description here\"", "Sleep 400ms",
          "Escape", "Sleep 200ms", "Up 1", "Type \"A\"", "Type \" Title\"", "Sleep 300ms",
          "Escape", "Sleep 200ms", "Type \":wq\"", "Enter"])
    ]
    
    for i in range(200):
        scenario_type = vim_basics[i % len(vim_basics)]
        scenario_id = i + 1
        
        require_cmd = "Require vim"
        instruction = f"Interactive vim session: {scenario_type[1]}. User opens vim, uses keyboard navigation (arrows, insert, escape), makes edits, and saves the file."
        class_dict = {"Editors": True, "Files": True}
        
        commands = ["Sleep 300ms"] + scenario_type[3] + ["Sleep 500ms"]
        command_str = "\n".join(commands)
        
        scenarios.append((require_cmd, instruction, class_dict, command_str))
    
    return scenarios

def generate_command_history_scenarios() -> List[Tuple[str, str, Dict[str, bool], str]]:
    """Generate 150 command line history scenarios."""
    scenarios = []
    
    history_patterns = [
        ("Up arrow history navigation", "Navigating command history with arrow keys",
         ["Sleep 200ms", "Type \"ls -la\"", "Enter", "Sleep 400ms", "Type \"pwd\"", "Enter",
          "Sleep 400ms", "Up 1", "Sleep 300ms", "Enter", "Sleep 300ms", "Up 2", "Sleep 300ms", "Enter"]),
        
        ("Ctrl+R reverse search", "Using Ctrl+R for reverse history search",
         ["Sleep 200ms", "Type \"echo test\"", "Enter", "Sleep 400ms", "Type \"ls -la\"", "Enter",
          "Sleep 400ms", "Ctrl+R", "Sleep 300ms", "Type \"echo\"", "Sleep 500ms", "Enter"]),
        
        ("Command history with tab completion", "Using up arrows and tab completion",
         ["Sleep 200ms", "Type \"cd /usr/loc\"", "Tab", "Sleep 300ms", "Enter", "Sleep 400ms",
          "Type \"ls\"", "Enter", "Sleep 400ms", "Up 2", "Sleep 200ms", "Enter"]),
        
        ("History navigation and editing", "Navigating history and editing commands",
         ["Sleep 200ms", "Type \"grep test file.txt\"", "Enter", "Sleep 400ms", "Up 1",
          "Sleep 200ms", "Left 8", "Backspace 4", "Type \"data\"", "Sleep 300ms", "Enter"]),
        
        ("Multiple history commands", "Using multiple up/down arrow navigations",
         ["Sleep 200ms", "Type \"date\"", "Enter", "Sleep 300ms", "Type \"whoami\"", "Enter",
          "Sleep 300ms", "Type \"uname -a\"", "Enter", "Sleep 400ms", "Up 1", "Sleep 200ms",
          "Up 1", "Sleep 200ms", "Down 1", "Sleep 200ms", "Enter"])
    ]
    
    for i in range(150):
        pattern = history_patterns[i % len(history_patterns)]
        
        require_cmd = "Require bash"
        instruction = f"Command history interaction: {pattern[1]}. User demonstrates shell history navigation using arrow keys, Ctrl+R search, and command editing."
        class_dict = {"Basic": True}
        
        command_str = "\n".join(pattern[2] + ["Sleep 500ms"])
        
        scenarios.append((require_cmd, instruction, class_dict, command_str))
    
    return scenarios

def generate_file_navigation_scenarios() -> List[Tuple[str, str, Dict[str, bool], str]]:
    """Generate 150 file navigation scenarios."""
    scenarios = []
    
    nav_patterns = [
        ("Tab completion for files", "Using tab completion to navigate files",
         ["Sleep 200ms", "Type \"ls Doc\"", "Tab", "Sleep 300ms", "Enter", "Sleep 400ms",
          "Type \"cd Doc\"", "Tab", "Sleep 300ms", "Enter"]),
        
        ("Long directory listing with PageDown", "Scrolling through long ls output",
         ["Sleep 200ms", "Type \"ls -la /usr/bin\"", "Enter", "Sleep 800ms", "PageDown 3",
          "Sleep 400ms", "PageUp 2", "Sleep 300ms"]),
        
        ("File completion with multiple tabs", "Using multiple tab presses for completion",
         ["Sleep 200ms", "Type \"cat read\"", "Tab", "Sleep 300ms", "Tab", "Sleep 400ms",
          "Type \"me\"", "Tab", "Sleep 300ms", "Enter"]),
        
        ("Arrow navigation in file lists", "Using arrows to select from file lists",
         ["Sleep 200ms", "Type \"find . -name \\\"*.txt\\\"\"", "Enter", "Sleep 600ms",
          "Up 2", "Sleep 300ms", "Down 1", "Sleep 300ms"]),
        
        ("Directory navigation with completion", "Tab completion for directory navigation",
         ["Sleep 200ms", "Type \"cd /var/l\"", "Tab", "Sleep 300ms", "Enter", "Sleep 400ms",
          "Type \"ls\"", "Enter", "Sleep 400ms"])
    ]
    
    for i in range(150):
        pattern = nav_patterns[i % len(nav_patterns)]
        
        require_cmd = "Require ls\nRequire find"
        instruction = f"File navigation: {pattern[1]}. User demonstrates file system navigation using tab completion, arrow keys, and pagination for long file lists."
        class_dict = {"Files": True, "FS": True}
        
        command_str = "\n".join(pattern[2] + ["Sleep 500ms"])
        
        scenarios.append((require_cmd, instruction, class_dict, command_str))
    
    return scenarios

def generate_interactive_program_scenarios() -> List[Tuple[str, str, Dict[str, bool], str]]:
    """Generate 150 interactive program scenarios."""
    scenarios = []
    
    interactive_patterns = [
        ("top navigation", "Using top with arrow keys and q to quit",
         ["Sleep 200ms", "Type \"top\"", "Enter", "Sleep 1000ms", "Down 3", "Sleep 400ms",
          "Up 1", "Sleep 400ms", "Type \"q\""], "Require top"),
        
        ("less file navigation", "Navigating a file with less using space and arrows",
         ["Sleep 200ms", "Type \"cat /etc/passwd | less\"", "Enter", "Sleep 600ms",
          "Space 2", "Sleep 400ms", "PageDown 1", "Sleep 400ms", "PageUp 1", "Sleep 300ms",
          "Type \"q\""], "Require less"),
        
        ("more command navigation", "Using more with space bar navigation",
         ["Sleep 200ms", "Type \"ls -la /usr/bin | more\"", "Enter", "Sleep 600ms",
          "Space 3", "Sleep 400ms", "Type \"q\""], "Require more"),
        
        ("man page navigation", "Navigating man pages with arrows and q",
         ["Sleep 200ms", "Type \"man ls\"", "Enter", "Sleep 800ms", "Down 5", "Sleep 400ms",
          "PageDown 2", "Sleep 400ms", "Up 3", "Sleep 300ms", "Type \"q\""], "Require man"),
        
        ("htop interactive usage", "Using htop with arrow navigation",
         ["Sleep 200ms", "Type \"htop\"", "Enter", "Sleep 1000ms", "Right 2", "Sleep 300ms",
          "Left 1", "Sleep 300ms", "Down 4", "Sleep 400ms", "Type \"q\""], "Require htop")
    ]
    
    for i in range(150):
        pattern = interactive_patterns[i % len(interactive_patterns)]
        
        require_cmd = pattern[3]
        instruction = f"Interactive program: {pattern[1]}. User demonstrates navigation within interactive terminal programs using keyboard controls and proper exit procedures."
        class_dict = {"Process": True, "Basic": True}
        
        command_str = "\n".join(pattern[2] + ["Sleep 500ms"])
        
        scenarios.append((require_cmd, instruction, class_dict, command_str))
    
    return scenarios

def generate_terminal_control_scenarios() -> List[Tuple[str, str, Dict[str, bool], str]]:
    """Generate 100 terminal control scenarios."""
    scenarios = []
    
    control_patterns = [
        ("Ctrl+C interrupt", "Interrupting a long-running command with Ctrl+C",
         ["Sleep 200ms", "Type \"ping google.com\"", "Enter", "Sleep 1200ms", "Ctrl+C", "Sleep 400ms"]),
        
        ("Ctrl+Z suspend", "Suspending a process with Ctrl+Z",
         ["Sleep 200ms", "Type \"nano test.txt\"", "Enter", "Sleep 800ms", "Type \"Some text\"",
          "Sleep 400ms", "Ctrl+Z", "Sleep 400ms"]),
        
        ("Ctrl+L clear screen", "Clearing terminal screen with Ctrl+L",
         ["Sleep 200ms", "Type \"ls\"", "Enter", "Sleep 400ms", "Type \"pwd\"", "Enter",
          "Sleep 400ms", "Ctrl+L", "Sleep 500ms"]),
        
        ("Ctrl+D exit", "Exiting shell or program with Ctrl+D",
         ["Sleep 200ms", "Type \"python3\"", "Enter", "Sleep 800ms", "Type \"print('hello')\"",
          "Enter", "Sleep 400ms", "Ctrl+D", "Sleep 400ms"]),
        
        ("Ctrl+R history search", "Using Ctrl+R for command history search",
         ["Sleep 200ms", "Type \"echo test123\"", "Enter", "Sleep 400ms", "Ctrl+R",
          "Sleep 300ms", "Type \"echo\"", "Sleep 500ms", "Enter"])
    ]
    
    for i in range(100):
        pattern = control_patterns[i % len(control_patterns)]
        
        require_cmd = "Require bash"
        instruction = f"Terminal control: {pattern[1]}. User demonstrates terminal control key combinations for process management and navigation."
        class_dict = {"Process": True, "Basic": True}
        
        command_str = "\n".join(pattern[2] + ["Sleep 500ms"])
        
        scenarios.append((require_cmd, instruction, class_dict, command_str))
    
    return scenarios

def generate_copy_paste_scenarios() -> List[Tuple[str, str, Dict[str, bool], str]]:
    """Generate 100 copy/paste operation scenarios."""
    scenarios = []
    
    clipboard_patterns = [
        ("Copy command output", "Copying command output to clipboard",
         ["Sleep 200ms", "Type \"echo 'important data' | pbcopy\"", "Enter", "Sleep 400ms",
          "Type \"pbpaste\"", "Enter", "Sleep 400ms"]),
        
        ("Copy file content", "Copying file content to clipboard",
         ["Sleep 200ms", "Type \"cat ~/.bashrc | head -5 | pbcopy\"", "Enter", "Sleep 600ms",
          "Type \"pbpaste\"", "Enter", "Sleep 400ms"]),
        
        ("Paste into command", "Pasting clipboard content into a command",
         ["Sleep 200ms", "Type \"echo 'test data' | pbcopy\"", "Enter", "Sleep 400ms",
          "Type \"echo \\\"Copied: $(pbpaste)\\\"\"", "Enter", "Sleep 400ms"]),
        
        ("Copy URL and use", "Copying a URL and using it in curl",
         ["Sleep 200ms", "Type \"echo 'https://httpbin.org/ip' | pbcopy\"", "Enter", "Sleep 400ms",
          "Type \"curl $(pbpaste)\"", "Enter", "Sleep 800ms"]),
        
        ("Multi-step copy paste", "Multiple copy/paste operations",
         ["Sleep 200ms", "Type \"pwd | pbcopy\"", "Enter", "Sleep 400ms",
          "Type \"echo \\\"Current dir: $(pbpaste)\\\"\"", "Enter", "Sleep 400ms",
          "Type \"date | pbcopy\"", "Enter", "Sleep 400ms", "Type \"pbpaste\"", "Enter"])
    ]
    
    for i in range(100):
        pattern = clipboard_patterns[i % len(clipboard_patterns)]
        
        require_cmd = "Require pbcopy\nRequire pbpaste"
        instruction = f"Clipboard operations: {pattern[1]}. User demonstrates copying data to clipboard and pasting it in various contexts."
        class_dict = {"Basic": True, "Misc": True}
        
        command_str = "\n".join(pattern[2] + ["Sleep 500ms"])
        
        scenarios.append((require_cmd, instruction, class_dict, command_str))
    
    return scenarios

def generate_correction_scenarios() -> List[Tuple[str, str, Dict[str, bool], str]]:
    """Generate 150 correction scenarios."""
    scenarios = []
    
    correction_patterns = [
        ("Backspace correction", "Correcting typos with backspace",
         ["Sleep 200ms", "Type \"ls -laa\"", "Sleep 200ms", "Backspace 1", "Sleep 200ms", "Enter"]),
        
        ("Arrow and backspace", "Using arrows to navigate and correct",
         ["Sleep 200ms", "Type \"cat fiile.txt\"", "Sleep 300ms", "Left 7", "Sleep 200ms",
          "Backspace 1", "Sleep 200ms", "Right 7", "Sleep 200ms", "Enter"]),
        
        ("Delete key correction", "Using delete key for corrections",
         ["Sleep 200ms", "Type \"echho hello\"", "Sleep 300ms", "Left 8", "Sleep 200ms",
          "Delete 1", "Sleep 200ms", "Right 8", "Sleep 200ms", "Enter"]),
        
        ("Insert mode correction", "Using insert key and retyping",
         ["Sleep 200ms", "Type \"mkdir folder\"", "Sleep 300ms", "Left 6", "Sleep 200ms",
          "Insert", "Sleep 200ms", "Type \"new_\"", "Sleep 300ms", "Insert", "Sleep 200ms",
          "Right 6", "Sleep 200ms", "Enter"]),
        
        ("Complex correction", "Multiple correction steps",
         ["Sleep 200ms", "Type \"cp source.txt desination.txt\"", "Sleep 400ms", "Left 4",
          "Sleep 200ms", "Backspace 2", "Sleep 200ms", "Type \"t\"", "Sleep 200ms",
          "Right 4", "Sleep 200ms", "Enter"])
    ]
    
    for i in range(150):
        pattern = correction_patterns[i % len(correction_patterns)]
        
        require_cmd = "Require bash"
        instruction = f"Command correction: {pattern[1]}. User types a command with mistakes and demonstrates various correction techniques using backspace, delete, arrows, and insert keys."
        class_dict = {"Basic": True}
        
        command_str = "\n".join(pattern[2] + ["Sleep 500ms"])
        
        scenarios.append((require_cmd, instruction, class_dict, command_str))
    
    return scenarios

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("engine/cli/vhs/generated/interactive"),
        help="Directory for generated tapes",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=1000,
        help="Maximum number of tapes to emit",
    )
    return parser.parse_args()


def main() -> None:
    """Generate all VHS tape files across scripted scenarios."""
    args = parse_args()

    print("Generating VHS tape files with keyboard interactions...")
    
    # Generate all scenario types
    all_scenarios = []
    
    print("Generating vim/editor scenarios (200 files)...")
    all_scenarios.extend(generate_vim_scenarios())
    
    print("Generating command history scenarios (150 files)...")
    all_scenarios.extend(generate_command_history_scenarios())
    
    print("Generating file navigation scenarios (150 files)...")
    all_scenarios.extend(generate_file_navigation_scenarios())
    
    print("Generating interactive program scenarios (150 files)...")
    all_scenarios.extend(generate_interactive_program_scenarios())
    
    print("Generating terminal control scenarios (100 files)...")
    all_scenarios.extend(generate_terminal_control_scenarios())
    
    print("Generating copy/paste scenarios (100 files)...")
    all_scenarios.extend(generate_copy_paste_scenarios())
    
    print("Generating correction scenarios (150 files)...")
    all_scenarios.extend(generate_correction_scenarios())
    
    print(f"Total scenarios generated: {len(all_scenarios)}")

    output_path = args.output_dir
    ensure_output_dir(output_path)

    limit = max(1, args.limit)

    for index, (require_cmd, instruction, class_dict, commands) in enumerate(all_scenarios, 1):
        if index > limit:
            break

        tape_id = f"interactive_{index:03d}"
        body = [line for line in commands.splitlines() if line.strip()]
        metadata = TapeMetadata(
            tape_id=tape_id,
            instruction=sanitize_instruction(instruction),
            active_classes=class_dict,
            level=2,
            interactive=True,
            events=estimate_events(body),
            visual_complexity=estimate_visual_complexity(body),
            requires=parse_requirements(require_cmd),
            body_lines=body,
            output_name=f"tape_interactive_{index:03d}.webm",
        )

        destination = output_path / f"{tape_id}.tape"
        destination.write_text(render_tape(metadata), encoding="utf-8")

        if index % 100 == 0:
            print(f"Generated {index} tape files...")

    generated = min(len(all_scenarios), limit)
    print(f"Successfully generated {generated} VHS tape files!")
    print(f"Files saved to: {output_path}")

if __name__ == "__main__":
    main()
