# demo_cpp_pkg

This package records my basic C++ and ROS2 C++ programming practice.

The main purpose of this package is to learn the C++ features that are frequently used in ROS2 development, understand the basic structure of a ROS2 C++ node, and become familiar with the ROS2 C++ build and execution process.

During this stage, I also studied basic Linux and ROS2 environment variables, especially how ROS2 locates installed packages and executables.

## Learning Contents

### `cpp_node.cpp`

A minimal ROS2 C++ node.

This example is used to understand the basic lifecycle of a ROS2 node:

* Initialize ROS2 with `rclcpp::init()`
* Create a ROS2 node
* Print ROS2 log messages
* Use `rclcpp::spin()` to let the executor continuously process callbacks and ROS2 events
* Shut down ROS2 with `rclcpp::shutdown()`

### `person_node.cpp`

A ROS2 node implemented using C++ object-oriented programming.

This example is used to practice:

* Class definition
* Class members and member functions
* Constructors
* Inheritance
* Inheriting from `rclcpp::Node`
* Calling the parent-class constructor
* Using inherited ROS2 APIs such as `get_logger()`

### `learn_auto.cpp`

Practice using C++ `auto` type deduction.

The compiler determines the variable type during compilation according to the initialization expression.

### `learn_shared_ptr.cpp`

Practice using `std::shared_ptr` and `std::make_shared`.

This example is used to understand:

* Shared ownership
* Reference counting
* `reset()`
* `get()`
* Pointer dereferencing with `*`
* Member access with `->`

These concepts are important because smart pointers are frequently used in ROS2 C++ APIs.

### `learn_lambda.cpp`

Practice defining and calling Lambda expressions.

This example also introduces Lambda capture and shows how external variables can be captured inside a Lambda.

### `learn_functional.cpp`

Practice using `std::function` and `std::bind`.

Different callable objects, such as:

* Free functions
* Member functions
* Lambda expressions

can be wrapped using a common callable interface when their parameter and return types are compatible.

This is useful for understanding callback-based programming in ROS2.

### `learn_thread.cpp`

Practice basic C++ multithreading.

This example combines:

* `std::thread`
* `std::function`
* `std::bind`
* Lambda callbacks
* `join` / `detach` concepts

Multiple download tasks can run concurrently instead of waiting for one task to finish before starting the next one.

## Build Process

ROS2 workspaces are normally built using:

```bash
colcon build
```

`colcon` manages the workspace-level build process. It discovers ROS2 packages, analyzes their dependencies, determines the appropriate build order, and invokes the corresponding build system for each package.

For an `ament_cmake` C++ package, the simplified build relationship can be understood as:

```text
colcon
  ↓
ament_cmake
  ↓
CMake
  ↓
Make
  ↓
g++
```

CMake reads `CMakeLists.txt` and generates build rules, while the compiler such as `g++` ultimately compiles the C++ source code.

## Running ROS2 Executables

After building the workspace, source the workspace environment:

```bash
source install/setup.bash
```

Then a ROS2 executable can be started with:

```bash
ros2 run <package_name> <executable_name>
```

For example:

```bash
ros2 run demo_cpp_pkg cpp_node
```

The sourced ROS2 environment allows ROS2 to discover the installed package and locate its executable.
