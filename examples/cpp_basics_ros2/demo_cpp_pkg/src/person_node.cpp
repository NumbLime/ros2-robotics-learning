#include "rclcpp/rclcpp.hpp"

class PersonNode : public rclcpp::Node
{
private:
    // 申明
    std::string name_;
    int age_;

public:
    PersonNode(const std::string &node_name, const std::string &name, const int age)
        : Node(node_name) /*调用父类构造函数*/
    {
        this->name_ = name;
        this->age_ = age;
    };

    void eat(const std::string &food_name)
    {
        RCLCPP_INFO(this->get_logger(), "我是%s,我今年%d岁,爱吃%s", this->name_.c_str(),
                    this->age_, food_name.c_str());
    };
};

int main(int argc, char **argv)
{
    rclcpp::init(argc, argv);
    auto node = std::make_shared<PersonNode>("person_node", "养院士", 18);
    RCLCPP_INFO(node->get_logger(), "你好,这是一个C++节点!用来记录一个人的信息");
    node->eat("汉堡王");
    rclcpp::spin(node);
    rclcpp::shutdown();

    return 0;
}