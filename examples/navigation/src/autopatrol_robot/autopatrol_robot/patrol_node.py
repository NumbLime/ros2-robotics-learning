import rclpy
from pathlib import Path
import time
from rclpy.time import Time
from geometry_msgs.msg import PoseStamped
from nav2_simple_commander.robot_navigator import BasicNavigator, TaskResult
from tf2_ros import TransformListener, Buffer  # 坐标监听器
from tf_transformations import quaternion_from_euler  # 四元数与欧拉角转换函数
from autopatrol_interfaces.srv import SpeechText
from sensor_msgs.msg import Image  # 消息接口
from cv_bridge import CvBridge  # 转换图像格式
import cv2  # 保存图像


class PatrolNode(BasicNavigator):
    def __init__(self, node_name='patrol_node'):
        super().__init__(node_name)
        # 声明相关参数
        self.declare_parameter('initial_point', [0.0, 0.0, 0.0])
        self.declare_parameter(
            'target_points', [
                0.0, 0.0, 0.0, 1.0, 1.0, 1.57])  # 参数不支持二维数组，所以需要后面处理
        self.declare_parameter('image_save_path', '')
        self.initial_point_ = self.get_parameter('initial_point').value
        self.target_points_ = self.get_parameter('target_points').value

        configured_image_path = self.get_parameter('image_save_path').value
        if configured_image_path:
            self.image_save_path_ = Path(configured_image_path).expanduser()
        else:
            self.image_save_path_ = Path.home() / '.ros' / 'autopatrol_images'

        self.image_save_path_.mkdir(parents=True, exist_ok=True)
        self.get_logger().info(f'巡检图像保存目录：{self.image_save_path_}')

        self.buffer_ = Buffer()
        self.listener_ = TransformListener(self.buffer_, self)
        self.speech_client_ = self.create_client(SpeechText, 'speech_text')
        self.cv_bridge_ = CvBridge()
        self.latest_img_ = None
        self.img_sub_ = self.create_subscription(
            Image, '/camera_sensor/image_raw', self.image_callback, 1)

    def image_callback(self, msg):
        self.latest_img_ = msg

    def record_image(self, timeout_sec=3.0):
        """等待到达目标点后产生的新图像并保存."""
        capture_requested_at = self.get_clock().now()
        deadline = time.monotonic() + timeout_sec

        while rclpy.ok() and time.monotonic() < deadline:
            rclpy.spin_once(self, timeout_sec=0.1)

            if self.latest_img_ is None:
                continue

            image_time = Time.from_msg(self.latest_img_.header.stamp)
            if image_time <= capture_requested_at:
                continue

            pose = self.get_current_pose()
            cv_image = self.cv_bridge_.imgmsg_to_cv2(
                self.latest_img_,
                desired_encoding='bgr8'
            )

            image_path = self.image_save_path_ / (
                f'img_{pose.translation.x:.2f}_'
                f'{pose.translation.y:.2f}.png'
            )

            if cv2.imwrite(str(image_path), cv_image):
                self.get_logger().info(f'图像已保存：{image_path}')
                return True

            self.get_logger().error(f'图像保存失败：{image_path}')
            return False

        self.get_logger().warn(
            f'{timeout_sec:.1f} 秒内没有收到到达目标点后的新图像'
        )
        return False

    def get_pose_by_xyywa(self, x, y, yaw):
        """根据x、y和yaw生成PoseStamped对象."""
        pose = PoseStamped()
        pose.header.frame_id = "map"
        pose.pose.position.x = x
        pose.pose.position.y = y
        # 注意函数返回四元数的顺序，此函数返回为xyzw
        quat = quaternion_from_euler(0, 0, yaw)
        pose.pose.orientation.x = quat[0]
        pose.pose.orientation.y = quat[1]
        pose.pose.orientation.z = quat[2]
        pose.pose.orientation.w = quat[3]
        return pose

    def init_robot_pose(self):
        """初始化机器人位姿."""
        self.initial_point_ = self.get_parameter('initial_point').value
        init_pose = self.get_pose_by_xyywa(self.initial_point_[0],
                                           self.initial_point_[1], self.initial_point_[2])
        self.setInitialPose(init_pose)
        self.waitUntilNav2Active()  # 等待导航可用

    def get_target_points(self):
        """从参数中解析并返回目标点集合."""
        points = []
        self.target_points_ = self.get_parameter('target_points').value
        for index in range(int(len(self.target_points_) / 3)):
            x = self.target_points_[index * 3]
            y = self.target_points_[index * 3 + 1]
            yaw = self.target_points_[index * 3 + 2]
            points.append([x, y, yaw])
            self.get_logger().info(f'获取到目标点{index}->{x},{y},{yaw}')
        return points

    def nav_to_pose(self, target_pose):
        """导航到目标点并返回任务最终状态."""
        self.goToPose(target_pose)

        while not self.isTaskComplete():
            feedback = self.getFeedback()
            if feedback is not None:
                self.get_logger().info(
                    f'剩余距离：{feedback.distance_remaining:.2f} m'
                )

        result = self.getResult()
        self.get_logger().info(f'导航结果：{result}')
        return result

    def get_current_pose(self):
        """查询并返回机器人当前位姿."""
        while rclpy.ok():
            try:
                result = self.buffer_.lookup_transform('map', 'base_footprint',
                                                       rclpy.time.Time())
                #    rclpy.time.Time(seconds = 0.0))
                #    rclpy.time.Duration(seconds = 1.0))
                transform = result.transform
                self.get_logger().info(f'平移：{transform.translation}')
                return transform
            except Exception as e:
                self.get_logger().warn(f'获取TF失败,原因:{str(e)}')

    def speech_text(self, text):
        """调用语音合成服务并等待结果."""
        while not self.speech_client_.wait_for_service(timeout_sec=1.0):
            self.get_logger().info('语音合成服务未上线，等待中...')
        request = SpeechText.Request()
        request.text = text
        future = self.speech_client_.call_async(request)
        rclpy.spin_until_future_complete(self, future)
        if future.result() is not None:
            response = future.result()
            if response.result:
                self.get_logger().info(f'语音合成成功{text}')
            else:
                self.get_logger().warn('语音合成失败')
        else:
            self.get_logger().warn('语音合成服务响应失败')


def main():
    rclpy.init()
    patrol = PatrolNode()  # 节点
    # rclpy.spin(patrol)
    patrol.speech_text('正在准备初始化位置')
    patrol.init_robot_pose()
    patrol.speech_text('位置初始化完成')

    while rclpy.ok():
        points = patrol.get_target_points()

        for point in points:
            x, y, yaw = point
            target_pose = patrol.get_pose_by_xyywa(x, y, yaw)

            patrol.speech_text(f'正在准备前往{x},{y}目标点')
            result = patrol.nav_to_pose(target_pose)

            if result == TaskResult.SUCCEEDED:
                patrol.speech_text(
                    f'已经到达{x},{y}目标点，正在准备记录图像'
                )
                if patrol.record_image():
                    patrol.speech_text('图像记录完毕')
                else:
                    patrol.speech_text('图像记录失败')
            elif result == TaskResult.CANCELED:
                patrol.speech_text(f'前往{x},{y}的导航任务已取消')
            elif result == TaskResult.FAILED:
                patrol.speech_text(f'前往{x},{y}的导航任务失败')
            else:
                patrol.speech_text(f'前往{x},{y}的导航结果未知')
