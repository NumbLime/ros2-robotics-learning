#include "rclcpp/rclcpp.hpp"
#include "geometry_msgs/msg/twist.hpp"
#include <chrono>
#include "turtlesim/msg/pose.hpp"
#include "chapt4_interfaces/srv/patrol.hpp"
#include "rcl_interfaces/msg/set_parameters_result.hpp"

using Patrol = chapt4_interfaces::srv::Patrol;
using SetParametersResult = rcl_interfaces::msg::SetParametersResult;

using namespace std::chrono_literals;

class TurtleControlNode : public rclcpp::Node
{
private:
    OnSetParametersCallbackHandle::SharedPtr parameter_callback_handle_; // 参数回调句柄
    rclcpp::Service<Patrol>::SharedPtr patrol_service_;                  // 服务的智能指针
    rclcpp::Publisher<geometry_msgs::msg::Twist>::SharedPtr publisher_;  // 发布者的智能指针
    rclcpp::Subscription<turtlesim::msg::Pose>::SharedPtr subscriber_;   // 订阅者的智能指针
    double target_x_{1.0};                                               // 目标位置的x坐标
    double target_y_{1.0};                                               // 目标位置的y坐标
    double k_{1.0};                                                      // 线速度比例系数
    double k_angle_{1.0};                                                // 角速度比例系数
    double max_speed_{3.0};                                              // 最大线速度

public:
    explicit TurtleControlNode(const std::string &node_name)
        : Node(node_name)
    {
        this->declare_parameter("k", 1.0);
        this->declare_parameter("max_speed", 1.0);
        this->get_parameter("k", k_);
        this->get_parameter("max_speed", max_speed_);
        // 节点内部改变参数数值的方法
        // this->set_parameters({rclcpp::Parameter("k", 2.0), rclcpp::Parameter("max_speed", 2.0)});
        parameter_callback_handle_ = this->add_on_set_parameters_callback([&](
                    const std::vector<rclcpp::Parameter> &parameters)
                    -> rcl_interfaces::msg::SetParametersResult
                {
                rcl_interfaces::msg::SetParametersResult result;
                result.successful = true;
                for (const auto &parameter : parameters)
                {
                    if (parameter.get_name() == "k")
                    {
                        k_ = parameter.as_double();
                        RCLCPP_INFO(this->get_logger(), "更新参数k为：%f", k_);
                    }
                    else if (parameter.get_name() == "max_speed")
                    {
                        max_speed_ = parameter.as_double();
                        RCLCPP_INFO(this->get_logger(), "更新参数max_speed为：%f", max_speed_);
                    }
                }
                return result; });
        patrol_service_ = this->create_service<Patrol>("patrol",
            [&](const Patrol::Request::SharedPtr request,
                Patrol::Response::SharedPtr response) -> void
            {
                if (
                    (request->target_x > 0.0 && request->target_x < 12.0f) &&
                    (request->target_y > 0.0 && request->target_y < 12.0f))
                {
                    this->target_x_ = request->target_x;
                    this->target_y_ = request->target_y;
                    response->result = Patrol::Response::SUCCESS;
                    RCLCPP_INFO(get_logger(), "设置目标位置为：x=%f,y=%f", this->target_x_, this->target_y_);
                }
                else
                {
                    response->result = Patrol::Response::FAIL;
                    RCLCPP_WARN(get_logger(), "目标位置超出范围，请设置在(0,0)到(12,12)之间");
                }
            });
        publisher_ = this->create_publisher<geometry_msgs::msg::Twist>("turtle1/cmd_vel", 10);
        subscriber_ = this->create_subscription<turtlesim::msg::Pose>(
            "turtle1/pose", 10,
            std::bind(&TurtleControlNode::on_pose_received_, this, std::placeholders::_1));
    }

    void on_pose_received_(const turtlesim::msg::Pose::SharedPtr pose) // 参数：收到数据的共享指针
    {
        // 1.获取当前位置
        auto current_x = pose->x;
        auto current_y = pose->y;
        // RCLCPP_INFO(get_logger(), "当前：x=%f,y=%f", current_x, current_y);

        // 2.计算当前位置与目标位置之间的距离差和朝向角度差
        auto distance = std::sqrt(
            (target_x_ - current_x) * (target_x_ - current_x) +
            (target_y_ - current_y) * (target_y_ - current_y));

        auto angle = std::atan2((target_y_ - current_y), (target_x_ - current_x)) - pose->theta;

        // 3.控制策略
        auto msg = geometry_msgs::msg::Twist();
        if (distance > 0.2)
        {
            if (fabs(angle) > 0.2)
            {
                msg.angular.z = k_angle_ * angle;
            }
            else
            {
                msg.linear.x = k_ * distance;
            }
        }

        // 4.限制线速度最大值
        if (msg.linear.x > max_speed_)
        {
            msg.linear.x = max_speed_;
        }

        publisher_->publish(msg);
    }
};

int main(int argc, char *argv[])
{
    rclcpp::init(argc, argv);
    auto node = std::make_shared<TurtleControlNode>("turtle_control");
    rclcpp::spin(node);
    rclcpp::shutdown();

    return 0;
}