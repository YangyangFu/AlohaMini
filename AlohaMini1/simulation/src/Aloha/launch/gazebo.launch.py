import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, TimerAction
from launch.conditions import IfCondition, UnlessCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    package_share = get_package_share_directory("aloha")
    ros_gz_share = get_package_share_directory("ros_gz_sim")
    world_path = os.path.join(package_share, "worlds", "empty.sdf")
    urdf_path = os.path.join(package_share, "urdf", "Aloha.urdf")
    controllers_yaml = os.path.join(package_share, "config", "controllers.yaml")

    with open(urdf_path, "r", encoding="utf-8") as urdf_file:
        robot_description = urdf_file.read()

    # The URDF ships with a placeholder token for the gz_ros2_control parameters
    # file so it stays portable; resolve it to this machine's absolute path here.
    robot_description = robot_description.replace(
        "__CONTROLLERS_YAML__", controllers_yaml
    )

    gui = LaunchConfiguration("gui")
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

    clock_bridge = Node(
        package="ros_gz_bridge",
        executable="parameter_bridge",
        arguments=["/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock"],
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
    controller_spawner = spawner(
        "wheel_velocity_controller",
        "left_arm_controller",
        "right_arm_controller",
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
            clock_bridge,
            TimerAction(period=3.0, actions=[spawn_robot]),
            # Give the model + gz_ros2_control plugin time to come up before the
            # spawners try to reach /controller_manager.
            TimerAction(period=8.0, actions=[jsb_spawner]),
            TimerAction(period=10.0, actions=[controller_spawner]),
        ]
    )
