# 第五章：TF 坐标变换与 ROS 2 常用工具

本示例记录《ROS 2 机器人开发从入门到实践》第五章的实操与复习内容，使用 Python 和 C++ 实现静态 TF 广播、动态 TF 广播和变换查询，并学习 launch、rqt、RViz、ros2 bag 和 Git。

环境：Ubuntu 22.04 / ROS 2 Humble。

## 学习目标

- 理解父子坐标系、位置与位姿，以及坐标变换的方向。
- 使用广播器发布 TF，理解 TransformListener 和 Buffer 的职责。
- 区分最新可用变换与指定时刻变换，理解插值、超时和回调阻塞。
- 使用 launch 启动多个节点，以 RViz 和命令行检查坐标关系。
- 理解 bag 记录的话题数据与实际运动轨迹之间的区别。

## 目录

| 路径 | 内容 |
| --- | --- |
| `src/demo_python_tf/` | 底座、相机、瓶子的坐标变换示例 |
| `src/demo_cpp_tf/` | 地图、机器人、目标点的坐标变换示例 |
| `src/demo_python_tf/launch/python_tf.launch.py` | 启动 Python 三个节点 |
| `src/demo_cpp_tf/launch/cpp_tf.launch.py` | 启动 C++ 三个节点 |
| `config/rviz_tf.rviz` | RViz 配置；加载后按示例检查 Fixed Frame |

本目录作为示例工作空间使用，在这里执行 colcon build；不提交生成的 build、install、log 目录。

## 构建与运行

```bash
cd ~/ros2-robotics-learning/examples/tf_tools
source /opt/ros/humble/setup.bash
colcon build --packages-select demo_python_tf demo_cpp_tf
source install/setup.bash
```

在已安装 ROS 2 Humble 的环境中，如缺少包依赖，可先执行：

```bash
rosdep install --from-paths src --ignore-src -r -y
```

Python 示例：

```bash
ros2 launch demo_python_tf python_tf.launch.py
```

按 Ctrl+C 结束当前组后，运行 C++ 示例：

```bash
ros2 launch demo_cpp_tf cpp_tf.launch.py
```

每个 launch 启动三个独立进程，并将日志输出到当前终端。启动前结束此前手动运行的同组节点，避免重复广播相同 TF。launch 中的排列顺序不保证数据已准备好；监听器保留异常捕获，并在后续定时回调中重试。

新终端使用本工作空间前，也需要 source ROS 环境和本目录的 install/setup.bash。

## Python：底座、相机与瓶子

坐标链：`base_link → camera_link → bottle_link`。

| 关系 | 平移（米） | RPY（度） | 发布方式 |
| --- | --- | --- | --- |
| base_link → camera_link | (0.5, 0.3, 0.6) | (180, 0, 0) | 静态 |
| camera_link → bottle_link | (0.2, 0.3, 0.5) | (0, 0, 0) | 动态，约 10 Hz |

查询 `lookup_transform('base_link', 'bottle_link', ...)` 得到瓶子在底座坐标系中的位姿。

相机绕 X 轴旋转 180° 后，其 Y、Z 轴方向与底座相反。因此瓶子的位置为：

```text
(0.5, 0.3, 0.6) + (0.2, -0.3, -0.5) = (0.7, 0, 0.1)
```

预期旋转 RPY 为 `(π, 0, 0)`，单位弧度。当前动态广播器的数值固定，只更新时间戳，没有模拟瓶子移动。模拟沿相机 X 轴运动时，需要让 translation.x 随时间变化；真实应用需要用检测或估计得到的位姿更新消息。

## C++：地图、机器人与目标点

| 关系 | 平移（米） | yaw（度） | 发布方式 |
| --- | --- | --- | --- |
| map → target_point | (5, 3, 0) | 60 | 静态 |
| map → base_link | (2, 3, 0) | 30 | 动态，约 10 Hz |

查询 `lookupTransform("base_link", "target_point", ...)` 得到目标点在机器人坐标系中的位姿。

先在地图中求位移 `(3, 0, 0)`，再使用逆旋转换成机器人坐标分量：

```text
translation = Rz(-30°) × (3, 0, 0)
            ≈ (2.598076, -1.5, 0)
yaw = 60° - 30° = 30° ≈ 0.523599 rad
```

这里目标点没有移动，改变的是描述位移所用的坐标轴。yaw 相减适用于本例同轴旋转，不能推广为任意 RPY 分量直接相减。

`tf2::getEulerYPR(rotation, y, p, r)` 的输出顺序为 yaw、pitch、roll，单位弧度；日志应标为 YPR。

## TF 核心理解

### 变换方向

`header.frame_id` 是父坐标系，`child_frame_id` 是子坐标系。translation 描述子坐标系原点在父坐标系中的位置。

若 `p_A = R × p_B + t`，则反向关系为：

```text
p_B = inverse(R) × p_A - inverse(R) × t
```

反向平移通常不是简单的 -t。单位四元数 `(x,y,z,w)` 的逆旋转可用 `(-x,-y,-z,w)` 表示；四个分量全部取负仍表示原来的旋转。

### 接收、保存、查询

- 广播器发布 /tf 或 /tf_static。
- TransformListener 订阅 TF，将收到的变换写入 Buffer。
- Buffer 保存数据，并支持组合、求逆和按时间查询。
- lookup_transform / lookupTransform 查询本地 Buffer，不是向广播器发起服务请求。
- 查询频率与订阅回调执行频率不同；删除查询定时器不会自动取消 TF 订阅。

静态关系看相对位姿是否固定。相机随机器人运动，但相机相对于底座仍可保持静态。/tf_static 使用 transient local 持久性，让仍存在的发布者向后加入且 QoS 兼容的订阅者提供保留数据，不代表节点退出后数据仍由系统永久保存。

### 时间与线程

- Time(0) / tf2::TimePointZero 表示最新可用变换；多段动态链需要共同可用时刻。
- now() 表示调用时求得的具体时刻。
- 指定时刻位于两条有效动态数据之间时，可以插值；超出缓存范围时不自动预测。
- timeout 是最长等待时间，不是允许返回相邻时刻的误差范围。
- Python 本例默认单线程执行，同步等待可能阻塞 Listener 回调；周期性查看最新结果可省略 timeout，捕获失败后下次重试。
- C++ 本例 TransformListener(*buffer_, this) 默认 spin_thread=true，独立监听线程可在主线程查询等待期间更新 Buffer。主线程仍需 spin 来执行自己的查询定时器。
- C++ 成员按声明逆序销毁。将成员声明为 buffer_、listener_、timer_，保证监听器销毁前 Buffer 仍存在。

## 工程整理要点

- Python 节点末尾应调用 rclpy.shutdown()，不能只写函数名。
- Python package.xml 的依赖应为 tf2_ros，而非 tf_ros。
- C++ 动态广播器源码节点名应与静态广播器区分。
- C++ 直接使用 tf2，应在 CMake 和 package.xml 中显式声明依赖。
- Python setup.py 用 data_files 安装 launch 文件；C++ 用 install(DIRECTORY launch DESTINATION share/${PROJECT_NAME})。
- 两个包声明 launch、launch_ros 运行依赖。
- 高频完整消息日志可从 info 改为 debug，方便观察监听器结果。

这些是复习中确认的修改要点；运行日志本身不能证明每一处源码修改均已落实。

## 可视化与命令行

另开已加载环境的终端：

```bash
ros2 run tf2_tools view_frames
ros2 run tf2_ros tf2_echo base_link bottle_link
```

上面的 echo 用于 Python 示例；C++ 示例使用：

```bash
ros2 run tf2_ros tf2_echo base_link target_point
```

从本示例目录加载 RViz 配置：

```bash
rviz2 -d config/rviz_tf.rviz
```

- Python 示例以底座观察时设置 Fixed Frame 为 base_link。
- C++ 示例以地图观察时设置 Fixed Frame 为 map。
- 添加或启用 TF 显示项，检查坐标轴和关系。
- rqt 的 TF Tree 插件用于查看坐标树结构；RViz 用于观察空间位置和姿态。

## ros2 bag

以 turtlesim 的速度话题为例：

```bash
ros2 bag record /turtle1/cmd_vel
```

Ctrl+C 停止后，用生成的实际目录名回放：

```bash
ros2 bag info <记录目录>
ros2 bag play <记录目录>
```

这里只记录开始录制后接收到的速度消息，不包含录制前的操作，也不等同于记录实际位置轨迹。初始位置或朝向不同，即使执行相同指令，绝对轨迹通常也不同；初始状态一致也不能仅凭速度录制保证完全相同的回放轨迹。

## Git 复习

| 命令 | 含义 |
| --- | --- |
| git add 文件 | 将该时刻的文件内容加入本地暂存区 |
| git commit -m "说明" | 基于暂存区创建本地提交 |
| git push | 推送本地提交到远程 |
| git diff | 查看工作区相对暂存区的修改 |
| git diff --cached | 查看暂存区相对当前提交的修改 |
| git reset 文件 | 撤销该文件的暂存，保留工作区修改 |
| git restore 文件 | 用暂存区版本恢复工作区文件，会丢弃该文件未暂存的修改 |
| git switch -c rolling | 创建并切换到 rolling 分支 |
| git merge rolling | 将 rolling 合入当前分支 |

add 之后再次修改文件，需要再次 add 才能将新增修改纳入提交。git reset 提交号 默认会移动当前分支并重置暂存区、保留工作区，不等于把所有文件恢复到那个版本；操作前先检查状态。已共享的提交需要撤销时，通常优先考虑 git revert。

## 已验证结果

2026-09-06，在原练习工作空间 `~/chapt5/chapt5_ws` 中：

- Python launch 成功启动三个节点；查询平移约 (0.7,0,0.1)，RPY 约 (π,0,0)。
- C++ launch 成功启动三个节点；查询平移约 (2.598076,-1.5,0)，YPR 约 (0.523599,0,0)，日志约每秒输出一次。
- 接近零的浮点残差，以及 0.09999999999999998，属于本例正常浮点误差。

迁移后的仓库目录已检查；以上运行证据来自原练习工作空间，不宣称已在迁移目录重新编译运行。

## 后续应用

将本章的坐标关系用于机器人建模与导航：理解传感器安装坐标系，并为后续学习 map、odom、base_link 之间的变换打基础。
