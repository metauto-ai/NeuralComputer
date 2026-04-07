#!/usr/bin/env python3
"""Run a single computer-use session with recording."""

import argparse
import asyncio
import contextlib
import os
import sys
import time
from pathlib import Path

RUNTIME_DIR = Path(__file__).resolve().parent
GUI_DIR = RUNTIME_DIR.parent
for search_path in (GUI_DIR, RUNTIME_DIR):
    if str(search_path) not in sys.path:
        sys.path.insert(0, str(search_path))

from anthropic.types.beta import BetaContentBlockParam, BetaMessageParam, BetaTextBlockParam

from computer_use_agent.action_recorder import (
    get_recorder,
    save_tool_actions,
    start_tool_recording,
)
from computer_use_agent.loop import APIProvider, sampling_loop
from computer_use_agent.tools import ToolResult

from record_agent_actions import AgentActionRecorder


def output_callback(content: BetaContentBlockParam) -> None:
    """Handle Claude's output."""
    if content["type"] == "text":
        print(f"🤖 Claude: {content['text']}")
    elif content["type"] == "tool_use":
        print(f"🔧 Using tool: {content['name']}")


def tool_output_callback(result: ToolResult, _tool_id: str) -> None:
    """Handle tool execution results."""
    if result.error:
        print(f"❌ Tool error: {result.error}")
    else:
        print(f"✅ Tool completed")


def api_response_callback(_request, _response, error) -> None:
    """Handle API response for debugging."""
    if error:
        print(f"⚠️  API Error: {error}")


async def computer_use(
    api_key: str,
    *,
    instruction: str,
    model: str,
    fps: int,
    max_tokens: int,
    session_name: str | None = None,
    allow_prompt: bool = True,
) -> bool:
    """Run a single instruction with screen and tool recording."""
    print("🚀 Computer Control Mode - Single Execution with Action Recording")
    print("=" * 50)

    session_name = session_name or f"agent_session_{int(time.time())}"
    recorder = AgentActionRecorder(save_dir="", save_name=session_name, fps=fps)

    messages: list[BetaMessageParam] = []

    try:
        if not instruction:
            if not allow_prompt:
                print("❌ No instruction provided")
                return False
            instruction = input("\n💬 Enter your instruction: ").strip()
        if not instruction:
            print("❌ No instruction provided")
            return False
        
        print(f"\n👤 You: {instruction}")
        print("-" * 50)

        print("🎬 Starting action recording...")
        recorder.start_session()
        screen_start_time = getattr(recorder, "start_time", None)

        try:
            start_tool_recording(session_name)
            tool_recorder = get_recorder()
            if tool_recorder and screen_start_time is not None:
                tool_recorder.sync_with_screen_recorder(screen_start_time)
                if hasattr(recorder, "get_video_time"):
                    tool_recorder.set_video_time_provider(recorder.get_video_time)
                print("✅ Tool recorder synced with screen recorder")
            else:
                print("⚠️  Tool recorder not available; action CSV/JSON may be missing")
        except Exception as e:
            print(f"⚠️  Failed to initialize tool recorder: {e}")

        messages.append({
            "role": "user",
            "content": [BetaTextBlockParam(type="text", text=instruction)]
        })

        try:
            async def screen_recording_task():
                while recorder.session_active:
                    recorder._capture_frame()
                    await asyncio.sleep(1 / max(1, recorder.fps))

            screen_task = asyncio.create_task(screen_recording_task())

            messages = await sampling_loop(
                model=model,
                provider=APIProvider.ANTHROPIC,
                system_prompt_suffix="",
                messages=messages,
                output_callback=output_callback,
                tool_output_callback=tool_output_callback,
                api_response_callback=api_response_callback,
                api_key=api_key,
                tool_version="computer_use_20250124",
                max_tokens=max_tokens,
            )

            screen_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await screen_task

        except Exception as e:
            print(f"❌ Error during execution: {e}")
            return False
        finally:
            try:
                save_tool_actions(session_name)
            except Exception as e:
                print(f"Warning: Failed to save tool actions: {e}")

            print("🎬 Stopping action recording...")
            recorder.stop_recording()

        print("-" * 50)
        print("✅ Execution completed")
        return True

    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
        if recorder.session_active:
            recorder.stop_recording()
        return False
    except EOFError:
        print("\n👋 Goodbye!")
        if recorder.session_active:
            recorder.stop_recording()
        return False


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Run a single computer-use instruction with recording.")
    parser.add_argument(
        "-i",
        "--instruction",
        default="",
        help="Instruction text (if empty, prompt interactively).",
    )
    parser.add_argument(
        "--model",
        default=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514"),
        help="Anthropic model name.",
    )
    parser.add_argument("--fps", type=int, default=15, help="Recording FPS.")
    parser.add_argument("--max-tokens", type=int, default=4096, help="Max tokens per model call.")
    parser.add_argument(
        "--session-name",
        default="",
        help="Optional session name for output files.",
    )
    args = parser.parse_args()

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        api_key = input("🔑 Enter your Anthropic API key: ").strip()
        if not api_key:
            print("❌ API key is required")
            sys.exit(1)
    success = asyncio.run(
        computer_use(
            api_key,
            instruction=args.instruction,
            model=args.model,
            fps=args.fps,
            max_tokens=args.max_tokens,
            session_name=args.session_name or None,
            allow_prompt=True,
        )
    )
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
