#!/usr/bin/env python3
"""Run computer-use instructions in parallel containers."""

import subprocess
import os
import time
import multiprocessing
import psutil
from pathlib import Path
from typing import List, Dict, Any
from tqdm import tqdm

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = next((p for p in [SCRIPT_DIR, *SCRIPT_DIR.parents] if (p / "main.py").is_file()), None)
if REPO_ROOT is None:
    raise SystemExit("Could not locate repo root (expected to find main.py in parent directories).")

GUI_DIR = REPO_ROOT / "engine" / "gui"
GUI_AGENT_DIR = GUI_DIR / "computer_use_agent"
GUI_RECORDINGS_DIR = REPO_ROOT / "workspace" / "videos" / "gui"
HOST_RUNTIME_DIR = SCRIPT_DIR

SCREEN_WIDTH = 1024
SCREEN_HEIGHT = 768
CONTAINER_IMAGE = "computer-use-gui:local"
DISPLAY_NUM = "1"
DEFAULT_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")
DEFAULT_FPS = int(os.getenv("GUI_RECORDING_FPS", "15"))
DEFAULT_MAX_TOKENS = int(os.getenv("GUI_MAX_TOKENS", "4096"))
CONTAINER_TIMEOUT_SECONDS = 600
CONTAINER_RUNNER = "/home/computeruse/runtime/run_single_in_container.sh"

CURSOR_THEME = os.getenv("CURSOR_THEME", "Adwaita")
CURSOR_SIZE = os.getenv("CURSOR_SIZE", "40")
WALLPAPER_HOST_PATH = os.getenv("WALLPAPER_HOST_PATH", "").strip()
WALLPAPER_PATH = os.getenv("WALLPAPER_PATH", "/usr/share/backgrounds/xfce/background.png").strip()

if WALLPAPER_HOST_PATH:
    WALLPAPER_HOST_PATH = str(Path(WALLPAPER_HOST_PATH).expanduser().resolve())
    if not WALLPAPER_PATH:
        WALLPAPER_PATH = "/home/computeruse/wallpaper.png"
    if not Path(WALLPAPER_HOST_PATH).exists():
        raise SystemExit(f"WALLPAPER_HOST_PATH not found: {WALLPAPER_HOST_PATH}")

class ContainerParallelComputerUse:
    """Manage parallel execution with container isolation."""

    def _docker_ui_args(self) -> list[str]:
        args = [
            "--env",
            f"CURSOR_THEME={CURSOR_THEME}",
            "--env",
            f"CURSOR_SIZE={CURSOR_SIZE}",
            "--env",
            f"WALLPAPER_PATH={WALLPAPER_PATH}",
        ]
        if WALLPAPER_HOST_PATH:
            args += ["-v", f"{WALLPAPER_HOST_PATH}:{WALLPAPER_PATH}:ro"]
        return args

    def _build_container_base_command(self, *, image: str, hostname: str) -> list[str]:
        return [
            "docker",
            "run",
            "-d",
            "-e",
            f"ANTHROPIC_API_KEY={self.api_key}",
            "-v",
            f"{GUI_AGENT_DIR}:/home/computeruse/computer_use_agent",
            "-v",
            f"{HOST_RUNTIME_DIR}:/home/computeruse/runtime",
            "-v",
            f"{self.base_path}:/home/computeruse/agent_recordings",
            "-v",
            f"{os.path.expanduser('~')}/.anthropic:/home/computeruse/.anthropic",
            "--hostname",
            hostname,
            "--env",
            f"DISPLAY=:{DISPLAY_NUM}",
            "--env",
            f"DISPLAY_NUM={DISPLAY_NUM}",
            "--env",
            f"SCREEN_WIDTH={SCREEN_WIDTH}",
            "--env",
            f"SCREEN_HEIGHT={SCREEN_HEIGHT}",
            *self._docker_ui_args(),
            image,
        ]
    
    def __init__(self, api_key: str, max_workers: int = None):
        self.api_key = api_key
        self.max_workers = max_workers or self._calculate_optimal_workers()
        recordings_env = os.getenv("RECORDINGS_DIR", "").strip()
        if recordings_env:
            recordings_path = Path(recordings_env).expanduser()
            if not recordings_path.is_absolute():
                recordings_path = (REPO_ROOT / recordings_path).resolve()
            self.base_path = recordings_path
        else:
            self.base_path = GUI_RECORDINGS_DIR
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.clean_state = None

    def _calculate_optimal_workers(self) -> int:
        """Calculate optimal number of workers based on system resources."""
        total_memory_gb = psutil.virtual_memory().total / (1024**3)
        num_cpus = os.cpu_count()

        memory_needed_per_worker = 2
        max_by_memory = int((total_memory_gb - 4) / memory_needed_per_worker)
        max_by_cpu = num_cpus - 2
        max_workers = min(max_by_memory, max_by_cpu)

        max_workers = min(max_workers, 8)
        print(f"System resources: {num_cpus} CPUs, {total_memory_gb:.1f}GB RAM")
        print(f"Using {max_workers} workers")

        return max_workers

    def _initialize_clean_state(self):
        """Create and save a clean container state with initialized desktop."""
        print("🚀 Initializing clean container state...")

        base_cmd = self._build_container_base_command(
            image=CONTAINER_IMAGE,
            hostname="world-program-clean",
        )
        base_container_id = subprocess.check_output(base_cmd + [
            '/bin/bash', '-c', '''
echo "Starting XFCE4 desktop environment..." && 
./start.sh & DESKTOP_PID=$! && 
sleep 20 && 
if ! ps -p $DESKTOP_PID > /dev/null; then 
    echo "Error: Desktop environment failed to start" && exit 1; 
fi && 
echo "Desktop environment started successfully" &&
echo "Testing X server connection..." &&
if xdpyinfo >/dev/null 2>&1; then
    echo "X server connection successful"
else
    echo "X server connection failed"
    exit 1
fi &&
echo "Clean state initialized, keeping container alive..."
while true; do sleep 1; done
'''
        ]).decode().strip()

        print(f"📦 Clean container {base_container_id} created, waiting for initialization...")

        time.sleep(15)

        print("💾 Saving clean state...")
        self.clean_state = subprocess.check_output([
            'docker', 'commit', base_container_id
        ]).decode().strip()

        subprocess.run(['docker', 'rm', '-f', base_container_id], check=True)

        print(f"✅ Clean state saved: {self.clean_state}")
        return self.clean_state

    def _execute_single_instruction_container(self, instruction_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single instruction in its own container."""
        instruction = instruction_data['instruction']
        session_id = instruction_data['session_id']

        try:
            print(f"🚀 Creating container for session {session_id}: {instruction}")

            container_cmd = self._build_container_base_command(
                image=self.clean_state,
                hostname=f"world-program-{session_id}",
            ) + [
                "bash",
                CONTAINER_RUNNER,
                "--instruction",
                instruction,
                "--session-name",
                session_id,
                "--model",
                DEFAULT_MODEL,
                "--fps",
                str(DEFAULT_FPS),
                "--max-tokens",
                str(DEFAULT_MAX_TOKENS),
            ]
            container_id = subprocess.check_output(container_cmd).decode().strip()

            print(f"📦 Container {container_id} created for session {session_id}")

            try:
                result = subprocess.run(
                    ['docker', 'wait', container_id],
                    capture_output=True,
                    text=True,
                    timeout=CONTAINER_TIMEOUT_SECONDS,
                )
                exit_code = int(result.stdout.strip())
                success = exit_code == 0

                logs = subprocess.run(
                    ['docker', 'logs', container_id],
                    capture_output=True,
                    text=True
                )
                print(f"📋 Container {session_id} logs:")
                print(logs.stdout)
                if logs.stderr:
                    print(f"❌ Container {session_id} errors:")
                    print(logs.stderr)

            except subprocess.TimeoutExpired:
                print(f"⏰ Timeout for session {session_id}")
                success = False

            finally:
                subprocess.run(['docker', 'rm', '-f', container_id], check=False)
                print(f"🧹 Container {container_id} cleaned up")

            return {
                'session_id': session_id,
                'instruction': instruction,
                'success': success,
                'container_id': container_id,
                'session_dir': str(self.base_path / f"session_{session_id}")
            }

        except Exception as e:
            print(f"❌ Failed to execute session {session_id}: {e}")
            return {
                'session_id': session_id,
                'instruction': instruction,
                'success': False,
                'error': str(e)
            }

    def execute_instructions(self, instructions: List[str]) -> List[Dict[str, Any]]:
        """Execute multiple instructions in parallel with container isolation."""
        print(f"🚀 Starting parallel execution of {len(instructions)} instructions")
        print("=" * 60)

        if not self.clean_state:
            self._initialize_clean_state()

        instruction_data = []
        for i, instruction in enumerate(instructions):
            instruction_data.append({
                'instruction': instruction,
                'session_id': f"{int(time.time())}_{i}"
            })

        results = []
        with multiprocessing.Pool(self.max_workers) as pool:
            for result in tqdm(
                pool.imap(self._execute_single_instruction_container, instruction_data),
                total=len(instruction_data),
                desc="Executing instructions"
            ):
                results.append(result)

        print("\n" + "=" * 60)
        print(f"✅ Execution completed!")
        successful = len([r for r in results if r['success']])
        print(f"📊 Summary: {successful}/{len(instructions)} successful")

        return results


def main():
    """Main function for container-based parallel computer use."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        api_key = input("🔑 Enter your Anthropic API key: ").strip()
        if not api_key:
            print("❌ API key is required")
            return

    instructions_file = Path(__file__).parent / "instructions.txt"
    if instructions_file.exists():
        print(f"📖 Loading instructions from: {instructions_file}")
        with open(instructions_file, 'r') as f:
            instructions = [line.strip() for line in f if line.strip() and not line.startswith('#')]
    else:
        print("📝 Using default instructions")
        instructions = [
            "Open Firefox and navigate to google.com",
            "Open the terminal and run 'ls -la'"
        ]

    print(f"📋 Loaded {len(instructions)} instructions:")
    for i, instruction in enumerate(instructions, 1):
        print(f"  {i}. {instruction}")

    response = input(f"\n🚀 Execute {len(instructions)} instructions in parallel containers? (y/N): ").strip().lower()
    if response not in ['y', 'yes']:
        print("❌ Execution cancelled")
        return

    executor = ContainerParallelComputerUse(api_key)

    results = executor.execute_instructions(instructions)

    print("\n📋 Detailed Results:")
    for result in results:
        status = "✅" if result['success'] else "❌"
        print(f"{status} Session {result['session_id']}: {result['instruction']}")
        if not result['success'] and 'error' in result:
            print(f"   Error: {result['error']}")

    successful = len([r for r in results if r['success']])
    failed = len([r for r in results if not r['success']])
    print(f"\n📊 Final Summary: {successful} successful, {failed} failed")


if __name__ == "__main__":
    main()
