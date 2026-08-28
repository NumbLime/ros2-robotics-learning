#include <iostream>
#include <thread>                //多线程
#include <chrono>                //时间相关
#include <functional>            //函数包装器
#include <cpp-httplib/httplib.h> //下载相关,下载时域名与路径分成了两个参数

class Download
{
private:
    /*data */
public:
    void download(const std::string &host, const std::string &path, 
        const std::function<void(const std::string &, const std::string &)> &callback_word_count)
    {
        std::cout << "线程id: " << std::this_thread::get_id() << std::endl;
        httplib::Client client(host);
        auto respense = client.Get(path);
        if (respense && respense->status == 200)
        {
            callback_word_count(path, respense->body);
        }
        else
        {
            std::cout << "下载失败, 文件路径: " << path << std::endl;
        }
    };

    void start_download(const std::string &host, const std::string &path, 
        const std::function<void(const std::string &, const std::string &)> &callback_word_count)
    {
        auto download_fun = std::bind(&Download::download, this, std::placeholders::_1, 
            std::placeholders::_2, std::placeholders::_3);
        std::thread thread(download_fun, host, path, callback_word_count); //创建线程对象,并传入参数
        thread.detach(); //分离线程,不阻塞主线程
    };
};

int main()
{
    auto d = Download();
    auto word_count = [](const std::string &path, const std::string &content) -> void
    {
        std::cout << "下载完成, 文件路径: " << path << ", 文件内容长度: " << content.size() 
                     << "部分文件内容：" << content.substr(0, 9) << std::endl;
    };
    d.start_download("http://0.0.0.0:8000", "/novel1.txt", word_count); //第三个参数是一个函数对象，将Lambda表达式直接传入
    d.start_download("http://0.0.0.0:8000", "/novel2.txt", word_count);
    d.start_download("http://0.0.0.0:8000", "/novel3.txt", word_count);

    std::this_thread::sleep_for(std::chrono::seconds(10)); //休眠10s,等待下载完成

    return 0;
}