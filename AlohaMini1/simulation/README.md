# AlohaMini1 Simulation

![AlohaMini preview](picture/P2.png)

This workspace contains the AlohaMini1 mesh and URDF export plus a Docker
environment for ROS 2 Jazzy and Gazebo Harmonic. Gazebo is displayed through
KasmVNC in the browser, so the same workflow works on Linux, macOS, and
Windows. KasmVNC replaces the older x11vnc + noVNC stack and gives noticeably
sharper streaming. Note that 3D is still rendered with software OpenGL
(`LIBGL_ALWAYS_SOFTWARE=1`) for portability — KasmVNC improves how the image is
streamed, not how fast Gazebo renders. For hardware-accelerated rendering, run
natively on a Linux machine with a GPU (see "Native ROS 2 Use").

## Requirements

- Docker Engine with Docker Compose, or Docker Desktop
- About 8 GB of free disk space for the first image build
- A browser for the Gazebo desktop

## Start Gazebo

From this directory:

```bash
docker compose up --build gazebo
```

When the log reports that the server is listening, open:

<http://localhost:6080>

Log in with the default KasmVNC credentials:

- User: `kasm`
- Password: `password`

Change them by setting `VNC_USER` / `VNC_PW` in `compose.yaml` (or as
environment variables). The web port is bound to `127.0.0.1` only.

The first build downloads ROS 2 and Gazebo packages and can take several
minutes. Later starts reuse the image:

```bash
docker compose up gazebo
```

Stop the simulation with `Ctrl+C`, then remove the stopped container:

```bash
docker compose down
```

## X11 Native Window

As an alternative to the browser, `gazebo-x11` renders Gazebo into a real
window on your host X server. It uses a separate, slimmer image
(`Dockerfile.x11`, no VNC stack) and the shared `entrypoint.sh`.

Software OpenGL stays on (`LIBGL_ALWAYS_SOFTWARE=1`): Mesa renders inside the
container and ships finished images to the X server. This is the reliable path
on macOS — XQuartz only offers indirect GLX, which modern Gazebo's OpenGL core
profile cannot use, so forwarding raw GL calls would crash or render nothing.

### macOS (XQuartz)

1. Install XQuartz and log out/in (it registers an X server):

   ```bash
   brew install --cask xquartz
   ```

2. Launch XQuartz, open **Settings → Security**, tick **"Allow connections
   from network clients"**, then quit and reopen XQuartz.

3. Allow the local connection (run in a normal macOS terminal, with XQuartz
   running):

   ```bash
   export DISPLAY=:0
   xhost + 127.0.0.1
   ```

4. Start the service:

   ```bash
   docker compose --profile x11 up --build gazebo-x11
   ```

> **Known limitation — this does not work for Gazebo on macOS.** The container
> connects to XQuartz and creates its window, but Gazebo's GUI then aborts when
> it tries to create an OpenGL context: XQuartz only provides *indirect* GLX,
> which Gazebo's Qt Quick + Ogre 3D engine cannot use. Observed failures include
> `QSGRenderLoop::handleContextCreationFailure`, `glx: failed to create drisw
> screen`, GLX `BadValue`, and a segfault in the 3D engine. `LIBGL_ALWAYS_SOFTWARE`
> does not help, because the GL context must still come from the X server's GLX
> (the container has no X server of its own — which is exactly what KasmVNC's
> Xvnc provides, and why the browser path works).
>
> **On macOS, use the default KasmVNC `gazebo` service instead.** This `x11`
> profile is intended for Linux hosts (below), where it works well — especially
> with a GPU.

### Linux

On Linux the host X server uses a local socket, so override `DISPLAY` and mount
the socket instead of using `host.docker.internal`:

```bash
xhost +local:docker
DISPLAY="$DISPLAY" docker compose --profile x11 run --rm \
  -e DISPLAY \
  -v /tmp/.X11-unix:/tmp/.X11-unix:rw \
  gazebo-x11
```

On a Linux host with a GPU you can also drop `LIBGL_ALWAYS_SOFTWARE` for
hardware-accelerated rendering (add `--gpus all` and the NVIDIA Container
Toolkit for NVIDIA cards).

## Headless Mode

For CI or physics-only testing:

```bash
docker compose --profile headless up --build gazebo-headless
```

This starts the Gazebo server, spawns `AlohaMini1`, publishes the URDF through
`robot_state_publisher`, and bridges `/clock` into ROS 2.

To inspect ROS 2 from another terminal:

```bash
docker compose exec gazebo bash
ros2 node list
ros2 topic list
gz model --list
```

## Native ROS 2 Use

On an Ubuntu 24.04 machine with ROS 2 Jazzy and `ros_gz` installed:

```bash
colcon build --symlink-install
source install/setup.bash
ros2 launch aloha gazebo.launch.py
```

RViz-only visualization remains available:

```bash
ros2 launch aloha display.launch.py
```

## Current Model Scope

The SolidWorks URDF includes visual meshes, collision meshes, masses, and
inertias. It is suitable for loading and inspecting the complete robot in
Gazebo.

The exported arm joints and vertical lift currently have zero-width limits
(`lower="0"` and `upper="0"`), and the URDF has no `ros2_control` hardware
description or Gazebo drive plugin. Consequently:

- The robot spawns as a passive physics model.
- The arms and lift remain at their exported zero positions.
- The three wheel joints are free, but there is no mobile-base controller yet.

The wheel joints use the ROS names `wheel1_joint`, `wheel2_joint`, and
`wheel3_joint`. They intentionally differ from their child-link names because
Gazebo requires joint and link frame names to be unique.

Accurate actuation requires measured joint limits and a controller model that
matches the physical servos and three-wheel drivetrain. Do not infer those
values from the mesh geometry.

## Troubleshooting

- Blank KasmVNC page: wait a few seconds, refresh, and reconnect.
- Login prompt rejects credentials: the account is created on first start. If
  you changed `VNC_USER`/`VNC_PW` after the first run, recreate the container
  (`docker compose up --force-recreate gazebo`) so the new account is written.
- For higher visual quality, open the KasmVNC control bar (left edge of the
  page) and raise the image quality / frame rate, or switch the encoding to a
  lossless mode.
- Empty world or missing robot: rebuild and recreate the container so URDF and
  mesh-path changes are included:

  ```bash
  docker compose up --build --force-recreate -d gazebo
  docker compose logs -f gazebo
  ```

  A successful startup contains `Entity creation successful`. Confirm the
  entity from another terminal with:

  ```bash
  docker compose exec gazebo bash -c \
    'source /opt/ros/jazzy/setup.bash; source /aloha_ws/install/setup.bash; gz model --list'
  ```

  The list should contain `AlohaMini1`. Refresh the KasmVNC browser page after
  a container restart. In Gazebo, select `AlohaMini1` in the Entity Tree and use
  the mouse wheel over the 3D viewport to zoom toward it.
- Slow rendering: software OpenGL is enabled for portability. Increase Docker
  Desktop CPU and memory allocation if needed.
- Port conflict: change `6080:6080` in `compose.yaml`, for example to
  `6081:6080`, then open port 6081.
- Rebuild after source changes with
  `docker compose build --no-cache gazebo`.

## Legacy ROS 1 Files

`launch/gazebo.launch` and `launch/display.launch` are retained from the
original ROS 1 package. ROS 2 uses the `.launch.py` files.

## Acknowledgements

This module was originally developed as the standalone
`lemon198/AlohaMini-Simulation` repository and later integrated into AlohaMini.
