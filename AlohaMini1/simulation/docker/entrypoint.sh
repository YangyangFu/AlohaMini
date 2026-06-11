#!/usr/bin/env bash
set -e

source /opt/ros/jazzy/setup.bash
source /aloha_ws/install/setup.bash

export GZ_SIM_RESOURCE_PATH="/aloha_ws/install/aloha/share${GZ_SIM_RESOURCE_PATH:+:${GZ_SIM_RESOURCE_PATH}}"

exec "$@"
