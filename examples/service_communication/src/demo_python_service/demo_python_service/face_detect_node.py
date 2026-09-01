import rclpy
from rclpy.node import Node
from chapt4_interfaces.srv import FaceDetector

import face_recognition
import cv2
from ament_index_python.packages import get_package_share_directory #获取功能包share目录绝对路径
import os

from cv_bridge import CvBridge

import time


class FaceDetectNode(Node):
    def __init__(self):
        super().__init__('face_detect_node')
        self.service_ = self.create_service(FaceDetector, 'face_detect', 
                             self.face_detect_callback)
        self.bridge = CvBridge() #实例化
        self.number_of_times_to_upsample = 1
        self.model = "hog"
        self.default_image_path = os.path.join(get_package_share_directory('demo_python_service'), 
                                                      'resource', 'default.jpg')
        self.get_logger().info('Face Detect Service is ready.')

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