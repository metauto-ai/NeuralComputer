#!/usr/bin/env python3
"""Record screen frames and cursor positions for a GUI session."""

import os
import sys
import time
import signal
import csv

try:
    import cv2
    import numpy as np
    import mss
    SCREEN_RECORDING_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Screen recording libraries not available: {e}")
    SCREEN_RECORDING_AVAILABLE = False

if "DISPLAY" not in os.environ:
    os.environ["DISPLAY"] = ":1"
    print(f"Set DISPLAY environment variable to: {os.environ['DISPLAY']}")

try:
    import pyautogui
    pyautogui.FAILSAFE = False
    pyautogui.PAUSE = 0
except ImportError as e:
    print(f"Warning: pyautogui not available: {e}")
    pyautogui = None


class AgentActionRecorder:
    """Record screen frames and cursor positions."""

    def __init__(self, save_dir: str = "raw_data", save_name: str = None, fps: int = 15):
        self.save_dir = save_dir
        self.save_name = save_name or f"agent_actions_{int(time.time())}"
        self.fps = fps
        self.interval = 1.0 / fps

        self.data = []
        self.start_time = None
        self.recording = False
        self.session_active = False

        if os.path.isabs(save_dir):
            self.base_directory = save_dir
        else:
            self.base_directory = "/home/computeruse/agent_recordings"

        os.makedirs(os.path.join(self.base_directory, "videos"), exist_ok=True)
        os.makedirs(os.path.join(self.base_directory, "actions"), exist_ok=True)

        self.video_writer = None
        self.monitor = None
        self.frame_count = 0

        self.tool_recorder_start_time = None

        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def sync_with_tool_recorder(self, tool_start_time: float) -> None:
        """Synchronize with tool recorder start time."""
        self.tool_recorder_start_time = tool_start_time
        print(f"🕐 Synchronized with tool recorder start time: {tool_start_time}")
    
    def _get_synchronized_timestamp(self) -> float:
        """Get timestamp synchronized with tool recorder."""
        if self.tool_recorder_start_time and self.start_time:
            current_time = time.time()
            return current_time - self.tool_recorder_start_time
        return time.time() - self.start_time if self.start_time else 0

    def _signal_handler(self, signum, _frame) -> None:
        """Handle shutdown signals gracefully."""
        print(f"\nReceived signal {signum}, stopping recording...")
        self.stop_recording()
        sys.exit(0)

    def start_session(self) -> None:
        """Start a new recording session."""
        if self.session_active:
            print("Session already active")
            return

        print(f"Starting new agent session recording: {self.save_name}")
        self.session_active = True
        self.start_time = time.time()
        self.recording = True

        self._start_screen_recording()

        print("✅ Recording session started (screen recording only)")

    def _start_screen_recording(self) -> None:
        """Start screen recording using data_collection logic."""
        if not SCREEN_RECORDING_AVAILABLE:
            print("❌ Screen recording libraries not available")
            return

        try:
            self.monitor = mss.mss(with_cursor=True)
            monitor_info = self.monitor.monitors[1]
            video_path = os.path.join(self.base_directory, "videos", f"{self.save_name}.mp4")
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            self.video_writer = cv2.VideoWriter(
                video_path,
                fourcc,
                self.fps,
                (monitor_info["width"], monitor_info["height"]),
            )

            if not self.video_writer.isOpened():
                print("❌ Failed to open video writer")
                return

            print(f"📹 Screen recording started with cursor: {video_path}")

        except Exception as e:
            print(f"❌ Failed to start screen recording: {e}")

    def _capture_frame(self) -> None:
        """Capture a single frame and record cursor position."""
        if not self.recording or not self.video_writer:
            return

        try:
            screenshot = self.monitor.grab(self.monitor.monitors[1])
            frame = np.array(screenshot)

            frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)

            try:
                if pyautogui:
                    x, y = pyautogui.position()
                else:
                    x, y = 0, 0
            except Exception:
                x, y = 0, 0

            self.video_writer.write(frame)

            frame_timestamp = self.frame_count / self.fps
            seconds = int(frame_timestamp)
            milliseconds = int((frame_timestamp - seconds) * 1000)
            time_formatted = f"{seconds}:{milliseconds}"

            self.data.append([
                frame_timestamp,
                time_formatted,
                x,
                y,
                False,
                False,
                [],
            ])

            self.frame_count += 1

        except Exception as e:
            print(f"Warning: Frame capture error: {e}")

    def stop_recording(self) -> None:
        """Stop recording and save data."""
        if not self.session_active:
            return

        print("Stopping recording...")
        self.recording = False
        self.session_active = False

        if self.video_writer:
            self.video_writer.release()
            self.video_writer = None
            print("📹 Screen recording stopped")

        if self.monitor:
            self.monitor.close()
            self.monitor = None

        self._save_actions()

        print(f"✅ Recording session completed: {self.save_name}")
        print(f"📊 Total frames recorded: {self.frame_count}")

    def _save_actions(self) -> None:
        """Save recorded actions to CSV file in actions folder."""
        if not self.data:
            print("No data to save")
            return

        actual_duration = self.frame_count / self.fps
        csv_path = os.path.join(self.base_directory, "actions", f"screen_{self.save_name}.csv")

        try:
            with open(csv_path, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(
                    ["Timestamp", "Time", "X", "Y", "Left Click", "Right Click", "Keys"]
                )
                for row in self.data:
                    if not isinstance(row, (list, tuple)) or len(row) != 7:
                        continue
                    writer.writerow(
                        [
                            row[0],
                            row[1],
                            row[2],
                            row[3],
                            row[4],
                            row[5],
                            str(row[6]),
                        ]
                    )
        except Exception as e:
            print(f"❌ Failed to save actions CSV: {e}")
            return

        print(f"💾 Screen recording completed:")
        print(f"  Video: {os.path.join(self.base_directory, 'videos', f'{self.save_name}.mp4')}")
        print(f"  Mouse data: {csv_path}")
        print(f"  Total frames: {len(self.data)}")
        print(f"  Duration: {actual_duration:.2f} seconds (based on {self.frame_count} frames @ {self.fps} fps)")

    def get_video_time(self) -> float:
        """Return current video time based on produced frames (compacted timeline)."""
        return (self.frame_count / self.fps) if self.fps > 0 else 0.0
