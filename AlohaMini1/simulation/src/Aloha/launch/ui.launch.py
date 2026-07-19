from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    ui_port = LaunchConfiguration("ui_port")
    rosbridge_port = LaunchConfiguration("rosbridge_port")
    bind_address = LaunchConfiguration("bind_address")
    use_sim_time = LaunchConfiguration("use_sim_time")

    ui_gateway = Node(
        package="aloha",
        executable="ui_gateway.py",
        output="screen",
        parameters=[{"use_sim_time": ParameterValue(use_sim_time, value_type=bool)}],
    )

    rosbridge = Node(
        package="rosbridge_server",
        executable="rosbridge_websocket",
        name="rosbridge_websocket",
        output="screen",
        parameters=[
            {
                "address": ParameterValue(bind_address, value_type=str),
                "port": ParameterValue(rosbridge_port, value_type=int),
            }
        ],
    )

    ui_server = Node(
        package="aloha",
        executable="ui_server.py",
        name="ui_server",
        output="screen",
        parameters=[
            {
                "address": ParameterValue(bind_address, value_type=str),
                "port": ParameterValue(ui_port, value_type=int),
                "use_sim_time": ParameterValue(use_sim_time, value_type=bool),
            }
        ],
    )

    return LaunchDescription(
        [
            DeclareLaunchArgument("ui_port", default_value="8000"),
            DeclareLaunchArgument("rosbridge_port", default_value="9090"),
            DeclareLaunchArgument("bind_address", default_value="127.0.0.1"),
            DeclareLaunchArgument("use_sim_time", default_value="false"),
            ui_gateway,
            rosbridge,
            ui_server,
        ]
    )
