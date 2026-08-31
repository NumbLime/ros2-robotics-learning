import rclpy
from rclpy.node import Node
import requests
from example_interfaces.msg import String
from queue import Queue


class NovelPubNode(Node):
    def __init__(self, node_name):
        super().__init__(node_name)
        self.get_logger().info(f"Node {node_name} has been started.")
        self.novels_queue_= Queue() #创建一个队列来存储小说内容
        self.novel_publisher_= self.create_publisher(String, 'novel', 10) #第三个参数是队列长度
        self.timer_ = self.create_timer(5, self.timer_callback)

    def timer_callback(self):
        if self.novels_queue_.qsize() > 0:
            line = self.novels_queue_.get()  # 从队列中获取一行小说内容
            msg = String()
            msg.data = line
            self.novel_publisher_.publish(msg)
            self.get_logger().info(f'Published novel line: {line}')

    def download(self, url):
        response = requests.get(url)
        response.encoding = 'utf-8'
        text = response.text
        self.get_logger().info(f'Downloaded text from {url}: {len(text)}')
        for line in text.splitlines():
            self.novels_queue_.put(line)  # 将每一行小说内容放入队列中


def main():
    rclpy.init()
    node = NovelPubNode("novel_pub")
    node.download('http://0.0.0.0:8000/novel1.txt')
    rclpy.spin(node)
    rclpy.shutdown()