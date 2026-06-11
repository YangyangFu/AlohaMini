#!/usr/bin/env bash
set -e

export DISPLAY="${DISPLAY:-:1}"
export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/tmp/runtime-aloha}"
mkdir -p "${XDG_RUNTIME_DIR}"
chmod 700 "${XDG_RUNTIME_DIR}"

Xvfb "${DISPLAY}" -screen 0 "${VNC_RESOLUTION:-1600x900x24}" -ac +extension GLX +render -noreset &
sleep 1
fluxbox >/tmp/fluxbox.log 2>&1 &
x11vnc -display "${DISPLAY}" -forever -shared -nopw -rfbport 5900 >/tmp/x11vnc.log 2>&1 &
websockify --web=/usr/share/novnc/ 6080 localhost:5900 >/tmp/novnc.log 2>&1 &

sleep 1
exec ros2 launch aloha gazebo.launch.py gui:=true
