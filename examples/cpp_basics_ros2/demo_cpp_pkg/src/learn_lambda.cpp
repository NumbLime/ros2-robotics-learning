#include <iostream>
#include <algorithm>

int main()
{
    auto add = [](int a, int b)  -> int {return a + b;}; // 定义一个lambda表达式，接受两个整数参数，返回它们的和
    int sum = add(3, 5); // 调用lambda表达式

    auto print_sum = [sum]()
    {
      std::cout << "The sum is: " << sum << std::endl; // 输出sum的值
    };
    sum = 100;
    print_sum(); // 调用print_sum lambda表达式
    

    return 0;
}