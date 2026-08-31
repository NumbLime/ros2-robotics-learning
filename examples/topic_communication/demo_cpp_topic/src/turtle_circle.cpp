#include "rclcpp/rclcpp.hpp"
#include "geometry_msgs/msg/twist.hpp"
#include <chrono>

using namespace std::chrono_literals;

class TurtleCircleNode : public rclcpp::Node
{
private:
    rclcpp::TimerBase::SharedPtr timer_;                                // 定时器的智能指针
    rclcpp::Publisher<geometry_msgs::msg::Twist>::SharedPtr publisher_; // 发布者的智能指针

public:
    explicit TurtleCircleNode(const std::string &node_name)
        : Node(node_name)
    {
        // Create a publisher for the turtle's velocity
        publisher_ = this->create_publisher<geometry_msgs::msg::Twist>("turtle1/cmd_vel", 10);

        // Set the timer to publish at a fixed rate
        timer_ = this->create_wall_timer(
            1000ms,
            std::bind(&TurtleCircleNode::timer_callback, this));
    }

    void timer_callback()
    {
        auto message = geometry_msgs::msg::Twist();
        message.linear.x = 1.0;
        message.angular.z = 0.5;
        publisher_->publish(message);
    }
};

int main(int argc, char* argv[])
{
    rclcpp::init(argc, argv);
    auto node = std::make_shared<TurtleCircleNode>("turtle_circle");
    rclcpp::spin(node);
    rclcpp::shutdown();

    return 0;
}
