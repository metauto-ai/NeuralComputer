#!/usr/bin/env python3
"""Generate Files+Editors class VHS tapes with consistent headers."""

import argparse
import random
from pathlib import Path
from typing import List

from _common import TapeMetadata, ensure_output_dir, render_tape


def sanitize_instruction(text: str) -> str:
    return text.replace("\\", "\\\\").replace('"', '\\"')

class FilesEditorsGenerator:
    def __init__(self, output_dir: Path):
        self.output_dir = Path(output_dir)
        ensure_output_dir(self.output_dir)
        self.file_counter = 200000  # Start very high to avoid conflicts
        
        # Target CLASS configuration
        self.target_class = {
            "Basic": False,
            "Files": True,
            "Text": False,
            "Process": False,
            "Network": False,
            "Package": False,
            "VCS": False,
            "Build": False,
            "Users": False,
            "Admin": False,
            "FS": False,
            "Security": False,
            "DB": False,
            "Container": False,
            "Editors": True,
            "Exec": False,
            "Misc": False
        }
        
        # File operations commands by level
        self.file_commands = {
            1: [  # Level 1 - Basic file operations
                {
                    'cmd': 'cp document.txt backup.txt',
                    'desc': 'demonstrates basic file copying using cp command',
                    'complexity': (15, 25),
                    'events': (3, 5),
                    'interactive': False
                },
                {
                    'cmd': 'mv oldfile.txt newfile.txt',
                    'desc': 'shows simple file renaming with mv command',
                    'complexity': (15, 25),
                    'events': (3, 5),
                    'interactive': False
                },
                {
                    'cmd': 'mkdir project_folder',
                    'desc': 'executes directory creation using mkdir command',
                    'complexity': (10, 20),
                    'events': (3, 4),
                    'interactive': False
                },
                {
                    'cmd': 'touch newfile.txt',
                    'desc': 'demonstrates file creation with touch command',
                    'complexity': (10, 20),
                    'events': (3, 4),
                    'interactive': False
                },
                {
                    'cmd': 'ls -l documents/',
                    'desc': 'shows directory listing with detailed file information',
                    'complexity': (15, 25),
                    'events': (3, 5),
                    'interactive': False
                },
                {
                    'cmd': 'cp -r folder1/ folder2/',
                    'desc': 'demonstrates recursive directory copying with cp',
                    'complexity': (20, 30),
                    'events': (4, 6),
                    'interactive': False
                },
                {
                    'cmd': 'rm unwanted.txt',
                    'desc': 'executes safe file deletion using rm command',
                    'complexity': (15, 25),
                    'events': (3, 5),
                    'interactive': False
                }
            ],
            2: [  # Level 2 - Advanced file operations
                {
                    'cmd': 'find . -name "*.txt" -type f',
                    'desc': 'demonstrates file searching with find command and filters',
                    'complexity': (25, 40),
                    'events': (4, 7),
                    'interactive': False
                },
                {
                    'cmd': 'chmod 755 script.sh',
                    'desc': 'shows file permission modification using chmod',
                    'complexity': (25, 40),
                    'events': (4, 6),
                    'interactive': False
                },
                {
                    'cmd': 'find /home -name "*.log" -size +1M',
                    'desc': 'executes complex file search with size criteria',
                    'complexity': (30, 45),
                    'events': (5, 8),
                    'interactive': False
                },
                {
                    'cmd': 'cp *.txt backup/',
                    'desc': 'demonstrates wildcard file copying to directory',
                    'complexity': (25, 35),
                    'events': (4, 6),
                    'interactive': False
                },
                {
                    'cmd': 'find . -type f -name "*.py" -exec wc -l {} +',
                    'desc': 'shows advanced file processing with exec command',
                    'complexity': (35, 50),
                    'events': (6, 9),
                    'interactive': False
                },
                {
                    'cmd': 'chmod -R 644 documents/',
                    'desc': 'executes recursive permission changes on directory',
                    'complexity': (30, 40),
                    'events': (5, 7),
                    'interactive': False
                },
                {
                    'cmd': 'mv *.log archive/ 2>/dev/null || echo "No log files found"',
                    'desc': 'demonstrates conditional file movement with error handling',
                    'complexity': (40, 55),
                    'events': (6, 9),
                    'interactive': False
                }
            ]
        }
        
        # Editor commands by level
        self.editor_commands = {
            1: [  # Level 1 - Basic editor usage
                {
                    'cmd': 'nano simple.txt',
                    'desc': 'demonstrates basic text editing with nano editor',
                    'complexity': (20, 30),
                    'events': (5, 8),
                    'interactive': True
                },
                {
                    'cmd': 'vim README.md',
                    'desc': 'shows basic Vim editor usage for file editing',
                    'complexity': (25, 35),
                    'events': (6, 9),
                    'interactive': True
                },
                {
                    'cmd': 'nano config.conf',
                    'desc': 'executes configuration file editing with nano',
                    'complexity': (20, 30),
                    'events': (5, 8),
                    'interactive': True
                },
                {
                    'cmd': 'vim notes.txt',
                    'desc': 'demonstrates text file editing with Vim editor',
                    'complexity': (25, 35),
                    'events': (6, 9),
                    'interactive': True
                }
            ],
            2: [  # Level 2 - Advanced editor usage
                {
                    'cmd': 'vim +10 large_file.txt',
                    'desc': 'demonstrates Vim editor with line number positioning',
                    'complexity': (35, 50),
                    'events': (7, 11),
                    'interactive': True
                },
                {
                    'cmd': 'nano -w config.yaml',
                    'desc': 'shows nano editor with word wrap disabled for configuration',
                    'complexity': (30, 45),
                    'events': (6, 10),
                    'interactive': True
                },
                {
                    'cmd': 'vim -R readonly.txt',
                    'desc': 'executes Vim in read-only mode for safe file viewing',
                    'complexity': (30, 45),
                    'events': (6, 10),
                    'interactive': True
                },
                {
                    'cmd': 'nano +5 script.py',
                    'desc': 'demonstrates nano editor with line number positioning',
                    'complexity': (35, 50),
                    'events': (7, 11),
                    'interactive': True
                },
                {
                    'cmd': 'vim -c ":set number" document.txt',
                    'desc': 'shows advanced Vim usage with command-line options',
                    'complexity': (40, 55),
                    'events': (8, 12),
                    'interactive': True
                }
            ]
        }
        
        # File types and names for variety
        self.file_types = ['txt', 'py', 'js', 'md', 'conf', 'log', 'json', 'yaml', 'sh', 'csv']
        self.file_names = ['document', 'config', 'script', 'data', 'notes', 'readme', 'backup', 'temp', 'output', 'input']
        self.dir_names = ['backup', 'archive', 'documents', 'scripts', 'data', 'config', 'logs', 'temp', 'project', 'src']
    
    def generate_file_variations(self, base_cmd, level):
        """Generate variations of file commands with different names"""
        variations = []
        
        # Replace generic names with specific ones
        for file_name in self.file_names[:5]:
            for file_ext in self.file_types[:3]:
                for dir_name in self.dir_names[:3]:
                    cmd = base_cmd
                    cmd = cmd.replace('document.txt', f'{file_name}.{file_ext}')
                    cmd = cmd.replace('newfile.txt', f'new_{file_name}.{file_ext}')
                    cmd = cmd.replace('oldfile.txt', f'old_{file_name}.{file_ext}')
                    cmd = cmd.replace('backup.txt', f'{file_name}_backup.{file_ext}')
                    cmd = cmd.replace('project_folder', f'{dir_name}_folder')
                    cmd = cmd.replace('folder1/', f'{dir_name}1/')
                    cmd = cmd.replace('folder2/', f'{dir_name}2/')
                    cmd = cmd.replace('documents/', f'{dir_name}/')
                    cmd = cmd.replace('backup/', f'{dir_name}_backup/')
                    cmd = cmd.replace('archive/', f'{dir_name}_archive/')
                    
                    if cmd != base_cmd:  # Only add if it's actually different
                        variations.append(cmd)
        
        return variations[:10]  # Limit variations

    @staticmethod
    def determine_requires(command: str) -> List[str]:
        token = command.strip().split()[0]
        return [token] if token else ["bash"]

    def generate_interactive_sequence(self, command, level, is_interactive) -> List[str]:
        """Generate VHS command sequence for a given operation."""

        if level == 1:
            type_speed = random.randint(150, 250)
            sleep_after = random.randint(1000, 2000)
        else:
            type_speed = random.randint(100, 200)
            sleep_after = random.randint(1500, 2500)

        sequence: List[str] = [
            "Sleep 500ms",
            f'Type "{command}"',
            f"Sleep {type_speed}ms",
            "Enter",
            f"Sleep {sleep_after}ms",
        ]

        if is_interactive:
            if "vim" in command:
                sequence.extend(
                    [
                        'Type "i"',
                        "Sleep 300ms",
                        'Type "Hello, this is a test edit"',
                        "Sleep 200ms",
                        "Escape",
                        "Sleep 200ms",
                        'Type ":wq"',
                        "Sleep 100ms",
                        "Enter",
                        "Sleep 500ms",
                    ]
                )
            elif "nano" in command:
                sequence.extend(
                    [
                        'Type "Hello, this is a test edit"',
                        "Sleep 200ms",
                        "Ctrl+X",
                        "Sleep 300ms",
                        'Type "y"',
                        "Sleep 200ms",
                        "Enter",
                        "Sleep 500ms",
                    ]
                )

        return sequence
    
    def generate_single_file(self, cmd_data, level, cmd_type):
        """Generate a single Files+Editors file"""
        
        command = cmd_data['cmd']
        description = cmd_data['desc']
        complexity_range = cmd_data['complexity']
        events_range = cmd_data['events']
        is_interactive = cmd_data['interactive']
        
        # Generate variations of the command
        variations = self.generate_file_variations(command, level)
        if variations:
            command = random.choice([command] + variations)
        
        # Calculate properties
        visual_complexity = random.randint(complexity_range[0], complexity_range[1])
        events = random.randint(events_range[0], events_range[1])
        
        # Generate VHS sequence
        vhs_commands = self.generate_interactive_sequence(command, level, is_interactive)

        # Create unique ID
        unique_id = f"files_editors_{self.file_counter}_{level}_{cmd_type}"

        requires = self.determine_requires(command)

        metadata = TapeMetadata(
            tape_id=unique_id,
            instruction=sanitize_instruction(description),
            active_classes=dict(self.target_class),
            level=level,
            interactive=is_interactive,
            events=events,
            visual_complexity=visual_complexity,
            requires=requires,
            body_lines=vhs_commands,
            output_name=f"{unique_id}.webm",
        )

        content = render_tape(metadata)
        filename = f"tape_{unique_id}.tape"
        self.file_counter += 1
        
        return {
            'filename': filename,
            'content': content,
            'level': level,
            'complexity': visual_complexity,
            'command': command,
            'type': cmd_type
        }
    
    def generate_files_editors_dataset(self, level1_count=1000, level2_count=1000):
        """Generate Files+Editors dataset"""
        
        print(f"🚀 Files+Editors Generator")
        print("=" * 30)
        print(f"Target CLASS: Files=true, Editors=true")
        print(f"Level 1 target: {level1_count:,} files")
        print(f"Level 2 target: {level2_count:,} files")
        
        generated_files = []
        
        # Generate Level 1 files
        print(f"\n📁 Generating Level 1 Files+Editors...")
        level1_file_target = level1_count // 2
        level1_editor_target = level1_count - level1_file_target
        
        # Level 1 file operations
        for i in range(level1_file_target):
            cmd_data = random.choice(self.file_commands[1])
            file_data = self.generate_single_file(cmd_data, 1, 'file')
            generated_files.append(file_data)
            
            if (i + 1) % 200 == 0:
                print(f"  Generated {i + 1}/{level1_file_target} Level 1 file operations...")
        
        # Level 1 editor operations
        for i in range(level1_editor_target):
            cmd_data = random.choice(self.editor_commands[1])
            file_data = self.generate_single_file(cmd_data, 1, 'editor')
            generated_files.append(file_data)
            
            if (i + 1) % 200 == 0:
                print(f"  Generated {i + 1}/{level1_editor_target} Level 1 editor operations...")
        
        # Generate Level 2 files
        print(f"\n📁 Generating Level 2 Files+Editors...")
        level2_file_target = level2_count // 2
        level2_editor_target = level2_count - level2_file_target
        
        # Level 2 file operations
        for i in range(level2_file_target):
            cmd_data = random.choice(self.file_commands[2])
            file_data = self.generate_single_file(cmd_data, 2, 'file')
            generated_files.append(file_data)
            
            if (i + 1) % 200 == 0:
                print(f"  Generated {i + 1}/{level2_file_target} Level 2 file operations...")
        
        # Level 2 editor operations
        for i in range(level2_editor_target):
            cmd_data = random.choice(self.editor_commands[2])
            file_data = self.generate_single_file(cmd_data, 2, 'editor')
            generated_files.append(file_data)
            
            if (i + 1) % 200 == 0:
                print(f"  Generated {i + 1}/{level2_editor_target} Level 2 editor operations...")
        
        print(f"\n✅ Generated {len(generated_files):,} Files+Editors files")
        
        # Show statistics
        level1_files = [f for f in generated_files if f['level'] == 1]
        level2_files = [f for f in generated_files if f['level'] == 2]
        
        print(f"\nGeneration summary:")
        print(f"  Level 1: {len(level1_files):,} files")
        print(f"  Level 2: {len(level2_files):,} files")
        
        # Complexity stats
        if generated_files:
            complexities = [f['complexity'] for f in generated_files]
            avg_complexity = sum(complexities) / len(complexities)
            print(f"  Average complexity: {avg_complexity:.1f}")
            print(f"  Complexity range: {min(complexities)} - {max(complexities)}")
        
        return generated_files
    
    def write_files_batch(self, generated_files):
        """Write generated files in batches"""
        
        print(f"\n💾 Writing {len(generated_files):,} files...")
        
        batch_size = 500
        success_count = 0
        
        for i in range(0, len(generated_files), batch_size):
            batch = generated_files[i:i + batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (len(generated_files) + batch_size - 1) // batch_size
            
            print(f"  Writing batch {batch_num}/{total_batches} ({len(batch)} files)...")
            
            for file_data in batch:
                try:
                    file_path = self.output_dir / file_data['filename']
                    file_path.write_text(file_data['content'], encoding='utf-8')
                    success_count += 1
                except Exception:
                    continue
        
        print(f"✅ Successfully wrote {success_count:,} files")
        return success_count

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("engine/cli/vhs/generated/files_editors"),
        help="Directory for generated tapes",
    )
    parser.add_argument("--level1-count", type=int, default=1000, help="Number of level 1 tapes")
    parser.add_argument("--level2-count", type=int, default=1000, help="Number of level 2 tapes")
    parser.add_argument("--seed", type=int, default=2024, help="Random seed for reproducibility")
    return parser.parse_args()


def main() -> None:
    """Generate Files+Editors dataset"""

    args = parse_args()
    random.seed(args.seed)

    output_dir = args.output_dir
    generator = FilesEditorsGenerator(output_dir)

    print("🎯 FILES+EDITORS GENERATOR")
    print("=" * 30)

    current_files = list(output_dir.glob("tape_*.tape"))
    print(f"Current total files: {len(current_files):,}")

    generated_files = generator.generate_files_editors_dataset(
        level1_count=args.level1_count,
        level2_count=args.level2_count,
    )

    written_count = generator.write_files_batch(generated_files)
    final_count = len(list(output_dir.glob("tape_*.tape")))

    print("\n🎉 FILES+EDITORS GENERATION COMPLETE!")
    print(f"  Generated Files+Editors: {written_count:,}")
    print(f"  Final total files: {final_count:,}")
    print("  New files have: Files=true, Editors=true")


if __name__ == '__main__':
    main()
