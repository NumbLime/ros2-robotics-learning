#include "rclcpp/rclcpp.hpp"
#include "chapt4_interfaces/srv/patrol.hpp"
#include <chrono>
#include <ctime>
#include "rcl_interfaces/msg/parameter.hpp"
#include "rcl_interfaces/msg/parameter_value.hpp"
#include "rcl_interfaces/msg/parameter_type.hpp"
#include "rcl_interfaces/srv/set_parameters.hpp"

using Patrol = chapt4_interfaces::srv::Patrol;
using namespace std::chrono_literals; //使用 std::chrono_literals 命名空间中的时间单位 s,ms
using SetP = rcl_interfaces::srv::SetParameters;

class PatrolClient : public rclcpp::Node
{
private:
    rclcpp::TimerBase::SharedPtr timer_;
    rclcpp::Client<Patrol>::SharedPtr patrol_client_;
  

public:
    explicit PatrolClient(const std::string &node_name)
        : Node(node_name)
    {
        srand48(time(NULL)); //初始化随机数种子
        patrol_client_ = this->create_client<Patrol>("patrol");
        timer_ = this->create_wall_timer(
            10s,
            [this]() -> void {
                // 1.检测服务是否启动
                while (!this->patrol_client_->wait_for_service(1s))
                {
                    if (!rclcpp::ok())
                    {
                        RCLCPP_ERROR(this->get_logger(), "客户端被中断，退出");
                        return;
                    }
                    RCLCPP_INFO(this->get_logger(), "等待服务启动...");
                }
                // 2.创建请求对象
                auto request = std::make_shared<Patrol::Request>();
                request->target_x = (float)(drand48() * 10.0);
                request->target_y = (float)(drand48() * 10.0);
                RCLCPP_INFO(this->get_logger(), "请求巡逻目标点: [%.2f, %.2f]", request->target_x, request->target_y);
                // 3.发送请求
                this->patrol_client_->async_send_request(request,[&]
                    (rclcpp::Client<Patrol>::SharedFuture result_future) -> void {
                        auto response = result_future.get();
                        if(response->result == Patrol::Response::SUCCESS)
                        {
                            RCLCPP_INFO(this->get_logger(), "巡逻成功");
                        }
                        else
                        {
                            RCLCPP_ERROR(this->get_logger(), "巡逻失败");
                        }
                });
            }
        );
    }

    //创建客户端发送请求，返回结果
    SetP::Response::SharedPtr call_set_parameter(const rcl_interfaces::msg::Parameter &param)
    {
        auto set_param_client = this->create_client<SetP>("/turtle_control/set_parameters");
        
        // 1.检测服务是否启动
        while (!set_param_client->wait_for_service(1s))
        {
            if (!rclcpp::ok())
            {
                RCLCPP_ERROR(this->get_logger(), "客户端被中断，退出");
                return nullptr;
            }
            RCLCPP_INFO(this->get_logger(), "等待服务启动...");
        }
        // 2.创建请求对象
        auto request = std::make_shared<SetP::Request>();
        request->parameters.push_back(param);

        // 3.发送请求
        auto future = set_param_client->async_send_request(request);
        rclcpp::spin_until_future_complete(this->get_node_base_interface(), future);
        auto response = future.get();
        return response;
        // this->patrol_client_->async_send_request(request,[&]
        //     (rclcpp::Client<Patrol>::SharedFuture result_future) -> void {
        //         auto response = result_future.get();
        //         if(response->result == Patrol::Response::SUCCESS)
        //         {
        //             RCLCPP_INFO(this->get_logger(), "巡逻成功");
        //         }
        //         else
        //         {
        //             RCLCPP_ERROR(this->get_logger(), "巡逻失败");
        //         }
        // });
            
    }

    //外部调用更新参数K的函数
    void update_server_param_k(double k){
        // 创建参数对象
        auto param = rcl_interfaces::msg::Parameter();
        param.name = "k";
        // 创建参数值对象
        auto param_value = rcl_interfaces::msg::ParameterValue();
        param_value.type = rcl_interfaces::msg::ParameterType::PARAMETER_DOUBLE;
        param_value.double_value = k;
        param.value = param_value;
        // 请求更新参数并处理
        auto response = this->call_set_parameter(param);
        if (response == NULL){
            RCLCPP_ERROR(this->get_logger(), "请求更新参数失败");
            return;
        }
        for (const auto &result : response->results) {
            if (result.successful == true) {
                RCLCPP_INFO(this->get_logger(), "参数更新成功");
            } else {
                RCLCPP_ERROR(this->get_logger(), "参数更新失败: %s", result.reason.c_str());
            }
        }
    }


};

int main(int argc, char *argv[])
{
    rclcpp::init(argc, argv);
    auto node = std::make_shared<PatrolClient>("patrol_client");
    node->update_server_param_k(4.0);
    rclcpp::spin(node);
    rclcpp::shutdown();

    return 0;
}