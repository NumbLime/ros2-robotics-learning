#include "rclcpp/rclcpp.hpp"

int main(int argc,char** argv)
{
    rclcpp::init(argc,argv); //初始化rclcpp
    auto node = std::make_shared<rclcpp::Node>("cpp_node"); //创建一个C++节点
    RCLCPP_INFO(node->get_logger(),"你好,这是一个C++节点!"); //打印日志信息
    rclcpp::spin(node);
    rclcpp::shutdown();
    return 0;
}