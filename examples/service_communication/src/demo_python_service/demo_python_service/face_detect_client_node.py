import rclpy
from rclpy.node import Node
from chapt4_interfaces.srv import FaceDetector

import face_recognition
import cv2
from ament_index_python.packages import get_package_share_directory #获取功能包share目录绝对路径
import os

from cv_bridge import CvBridge

import time

from rcl_interfaces.srv import SetParameters
from rcl_interfaces.msg import Parameter,ParameterValue,ParameterType

class FaceDetectClientNode(Node):
    def __init__(self):
        super().__init__('face_detect_client_node')
        self.bridge = CvBridge() #实例化
        self.default_image_path = os.path.join(get_package_share_directory('demo_python_service'), 
                                                      'resource', 'test01.jpg')
        self.get_logger().info('Face Detect Client is ready.')
        self.client = self.create_client(FaceDetector, 'face_detect')
        self.image = cv2.imread(self.default_image_path)

    def call_set_parameters(self, parameters):
        """
        调用服务端的set_parameters服务，设置参数
        """
        # 1. 创建客户端
        update_param_client = self.create_client(SetParameters, '/face_detect_node/set_parameters')
        # 2. 等待服务端启动
        while update_param_client.wait_for_service(timeout_sec=1.0) is False:
            self.get_logger().info('Service not available, waiting again...')
        # 3. 创建请求对象
        request = SetParameters.Request()
        request.parameters = parameters
        # 4. 发送请求并等待响应
        future = update_param_client.call_async(request)
        rclpy.spin_until_future_complete(self, future) #因为参数更新往往需要更新完毕再进行下一步操作，所以这里使用阻塞方式等待服务端响应
        response = future.result()
        return response 

    def update_detect_model(self, model = 'hog'):
        """
        根据传入的model参数，构造Parameter对象，然后调用call_set_parameters更新服务端的人脸检测模型
        """
        # 构造Parameter对象
        param = Parameter()
        param.name = 'model'
        # 创建param_value，赋值
        param_value = ParameterValue()
        param_value.string_value = model
        param_value.type = ParameterType.PARAMETER_STRING
        param.value = param_value
        # 调用call_set_parameters更新服务端参数
        response = self.call_set_parameters([param])
        for result in response.results:
            if result.successful:
                self.get_logger().info(f'Parameter update successful: {result.reason}')
            else:
                self.get_logger().error(f'Parameter update failed: {result.reason}')

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
        rclpy.spin_until_future_complete(self, future)  # 边查看future结果边spin,等待服务端处理完成，直到future完成
        
        # def result_callback(future):
        #     response = future.result()  # 获取服务端响应结果
        #     self.get_logger().info(f'Face detection completed. Number of faces detected: {response.number}, Time taken: {response.use_time:.4f} seconds.')
        #     # self.show_response(response)  # 显示响应结果
        # future.add_done_callback(result_callback)
        response = future.result()  # 获取服务端响应结果
        self.get_logger().info(f'Face detection completed. Number of faces detected: {response.number}, Time taken: {response.use_time:.4f} seconds.')
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
    node.update_detect_model('hog')  # 更新服务端的人脸检测模型为HOG
    node.send_request()
    node.update_detect_model('cnn')  # 更新服务端的人脸检测模型为CNN
    node.send_request()
    rclpy.spin(node)
    rclpy.shutdown()        