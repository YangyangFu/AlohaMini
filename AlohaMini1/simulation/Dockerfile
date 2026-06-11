FROM ros:jazzy-ros-base

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    fluxbox \
    mesa-utils \
    novnc \
    python3-colcon-common-extensions \
    ros-jazzy-joint-state-publisher \
    ros-jazzy-joint-state-publisher-gui \
    ros-jazzy-robot-state-publisher \
    ros-jazzy-ros-gz-bridge \
    ros-jazzy-ros-gz-sim \
    ros-jazzy-rviz2 \
    ros-jazzy-xacro \
    websockify \
    x11vnc \
    xvfb \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /aloha_ws
COPY src ./src
COPY docker ./docker

RUN . /opt/ros/jazzy/setup.sh \
    && colcon build --symlink-install \
    && chmod +x /aloha_ws/docker/entrypoint.sh \
        /aloha_ws/docker/run-vnc.sh

ENTRYPOINT ["/aloha_ws/docker/entrypoint.sh"]
CMD ["/aloha_ws/docker/run-vnc.sh"]
