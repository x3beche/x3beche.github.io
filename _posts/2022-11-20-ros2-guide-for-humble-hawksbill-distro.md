---
layout: post
title: ROS2
description: ROS2 Guide For Humble Hawksbill Distro on Ubuntu 22.04
summary: ROS2 Guide For Humble Hawksbill Distro on Ubuntu 22.04
tags: ros2 robotics guide
minute: 60
---

# installing colcon for autocomplete
```
sudo apt install python3-colcon-common-extensions -y
sudo apt-get install python3-pip -y
pip3 install setuptools==58.2.0
```

# add these lines to .bashrc if they not exist
```
echo "source /opt/ros/humble/setup.bash" >> ~/.bashrc
echo "source /usr/share/colcon_argcomplete/hook/colcon-argcomplete.bash" >> ~/.bashrc
```

# creating workspace
```
cd ~ 
mkdir ros2_ws
cd ros2_ws
mkdir src
colcon build
echo "source ~/ros2_ws/install/setup.bash" >> ~/.bashrc
```

# creating python package
```
cd ~/ros2_ws/src/
ros2 pkg create my_robot_controller --build-type ament_python --dependencies rclpy
cd ..
colcon build
```

# build should be like this
```
Starting >>> my_robot_controller
Finished <<< my_robot_controller [1.17s]    
Summary: 1 package finished [1.37s]
```

# creating ros2 node
```
cd src/my_robot_controller/my_robot_controller/
touch my_first_node.py
sudo chmod +x my_first_node.py
```

# git settings
```
git config user.name "x3beche"
git config user.email "x3beche@gmail.com"
git remote remove origin
git remote add origin https://<TOKEN>@github.com/<USERNAME>/<REPO>.git
git push --set-upstream origin main
```