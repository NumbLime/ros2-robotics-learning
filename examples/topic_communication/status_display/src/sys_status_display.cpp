#include <QApplication>
#include <QLabel>
#include <QString>

#include <rclcpp/rclcpp.hpp>
#include <status_interfaces/msg/system_status.hpp>


using SystemStatus = status_interfaces::msg::SystemStatus;

class SysStatusDisplay : public rclcpp::Node
{
private:
    /* data */
    rclcpp::Subscription<SystemStatus>::SharedPtr subscriber_;
    QLabel *label_;

public:
    SysStatusDisplay(/* args */) : Node("sys_status_display")
    {
        label_ = new QLabel();
        subscriber_ = this->create_subscription<SystemStatus>("sys_status", 10,
                                                              [&](const SystemStatus::SharedPtr msg) -> void
                                                              {
                                                                  label_->setText(get_qstr_from_msg(msg));
                                                              });
        label_->setText(get_qstr_from_msg(std::make_shared<SystemStatus>()));
        label_->show();
    };

    QString get_qstr_from_msg(const SystemStatus::SharedPtr msg)
    {
        std::stringstream show_str;
        show_str
            << "============系统状态可视化显示工具=============\n"
            << "数 据 时 间：\t" << msg->stamp.sec << "\ts\n"
            << "主 机 名 称：\t" << msg->host_name << "\t\n"
            << "CPU使用率：\t" << msg->cpu_percent << "\t%\n"
            << "内存使用率：\t" << msg->memory_percent << "\t%\n"
            << "内存总大小：\t" << msg->memory_total << "\tMiB\n"
            << "剩余可用内存：\t" << msg->memory_available << "\tMiB\n"
            << "网络发送量：\t" << msg->net_sent << "\tMiB\n"
            << "网络接收量：\t" << msg->net_recv << "\tMiB\n"
            << "===========================================";

        return QString::fromStdString(show_str.str());
    };
};

int main(int argc, char *argv[])
{
    rclcpp::init(argc, argv);
    QApplication app(argc, argv);
    auto node = std::make_shared<SysStatusDisplay>();
    std::thread spin_thread([&]() -> void
                            {
        rclcpp::spin(node); //阻塞代码
    });
    spin_thread.detach();
    app.exec(); // 执行应用，阻塞代码
    return 0;
}