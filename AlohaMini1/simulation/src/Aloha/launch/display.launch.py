import os
import xacro
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    # 获取包的目录
    bringup_dir = get_package_share_directory('aloha')
    
    # Portable visualization description (no Gazebo or ros2_control tags).
    xacro_path = os.path.join(bringup_dir, 'urdf', 'aloha_visual.urdf.xacro')
    
    # RViz 配置文件路径
    rviz_config_path = os.path.join(bringup_dir, 'rviz', 'urdf.rviz')
    
    robot_description = xacro.process_file(xacro_path).toxml()
    
    # 创建节点
    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        output='screen',
        parameters=[{
            'robot_description': robot_description,
            'use_sim_time': False
        }]
    )
    
    joint_state_publisher = Node(
        package='joint_state_publisher',
        executable='joint_state_publisher',
        name='joint_state_publisher',
        output='screen',
        parameters=[{
            'use_sim_time': False
        }]
    )
    
    rviz2 = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        arguments=['-d', rviz_config_path],
        output='screen',
        parameters=[{'use_sim_time': False}]
    )
    
    return LaunchDescription([
        robot_state_publisher,
        joint_state_publisher,
        rviz2
    ])
