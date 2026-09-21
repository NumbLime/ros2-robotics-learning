# ROS 2 自主导航与自动巡检

本示例对应 ROS 2 学习的第七章，基于 Gazebo、Navigation 2 和 Python 节点实现二维建图后的自主导航，并进一步组合语音播报、目标点巡航和相机图像保存功能。

## 学习目标

- 理解 SLAM 建图与已有地图定位的区别。
- 理解 `map -> odom -> base_footprint` 的 TF 定位链。
- 理解 Nav2 中 BT Navigator、Planner Server、Controller Server、Behavior Server 和代价地图的分工。
- 使用 `nav2_simple_commander` 完成初始位姿设置、单点导航和路点导航。
- 将导航、同步语音服务和相机订阅组合成自动巡检流程。
- 使用实际 Topic、Action、TF、日志和测试结果验证系统行为。

## 功能包结构

```text
src/
├── autopatrol_interfaces   # SpeechText 自定义语音服务接口
├── autopatrol_robot        # 自动巡检、语音播报和图像保存
├── fishbot_application     # 初始位姿、TF查询、单点和路点导航示例
├── fishbot_description     # FishBot模型、Gazebo世界、传感器和控制器
└── fishbot_navigation2     # Nav2参数、地图和启动文件
```

`fishbot_description` 来源于第六章，并在本章中作为可独立运行的仿真基础设施使用。

## 系统数据流

### 定位坐标链

```text
map --AMCL--> odom --差速控制器/里程计--> base_footprint
```

- `map_server` 读取保存的地图并发布 `/map`。
- AMCL结合静态地图、`/scan` 和里程计估计机器人在地图中的位置，并发布 `map -> odom`。
- 差速控制器根据轮子里程计发布 `odom -> base_footprint`。
- TF2组合两段变换，得到机器人在地图中的位姿。

### 导航控制链

```text
目标点
  -> NavigateToPose Action
  -> BT Navigator
  -> Planner Server / 全局代价地图
  -> Controller Server / 局部代价地图
  -> velocity_smoother
  -> /cmd_vel
  -> diff_drive_controller
  -> gazebo_ros2_control
  -> 左右轮关节
```

局部和全局代价地图均订阅 `/scan`：局部代价地图用于实时避障，全局代价地图可在重新规划时考虑新障碍物。

## 环境与依赖

验证环境：

- Ubuntu 22.04
- ROS 2 Humble
- Gazebo Classic
- Navigation 2
- Python 3.10

先使用 rosdep安装功能包声明的依赖：

```bash
cd ~/ros2-robotics-learning/examples/navigation
source /opt/ros/humble/setup.bash
rosdep install --from-paths src --ignore-src -r -y
```

语音节点还使用没有对应 rosdep规则的 Python模块 `espeakng`。本项目验证的版本为 `1.0.5`：

```bash
sudo apt install espeak-ng
python3 -m pip install --user espeakng==1.0.5
```

## 构建

```bash
cd ~/ros2-robotics-learning/examples/navigation
source /opt/ros/humble/setup.bash
colcon build --symlink-install
source install/setup.bash
```

已验证的构建结果：

```text
Summary: 5 packages finished
```

## 启动仿真与导航

终端一：启动 Gazebo、机器人模型和控制器。

```bash
source /opt/ros/humble/setup.bash
source ~/ros2-robotics-learning/examples/navigation/install/setup.bash
ros2 launch fishbot_description gazebo_sim.launch.py
```

终端二：启动地图服务器、AMCL、Nav2和RViz。

```bash
source /opt/ros/humble/setup.bash
source ~/ros2-robotics-learning/examples/navigation/install/setup.bash
ros2 launch fishbot_navigation2 navigation2.launch.py
```

在 RViz 中使用 `2D Pose Estimate` 设置机器人的初始位姿，再使用 `Nav2 Goal` 发送导航目标。

## 导航应用示例

设置初始位姿：

```bash
ros2 run fishbot_application init_robot_pose
```

查询 `map -> base_footprint`：

```bash
ros2 run fishbot_application get_robot_pose
```

执行单点导航：

```bash
ros2 run fishbot_application nav_to_pose
```

执行路点导航：

```bash
ros2 run fishbot_application waypoints_follower
```

## 自动巡检

`autopatrol_robot` 从 YAML参数读取初始位姿和目标点，在目标点之间循环导航。每次成功到达后，系统会：

1. 检查 Action最终状态是否为 `TaskResult.SUCCEEDED`；
2. 调用同步等待的语音播报服务；
3. 等待到达时刻之后产生的新相机帧；
4. 将图片写入配置目录，并检查 `cv2.imwrite()` 的返回值；
5. 仅在保存成功后播报“图像记录完毕”。

启动：

```bash
source /opt/ros/humble/setup.bash
source ~/ros2-robotics-learning/examples/navigation/install/setup.bash
ros2 launch autopatrol_robot autopatrol.launch.py
```

默认图像目录：

```text
~/.ros/autopatrol_images
```

主要参数位于：

```text
src/autopatrol_robot/config/patrol_config.yaml
```

其中目标点使用一维数组保存，每三个值分别为 `x`、`y` 和 `yaw`。

## Nav2参数要点

- `FollowPath.max_vel_x`：限制局部控制器计算的最大前进速度。
- `velocity_smoother.max_velocity`：在控制器之后再次限速并平滑速度。
- `robot_radius`：使用圆形近似表示机器人的碰撞范围。
- `inflation_radius`：在障碍物周围建立代价衰减区域。
- `xy_goal_tolerance`：目标位置允许误差。
- `yaw_goal_tolerance`：目标朝向允许误差。
- `room.yaml` 中的 `resolution` 和 `origin` 用于把地图栅格转换为 `map` 坐标。

## 实际验证结果

### TF链

实测得到：

```text
map -> odom:
  translation = [-0.023, 0.010, 0.000]
  yaw = 0.577 deg

odom -> base_footprint:
  translation ≈ [0.000, 0.000, 0.000]
  yaw = 0.025 deg

map -> base_footprint:
  translation = [-0.023, 0.010, 0.000]
  yaw = 0.605 deg
```

组合结果与前两段TF一致，证明完整定位链已经建立。

### Action和速度输出

已确认以下 Action Server：

```text
/follow_waypoints [nav2_msgs/action/FollowWaypoints]
/navigate_to_pose [nav2_msgs/action/NavigateToPose]
```

导航过程中实测 `/cmd_vel` 包含非零线速度和角速度：

```text
linear.x: 0.25
angular.z: 0.32
```

Nav2成功日志：

```text
[controller_server]: Passing new path to controller.
[controller_server]: Reached the goal!
[bt_navigator]: Goal succeeded
```

### 巡检图像

自动巡检实际生成了 `800 x 600`、8位RGB PNG图片。第二个目标设为 `(1.0, 2.0)`，保存图片时机器人位置约为 `(0.83, 1.87)`，位置误差约 `0.21 m`，符合 `xy_goal_tolerance: 0.25` 的到点条件。

### 自动测试

```text
Summary: 27 tests, 0 errors, 0 failures, 2 skipped
```

## 本章修正的问题

1. 修正 `nav2_simple_commander` 依赖名称，并补齐直接运行依赖。
2. 区分“Action任务已经结束”和“导航成功”，只在 `SUCCEEDED` 时拍照。
3. 将不确定的相对图片路径改为可配置目录，并使用 `Path.expanduser()` 展开 `~`。
4. 等待目标点到达后的新相机帧，避免保存到达前的旧图像。
5. 检查 `cv2.imwrite()` 返回值，避免保存失败却播报成功。
6. 清除重复方法、未使用导入和Python格式问题。

## 已知限制

- 当前验证仅覆盖 Gazebo仿真，尚未在真实机器人上验证。
- 语音Python模块 `espeakng` 没有可用的 rosdep规则，需要单独安装。
- 巡检目标点来自静态YAML配置，尚未提供运行时增删目标点的接口。
- 当前定位依赖二维激光雷达、静态地图和AMCL。

## 与移动机器人项目的关系

本示例已经形成移动机器人项目的基础闭环：感知障碍物、定位、规划、控制、目标点巡航和任务记录。后续可以继续加入地图动态更新、巡检任务管理、导航失败重试、超时策略和真实底盘适配。
