#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
GUI_DIR="$REPO_ROOT/engine/gui"

IMAGE="${IMAGE:-computer-use-gui:local}"
DOCKER_PLATFORM="${DOCKER_PLATFORM:-}"
SCREEN_WIDTH="${SCREEN_WIDTH:-1024}"
SCREEN_HEIGHT="${SCREEN_HEIGHT:-768}"
DISPLAY_NUM="${DISPLAY_NUM:-1}"
NOVNC_PORT="${NOVNC_PORT:-6080}"
RECORDINGS_DIR="${RECORDINGS_DIR:-$REPO_ROOT/workspace/videos/gui}"

CURSOR_THEME="${CURSOR_THEME:-Adwaita}"
CURSOR_SIZE="${CURSOR_SIZE:-40}"
UI_FONT_SIZE="${UI_FONT_SIZE:-13}"
DESKTOP_ICON_SIZE="${DESKTOP_ICON_SIZE:-96}"
VSCODE_ZOOM="${VSCODE_ZOOM:-1}"
VSCODE_FONT_SIZE="${VSCODE_FONT_SIZE:-18}"
VSCODE_TERMINAL_FONT_SIZE="${VSCODE_TERMINAL_FONT_SIZE:-16}"

WALLPAPER_HOST_PATH="${WALLPAPER_HOST_PATH:-}"
WALLPAPER_PATH="${WALLPAPER_PATH:-/usr/share/backgrounds/xfce/background.png}"

if ! command -v docker >/dev/null 2>&1; then
  echo "❌ docker not found. Please install Docker first."
  exit 1
fi

if ! docker info >/dev/null 2>&1; then
  echo "❌ Docker daemon not running. Please start Docker Desktop / dockerd."
  exit 1
fi

if ! docker image inspect "$IMAGE" >/dev/null 2>&1; then
  echo "❌ Docker image '$IMAGE' not found."
  echo "   Build it with: docker build -t \"$IMAGE\" -f \"${REPO_ROOT}/engine/dockerfiles/gui.Dockerfile\" \"${REPO_ROOT}\""
  exit 1
fi

if [ -z "${ANTHROPIC_API_KEY:-}" ]; then
  read -r -s -p "🔑 Enter your ANTHROPIC_API_KEY: " ANTHROPIC_API_KEY
  echo
  if [ -z "${ANTHROPIC_API_KEY:-}" ]; then
    echo "❌ ANTHROPIC_API_KEY is required."
    exit 1
  fi
fi

mkdir -p "$RECORDINGS_DIR"

platform_args=()
if [ -n "$DOCKER_PLATFORM" ]; then
  platform_args=(--platform "$DOCKER_PLATFORM")
fi

wallpaper_args=()
if [ -n "$WALLPAPER_HOST_PATH" ]; then
  if [ ! -f "$WALLPAPER_HOST_PATH" ]; then
    echo "❌ WALLPAPER_HOST_PATH not found: $WALLPAPER_HOST_PATH"
    exit 1
  fi
  if [ -z "$WALLPAPER_PATH" ]; then
    WALLPAPER_PATH="/home/computeruse/wallpaper.png"
  fi
  wallpaper_args=(-v "${WALLPAPER_HOST_PATH}:${WALLPAPER_PATH}:ro")
fi

echo "🖥️  noVNC: http://localhost:${NOVNC_PORT}"
echo "📁 Recordings: $RECORDINGS_DIR"
echo "🐳 Image: $IMAGE"
echo ""

docker run --rm -it \
  "${platform_args[@]}" \
  "${wallpaper_args[@]}" \
  -p "${NOVNC_PORT}:6080" \
  -e "ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}" \
  -e "DISPLAY_NUM=${DISPLAY_NUM}" \
  -e "SCREEN_WIDTH=${SCREEN_WIDTH}" \
  -e "SCREEN_HEIGHT=${SCREEN_HEIGHT}" \
  -e "CURSOR_THEME=${CURSOR_THEME}" \
  -e "CURSOR_SIZE=${CURSOR_SIZE}" \
  -e "UI_FONT_SIZE=${UI_FONT_SIZE}" \
  -e "DESKTOP_ICON_SIZE=${DESKTOP_ICON_SIZE}" \
  -e "VSCODE_ZOOM=${VSCODE_ZOOM}" \
  -e "VSCODE_FONT_SIZE=${VSCODE_FONT_SIZE}" \
  -e "VSCODE_TERMINAL_FONT_SIZE=${VSCODE_TERMINAL_FONT_SIZE}" \
  -e "WALLPAPER_PATH=${WALLPAPER_PATH}" \
  -v "$GUI_DIR/computer_use_agent:/home/computeruse/computer_use_agent" \
  -v "$SCRIPT_DIR:/home/computeruse/runtime" \
  -v "$RECORDINGS_DIR:/home/computeruse/agent_recordings" \
  -v "${HOME}/.anthropic:/home/computeruse/.anthropic" \
  "$IMAGE" \
  bash /home/computeruse/runtime/run_single_in_container.sh "$@"
