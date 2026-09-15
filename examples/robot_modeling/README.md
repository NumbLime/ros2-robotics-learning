# ROS 2 Robot Modeling and Gazebo Simulation

本示例记录 ROS 2 第六章的机器人建模与仿真实践，包括 URDF、Xacro、TF、RViz、Gazebo 传感器仿真以及 `ros2_control` 差速底盘控制。

## 学习目标

- 使用 URDF 描述机器人的 Link 和 Joint
- 理解 `visual`、`collision`、`inertial` 的不同作用
- 使用 Xacro 宏和模块化文件组织机器人模型
- 使用 `robot_state_publisher` 发布机器人 TF
- 在 Gazebo 中仿真激光雷达、IMU和深度相机
- 使用 `gazebo_ros2_control` 和差速控制器驱动机器人
- 建立 `/cmd_vel`、轮子接口、`/odom` 和 TF 之间的数据链路

## 环境

- Ubuntu 22.04
- ROS 2 Humble
- Gazebo Classic
- `ros2_control`
- RViz2

## 目录结构

```text
robot_modeling/
└── src/
    └── fishbot_description/
        ├── config/
        │   ├── display_robot_model.rviz
        │   └── fishbot_ros2_controller.yaml
        ├── launch/
        │   ├── display_robot.launch.py
        │   └── gazebo_sim.launch.py
        ├── urdf/
        │   ├── first_robot.urdf
        │   ├── first_robot.xacro
        │   └── fishbot/
        │       ├── actuator/
        │       ├── plugins/
        │       ├── sensor/
        │       ├── base.urdf.xacro
        │       ├── common_inertia.xacro
        │       ├── fishbot.ros2_control.xacro
        │       └── fishbot.urdf.xacro
        ├── world/
        │   ├── custom_room.world
        │   └── room/
        ├── CMakeLists.txt
        └── package.xml
```

## 主要文件

| 文件 | 作用 |
|---|---|
| `first_robot.urdf` | 基础 URDF 建模示例 |
| `first_robot.xacro` | Xacro 宏定义和复用示例 |
| `fishbot.urdf.xacro` | FishBot 总模型入口 |
| `base.urdf.xacro` | `base_footprint` 和底盘模型 |
| `wheel.urdf.xacro` | 左右驱动轮 |
| `caster.urdf.xacro` | 前后万向轮 |
| `common_inertia.xacro` | 惯性矩阵计算宏 |
| `laser.urdf.xacro` | 激光雷达模型 |
| `imu.urdf.xacro` | IMU模型 |
| `camera.urdf.xacro` | 深度相机及光学坐标系 |
| `gazebo_sensor_plugin.xacro` | Gazebo传感器插件 |
| `fishbot.ros2_control.xacro` | 硬件接口和 GazeboSystem |
| `fishbot_ros2_controller.yaml` | 控制器参数 |
| `display_robot.launch.py` | 启动 RViz 模型显示 |
| `gazebo_sim.launch.py` | 启动 Gazebo、生成实体并加载控制器 |

## URDF 与 TF

`link` 描述机器人部件，`joint` 描述父子 Link 之间的连接关系。

需要区分：

- `visual/origin`：只改变外观相对 Link 坐标系的位置；
- `collision/origin`：定义物理碰撞区域；
- `inertial`：定义质量、质心和惯性矩阵；
- `joint/origin`：确定子 Link 坐标系相对父坐标系的位置和姿态；
- `joint/axis`：定义可动关节的运动轴。

因此，修改 `visual/origin` 不会改变 TF；修改 `joint/origin` 会同时改变子坐标系及其整体模型位置。

本模型的主要 TF 结构为：

```text
base_footprint
└── base_link
    ├── left_wheel_link
    ├── right_wheel_link
    ├── front_caster_link
    ├── back_caster_link
    ├── imu_link
    ├── laser_cylinder_link
    │   └── laser_link
    └── camera_link
        └── camera_optical_link
```

其中：

- 固定关节由 `robot_state_publisher` 发布到 `/tf_static`；
- 轮子等可动关节需要 `/joint_states` 才能计算动态 TF；
- Gazebo运行时，差速控制器发布 `odom → base_footprint`；
- `robot_state_publisher` 发布 `base_footprint → base_link → sensor_link`。

## 构建

在本目录执行：

```bash
source /opt/ros/humble/setup.bash

rosdep install \
  --from-paths src \
  --ignore-src \
  -r \
  -y

colcon build \
  --symlink-install \
  --packages-select fishbot_description

source install/setup.bash
```

实际验证结果：

```text
Summary: 1 package finished
```

## 验证 Xacro 和 URDF

```bash
xacro \
  src/fishbot_description/urdf/fishbot/fishbot.urdf.xacro \
  > /tmp/fishbot_generated.urdf

check_urdf /tmp/fishbot_generated.urdf
```

验证结果：

```text
Successfully Parsed XML
root Link: base_footprint
```

## RViz 显示

```bash
MODEL_PATH="$(ros2 pkg prefix --share fishbot_description)/urdf/fishbot/fishbot.urdf.xacro"

ros2 launch fishbot_description display_robot.launch.py \
  model:="$MODEL_PATH"
```

已验证：

- `RobotModel` 状态为 `OK`
- 底盘、驱动轮、万向轮和传感器模型显示完整
- `Fixed Frame` 设置为 `base_footprint` 时显示正常
- TF 树完整

TF 查询示例：

```bash
ros2 run tf2_ros tf2_echo base_footprint laser_link
```

实际结果：

```text
Translation: [0.000, 0.000, 0.251]
Rotation: [0.000, 0.000, 0.000, 1.000]
```

## Gazebo 仿真

```bash
ros2 launch fishbot_description gazebo_sim.launch.py
```

启动顺序为：

1. 启动 Gazebo；
2. 发布 `robot_description`；
3. 使用 `spawn_entity.py` 生成机器人；
4. 机器人生成完成后加载 `joint_state_broadcaster`；
5. 再加载 `diff_drive_controller`。

等待实体生成后再加载控制器，可以避免控制器找不到 `controller_manager` 或硬件接口尚未注册的问题。

## 传感器

| 传感器 | 安装 Link | 主要输出 | 消息坐标系 |
|---|---|---|---|
| 激光雷达 | `laser_link` | `/scan` | `laser_link` |
| IMU | `imu_link` | `/imu` | `imu_link` |
| 深度相机 | `camera_link` | 图像、深度图、点云、相机信息 | `camera_optical_link` |

实际观测到的话题：

```text
/camera_sensor/camera_info
/camera_sensor/depth/camera_info
/camera_sensor/depth/image_raw
/camera_sensor/image_raw
/camera_sensor/points
/imu
/scan
```

IMU插件中显式设置：

```xml
<frame_name>imu_link</frame_name>
```

这只明确消息头中的坐标系语义，不会改变 IMU 在机器人上的物理安装位置。

## ros2_control

当前激活的控制器：

```text
fishbot_joint_state_broadcaster  active
fishbot_diff_drive_controller    active
```

控制链路：

```text
/cmd_vel
→ diff_drive_controller
→ wheel velocity command interfaces
→ gazebo_ros2_control/GazeboSystem
→ Gazebo左右轮关节
```

左右轮提供：

- `velocity` 和 `effort` 命令接口；
- `position`、`velocity` 和 `effort` 状态接口。

运行时，左右轮的 `velocity` 接口由差速控制器占用，`effort` 接口保持可用但未占用。`fishbot_effort_controller` 已在 YAML 中声明，但没有同时激活，以避免多个控制器竞争相同关节。

发送运动命令：

```bash
ros2 topic pub -r 10 \
  /cmd_vel \
  geometry_msgs/msg/Twist \
  "{linear: {x: 0.15}, angular: {z: 0.3}}"
```

机器人已实际验证能够在 Gazebo 中按弧线运动。

## 里程计

差速控制器配置：

```yaml
open_loop: true
enable_odom_tf: true
odom_frame_id: odom
base_frame_id: base_footprint
```

因此控制器会：

- 发布 `/odom`；
- 发布 `odom → base_footprint`；
- 使用命令速度积分计算开环里程计。

实际观测：

```text
header.frame_id: odom
child_frame_id: base_footprint
```

停止 `/cmd_vel` 后，里程计速度回到零，已累计的非零位姿继续保留。

由于当前使用 `open_loop: true`，里程计主要根据控制命令积分，而不是根据轮子实际反馈修正。机器人被障碍物阻挡时，里程计仍可能继续变化。

## 排错记录

### `tf2_echo` 启动时短暂提示 frame 不存在

监听器刚启动时可能尚未收到 `/tf_static`，因此短暂提示：

```text
Invalid frame ID
```

如果随后能够持续输出正确变换，这只是初始化时序，不代表 TF 树缺失。

### 控制器过早加载

如果机器人实体和 `gazebo_ros2_control` 尚未初始化，控制器可能找不到 `controller_manager` 或相应硬件接口。

本项目通过 `OnProcessExit` 等待 `spawn_entity.py` 完成后，再依次加载控制器。

### 视觉模型正常但碰撞行为异常

RViz主要显示 `visual`。Gazebo的碰撞行为依赖 `collision`。如果两者尺寸或位置不一致，可能出现“看起来没有接触，但实际已经碰撞”或穿模等问题。

## 与移动机器人项目的关系

本章模型提供了后续移动机器人项目的基础接口：

- `/scan`：用于障碍物检测和代价地图；
- `/imu`：用于姿态和运动状态估计；
- 深度图和点云：用于环境感知；
- `/cmd_vel`：接收导航或控制算法输出；
- `/odom`：提供局部运动估计；
- TF树：统一机器人本体和传感器数据的坐标关系。

下一步可在此模型基础上接入 SLAM、定位和 Nav2，形成路径规划与自动避障移动机器人。

## 尚待继续验证

- 对比 `open_loop: true` 与闭环里程计的差异
- 检查深度相机图像和点云的实际内容
- 接入 SLAM 建图
- 接入 Nav2 完成目标点导航与局部避障