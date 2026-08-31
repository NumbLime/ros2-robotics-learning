import espeakng
import rclpy
from rclpy.node import Node
from example_interfaces.msg import String
from queue import Queue
import threading
import time

class NovelSubNode(Node):
    def __init__(self, node_name):
        super().__init__(node_name)
        self.get_logger().info(f"Node {node_name} has been started.")
        self.novels_queue_ = Queue()  # 创建一个队列来存储小说内容
        self.novel_subscriber = self.create_subscription(String, 'novel',
                                                         self.novel_callback, 10)
        self.speech_thread_= threading.Thread(target=self.speak_thread)
        self.speech_thread_.start()  # 启动语音线程

    def novel_callback(self, msg):
        self.novels_queue_.put(msg.data)  # 将接收到的小说内容放入队列中

    def speak_thread(self):
        speaker = espeakng.Speaker()
        speaker.voice = 'zh'
        while rclpy.ok():
            if self.novels_queue_.qsize() > 0:
                text = self.novels_queue_.get()  # 从队列中获取一行小说内容
                self.get_logger().info(f'Speaking novel line: {text}')
                speaker.say(text)  # 使用espeak-ng进行语音合成
                speaker.wait()  # 等待语音合成完成
            else:
                time.sleep(1.0)  # 如果队列为空,休眠


def main():
    rclpy.init()
    node = NovelSubNode("novel_sub")
    rclpy.spin(node)
    rclpy.shutdown()