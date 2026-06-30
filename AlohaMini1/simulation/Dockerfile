FROM ros:jazzy-ros-base

ENV DEBIAN_FRONTEND=noninteractive

# TARGETARCH is provided automatically by BuildKit (amd64 on Intel, arm64 on
# Apple Silicon). It maps directly onto the KasmVNC .deb naming scheme.
ARG TARGETARCH
ARG KASMVNC_VERSION=1.4.0

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    fluxbox \
    mesa-utils \
    python3-colcon-common-extensions \
    ros-jazzy-joint-state-publisher \
    ros-jazzy-joint-state-publisher-gui \
    ros-jazzy-robot-state-publisher \
    ros-jazzy-ros-gz-bridge \
    ros-jazzy-ros-gz-sim \
    ros-jazzy-rviz2 \
    ros-jazzy-xacro \
    xfonts-base \
    && curl -fsSL -o /tmp/kasmvnc.deb \
        "https://github.com/kasmtech/KasmVNC/releases/download/v${KASMVNC_VERSION}/kasmvncserver_noble_${KASMVNC_VERSION}_${TARGETARCH}.deb" \
    && apt-get install -y --no-install-recommends /tmp/kasmvnc.deb \
    && rm -f /tmp/kasmvnc.deb \
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
