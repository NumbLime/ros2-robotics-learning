from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        Node(
            package='demo_python_tf',
            executable='static_tf_broadcaster',
            name='python_tf_static_broadcaster',
            output='screen',
        ),
        Node(
            package='demo_python_tf',
            executable='dynamic_tf_broadcaster',
            name='python_tf_dynamic_broadcaster',
            output='screen',
        ),
        Node(
            package='demo_python_tf',
            executable='tf_listener',
            name='python_tf_listener',
            output='screen',
        ),
    ])