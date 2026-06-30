#!/usr/bin/env bash
set -e

export DISPLAY="${DISPLAY:-:1}"
export HOME="${HOME:-/root}"
export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/tmp/runtime-aloha}"
mkdir -p "${XDG_RUNTIME_DIR}"
chmod 700 "${XDG_RUNTIME_DIR}"

# Split VNC_RESOLUTION (e.g. 2400x1440x24) into width, height and depth.
RES="${VNC_RESOLUTION:-1600x900x24}"
GEOMETRY="${RES%x*}"
WIDTH="${GEOMETRY%x*}"
HEIGHT="${GEOMETRY#*x}"
DEPTH="${RES##*x}"

# KasmVNC requires at least one account. These are only reachable on
# 127.0.0.1:6080 (see compose.yaml); override with VNC_USER / VNC_PW if desired.
VNC_USER="${VNC_USER:-kasm}"
VNC_PW="${VNC_PW:-password}"

mkdir -p "${HOME}/.vnc"

# Resolution is driven by desktop.resolution (NOT the -geometry CLI flag, which
# KasmVNC ignores). max_resolution is raised to match so the image is not
# downscaled to 1920x1080 while the camera is moving. Plain HTTP on port 6080
# avoids self-signed-cert warnings in the browser.
cat > "${HOME}/.vnc/kasmvnc.yaml" <<YAML
desktop:
  resolution:
    width: ${WIDTH}
    height: ${HEIGHT}
  pixel_depth: ${DEPTH}
  allow_resize: true
network:
  protocol: http
  interface: 0.0.0.0
  websocket_port: 6080
  ssl:
    require_ssl: false
  # A static public_ip skips the WebRTC STUN discovery that otherwise hangs the
  # web server for ~50s while it queries unreachable public STUN servers.
  udp:
    public_ip: 127.0.0.1
encoding:
  video_encoding_mode:
    max_resolution:
      width: ${WIDTH}
      height: ${HEIGHT}
YAML

# Window manager for the session. KasmVNC keeps the session alive as long as
# this script runs, so fluxbox must stay in the foreground.
cat > "${HOME}/.vnc/xstartup" <<'XSTARTUP'
#!/usr/bin/env bash
unset SESSION_MANAGER
unset DBUS_SESSION_BUS_ADDRESS
exec fluxbox
XSTARTUP
chmod +x "${HOME}/.vnc/xstartup"

# KasmVNC otherwise runs select-de.sh, which prompts interactively for a desktop
# environment and aborts when there is no TTY. This marker tells it the choice
# was already made, so it uses the xstartup above as-is.
touch "${HOME}/.vnc/.de-was-selected"

# Open every window maximised and without a title bar, so Gazebo's top toolbar
# sits flush against the top edge instead of being pushed off-screen by fluxbox.
mkdir -p "${HOME}/.fluxbox"
cat > "${HOME}/.fluxbox/apps" <<'APPS'
[app] (name=.*)
  [Deco]	{NONE}
  [Maximized]	{yes}
[end]
APPS

# Create the web/VNC account once (idempotent across container restarts).
if [ ! -f "${HOME}/.kasmpasswd" ]; then
  printf '%s\n%s\n' "${VNC_PW}" "${VNC_PW}" | kasmvncpasswd -u "${VNC_USER}" -wr
fi

# Start the KasmVNC X server + web server (replaces Xvfb + x11vnc + websockify).
# It daemonises and runs the xstartup window manager in the background. Geometry
# and depth come from kasmvnc.yaml above.
vncserver "${DISPLAY}"

sleep 2
exec ros2 launch aloha gazebo.launch.py gui:=true
