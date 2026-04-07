#!/usr/bin/env bash
set -euo pipefail

DISPLAY_NUM="${DISPLAY_NUM:-1}"
export DISPLAY="${DISPLAY:-:${DISPLAY_NUM}}"

cd /home/computeruse

sudo chown root:root /tmp/.X11-unix 2>/dev/null || true

./start.sh >/tmp/start.log 2>&1 &

echo "[run] waiting for X server on $DISPLAY..."
ready=0
for i in $(seq 1 30); do
  if xdpyinfo >/dev/null 2>&1; then
    echo "[run] X server is ready"
    ready=1
    break
  fi
  sleep 1
done

if [ "$ready" -ne 1 ]; then
  echo "[run] X server failed to start" >&2
  exit 1
fi

exec python3 /home/computeruse/runtime/computer_use.py "$@"
