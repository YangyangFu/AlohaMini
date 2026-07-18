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

On Linux the Compose service automatically inherits `DISPLAY` and mounts the
host X11 socket. The included launcher grants local Docker access and starts
the service in one command:

```bash
./run-x11.sh
```

On Docker Desktop for Linux, the launcher automatically proxies X11 over TCP
because Docker Desktop does not expose the host's `/tmp/.X11-unix` socket.

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

## Controlling the Robot

The robot is actuated through `ros2_control` with the `gz_ros2_control`
plugin. The controller manager runs inside the Gazebo process and is
configured by [`config/controllers.yaml`](src/Aloha/config/controllers.yaml).
`gazebo.launch.py` spawns five controllers, all of which come up `active`:

| Controller | Type | Joints | Command |
| --- | --- | --- | --- |
| `joint_state_broadcaster` | broadcaster | all | publishes `/joint_states` |
| `wheel_velocity_controller` | `JointGroupVelocityController` | `wheel1/2/3_joint` | wheel speed (rad/s) |
| `left_arm_controller` | `JointTrajectoryController` | `left_joint1..6` | position |
| `right_arm_controller` | `JointTrajectoryController` | `right_joint1..6` | position |
| `lift_controller` | `JointTrajectoryController` | `vertical_move` | position |

Because a controller actively holds every joint, the base stays put instead of
creeping across the floor as the earlier passive model did.

Check the controllers and drive the robot from another terminal:

```bash
docker compose exec gazebo bash
source /opt/ros/jazzy/setup.bash && source /aloha_ws/install/setup.bash

ros2 control list_controllers

# Spin the three wheels (equal speeds rotate the omni base in place):
ros2 topic pub -1 /wheel_velocity_controller/commands \
  std_msgs/msg/Float64MultiArray '{data: [3.0, 3.0, 3.0]}'

# Move the left arm to a pose:
ros2 topic pub -1 /left_arm_controller/joint_trajectory \
  trajectory_msgs/msg/JointTrajectory \
  '{joint_names: [left_joint1,left_joint2,left_joint3,left_joint4,left_joint5,left_joint6],
    points: [{positions: [0.5,0.0,0.0,0.0,0.0,0.0], time_from_start: {sec: 1}}]}'
```

## Current Model Scope

The SolidWorks URDF includes visual meshes, collision meshes, masses, and
inertias, plus a manually added `ros2_control` hardware description and the
`gz_ros2_control` plugin (see [`urdf/Aloha.urdf`](src/Aloha/urdf/Aloha.urdf)).

The wheel joints use the ROS names `wheel1_joint`, `wheel2_joint`, and
`wheel3_joint`. They intentionally differ from their child-link names because
Gazebo requires joint and link frame names to be unique.

> **Placeholder joint limits.** The SolidWorks export left every arm and lift
> joint with zero-width limits (`lower="0" upper="0"`), which position control
> cannot move. They have been replaced with clearly commented **placeholder**
> limits (±3.14 rad for the revolute arm joints; 0–0.20 m for the lift) purely
> so the controllers function. **Replace these with values measured from the
> real servos** before relying on them — do not infer limits from the mesh
> geometry.

Two other items remain approximate and are follow-up work:

- **Omni base kinematics.** There is no upstream 3-wheel omni-drive controller,
  so the base is driven per wheel via `wheel_velocity_controller`. A holonomic
  `(vx, vy, wz)` → wheel-speed mapping needs a small kinematics node or a custom
  controller.
- **Servo dynamics.** Effort/velocity limits and any gearing/PID behaviour are
  placeholders, not matched to the physical drivetrain.

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
