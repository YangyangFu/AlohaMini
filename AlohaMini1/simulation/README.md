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
`robot_state_publisher`, and bridges `/clock` plus all three base-camera streams
into ROS 2.

To inspect ROS 2 from another terminal:

```bash
docker compose exec gazebo bash
ros2 node list
ros2 topic list
gz model --list
```

## RGB Camera Streams

The first three physical base cameras are simulated. Their ROS names use the
requested `chest`, `head`, and `rear` terminology; the hardware documentation
also calls the chest camera **front** and the head camera **top**.

| Camera | Mounted to | View | Image | Calibration | Optical TF frame |
| --- | --- | --- | --- | --- | --- |
| Chest | `vertical_link` | level front; moves with lift | `/cameras/chest/image_raw` | `/cameras/chest/camera_info` | `chest_camera_optical_frame` |
| Head | `base_link` | front and downward | `/cameras/head/image_raw` | `/cameras/head/camera_info` | `head_camera_optical_frame` |
| Rear | `base_link` | rear and downward | `/cameras/rear/image_raw` | `/cameras/rear/camera_info` | `rear_camera_optical_frame` |

Each stream is configured for `rgb8` at 640×360, a 15 Hz target rate, and an
80° horizontal field of view. Software-only rendering may deliver a lower
wall-clock frame rate. These are deliberately provisional, low-cost UI and
integration settings—not calibrated models of the 720p USB cameras. Replace
the mount origins in `aloha_cameras.xacro` and sensor parameters in
`aloha_gazebo_cameras.xacro` after measuring the assembled hardware.

For a quick stream check inside the running container:

```bash
ros2 topic hz /cameras/head/image_raw
ros2 topic echo --once /cameras/head/camera_info
```

## Operator UI and Visualization

The tools have different responsibilities:

- **Browser UI:** operate the robot through deployable ROS interfaces and view
  its three camera streams. This is the interface intended to evolve into the
  workstation/phone operator client.
- **RViz:** inspect the ROS-side robot model, TF, odometry, maps, perception,
  goals, and planned paths. It works against both Gazebo and physical hardware.
- **Gazebo GUI:** inspect the simulated world, contacts, collisions, and
  physics. Do not make it the hardware control interface.

The browser UI starts automatically with `gazebo.launch.py`. After starting any
Compose simulation, open:

<http://localhost:8000>

The initial panel provides:

- hold-to-run forward, reverse, lateral, and yaw commands with a speed scale;
- a software base-stop button;
- five position targets for each arm;
- lift and left/right moving-jaw targets;
- chest, head, and rear camera previews;
- rosbridge connection state, wheel odometry, joint positions, and command
  status.

The lift control displays height above the mechanical bottom from `0.00` to
`0.60 m`. The underlying `vertical_move` joint uses the same bottom-relative
coordinate: `q=0` is the mechanical bottom and positive motion raises the
lift. At `q=0.40 m` its geometry matches the original CAD assembly pose;
Gazebo starts at the canonical bottom pose. The endpoints follow the documented
60 cm travel but still require validation against the assembled hardware during
calibration.

This is currently a simulation convention, not a hardware home definition.
The published AlohaMini1 lift utility drives servo velocity and stops on
over-current; it does not report an absolute mechanical-bottom zero. A physical
adapter therefore needs a homing procedure (or absolute position feedback)
before accepting the UI's bottom-relative height command.

Base commands are robot-relative, not Gazebo-world-relative: `+X` / Forward is
the direction faced by the chest, `+Y` is robot-left, and positive yaw turns
counter-clockwise. At the initial Gazebo pose, robot `+X` is aligned with world
`+X`. The unmodified SolidWorks coordinate system is isolated behind the fixed
`base_cad_link` frame so it cannot leak into controller or UI semantics.

The UI is deliberately separate from Gazebo. Against a native or hardware ROS
graph it can be started independently:

```bash
ros2 launch aloha ui.launch.py use_sim_time:=false
```

Its default endpoints are UI/camera video `8000` and rosbridge `9090`.
Compose exposes both only on `127.0.0.1`. The standalone launch also binds
to localhost by default. Do not expose rosbridge directly to an untrusted
network; an authenticated/TLS gateway and command-ownership layer are still
required before phone or remote operation.

To run Gazebo without the web processes:

```bash
ros2 launch aloha gazebo.launch.py ui:=false
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
`gazebo.launch.py` spawns seven controllers, all of which come up `active`:

| Controller | Type | Joints | Command |
| --- | --- | --- | --- |
| `joint_state_broadcaster` | broadcaster | all | publishes `/joint_states` |
| `omni_base_controller` | `OmniWheelDriveController` | `wheel1/2/3_joint` | body twist → wheel speed |
| `left_arm_controller` | `JointTrajectoryController` | `left_joint1..5` | position trajectory |
| `right_arm_controller` | `JointTrajectoryController` | `right_joint1..5` | position trajectory |
| `left_gripper_controller` | `GripperActionController` | `left_joint6` moving jaw | position action |
| `right_gripper_controller` | `GripperActionController` | `right_joint6` moving jaw | position action |
| `lift_controller` | `JointTrajectoryController` | `vertical_move` | effort PID (position trajectory) |

Because a controller actively holds every joint, the base stays put instead of
creeping across the floor as the earlier passive model did.

Check the controllers and drive the robot from another terminal:

```bash
docker compose exec gazebo bash
source /opt/ros/jazzy/setup.bash && source /aloha_ws/install/setup.bash

ros2 control list_controllers

# Drive toward the chest-facing side at 0.15 m/s (+X in base_link). The
# controller maps the body twist to all three wheel velocities and stops after
# 0.5 s if commands become stale.
ros2 topic pub -r 10 /cmd_vel geometry_msgs/msg/TwistStamped \
  '{header: {frame_id: base_link}, twist: {linear: {x: 0.15}}}'

# Move the left arm to a pose:
ros2 topic pub -1 /left_arm_controller/joint_trajectory \
  trajectory_msgs/msg/JointTrajectory \
  '{joint_names: [left_joint1,left_joint2,left_joint3,left_joint4,left_joint5],
    points: [{positions: [0.5,0.0,0.0,0.0,0.0], time_from_start: {sec: 1}}]}'

# Command the left moving jaw: 0 rad is open and -1.57 rad is the provisional
# CAD-derived closed endpoint (not a calibrated finger gap in metres).
ros2 action send_goal /left_gripper_controller/gripper_cmd \
  control_msgs/action/ParallelGripperCommand \
  '{command: {name: [left_joint6], position: [-1.57]}}'
```

## Robot Description Layout

The model is composed from focused Xacro modules rather than one consumer-
specific URDF:

| File | Responsibility |
| --- | --- |
| `aloha_description.xacro` | Portable links, joints, visuals, collisions, inertias, and the ROS-to-CAD base-frame alignment |
| `aloha_cameras.xacro` | Portable camera bodies, mount transforms, and optical frames |
| `aloha_ros2_control.xacro` | Position, velocity, and simulated lift-effort command/state interfaces |
| `aloha_gazebo.xacro` | Gazebo contact parameters and `gz_ros2_control` plugin |
| `aloha_gazebo_cameras.xacro` | Gazebo RGB sensors, provisional resolution, rate, and intrinsics |
| `aloha_visual.urdf.xacro` | Visualization-only composition for RViz/Rerun |
| `aloha_sim.urdf.xacro` | Complete Gazebo simulation composition |

The build also expands `aloha_visual.urdf.xacro` into
`install/aloha/share/aloha/urdf/Aloha.visual.urdf`. This generated file has no
Gazebo or `ros2_control` extension tags and is the preferred input for strict
URDF consumers such as Rerun.

The Gazebo world selects Bullet Featherstone because the rigid omni-wheel
collision approximation needs directional friction (`mu1`, `mu2`, and
`fdir1`). The portable description remains independent of that simulation
choice.

The wheel joints use the ROS names `wheel1_joint`, `wheel2_joint`, and
`wheel3_joint`. They intentionally differ from their child-link names because
Gazebo requires joint and link frame names to be unique.

> **Provisional joint limits.** The SolidWorks export left every arm, gripper,
> and lift joint with zero-width limits (`lower="0" upper="0"`), which cannot
> move in simulation. Arm limits remain clearly commented placeholders
> (±3.14 rad). The grippers use the CAD-derived provisional interval
> `[-1.57, 0.00] rad` (closed to open), and the lift uses the documented 0.60 m
> travel as the bottom-relative interval `[0.00, 0.60] m`. Validate every
> endpoint against the real mechanism before hardware use. Their URDF hard
> stops include a 0.01 rad margin beyond the operator interval because DART can
> pin a velocity-backed joint commanded exactly onto a hard limit.

The SO-101 CAD export names each moving jaw `left_joint6` / `right_joint6`.
They are controlled separately from the five arm joints through dedicated
parallel-gripper action controllers. Their endpoint, position-to-opening,
velocity, effort, and stall parameters remain intentionally uncalibrated until
they can be measured on the follower hardware.

Several model parameters remain approximate and are follow-up work:

- **Base-camera calibration.** The three mount transforms are derived from the
  CAD camera seats, and their pinhole intrinsics are placeholders. Measure and
  version physical extrinsics, resolution/rate, FOV, distortion, and exposure
  before using images for geometric perception.
- **Omni base geometry.** The controller parameters are derived from the CAD:
  `0.0495 m` wheel radius, `0.17878 m` center-to-wheel radius, and `0.51459 rad`
  first-wheel offset. Calibrate these values against the assembled robot before
  relying on wheel odometry.
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

## Acknowledgements

This module was originally developed as the standalone
`lemon198/AlohaMini-Simulation` repository and later integrated into AlohaMini.
