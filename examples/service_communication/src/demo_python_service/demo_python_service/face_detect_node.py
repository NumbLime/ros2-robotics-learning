import rclpy
from rclpy.node import Node
from chapt4_interfaces.srv import FaceDetector

import face_recognition
import cv2
from ament_index_python.packages import get_package_share_directory #获取功能包share目录绝对路径
import os

from cv_bridge import CvBridge

import time
from rcl_interfaces.msg import SetParametersResult

class FaceDetectNode(Node):
    def __init__(self):
        super().__init__('face_detect_node')
        self.default_image_path = os.path.join(get_package_share_directory('demo_python_service'), 
                                                      'resource', 'default.jpg')
        self.service_ = self.create_service(FaceDetector, 'face_detect', 
                             self.face_detect_callback)
        self.bridge = CvBridge() #实例化
        self.declare_parameter('number_of_times_to_upsample', 1)
        self.declare_parameter('model', 'hog')
        self.number_of_times_to_upsample = self.get_parameter('number_of_times_to_upsample').value
        self.model = self.get_parameter('model').value
        self.get_logger().info('Face Detect Service is ready.')
        self.add_on_set_parameters_callback(self.parameters_callback)
        
        # 设置自身节点参数的方法，确保在节点启动时就设置参数，而不是依赖外部客户端调用set_parameters服务
        # self.set_parameters([rclpy.Parameter('model', rclpy.Parameter.Type.STRING, 'cnn')])

    def parameters_callback(self, parameters):
        for parameter in parameters:
            if parameter.name == 'number_of_times_to_upsample':
                self.number_of_times_to_upsample = parameter.value
                self.get_logger().info(f'Updated number_of_times_to_upsample to {self.number_of_times_to_upsample}')
            elif parameter.name == 'model':
                self.model = parameter.value
                self.get_logger().info(f'Updated model to {self.model}')
        return SetParametersResult(successful=True)

    def face_detect_callback(self, request, response):
        if request.image.data:
            # 将ROS图像消息转换为OpenCV图像
            cv_image = self.bridge.imgmsg_to_cv2(request.image)
        else:
            # 如果没有提供图像数据，则使用默认图片进行人脸检测
            cv_image = cv2.imread(self.default_image_path)
            self.get_logger().info(f'No image data provided. Using default image: {self.default_image_path}')

        start_time = time.time()  # 记录开始时间
        self.get_logger().info(f'Starting face detection...')
        # 使用face_recognition库进行人脸检测
        face_locations = face_recognition.face_locations(cv_image,
                                number_of_times_to_upsample=self.number_of_times_to_upsample, 
                                model=self.model)
        response.use_time = time.time() - start_time  # 计算使用时间
        response.number = len(face_locations)
        for (top, right, bottom, left) in face_locations:
            response.top.append(top)
            response.right.append(right)
            response.bottom.append(bottom)
            response.left.append(left)
        
        return response #必须返回response对象，否则会报错


def main():
    rclpy.init()
    node = FaceDetectNode()
    rclpy.spin(node)
    rclpy.shutdown()