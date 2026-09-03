import launch
import launch_ros

def generate_launch_description():
    # 产生launch描述

    action_node_face_detect_node =  launch_ros.actions.Node(
            package='demo_python_service',
            executable='face_detect_node',
            output='both',
    )

    action_node_face_detect_client_node =  launch_ros.actions.Node(
            package='demo_python_service',
            executable='face_detect_client_node',
            output='both',
    )

    return launch.LaunchDescription([
        # actions动作
        action_node_face_detect_node,
        action_node_face_detect_client_node,
    ])