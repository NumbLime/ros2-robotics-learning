#include <iostream>
#include <memory>

int main()
{
    auto p1 = std::make_shared<std::string>("Hello, shared_ptr!"); // 创建一个 shared_ptr，指向一个字符串
    std::cout << "p1的引用计数：" << p1.use_count() << "指向内存地址：" << p1.get() << std::endl; // 计数1

    auto p2 = p1; // 复制 shared_ptr，引用计数增加
    std::cout << "p1的引用计数：" << p1.use_count() << "指向内存地址：" << p1.get() << std::endl; // 计数2
    std::cout << "p2的引用计数：" << p2.use_count() << "指向内存地址：" << p2.get() << std::endl; // 计数2

    p1.reset(); // 重置 p1，引用计数减少
    std::cout << "p1的引用计数：" << p1.use_count() << "指向内存地址：" << p1.get() << std::endl; // 计数0
    std::cout << "p2的引用计数：" << p2.use_count() << "指向内存地址：" << p2.get() << std::endl; // 计数1

    std::cout << "p2指向的内存地址数据：" << p2->c_str() << std::endl; // 输出 p2 指向的字符串内容
    return 0;
}