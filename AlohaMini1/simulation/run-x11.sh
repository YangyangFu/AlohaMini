#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

# Compose cannot execute commands on the host. Grant the local Docker X11
# connection immediately before starting the service instead.
xhost +local:docker

compose_files=(-f "$script_dir/compose.yaml")

if [[ "$(docker context show)" == "desktop-linux" ]]; then
  python3 "$script_dir/x11-proxy.py" &
  proxy_pid=$!
  trap 'kill "$proxy_pid" 2>/dev/null || true' EXIT INT TERM
  compose_files+=(-f "$script_dir/compose.desktop-x11.yaml")
fi

docker compose "${compose_files[@]}" \
  --project-directory "$script_dir" \
  --profile x11 \
  up --build gazebo-x11
