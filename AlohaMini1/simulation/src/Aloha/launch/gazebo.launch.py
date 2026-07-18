import os

import xacro
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    ExecuteProcess,
    IncludeLaunchDescription,
    TimerAction,
)
from launch.conditions import IfCondition, UnlessCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PythonExpression
from launch_ros.actions import Node


def generate_launch_description():
    package_share = get_package_share_directory("aloha")
    ros_gz_share = get_package_share_directory("ros_gz_sim")
    world_path = os.path.join(package_share, "worlds", "empty.sdf")
    xacro_path = os.path.join(package_share, "urdf", "aloha_sim.urdf.xacro")
    controllers_yaml = os.path.join(package_share, "config", "controllers.yaml")

    robot_description = xacro.process_file(
        xacro_path,
        mappings={"controllers_file": controllers_yaml},
    ).toxml()

    gui = LaunchConfiguration("gui")

    # The Gazebo GUI initializes its rendering scene asynchronously. This is
    # noticeably slower through X11 / software OpenGL, and a model inserted
    # before the scene exists can be simulated without ever appearing in the
    # client. Keep the short headless timings, but let graphical clients finish
    # creating their render scene before inserting the robot.
    def startup_delay(gui_seconds, headless_seconds):
        return PythonExpression(
            [
                str(gui_seconds),
                " if '",
                gui,
                "'.lower() in ('true', '1', 'yes', 'on') else ",
                str(headless_seconds),
            ]
        )

    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(ros_gz_share, "launch", "gz_sim.launch.py")
        ),
        launch_arguments={"gz_args": f"-r {world_path}"}.items(),
        condition=IfCondition(gui),
    )
    gazebo_headless = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(ros_gz_share, "launch", "gz_sim.launch.py")
        ),
        launch_arguments={"gz_args": f"-r -s {world_path}"}.items(),
        condition=UnlessCondition(gui),
    )

    robot_state_publisher = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        output="screen",
        parameters=[
            {
                "robot_description": robot_description,
                "use_sim_time": True,
            }
        ],
    )

    gazebo_bridge = Node(
        package="ros_gz_bridge",
        executable="parameter_bridge",
        arguments=[
            "/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock",
            "/cameras/chest/image_raw@sensor_msgs/msg/Image[gz.msgs.Image",
            "/cameras/chest/camera_info@sensor_msgs/msg/CameraInfo[gz.msgs.CameraInfo",
            "/cameras/head/image_raw@sensor_msgs/msg/Image[gz.msgs.Image",
            "/cameras/head/camera_info@sensor_msgs/msg/CameraInfo[gz.msgs.CameraInfo",
            "/cameras/rear/image_raw@sensor_msgs/msg/Image[gz.msgs.Image",
            "/cameras/rear/camera_info@sensor_msgs/msg/CameraInfo[gz.msgs.CameraInfo",
        ],
        output="screen",
    )

    spawn_robot = Node(
        package="ros_gz_sim",
        executable="create",
        arguments=[
            "-name",
            "AlohaMini1",
            "-topic",
            "robot_description",
            "-z",
            "0.05",
        ],
        output="screen",
    )

    # Once the delayed insertion has reached the graphical client, frame the
    # robot using Gazebo's own camera service. The default (-6, 0, 6) camera
    # makes this compact model look like a few pixels even when it rendered
    # successfully.
    focus_robot = ExecuteProcess(
        cmd=[
            "gz",
            "service",
            "-s",
            "/gui/move_to",
            "--reqtype",
            "gz.msgs.StringMsg",
            "--reptype",
            "gz.msgs.Boolean",
            "--timeout",
            "5000",
            "--req",
            'data: "AlohaMini1"',
        ],
        output="screen",
        condition=IfCondition(gui),
    )

    # Controller spawners. gz_ros2_control hosts the controller_manager inside
    # the Gazebo process, so these connect to /controller_manager once the model
    # (and its plugin) has been created. joint_state_broadcaster is brought up
    # first, then the motion controllers.
    def spawner(*controllers):
        return Node(
            package="controller_manager",
            executable="spawner",
            arguments=[*controllers, "--controller-manager", "/controller_manager"],
            parameters=[{"use_sim_time": True}],
            output="screen",
        )

    jsb_spawner = spawner("joint_state_broadcaster")
    base_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=[
            "omni_base_controller",
            "--controller-manager",
            "/controller_manager",
            "--controller-ros-args",
            "--ros-args --remap ~/cmd_vel:=/cmd_vel",
        ],
        parameters=[{"use_sim_time": True}],
        output="screen",
    )
    controller_spawner = spawner(
        "left_arm_controller",
        "right_arm_controller",
        "left_gripper_controller",
        "right_gripper_controller",
        "lift_controller",
    )

    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "gui",
                default_value="true",
                description="Start the Gazebo graphical client.",
            ),
            gazebo,
            gazebo_headless,
            robot_state_publisher,
            gazebo_bridge,
            TimerAction(period=startup_delay(12.0, 3.0), actions=[spawn_robot]),
            TimerAction(period=17.0, actions=[focus_robot]),
            # Give the model + gz_ros2_control plugin time to come up before the
            # spawners try to reach /controller_manager.
            TimerAction(period=startup_delay(17.0, 8.0), actions=[jsb_spawner]),
            TimerAction(
                period=startup_delay(19.0, 10.0),
                actions=[base_spawner, controller_spawner],
            ),
        ]
    )
