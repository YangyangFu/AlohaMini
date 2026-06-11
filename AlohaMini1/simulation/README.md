# AlohaMini1 Simulation

![AlohaMini preview](picture/P2.png)

This workspace contains the AlohaMini1 mesh and URDF export plus a Docker
environment for ROS 2 Jazzy and Gazebo Harmonic. Gazebo is displayed through
noVNC, so the same workflow works on Linux, macOS, and Windows.

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

<http://localhost:6080/vnc.html?autoconnect=true&resize=scale>

The first build downloads ROS 2 and Gazebo packages and can take several
minutes. Later starts reuse the image:

```bash
docker compose up gazebo
```

Stop the simulation with `Ctrl+C`, then remove the stopped container:

```bash
docker compose down
```

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

- Blank noVNC page: wait a few seconds, refresh, and reconnect.
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

  The list should contain `AlohaMini1`. Refresh the noVNC browser page after a
  container restart. In Gazebo, select `AlohaMini1` in the Entity Tree and use
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
