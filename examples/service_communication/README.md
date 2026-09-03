# ROS 2 第四章：服务与参数通信

本章记录 ROS 2 服务（Service）、参数（Parameter）、自定义 `.srv` 接口，以及 Python 人脸检测服务端/客户端的实践。

## 1. 本章工作空间结构

本仓库中，`service_communication` 是第四章的 **ROS 2 工作空间根目录**，而不是功能包；所有功能包统一放入 `src/`。

```text
ros2-robotics-learning/
└── examples/
    └── service_communication/              # 第四章 ROS 2 工作空间
        ├── README.md                        # 本学习记录
        └── src/
            ├── chapt4_interfaces/          # 自定义服务接口包
            │   ├── CMakeLists.txt
            │   ├── package.xml
            │   └── srv/
            │       ├── FaceDetector.srv
            │       └── Patrol.srv
            └── demo_python_service/        # 人脸检测功能包
                ├── demo_python_service/
                │   ├── __init__.py
                │   ├── learn_face_detect.py
                │   ├── face_detect_node.py
                │   └── face_detect_client_node.py
                ├── resource/
                │   ├── demo_python_service
                │   ├── default.jpg
                │   └── test01.jpg
                ├── package.xml
                ├── setup.py
                └── setup.cfg
            └── demo_cpp_service/           # 海龟巡逻功能包
                ├── CMakeLists.txt
                ├── package.xml
                ├── src/
                │   ├── turtle_control.cpp  # 服务端 + 闭环控制器
                │   └── patrol_client.cpp   # 定时产生随机巡逻目标
                └── launch/
                    ├── demo.launch.py
                    └── actions.launch.py
```

构建时产生的 `build/`、`install/`、`log/` 不属于源码，不提交到 GitHub。

## 2. Topic、Service 与 Parameter

| 通信机制 | 适用场景 | 本章示例 |
| --- | --- | --- |
| Topic | 持续、异步的数据流 | 相机持续发布图像 |
| Service | 一次请求对应一次完整响应 | 发送一张图像并返回人脸位置 |
| Parameter | 节点运行配置 | turtlesim 背景颜色 |

人脸检测采用服务，是因为客户端发起一次检测任务后，需要等待服务端返回完整结果。

常用命令：

```bash
ros2 service list -t
ros2 interface show <接口类型>
ros2 service call <服务名> <接口类型> "{字段名: 值}"

ros2 param list
ros2 param describe /turtlesim background_r
ros2 param get /turtlesim background_r
ros2 param set /turtlesim background_r <值>
ros2 param dump /turtlesim > turtlesim_param.yaml
```

## 3. 自定义服务接口

`chapt4_interfaces` 只定义双方共同遵守的通信协议；`demo_python_service` 负责实际的人脸检测功能。

1.`srv/FaceDetector.srv`：

```srv
# Request
sensor_msgs/Image image
---
# Response
int16 number
float32 use_time
int32[] top
int32[] right
int32[] bottom
int32[] left
```

`---` 上方是客户端发送的 Request，下方是服务端返回的 Response。第 `i` 张人脸的位置由 `(top[i], right[i], bottom[i], left[i])` 共同描述；服务端在同一个循环内按相同顺序填入四个数组，因此客户端可按同一个索引读取。

`chapt4_interfaces/CMakeLists.txt` 使用 `rosidl_generate_interfaces(...)` 根据 `.srv` 生成 ROS 2 所需的语言绑定，所以 Python 和 C++ 节点都能使用该接口：

```python
from chapt4_interfaces.srv import FaceDetector
```

2.`srv/Patrol.srv`：

```srv
# Request
float32 target_x
float32 target_y
---
# Response
int8 SUCCESS = 1
int8 FAIL = 0
int8 result # 结果，SUCCESS / FAIL 取其一

```

`---` 上方是客户端发送的 Request，下方是服务端返回的 Response。

`chapt4_interfaces/CMakeLists.txt` 使用 `rosidl_generate_interfaces(...)` 根据 `.srv` 生成 ROS 2 所需的语言绑定，所以 Python 和 C++ 节点都能使用该接口：

```python
from chapt4_interfaces.srv import FaceDetector
```

```C++
#include "chapt4_interfaces/srv/patrol.hpp"
```

## 4. 人脸检测程序的数据流

```text
客户端 OpenCV 图片
  → CvBridge.cv2_to_imgmsg()
  → Request: sensor_msgs/Image
  → 服务端 CvBridge.imgmsg_to_cv2()
  → face_recognition.face_locations()
  → Response: 数量、耗时、位置数组
  → 客户端绘制矩形并显示
```

### 4.1 独立检测：`learn_face_detect.py`

先不用 ROS 通信，验证 `OpenCV` 和 `face_recognition` 能否正确读图、检测并画出人脸框。图片通过 `get_package_share_directory('demo_python_service')` 从安装后的包共享目录获取。

### 4.2 服务端：`face_detect_node.py`

服务端创建 `face_detect` 服务，收到请求后：

1. 检查 `request.image.data` 是否包含图像。
2. 有图像时，使用 `imgmsg_to_cv2()` 转为 OpenCV 图像；没有图像时，读取 `resource/default.jpg` 作为默认输入。
3. 调用 `face_recognition.face_locations()` 检测人脸。
4. 填充 `response` 并 `return response`。

`return response` 是服务端把结果交还给 rclpy 的必要步骤；没有它，已填充的响应无法被发送给客户端。

### 4.3 客户端：`face_detect_client_node.py`

客户端使用 `cv2_to_imgmsg()` 把 OpenCV 图片转为 ROS 图像消息，然后调用：

```python
future = self.client.call_async(request)
future.add_done_callback(result_callback)
```

`call_async()` 立即返回一个 Future，服务端尚未完成时不能立刻调用 `future.result()`。客户端的 `rclpy.spin(node)` 必须运行，执行器才能接收服务端响应、使 Future 完成，并触发 `result_callback`。

不应在单线程客户端中用 `while not future.done(): time.sleep(...)` 等待，因为它会阻塞 `spin()`，导致响应无法被处理。可使用回调，或使用 `rclpy.spin_until_future_complete(node, future)`。

## 5. 包配置关键点

`demo_python_service/package.xml` 必须声明接口依赖：

```xml
<depend>chapt4_interfaces</depend>
```

`setup.py` 的 `console_scripts` 将 Python 的 `main()` 注册为 ROS 2 可执行程序：

```python
'learn_face_detect = demo_python_service.learn_face_detect:main',
'face_detect_node = demo_python_service.face_detect_node:main',
'face_detect_client_node = demo_python_service.face_detect_client_node:main',
```

`resource/default.jpg`、`resource/test01.jpg` 也必须在 `setup.py` 的 `data_files` 中声明。否则它们不会被复制到 `install/.../share/demo_python_service/resource`，程序通过 `get_package_share_directory()` 将找不到图片。

## 6. 构建、运行与检查

```bash
cd ~/ros2-robotics-learning/examples/service_communication
colcon build
source install/setup.bash

ros2 interface show chapt4_interfaces/srv/FaceDetector
ros2 run demo_python_service learn_face_detect
```

分别打开两个终端运行服务端和客户端：

```bash
# 终端 1
cd ~/ros2-robotics-learning/examples/service_communication
source install/setup.bash
ros2 run demo_python_service face_detect_node
```

```bash
# 终端 2
cd ~/ros2-robotics-learning/examples/service_communication
source install/setup.bash
ros2 run demo_python_service face_detect_client_node
```

运行中可检查：

```bash
ros2 service list -t
ros2 service type /face_detect
ros2 interface show chapt4_interfaces/srv/FaceDetector
```

## 7. 首次加入 GitHub 仓库

### 7.1 创建并复制代码

```bash
cd ~/ros2-robotics-learning/examples
mkdir -p service_communication/src

cp -r ~/chapt4/chapt4_ws/src/chapt4_interfaces service_communication/src/
cp -r ~/chapt4/chapt4_ws/src/demo_python_service service_communication/src/
```

把本文件保存为：

```text
~/ros2-robotics-learning/examples/service_communication/README.md
```

### 7.2 配置忽略文件

在仓库根目录的 `.gitignore` 中确保包含：

```gitignore
build/
install/
log/
__pycache__/
*.pyc
```

### 7.3 检查、提交并推送

```bash
cd ~/ros2-robotics-learning
git status
git add examples/service_communication .gitignore
git status
git commit -m "add chapter 4 service communication example"
git push origin main
```

`git status` 中应看到新增的 `examples/service_communication/README.md` 和 `src/` 下的两个功能包；不应看到 `build/`、`install/`、`log/`。

## 8. 后续每次学习后的 Git 操作

后续只要你修改了代码、增加了示例图片，或补充了本章 README，都在仓库根目录执行：

```bash
cd ~/ros2-robotics-learning
git status
git add examples/service_communication
git diff --cached
git commit -m "update chapter 4 service notes"
git push origin main
```

推荐先看 `git status`，确认只包含本次确实要提交的文件；`git diff --cached` 用于在提交前检查暂存内容。

如果本次只更新 README：

```bash
git add examples/service_communication/README.md
git commit -m "update chapter 4 learning notes"
git push origin main
```

如果本次增加一个新节点，例如 `parameter_client_node.py`，除了添加源文件外，还要同步检查 `setup.py` 的 `console_scripts` 是否需要增加对应入口；然后执行常规的 `git status → git add → git diff --cached → commit → push` 流程。

## 9. 本章已掌握的关键点

- Service 适合一次任务对应一次完整结果；Parameter 用于节点运行配置。
- `.srv` 用 `---` 分隔 Request 和 Response。
- 接口包把通信协议和功能实现解耦，Python/C++ 都能复用。
- `cv_bridge` 负责 ROS 图像消息与 OpenCV 图像的双向转换。
- `resource` 中的图片必须通过 `setup.py` 安装，运行时才能在包共享目录中找到。
- `call_async()` 返回 Future；客户端 `spin()` 负责处理响应并触发完成回调。
- 服务端回调必须返回填充好的 `response`。

## 10. C++ 服务实践：海龟随机巡逻

### 10.1 `Patrol.srv`

```srv
float32 target_x
float32 target_y
---
int8 SUCCESS = 1
int8 FAIL = 0
int8 result
```

客户端请求一个目标坐标；服务端以 `result` 返回是否接受该任务。`SUCCESS` 和 `FAIL` 是响应中定义的具名常量，避免代码中出现意义不明确的数字 `1`、`0`。

### 10.2 节点职责与完整链路

```text
patrol_client（每 10 秒生成随机目标）
  → 调用 /patrol 服务
  → turtle_control 校验目标范围
  → 成功：更新 target_x_ / target_y_，返回 SUCCESS
  → turtle_control 持续接收 /turtle1/pose
  → 按位置误差发布 /turtle1/cmd_vel
  → turtlesim 海龟移动到目标附近
```

`patrol_client` 负责“产生任务”，`turtle_control` 负责“闭环控制”。客户端不直接发布速度，是为了不把随机巡逻策略和实时控制策略耦合在一起。

服务端仅接受 `x`、`y` 均在 `(0, 12)` 内的目标。成功时更新目标成员变量并设置：

```cpp
response->result = Patrol::Response::SUCCESS;
```

失败时保持旧目标，并设置 `FAIL`。C++ 回调接收的是 `Patrol::Response::SharedPtr`，通过 `response->result` 直接修改框架持有的响应对象，因此与 Python 服务回调不同，不需要显式 `return response`。

### 10.3 定时异步请求

`patrol_client` 使用 `create_wall_timer(10s, ...)` 周期性生成随机坐标并调用：

```cpp
patrol_client_->async_send_request(request, callback);
```

回调被触发时，`SharedFuture` 已完成，因此其中的 `result_future.get()` 能安全取得响应。定时器使巡逻任务持续产生；若只在 `main()` 中发送一次请求，程序只会执行一次巡逻目标更新。

## 11. 参数的动态更新

### 11.1 本节点参数：声明、读取与回调

`turtle_control` 将控制器的 `k` 与 `max_speed` 参数化：

```cpp
this->declare_parameter("k", 1.0);
this->declare_parameter("max_speed", 1.0);
this->get_parameter("k", k_);
this->get_parameter("max_speed", max_speed_);
```

上面的 `get_parameter()` 只在构造时运行一次。之后在 rqt 修改参数，只会修改 ROS 参数存储值，不能自动改变控制器成员变量。`add_on_set_parameters_callback(...)` 才负责把新值同步给实际控制逻辑：

```cpp
k_ = parameter.as_double();
max_speed_ = parameter.as_double();
```

### 11.2 修改其他节点的参数

参数更新本质上也是服务通信。客户端向目标节点的：

```text
/目标节点名/set_parameters
```

发送 `rcl_interfaces/srv/SetParameters` 请求。

- Python 人脸检测客户端可修改 `/face_detect_node/set_parameters`，切换 `model` 与 `number_of_times_to_upsample`。
- C++ 巡逻客户端可修改 `/turtle_control/set_parameters`，例如把 `k` 更新为 `4.0`。

### 11.3 人脸检测的执行顺序

`update_detect_model()` 使用 `spin_until_future_complete()`，会等待参数设置完成；但原先的 `send_request()` 只发送检测请求并注册异步回调，立即返回。

因此以下顺序不能保证每次检测各自使用对应模型：

```text
设 HOG → 发检测请求 1（不等待）→ 设 CNN → 发检测请求 2（不等待）
```

不同服务的待处理请求没有跨服务的严格 FIFO 执行保证。若 CNN 参数回调先被服务端调度，两次检测都可能使用 CNN。

要保证顺序，应让检测请求也等待完成：

```text
设 HOG 并确认成功
→ 发送检测 1，并等待结果
→ 设 CNN 并确认成功
→ 发送检测 2，并等待结果
```

Python 中可用 `rclpy.spin_until_future_complete(self, future)`；也可将后续步骤写入检测完成回调，形成状态机。

## 12. Launch 文件

`demo.launch.py` 一次启动完整的巡逻系统：

```text
turtlesim_node + turtle_control + patrol_client
```

Launch 参数通过两步传递：

```python
DeclareLaunchArgument('launch_arg_background_g', default_value='150')
LaunchConfiguration('launch_arg_background_g')
```

前者声明可由命令行覆盖的启动参数；后者在节点启动时读取该值，并传给 `turtlesim_node` 的 `background_g` 参数。Launch 的替换值先按字符串处理，再由目标 ROS 参数类型转换。

```bash
ros2 launch demo_cpp_service demo.launch.py launch_arg_background_g:=220
```

该命令把 `220` 传给 `turtlesim_node`，改变背景 RGB 中的绿色分量。

`actions.launch.py` 练习了 Launch 的三类核心组件：

| 组件 | 本例 | 作用 |
| --- | --- | --- |
| 动作 | `Node`、`ExecuteProcess`、`IncludeLaunchDescription`、`TimerAction` | 启动节点、进程、其他 Launch 或延时动作 |
| 条件 | `IfCondition(startup_rqt)` | 仅在参数为真时启动 rqt |
| 替换 | `LaunchConfiguration('startup_rqt')` | 启动时读取命令行参数或默认值 |

```bash
# 不启动 rqt（默认 startup_rqt=False）
ros2 launch demo_cpp_service actions.launch.py

# 延时 4 秒后启动 rqt
ros2 launch demo_cpp_service actions.launch.py startup_rqt:=True
```

## 13. 本次代码加入仓库前的检查

将本地工作空间的新内容复制到仓库时，目标目录应为：

```text
~/ros2-robotics-learning/examples/service_communication/src/
├── chapt4_interfaces/       # 新增 Patrol.srv
├── demo_python_service/     # 更新参数通信与 Python launch
└── demo_cpp_service/        # 新增 C++ 服务和 launch
```

需要同步复制的实际内容：

```bash
cd ~/ros2-robotics-learning/examples/service_communication/src

cp ~/chapt4/chapt4_ws/src/chapt4_interfaces/srv/Patrol.srv chapt4_interfaces/srv/
cp -r ~/chapt4/chapt4_ws/src/demo_cpp_service .
cp ~/chapt4/chapt4_ws/src/demo_python_service/demo_python_service/face_detect_node.py demo_python_service/demo_python_service/
cp ~/chapt4/chapt4_ws/src/demo_python_service/demo_python_service/face_detect_client_node.py demo_python_service/demo_python_service/
cp ~/chapt4/chapt4_ws/src/demo_python_service/package.xml demo_python_service/
cp ~/chapt4/chapt4_ws/src/demo_python_service/setup.py demo_python_service/
cp -r ~/chapt4/chapt4_ws/src/demo_python_service/launch demo_python_service/
```

同时检查 `chapt4_interfaces/CMakeLists.txt` 的 `rosidl_generate_interfaces(...)` 已同时列出两个接口：

```cmake
"srv/FaceDetector.srv"
"srv/Patrol.srv"
```

不要复制 `launch/__pycache__/`，也不要提交任何 `__pycache__/`、`build/`、`install/`、`log/`。

由于代码直接使用了 `rcl_interfaces::srv::SetParameters`（C++）和 `rcl_interfaces`（Python），建议显式声明依赖，而不是依赖其他包的间接安装：

- `demo_cpp_service/package.xml` 加入 `<depend>rcl_interfaces</depend>`；`CMakeLists.txt` 加入 `find_package(rcl_interfaces REQUIRED)`，并把 `rcl_interfaces` 加入 `patrol_client` 的 `ament_target_dependencies(...)`。
- `demo_python_service/package.xml` 加入 `<depend>rcl_interfaces</depend>`；若尚未声明，也建议加入 `<depend>cv_bridge</depend>`。

修改依赖后重新构建并运行一次：

```bash
cd ~/ros2-robotics-learning/examples/service_communication
colcon build
source install/setup.bash
ros2 launch demo_cpp_service demo.launch.py
```

## 14. 本次 Git 提交

确认构建与运行正常后：

```bash
cd ~/ros2-robotics-learning
git status
git add examples/service_communication
git diff --cached
git commit -m "complete chapter 4 services parameters and launch"
git push origin main
```

提交前重点确认暂存区包含：`Patrol.srv`、`demo_cpp_service/`、更新后的 Python 文件与 Launch 文件、以及 `service_communication/README.md`；不包含构建产物。
