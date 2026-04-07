#!/usr/bin/env python3
"""
Action recorder for computer-use-agent tools.
Records actions at the tool execution level with video sync.
"""

import os
import time
import json
import csv
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict


@dataclass
class ActionRecord:
    """Record of a single tool action."""
    timestamp: float  # Relative timestamp from session start
    time_formatted: str  # Formatted time like "seconds:milliseconds"
    tool_name: str
    action: str
    x: Optional[int] = None
    y: Optional[int] = None
    text: Optional[str] = None
    key: Optional[str] = None
    scroll_direction: Optional[str] = None
    scroll_amount: Optional[int] = None
    duration: Optional[float] = None
    success: bool = True
    error: Optional[str] = None


class ToolActionRecorder:
    """Records tool actions in computer-use-agent with video sync."""
    
    def __init__(self, save_dir: str = "/home/computeruse/agent_recordings"):
        self.save_dir = Path(save_dir)
        self.actions: List[ActionRecord] = []
        self.start_time = None
        self.session_id = None
        
        # Optional provider that returns current compacted video time (float seconds)
        self._video_time_provider = None
        
        # Create save directories
        self.save_dir.mkdir(parents=True, exist_ok=True)
        (self.save_dir / "actions").mkdir(exist_ok=True)
        
        print(f"🔧 Tool action recorder initialized: {self.save_dir}")
    
    def set_video_time_provider(self, provider):
        """Set a callable that returns current compacted video time in seconds."""
        self._video_time_provider = provider
    
    def start_session(self, session_id: str = None):
        """Start a new recording session."""
        self.start_time = time.time()
        self.session_id = session_id or f"tool_session_{int(self.start_time)}"
        self.actions.clear()
        print(f"🎬 Tool recording session started: {self.session_id}")
    
    def sync_with_screen_recorder(self, screen_start_time: float):
        """Sync with screen recorder's time base."""
        if self.start_time is not None:
            # Store screen recorder's start time for timestamp calculations
            self.screen_start_time = screen_start_time
            print(f"🕐 Tool recorder synced with screen recorder start time: {screen_start_time}")
        else:
            print("⚠️  Cannot sync: tool recorder session not started")
    
    def record_action(
        self,
        tool_name: str,
        action: str,
        x: Optional[int] = None,
        y: Optional[int] = None,
        text: Optional[str] = None,
        key: Optional[str] = None,
        scroll_direction: Optional[str] = None,
        scroll_amount: Optional[int] = None,
        duration: Optional[float] = None,
        success: bool = True,
        error: Optional[str] = None
    ):
        """Record a tool action with video sync timing."""
        if self.start_time is None:
            print("⚠️  Tool recording session not started, cannot record action")
            return
        
        # Prefer compacted video time if provider is available
        if callable(self._video_time_provider):
            rel_timestamp = float(self._video_time_provider())
        else:
            # Use screen recorder's time base if available, otherwise fallback to wall-clock time
            if hasattr(self, 'screen_start_time') and self.screen_start_time is not None:
                current_time = time.time()
                rel_timestamp = current_time - self.screen_start_time
            else:
                current_time = time.time()
                rel_timestamp = current_time - self.start_time
        
        # Format timestamp like data_collection (seconds:milliseconds)
        seconds = int(rel_timestamp)
        milliseconds = int((rel_timestamp - seconds) * 1000)
        time_formatted = f"{seconds}:{milliseconds}"
        
        # Create action record
        action_record = ActionRecord(
            timestamp=rel_timestamp,
            time_formatted=time_formatted,
            tool_name=tool_name,
            action=action,
            x=x,
            y=y,
            text=text,
            key=key,
            scroll_direction=scroll_direction,
            scroll_amount=scroll_amount,
            duration=duration,
            success=success,
            error=error
        )
        
        self.actions.append(action_record)
        
        # Log the action
        action_desc = f"{action}"
        if x is not None and y is not None:
            action_desc += f" at ({x}, {y})"
        if text:
            action_desc += f" text: '{text}'"
        if key:
            action_desc += f" key: '{key}'"
        
        status = "✅" if success else "❌"
        print(f"{status} {tool_name}: {action_desc} [{time_formatted}]")
    
    def save_actions(self, save_name: str = None):
        """Save recorded actions to files."""
        if not self.actions:
            print("No actions recorded")
            return
        
        save_name = save_name or self.session_id
        
        # Save as JSON for detailed analysis
        json_path = self.save_dir / "actions" / f"{save_name}.json"
        with open(json_path, 'w') as f:
            json.dump({
                'metadata': {
                    'session_id': self.session_id,
                    'start_time': self.start_time,
                    'duration': time.time() - self.start_time if self.start_time else 0,
                    'total_actions': len(self.actions),
                    'recording_type': 'tool_execution',
                    'video_sync': True
                },
                'actions': [asdict(action) for action in self.actions]
            }, f, indent=2)
        
        # Convert to data_collection format for compatibility
        data_collection_format = []
        for action in self.actions:
            # Convert tool actions to data_collection format
            should_click = action.action in ['left_click', 'right_click', 'double_click', 'triple_click', 'middle_click']
            should_right_click = action.action == 'right_click'
            
            key_events = []
            
            # Handle different keyboard action types
            if action.action == 'key' and action.text:
                # Single key press/release
                key_events.append(('keydown', action.text))
                key_events.append(('keyup', action.text))
            elif action.action == 'type' and action.text:
                # Text typing - create key events for each character
                for char in action.text:
                    key_events.append(('keydown', char))
                    key_events.append(('keyup', char))
            elif action.action == 'hold_key' and action.text:
                # Key hold - keydown, wait, keyup
                key_events.append(('keydown', action.text))
                if action.duration:
                    key_events.append(('wait', str(action.duration)))
                key_events.append(('keyup', action.text))
            elif action.key:
                # Key modifier (like Ctrl, Alt, etc.)
                key_events.append(('keydown', action.key))
                key_events.append(('keyup', action.key))
            
            data_collection_format.append([
                action.timestamp,
                action.time_formatted,
                action.x or 0,
                action.y or 0,
                should_click,
                should_right_click,
                key_events
            ])
        
        # Save as CSV in data_collection format (avoid hard dependency on pandas)
        csv_path = self.save_dir / "actions" / f"{save_name}.csv"
        try:
            with open(csv_path, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(
                    [
                        "Timestamp",
                        "Timestamp_formated",
                        "X",
                        "Y",
                        "Left Click",
                        "Right Click",
                        "Key Events",
                    ]
                )
                for (
                    timestamp,
                    timestamp_formatted,
                    x,
                    y,
                    left_click,
                    right_click,
                    key_events,
                ) in data_collection_format:
                    writer.writerow(
                        [
                            timestamp,
                            timestamp_formatted,
                            x,
                            y,
                            left_click,
                            right_click,
                            str(key_events),
                        ]
                    )

            print("💾 Actions saved:")
            print(f"  JSON: {json_path}")
            print(f"  CSV: {csv_path}")
            print(f"  Total actions: {len(self.actions)}")
        except Exception as e:
            print("💾 Actions saved (JSON only, CSV write failed):")
            print(f"  JSON: {json_path}")
            print(f"  CSV error: {e}")
            print(f"  Total actions: {len(self.actions)}")


# Global recorder instance
_recorder: Optional[ToolActionRecorder] = None


def get_recorder() -> ToolActionRecorder:
    """Get the global recorder instance."""
    global _recorder
    print(f"🔧 get_recorder() called, _recorder is: {_recorder}")
    
    # If recorder exists and has a session, use it
    if _recorder is not None and _recorder.start_time is not None:
        print(f"🔧 Using existing active recorder instance with id: {id(_recorder)}")
        return _recorder

    # Create new recorder only if none exists
    if _recorder is None:
        print("🔧 Creating new tool action recorder instance")
        _recorder = ToolActionRecorder()
        print(f"🔧 Created recorder with id: {id(_recorder)}")
    
    return _recorder


def ensure_recorder_exists() -> ToolActionRecorder:
    """Ensure recorder exists, but don't create if it doesn't."""
    global _recorder
    if _recorder is None:
        print("⚠️  No recorder instance exists yet")
        return None
    return _recorder


def start_tool_recording(session_id: str = None):
    """Start tool recording session."""
    recorder = get_recorder()
    if recorder is None:
        print("❌ No recorder instance available")
        return
    
    if recorder.start_time is None:
        print(f"🎬 Starting new tool recording session: {session_id}")
        recorder.start_session(session_id)
    else:
        print(f"⚠️  Tool recording session already active: {recorder.session_id}")


def record_tool_action(
    tool_name: str,
    action: str,
    **kwargs
):
    """Record a tool action."""
    recorder = get_recorder()
    if recorder is None:
        print(f"⚠️  No active recorder session, skipping: {action}")
        return
    
    if recorder.start_time is not None:
        recorder.record_action(tool_name, action, **kwargs)
    else:
        print(f"⚠️  Recorder exists but no session active, skipping: {action}")


def save_tool_actions(save_name: str = None):
    """Save all recorded tool actions."""
    if _recorder:
        print(f"💾 Saving tool actions with save_name: {save_name}")
        print(f"💾 Total actions recorded: {len(_recorder.actions)}")
        if len(_recorder.actions) > 0:
            _recorder.save_actions(save_name)
        else:
            print("⚠️  No actions recorded")
    else:
        print("⚠️  No tool recorder instance found!") 
