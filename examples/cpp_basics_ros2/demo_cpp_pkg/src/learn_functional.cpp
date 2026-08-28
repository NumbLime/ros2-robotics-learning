#include <iostream>
#include <functional> // 函数包装器头文件

// 自由函数

void save_with_free_function(const std::string &filename)
{
    std::cout << "Saving with free function: " << filename << std::endl;
}

// 类成员函数

class FileSaver
{
private:
    /*data */
public:
    FileSaver(/* args */) = default;
    ~FileSaver() = default;

    void save_with_member_function(const std::string &filename)
    {
        std::cout << "Saving with member function: " << filename << std::endl;
    };
};

int main()
{
    FileSaver file_saver;

    // Lambda函数
    auto save_with_lambda = [](const std::string &filename) -> void
    {
        std::cout << "Saving with lambda function: " << filename << std::endl;
    };
    // save_with_free_function("file1.txt");
    // file_saver.save_with_member_function("file2.txt");
    // save_with_lambda("file3.txt");

    std::function<void(const std::string &)> save1 = save_with_free_function;
    std::function<void(const std::string &)> save3 = save_with_lambda;

    // 成员函数放入包装器
    std::function<void(const std::string &)> save2 = std::bind(&FileSaver::save_with_member_function,
                                                               &file_saver, std::placeholders::_1);

    // 统一的调用方式
    save1("file1.txt");
    save2("file2.txt");
    save3("file3.txt");

    return 0;
}