#!/usr/bin/env python3
"""Translate simple browser UI targets into the robot's ROS control APIs."""

from functools import partial

import rclpy
from control_msgs.action import ParallelGripperCommand
from rclpy.action import ActionClient
from rclpy.duration import Duration
from rclpy.node import Node
from std_msgs.msg import Float64, Float64MultiArray, String
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint


class UiGateway(Node):
    """Keep controller-specific message details out of the browser client."""

    ARM_JOINTS = {
        "left": [f"left_joint{index}" for index in range(1, 6)],
        "right": [f"right_joint{index}" for index in range(1, 6)],
    }
    GRIPPER_JOINTS = {
        "left": "left_joint6",
        "right": "right_joint6",
    }
    # The CAD assembly places the moving hook upright at q=0 (fully open).
    # Rotating it -pi/2 folds it against the serrated static jaw. These are
    # provisional simulation endpoints; hardware endpoints require calibration.
    GRIPPER_POSITION_MIN = -1.57
    GRIPPER_POSITION_MAX = 0.0
    # vertical_move directly represents height above the mechanical bottom.
    LIFT_HEIGHT_MIN = 0.0
    LIFT_HEIGHT_MAX = 0.60

    def __init__(self):
        super().__init__("ui_gateway")
        self.declare_parameter("trajectory_duration", 1.0)
        self.trajectory_duration = max(
            0.1, float(self.get_parameter("trajectory_duration").value)
        )
        self.declare_parameter("lift_trajectory_duration", 2.0)
        self.lift_trajectory_duration = max(
            1.2, float(self.get_parameter("lift_trajectory_duration").value)
        )

        self.status_publisher = self.create_publisher(String, "/ui/status", 10)
        self.arm_publishers = {
            side: self.create_publisher(
                JointTrajectory, f"/{side}_arm_controller/joint_trajectory", 10
            )
            for side in self.ARM_JOINTS
        }
        self.lift_publisher = self.create_publisher(
            JointTrajectory, "/lift_controller/joint_trajectory", 10
        )
        self.gripper_clients = {
            side: ActionClient(
                self,
                ParallelGripperCommand,
                f"/{side}_gripper_controller/gripper_cmd",
            )
            for side in self.GRIPPER_JOINTS
        }

        self._subscriptions = []
        for side in self.ARM_JOINTS:
            self._subscriptions.append(
                self.create_subscription(
                    Float64MultiArray,
                    f"/ui/{side}_arm_target",
                    partial(self._arm_target, side),
                    10,
                )
            )
            self._subscriptions.append(
                self.create_subscription(
                    Float64,
                    f"/ui/{side}_gripper_target",
                    partial(self._gripper_target, side),
                    10,
                )
            )
        self._subscriptions.append(
            self.create_subscription(
                Float64, "/ui/lift_target", self._lift_target, 10
            )
        )

        self._publish_status("UI gateway ready")

    @staticmethod
    def _clamp(value, lower, upper):
        return min(max(float(value), lower), upper)

    def _trajectory(self, joint_names, positions, duration=None):
        message = JointTrajectory()
        message.header.stamp = self.get_clock().now().to_msg()
        message.joint_names = list(joint_names)
        point = JointTrajectoryPoint()
        point.positions = list(positions)
        point.time_from_start = Duration(
            seconds=self.trajectory_duration if duration is None else duration
        ).to_msg()
        message.points = [point]
        return message

    def _arm_target(self, side, message):
        if len(message.data) != len(self.ARM_JOINTS[side]):
            self._publish_status(
                f"Rejected {side} arm target: expected 5 joint positions"
            )
            return

        # These are the model's explicitly documented placeholder limits. The
        # UI and gateway must be updated after hardware limits are calibrated.
        positions = [self._clamp(value, -3.14, 3.14) for value in message.data]
        self.arm_publishers[side].publish(
            self._trajectory(self.ARM_JOINTS[side], positions)
        )
        self._publish_status(f"Sent {side} arm target")

    def _lift_target(self, message):
        height = self._clamp(
            message.data, self.LIFT_HEIGHT_MIN, self.LIFT_HEIGHT_MAX
        )
        self.lift_publisher.publish(
            self._trajectory(
                ["vertical_move"], [height], self.lift_trajectory_duration
            )
        )
        self._publish_status(f"Sent lift height {height:.3f} m")

    def _gripper_target(self, side, message):
        position = self._clamp(
            message.data, self.GRIPPER_POSITION_MIN, self.GRIPPER_POSITION_MAX
        )
        client = self.gripper_clients[side]
        if not client.server_is_ready():
            self._publish_status(f"{side.capitalize()} gripper controller unavailable")
            return

        goal = ParallelGripperCommand.Goal()
        goal.command.name = [self.GRIPPER_JOINTS[side]]
        goal.command.position = [position]
        future = client.send_goal_async(goal)
        future.add_done_callback(partial(self._gripper_goal_response, side))
        self._publish_status(f"Sent {side} gripper target {position:.3f} rad")

    def _gripper_goal_response(self, side, future):
        try:
            goal_handle = future.result()
        except Exception as error:  # ROS action transport failure
            self._publish_status(f"{side.capitalize()} gripper goal failed: {error}")
            return

        if not goal_handle.accepted:
            self._publish_status(f"{side.capitalize()} gripper goal rejected")
            return

        result_future = goal_handle.get_result_async()
        result_future.add_done_callback(partial(self._gripper_result, side))

    def _gripper_result(self, side, future):
        try:
            result = future.result().result
            outcome = "reached target" if result.reached_goal else "stopped"
            if result.stalled:
                outcome = "stalled"
            self._publish_status(f"{side.capitalize()} gripper {outcome}")
        except Exception as error:  # ROS action result transport failure
            self._publish_status(f"{side.capitalize()} gripper result failed: {error}")

    def _publish_status(self, text):
        self.status_publisher.publish(String(data=text))
        self.get_logger().info(text)


def main(args=None):
    rclpy.init(args=args)
    node = UiGateway()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
