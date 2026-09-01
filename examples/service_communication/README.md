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
            │       └── FaceDetector.srv
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

`srv/FaceDetector.srv`：

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
