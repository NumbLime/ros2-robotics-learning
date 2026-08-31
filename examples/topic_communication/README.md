# ROS2 Topic Communication

This module records my practice and understanding of ROS2 topic communication using Python and C++.

The examples cover:

- Publisher and Subscriber communication
- Timer and subscription callbacks
- Application-level queues and worker threads
- Open-loop and closed-loop turtle control
- Custom ROS2 message interfaces

## Directory Structure

```text
topic_communication/
├── README.md
├── demo_cpp_topic/
│   └── src/
│       ├── turtle_circle.cpp
│       └── turtle_control.cpp
├── demo_python_topic/
│   └── demo_python_topic/
│       ├── novel_pub_node.py
│       └── novel_sub_node.py
├── status_interfaces/
│   └── msg/
│       └── SystemStatus.msg
└── status_publisher/
    └── status_publisher/
        └── sys_status_pub.py
```

## 1. Topic Communication

Topic communication is a decoupled communication mechanism provided by ROS2.

A Publisher publishes messages to a specified Topic. A Subscriber subscribes to the same Topic using a compatible message type. The Publisher does not need to know which Subscriber receives the data or how the data will be processed afterward.

```text
Publisher
    ↓
  Topic
    ↓
Subscriber
```

ROS2 middleware discovers compatible Publishers and Subscribers and establishes communication between them.

## 2. Python Novel Example

### 2.1 Publisher: `novel_pub_node.py`

The publisher downloads a text file through HTTP and then:

1. Splits the text into individual lines.
2. Stores the lines in a Python queue.
3. Creates a ROS2 timer.
4. Takes one line from the queue every five seconds.
5. Packages the line as a `std_msgs/msg/String` message.
6. Publishes the message to `/novel`.

```text
HTTP text
    ↓
requests
    ↓
splitlines()
    ↓
Python Queue
    ↓
Timer callback
    ↓
String message
    ↓
/novel
```

### 2.2 Subscriber: `novel_sub_node.py`

The subscriber receives text from `/novel`. Its subscription callback places each received line into another Python queue and returns quickly.

A separate worker thread takes text from the queue and uses `espeak-ng` to synthesize and play the speech.

```text
/novel
    ↓
Subscription callback
    ↓
Python Queue
    ↓
Speech thread
    ↓
espeak-ng
```

### 2.3 Why Use a Separate Thread?

Speech synthesis and audio playback are relatively slow operations. If they run directly inside the subscription callback, the callback execution thread may remain occupied for a long time.

With a single-threaded Executor, other ready callbacks cannot use that thread until the current callback finishes. If new messages arrive faster than they can be processed, samples may accumulate in the ROS2/DDS communication layer. When the configured QoS history depth is exceeded, older samples may be discarded according to the QoS policy.

The example therefore keeps the subscription callback short and moves slow speech processing to another thread:

```text
Receive message → Put into queue → Return from callback
                                      ↓
                          Worker thread processes text
```

This prevents speech processing from directly blocking the ROS2 callback. However, if data is permanently produced faster than the worker can consume it, the application-level Python queue may still continue growing.

## 3. C++ Turtle Examples

### 3.1 Open-Loop Circle Control: `turtle_circle.cpp`

The node periodically publishes a `geometry_msgs/msg/Twist` message containing fixed linear and angular velocities to:

```text
/turtle1/cmd_vel
```

The turtlesim node subscribes to the Topic and moves the turtle according to the received velocity command.

```text
Timer
    ↓
Timer callback
    ↓
Twist
    ↓
/turtle1/cmd_vel
    ↓
turtlesim
    ↓
Turtle motion
```

This is an open-loop example because the controller keeps sending predefined commands without checking the turtle's actual position.

### 3.2 Closed-Loop Target Control: `turtle_control.cpp`

The control node subscribes to `/turtle1/pose`, which contains the current position and orientation of the turtle.

After receiving a Pose message, the node:

1. Reads the current position and orientation.
2. Calculates the distance to the target position.
3. Calculates the heading error between the current orientation and target direction.
4. Decides whether to rotate or move forward.
5. Generates a Twist velocity command.
6. Publishes the command to `/turtle1/cmd_vel`.

The turtlesim node executes the command and publishes a new Pose, which becomes the next feedback sample.

```text
Target position
      ↓
Compare with current Pose
      ↓
Distance error and heading error
      ↓
Control logic
      ↓
Twist → /turtle1/cmd_vel → Turtle
                              ↓
                         New Pose
                              └── feedback
```

This is closed-loop control because the velocity command is continuously adjusted according to feedback from the turtle's current state.

The distance and heading thresholds define an acceptable error range. They avoid unnecessary repeated adjustments caused by requiring the calculated error to become exactly zero.

## 4. Custom ROS2 Message Interface

The custom-interface exercise contains two packages with separate responsibilities:

| Package | Responsibility |
|---|---|
| `status_interfaces` | Defines and generates the custom message interface. |
| `status_publisher` | Collects system information and publishes it using the generated message type. |

Separating the interface from the node logic allows multiple Python or C++ packages to reuse the same message definition.

### 4.1 Message Definition

`status_interfaces/msg/SystemStatus.msg` defines the data structure:

```text
builtin_interfaces/Time stamp
string host_name
float32 cpu_percent
float32 memory_percent
float32 memory_total
float32 memory_available
float64 net_sent
float64 net_recv
```

The fields contain:

- ROS timestamp
- Host name
- CPU usage percentage
- Memory usage percentage
- Total and available memory in MiB
- Cumulative sent and received network data in MiB

`net_sent` and `net_recv` are cumulative amounts of data, not current network speeds.

### 4.2 Interface Generation

The interface package uses `rosidl_generate_interfaces()` during the build:

```cmake
rosidl_generate_interfaces(
  ${PROJECT_NAME}
  "msg/SystemStatus.msg"
  DEPENDENCIES builtin_interfaces
)
```

The generation process is:

```text
SystemStatus.msg
        ↓
rosidl_generate_interfaces()
        ↓
Generated C++ and Python interface code
        ↓
status_interfaces.msg.SystemStatus
```

`SystemStatus` is therefore not a manually written Python class. It is generated from `SystemStatus.msg` during `colcon build`.

### 4.3 Package Dependency

`status_publisher/package.xml` declares:

```xml
<depend>status_interfaces</depend>
```

This tells the build system that `status_interfaces` must be available before `status_publisher` can use its generated message type.

The Python node imports the generated class with:

```python
from status_interfaces.msg import SystemStatus
```

After the build, `source install/setup.bash` updates the current terminal environment so ROS2 and Python can locate the generated interface.

### 4.4 System Status Publisher

`sys_status_pub.py` creates a timer that runs once per second. Each timer callback:

1. Reads CPU, memory, and network information with `psutil`.
2. Creates a `SystemStatus` message.
3. Fills each message field.
4. Publishes the message to `/sys_status`.

```text
Timer callback
      ↓
psutil collects system data
      ↓
Create and fill SystemStatus
      ↓
Publish to /sys_status
```

The timestamp is assigned with:

```python
msg.stamp = self.get_clock().now().to_msg()
```

- `get_clock()` returns the ROS Clock used by the node.
- `now()` obtains the current ROS time.
- `to_msg()` converts the Python `Time` object into `builtin_interfaces/msg/Time`, matching the type declared in `SystemStatus.msg`.

When creating the Publisher:

```python
self.create_publisher(SystemStatus, 'sys_status', 10)
```

`SystemStatus` is the message type, `sys_status` is the Topic name, and `10` is the QoS history depth used with the default keep-last behavior.

## 5. Build

From this module directory:

```bash
cd ~/ros2-robotics-learning/examples/topic_communication
colcon build
source install/setup.bash
```

The interface package must be built before its generated Python class can be imported. `colcon` uses the dependencies declared in `package.xml` to determine the correct build order.

For a clean dependency check, install missing dependencies with:

```bash
rosdep install --from-paths . --ignore-src -r -y
```

## 6. Run the Examples

Open a new terminal for each node and source the module environment first:

```bash
cd ~/ros2-robotics-learning/examples/topic_communication
source install/setup.bash
```

### 6.1 Novel Publisher and Subscriber

Start an HTTP server in the directory containing the novel text file:

```bash
python3 -m http.server 8000
```

Ensure that the URL used by `novel_pub_node.py` matches the text file served by the HTTP server. Then run:

```bash
ros2 run demo_python_topic novel_pub_node
```

In another terminal:

```bash
ros2 run demo_python_topic novel_sub_node
```

### 6.2 Turtle Circle Control

```bash
ros2 run turtlesim turtlesim_node
```

In another terminal:

```bash
ros2 run demo_cpp_topic turtle_circle
```

### 6.3 Turtle Target Control

```bash
ros2 run turtlesim turtlesim_node
```

In another terminal:

```bash
ros2 run demo_cpp_topic turtle_control
```

### 6.4 System Status Publisher

```bash
ros2 run status_publisher sys_status_pub
```

Inspect the custom Topic in another terminal:

```bash
ros2 topic echo /sys_status
```

The generated message definition can also be inspected with:

```bash
ros2 interface show status_interfaces/msg/SystemStatus
```

## 7. Key Concepts Learned

- Publishers and Subscribers are decoupled through Topics.
- ROS2 Executors schedule ready callbacks while nodes are spinning.
- Slow work inside a callback can block other callback processing.
- An application-level queue and worker thread can separate fast data reception from slow processing.
- QoS history depth and a Python application queue are different mechanisms.
- Fixed velocity commands without state feedback form an open-loop controller.
- Pose feedback can be used to build a simple closed-loop controller.
- A `.msg` file defines a custom data structure.
- `rosidl_generate_interfaces()` generates language-specific message code during the build.
- Package dependencies make the build order and runtime requirements reproducible.
- ROS time objects must be converted to the message type required by a timestamp field.
