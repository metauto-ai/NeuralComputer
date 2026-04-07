#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
SYNTH_DIR="$REPO_ROOT/engine/gui/synthetic_data_collection"
DEFAULT_OUTPUT_ROOT="$REPO_ROOT/workspace/videos/gui_synthetic"

OUTPUT_ROOT="${SYNTH_OUTPUT_DIR:-$DEFAULT_OUTPUT_ROOT}"
if [[ "$OUTPUT_ROOT" != /* ]]; then
    OUTPUT_ROOT="$REPO_ROOT/$OUTPUT_ROOT"
fi

CURSOR_THEME="${CURSOR_THEME:-Adwaita}"
CURSOR_SIZE="${CURSOR_SIZE:-40}"
UI_FONT_SIZE="${UI_FONT_SIZE:-13}"
DESKTOP_ICON_SIZE="${DESKTOP_ICON_SIZE:-96}"
VSCODE_ZOOM="${VSCODE_ZOOM:-1}"
VSCODE_FONT_SIZE="${VSCODE_FONT_SIZE:-18}"
VSCODE_TERMINAL_FONT_SIZE="${VSCODE_TERMINAL_FONT_SIZE:-16}"

echo "Starting synthetic data collection..."

if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

if ! docker image inspect "computer-use-gui:local" >/dev/null 2>&1; then
    echo "❌ Docker image 'computer-use-gui:local' not found."
    echo "Please build the GUI Docker image first:"
    echo "python ${REPO_ROOT}/main.py guiworld build-image --tag computer-use-gui:local"
    exit 1
fi

if ! python3 -c "import numpy, psutil, tqdm" >/dev/null 2>&1; then
    echo "❌ Missing Python deps on host for synthetic controller script."
    echo "   Install with: pip3 install -r ${SYNTH_DIR}/requirements.txt"
    exit 1
fi

echo "Building synthetic image..."
docker build -t synthetic-data-collection:local -f "${REPO_ROOT}/engine/dockerfiles/synthetic.Dockerfile" "${REPO_ROOT}"

mkdir -p "${OUTPUT_ROOT}"
mkdir -p "${OUTPUT_ROOT}/videos"
mkdir -p "${OUTPUT_ROOT}/actions"

chmod 777 "${OUTPUT_ROOT}"
chmod 777 "${OUTPUT_ROOT}/videos"
chmod 777 "${OUTPUT_ROOT}/actions"

echo "Output: ${OUTPUT_ROOT}"

export PYTHONPATH="${SYNTH_DIR}:${PYTHONPATH:-}"
export SYNTH_OUTPUT_DIR="${OUTPUT_ROOT}"
export CURSOR_THEME
export CURSOR_SIZE
export UI_FONT_SIZE
export DESKTOP_ICON_SIZE
export VSCODE_ZOOM
export VSCODE_FONT_SIZE
export VSCODE_TERMINAL_FONT_SIZE

cd "${SYNTH_DIR}"
python3 synthetic_script.py "$@"

echo "Done: ${OUTPUT_ROOT}"
