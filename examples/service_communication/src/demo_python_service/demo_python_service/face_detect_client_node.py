import rclpy
from rclpy.node import Node
from chapt4_interfaces.srv import FaceDetector

import face_recognition
import cv2
from ament_index_python.packages import get_package_share_directory #获取功能包share目录绝对路径
import os

from cv_bridge import CvBridge

import time

class FaceDetectClientNode(Node):
    def __init__(self):
        super().__init__('face_detect_client_node')
        self.bridge = CvBridge() #实例化
        self.default_image_path = os.path.join(get_package_share_directory('demo_python_service'), 
                                                      'resource', 'test01.jpg')
        self.get_logger().info('Face Detect Client is ready.')
        self.client = self.create_client(FaceDetector, 'face_detect')
        self.image = cv2.imread(self.default_image_path)

    def send_request(self):
        # 判断服务端是否在线
        while self.client.wait_for_service(timeout_sec=1.0) == False:
            self.get_logger().info('Service not available, waiting again...')
        # 创建请求对象
        request = FaceDetector.Request()
        request.image = self.bridge.cv2_to_imgmsg(self.image)
        # 发送请求并等待响应
        # 使用异步调用方式发送请求
        future = self.client.call_async(request) #现在的future并没有包含响应结果，等待服务端处理完成后放入。   
        # while not future.done():
        #     time.sleep(1.0)  # 休眠当前线程，等待服务端处理完成,造成阻塞，无法接收服务端响应结果，导致永远无法完成，循环无法结束
        # rclpy.spin_until_future_complete(self, future)  # 边查看future结果边spin,等待服务端处理完成，直到future完成
        
        def result_callback(future):
            response = future.result()  # 获取服务端响应结果
            self.get_logger().info(f'Face detection completed. Number of faces detected: {response.number}, Time taken: {response.use_time:.4f} seconds.')
            self.show_response(response)  # 显示响应结果
        future.add_done_callback(result_callback)
        # response = future.result()  # 获取服务端响应结果
        # self.get_logger().info(f'Face detection completed. Number of faces detected: {response.number}, Time taken: {response.use_time:.4f} seconds.')
        # self.show_response(response)  # 显示响应结果   

    def show_response(self, response):
        for i in range(response.number):
            top = response.top[i]
            right = response.right[i]
            bottom = response.bottom[i]
            left = response.left[i]
            cv2.rectangle(self.image, (left, top), (right, bottom), (0, 0, 255), 4)
        cv2.imshow("Detected Faces", self.image)

        cv2.waitKey(0) #也是阻塞的，直到按下任意键才会继续执行，也会阻塞rclpy.spin()，但在这里只显示一次图像，所以不会影响后续的服务调用
         

def main():
    rclpy.init()
    node = FaceDetectClientNode()
    node.send_request()
    rclpy.spin(node)
    rclpy.shutdown()        