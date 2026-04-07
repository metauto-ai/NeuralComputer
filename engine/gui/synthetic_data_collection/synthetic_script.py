#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import multiprocessing
import os
import re
import subprocess
import time
from functools import partial
from pathlib import Path

SCREEN_WIDTH = 1024
SCREEN_HEIGHT = 768


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _resolve_output_dir(raw_path: str | None = None) -> Path:
    raw = (raw_path or os.getenv("SYNTH_OUTPUT_DIR", "raw_data")).strip()
    target = Path(raw).expanduser()
    if not target.is_absolute():
        target = (Path.cwd() / target).resolve()
    return target


def _require_docker_image(image: str) -> None:
    result = subprocess.run(
        ["docker", "image", "inspect", image],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if result.returncode != 0:
        raise SystemExit(
            f"Missing Docker image '{image}'.\n"
            "Build it with:\n"
            "  python main.py guiworld synthetic  # (auto-builds synthetic image)\n"
            "or:\n"
            "  (cd ../.. && python main.py guiworld build-image --tag computer-use-gui:local)\n"
            "  (cd . && docker build -t synthetic-data-collection:local .)\n"
        )


def _parse_memory_limit_to_gb(memory_limit: str) -> float | None:
    """Parse docker --memory values like 2048m, 2g into GB for worker heuristics."""
    raw = memory_limit.strip().lower()
    if not raw:
        return None
    match = re.fullmatch(r"(?P<num>\\d+(?:\\.\\d+)?)(?P<unit>[bkmg]?)", raw)
    if not match:
        return None
    value = float(match.group("num"))
    unit = match.group("unit") or "g"
    if unit == "b":
        return value / (1024**3)
    if unit == "k":
        return value / (1024**2)
    if unit == "m":
        return value / 1024
    if unit == "g":
        return value
    return None


def initialize_clean_state(
    *,
    base_image: str,
    screen_width: int,
    screen_height: int,
    cursor_theme: str,
    cursor_size: int,
    ui_font_size: int,
    desktop_icon_size: int,
    vscode_zoom: int,
    vscode_font_size: int,
    vscode_terminal_font_size: int,
) -> str:
    """Create and save a clean container state with initialized desktop"""
    print("Initializing clean container state...")
    
    # Start a container and let it initialize
    base_container_id = subprocess.check_output(
        [
            "docker",
            "run",
            "-d",
            "--hostname",
            "world-program-clean",
            "--env",
            "DISPLAY=:1",
            "--env",
            f"SCREEN_WIDTH={screen_width}",
            "--env",
            f"SCREEN_HEIGHT={screen_height}",
            "--env",
            f"CURSOR_THEME={cursor_theme}",
            "--env",
            f"CURSOR_SIZE={cursor_size}",
            "--env",
            f"UI_FONT_SIZE={ui_font_size}",
            "--env",
            f"DESKTOP_ICON_SIZE={desktop_icon_size}",
            "--env",
            f"VSCODE_ZOOM={vscode_zoom}",
            "--env",
            f"VSCODE_FONT_SIZE={vscode_font_size}",
            "--env",
            f"VSCODE_TERMINAL_FONT_SIZE={vscode_terminal_font_size}",
            base_image,
            "/home/computeruse/start.sh",
        ],
        text=True,
    ).strip()
    
    try:
        # Wait for XFCE to fully initialize
        time.sleep(5)

        # Save the clean state
        clean_state = subprocess.check_output(
            ["docker", "commit", base_container_id],
            text=True,
        ).strip()
        return clean_state
    finally:
        # Clean up the initialization container
        subprocess.run(["docker", "rm", "-f", base_container_id], check=False)

def record_trajectory(container_id, trajectory_data, record_idx):
    """Send trajectory data to container and record"""
    # Convert numpy arrays to lists for JSON serialization
    def convert_trajectory(traj):
        return [
            ((int(d['pos'][0]), int(d['pos'][1])), True if d['left_click'] else False, True if d['right_click'] else False, list(d['key_events']))  # Use Python's True/False
            for d in traj
        ]
    
    # Convert and serialize
    trajectory_list = convert_trajectory(trajectory_data)
    
    # Create a temporary Python script in the container
    script_content = f'''
import sys
import traceback

sys.path.append('/home/computeruse')  # Add app directory to Python path

try:
    import os
    from record_script import record

    print("Python path:", sys.path)
    print("Contents of /home/computeruse:", os.listdir('/home/computeruse'))
    print("Current working directory:", os.getcwd())

    trajectory_data = {trajectory_list!r}  # Direct Python literal
    print("Starting recording with trajectory:", len(trajectory_data), "points")

    record(
        "",
        f"record_{record_idx}",
        duration=30,
        fps=15,
        trajectory=trajectory_data
    )
except Exception as e:
    print("Error occurred:")
    traceback.print_exc()
    sys.exit(1)
'''
    
    # Write the script to a temporary file in the container
    temp_script = f'/tmp/record_script_{record_idx}.py'
    cmd_write = [
        'docker', 'exec', container_id,
        'bash', '-c', f'cat > {temp_script} << \'EOL\'\n{script_content}\nEOL'
    ]
    subprocess.run(cmd_write, check=True)
    
    # Execute the script with proper Python path
    cmd_execute = [
        'docker', 'exec',
        '-e', 'DISPLAY=:1',
        '-e', 'PYTHONPATH=/home/computeruse',
        container_id,
        'bash', '-c',
        f'''
set -x  # Print commands as they execute
export PYTHONUNBUFFERED=1  # Ensure Python output isn't buffered

# Debug info
echo "Current environment:"
env | grep DISPLAY
env | grep PYTHON
echo "Contents of /home/computeruse:"
ls -la /home/computeruse/
echo "X server status:"
xdpyinfo | head -n 5 || echo "X server not running"
echo "Process status:"
ps aux | grep X

# Run the script with full error output
cd /home/computeruse  # Change to app directory
python3 -u {temp_script}
'''
    ]
    
    # Run with output capture
    result = subprocess.run(cmd_execute, capture_output=True, text=True)
    print("Command output:")
    print(result.stdout)
    print("Error output:")
    print(result.stderr)
    result.check_returncode()

def process_trajectory(
    args,
    screen_width,
    screen_height,
    clean_state,
    memory_limit,
    output_dir: Path,
    cursor_theme: str,
    cursor_size: int,
    ui_font_size: int,
    desktop_icon_size: int,
    vscode_zoom: int,
    vscode_font_size: int,
    vscode_terminal_font_size: int,
    max_retries=3,
):
    """Process a single trajectory in its own container with retries"""
    trajectory_idx, trajectory = args
    
    for attempt in range(max_retries):
        try:
            print(f"Recording trajectory {trajectory_idx} (attempt {attempt + 1}/{max_retries})")
            
            # Create a fresh container from clean state
            raw_data_host = str(output_dir.resolve())
            docker_cmd = [
                "docker",
                "run",
                "-d",
                "-v",
                f"{raw_data_host}:/home/computeruse/agent_recordings",
                "--hostname",
                "world-program-synthetic",
                "--env",
                "DISPLAY=:1",
                "--env",
                f"SCREEN_WIDTH={screen_width}",
                "--env",
                f"SCREEN_HEIGHT={screen_height}",
                "--env",
                f"CURSOR_THEME={cursor_theme}",
                "--env",
                f"CURSOR_SIZE={cursor_size}",
                "--env",
                f"UI_FONT_SIZE={ui_font_size}",
                "--env",
                f"DESKTOP_ICON_SIZE={desktop_icon_size}",
                "--env",
                f"VSCODE_ZOOM={vscode_zoom}",
                "--env",
                f"VSCODE_FONT_SIZE={vscode_font_size}",
                "--env",
                f"VSCODE_TERMINAL_FONT_SIZE={vscode_terminal_font_size}",
            ]
            if memory_limit:
                docker_cmd += ["--memory", memory_limit]
            docker_cmd += [
                clean_state,
                "/home/computeruse/start.sh",
            ]

            container_id = subprocess.check_output(docker_cmd, text=True).strip()
            
            success = False
            
            try:
                time.sleep(20)  # Wait for container to initialize
                record_trajectory(container_id, trajectory, trajectory_idx)
                success = True
            finally:
                # Always clean up the container
                subprocess.run(['docker', 'rm', '-f', container_id], check=False)
            
            if success:  # Only return after container cleanup
                return
                
        except Exception as e:
            print(f"Attempt {attempt + 1} failed for trajectory {trajectory_idx}: {str(e)}")
            if attempt == max_retries - 1:  # Last attempt
                print(f"All {max_retries} attempts failed for trajectory {trajectory_idx}")
                print (e)  # Re-raise the last exception
                print ('Ignoring this error')
                print ('*'*100)
            time.sleep(2)  # Wait a bit before retrying

def create_synthetic_dataset(
    *,
    count: int,
    max_workers: int | None,
    memory_per_worker: str,
    screen_width: int,
    screen_height: int,
    duration: int,
    fps: int,
    max_retries: int,
    base_image: str,
    cursor_theme: str,
    cursor_size: int,
    ui_font_size: int,
    desktop_icon_size: int,
    vscode_zoom: int,
    vscode_font_size: int,
    vscode_terminal_font_size: int,
    output_dir: Path | None = None,
):
    """Create synthetic dataset with both frame data and converted actions"""
    try:
        import psutil  # type: ignore
        from tqdm import tqdm  # type: ignore
    except ImportError as exc:  # pragma: no cover
        raise SystemExit(
            "Missing Python dependencies for synthetic runs.\n"
            "Install them with:\n"
            "  pip3 install -r requirements.txt\n"
            f"Original error: {exc}"
        ) from exc

    try:
        from synthetic_mouse_path import generate_multiple_trajectories  # type: ignore
    except ImportError as exc:  # pragma: no cover
        raise SystemExit(
            "Failed to import synthetic trajectory generator.\n"
            "Install dependencies with:\n"
            "  pip3 install -r requirements.txt\n"
            f"Original error: {exc}"
        ) from exc

    base_dir = _resolve_output_dir(str(output_dir) if output_dir else None)
    actions_dir = base_dir / 'actions'
    videos_dir = base_dir / 'videos'
    actions_dir.mkdir(parents=True, exist_ok=True)
    videos_dir.mkdir(parents=True, exist_ok=True)
    print(f"Synthetic output root: {base_dir}")

    def get_next_index() -> int:
        """Scan existing artifacts and return the next index to use.

        Looks for files like actions_#.json, record_#.csv, record_#.mp4 and
        returns max(existing indices) + 1. If none exist, returns 0.
        """
        pattern = re.compile(r'.*_(\d+)\.(json|csv|mp4)$')
        max_idx = -1
        for p in list(actions_dir.glob('actions_*.json')) + \
                 list(actions_dir.glob('record_*.csv')) + \
                 list(videos_dir.glob('record_*.mp4')):
            m = pattern.match(p.name)
            if m:
                try:
                    idx = int(m.group(1))
                    if idx > max_idx:
                        max_idx = idx
                except ValueError:
                    pass
        return max_idx + 1

    # Determine starting index based on existing files
    start_index = get_next_index()
    
    # Calculate optimal number of workers based on system resources
    total_memory_gb = psutil.virtual_memory().total / (1024**3)  # Convert to GB
    num_cpus = os.cpu_count() or 1
    
    if max_workers is None:
        # Calculate based on available resources
        reserve_gb = 4
        per_worker_gb = _parse_memory_limit_to_gb(memory_per_worker) or 2.0
        max_by_memory = max(1, int((total_memory_gb - reserve_gb) // per_worker_gb))
        max_by_cpu = max(1, num_cpus - 2)  # Leave 2 CPU cores for system
        max_workers = max(1, min(max_by_memory, max_by_cpu))
        
        # For very large machines, maybe cap at 32 or adjust based on your needs
        max_workers = min(max_workers, 64)  # Optional cap
        # max_workers = min(max_workers, 2)  # Optional cap

    print(f"System resources: {num_cpus} CPUs, {total_memory_gb:.1f}GB RAM")
    print(f"Using {max_workers} workers")
    
    # Initialize clean state first
    _require_docker_image(base_image)
    clean_state = initialize_clean_state(
        base_image=base_image,
        screen_width=screen_width,
        screen_height=screen_height,
        cursor_theme=cursor_theme,
        cursor_size=cursor_size,
        ui_font_size=ui_font_size,
        desktop_icon_size=desktop_icon_size,
        vscode_zoom=vscode_zoom,
        vscode_font_size=vscode_font_size,
        vscode_terminal_font_size=vscode_terminal_font_size,
    )
    
    try:
        # Generate all trajectories first with progress bar
        print("Generating all trajectories and converting to actions...")
        trajectories, actions_list = generate_multiple_trajectories(
            count,
            screen_width,
            screen_height,
            duration=duration,
            fps=fps,
        )
        
        # Save converted actions to JSON files
        print("Saving converted actions...")
        for i, actions in enumerate(actions_list):
            out_idx = start_index + i
            # Save individual trajectory actions
            actions_file = actions_dir / f'actions_{out_idx}.json'
            with open(actions_file, 'w') as f:
                json.dump({
                    'metadata': {
                        'trajectory_id': out_idx,
                        'source': 'synthetic_trajectory',
                        'fps': fps,
                        'total_actions': len(actions)
                    },
                    'actions': actions
                }, f, indent=2)
        
        # Save combined actions file
        all_actions = []
        for i, actions in enumerate(actions_list):
            all_actions.extend(actions)
        
        combined_file = actions_dir / "all_actions.json"
        with open(combined_file, 'w') as f:
                json.dump({
                    'metadata': {
                        'source': 'synthetic_trajectory',
                        'fps': fps,
                        'total_trajectories': len(trajectories),
                        'total_actions': len(all_actions)
                    },
                    'actions': all_actions
                }, f, indent=2)
        
        print(f"✅ Saved {len(actions_list)} action files and combined file")
        
        # Process in parallel with resource limits and progress bar
        def index_adjusted_args(item):
            idx, traj = item
            return (start_index + idx, traj)

        process_func = partial(
            process_trajectory,
            screen_width=screen_width,
            screen_height=screen_height,
            clean_state=clean_state,
            memory_limit=memory_per_worker,
            output_dir=base_dir,
            cursor_theme=cursor_theme,
            cursor_size=cursor_size,
            ui_font_size=ui_font_size,
            desktop_icon_size=desktop_icon_size,
            vscode_zoom=vscode_zoom,
            vscode_font_size=vscode_font_size,
            vscode_terminal_font_size=vscode_terminal_font_size,
            max_retries=max_retries,
        )
        
        with multiprocessing.Pool(max_workers) as pool:
            list(tqdm(
                pool.imap(process_func, map(index_adjusted_args, enumerate(trajectories))),
                total=len(trajectories),
                desc="Processing trajectories"
            ))
    
    finally:
        # Cleanup
        subprocess.run(['docker', 'rmi', clean_state], check=True)
        subprocess.run('docker container prune -f', shell=True, check=False)

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate synthetic GUI trajectories using Docker.")
    parser.add_argument(
        "--count",
        type=int,
        default=1,
        help="How many trajectories to generate (default: 1).",
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=None,
        help="Max parallel workers (default: auto).",
    )
    parser.add_argument(
        "--memory-per-worker",
        default="2g",
        help="Docker --memory limit per worker container (default: 2g).",
    )
    parser.add_argument("--screen-width", type=int, default=SCREEN_WIDTH)
    parser.add_argument("--screen-height", type=int, default=SCREEN_HEIGHT)
    parser.add_argument("--duration", type=int, default=30, help="Seconds per trajectory.")
    parser.add_argument("--fps", type=int, default=15, help="Recording FPS.")
    parser.add_argument("--retries", type=int, default=3, help="Max retries per trajectory.")
    parser.add_argument(
        "--image",
        default="synthetic-data-collection:local",
        help="Base Docker image to use (default: synthetic-data-collection:local).",
    )
    parser.add_argument(
        "--cursor-theme",
        default=os.getenv("CURSOR_THEME", "Adwaita"),
        help="Cursor theme for desktop sessions (default: $CURSOR_THEME or Adwaita).",
    )
    parser.add_argument(
        "--cursor-size",
        type=int,
        default=_env_int("CURSOR_SIZE", 40),
        help="Cursor size for desktop sessions (default: $CURSOR_SIZE or 40).",
    )
    parser.add_argument(
        "--ui-font-size",
        type=int,
        default=_env_int("UI_FONT_SIZE", 13),
        help="System UI font size (default: $UI_FONT_SIZE or 13).",
    )
    parser.add_argument(
        "--desktop-icon-size",
        type=int,
        default=_env_int("DESKTOP_ICON_SIZE", 96),
        help="Desktop icon size (default: $DESKTOP_ICON_SIZE or 96).",
    )
    parser.add_argument(
        "--vscode-zoom",
        type=int,
        default=_env_int("VSCODE_ZOOM", 1),
        help="VS Code window zoom (default: $VSCODE_ZOOM or 1).",
    )
    parser.add_argument(
        "--vscode-font-size",
        type=int,
        default=_env_int("VSCODE_FONT_SIZE", 18),
        help="VS Code editor font size (default: $VSCODE_FONT_SIZE or 18).",
    )
    parser.add_argument(
        "--vscode-terminal-font-size",
        type=int,
        default=_env_int("VSCODE_TERMINAL_FONT_SIZE", 16),
        help="VS Code terminal font size (default: $VSCODE_TERMINAL_FONT_SIZE or 16).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help=(
            "Host output directory for synthetic data "
            "(default: $SYNTH_OUTPUT_DIR or ./raw_data)."
        ),
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    if args.count <= 0:
        raise SystemExit("--count must be positive")
    if args.max_workers is not None and args.max_workers <= 0:
        raise SystemExit("--max-workers must be positive")
    if args.duration <= 0:
        raise SystemExit("--duration must be positive")
    if args.fps <= 0:
        raise SystemExit("--fps must be positive")
    if args.retries < 0:
        raise SystemExit("--retries must be >= 0")
    if args.cursor_size <= 0:
        raise SystemExit("--cursor-size must be positive")
    if args.ui_font_size <= 0:
        raise SystemExit("--ui-font-size must be positive")
    if args.desktop_icon_size <= 0:
        raise SystemExit("--desktop-icon-size must be positive")
    if args.vscode_font_size <= 0:
        raise SystemExit("--vscode-font-size must be positive")
    if args.vscode_terminal_font_size <= 0:
        raise SystemExit("--vscode-terminal-font-size must be positive")

    resolved_output_dir = _resolve_output_dir(str(args.output_dir) if args.output_dir else None)
    resolved_output_dir.mkdir(parents=True, exist_ok=True)
    create_synthetic_dataset(
        count=args.count,
        max_workers=args.max_workers,
        memory_per_worker=args.memory_per_worker,
        screen_width=args.screen_width,
        screen_height=args.screen_height,
        duration=args.duration,
        fps=args.fps,
        max_retries=args.retries,
        base_image=args.image,
        cursor_theme=args.cursor_theme,
        cursor_size=args.cursor_size,
        ui_font_size=args.ui_font_size,
        desktop_icon_size=args.desktop_icon_size,
        vscode_zoom=args.vscode_zoom,
        vscode_font_size=args.vscode_font_size,
        vscode_terminal_font_size=args.vscode_terminal_font_size,
        output_dir=resolved_output_dir,
    )
