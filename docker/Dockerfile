# Copyright (c) 2022-2024, The Isaac Lab Project Developers.
# All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause

# Nvidia Dockerfiles: https://github.com/NVIDIA-Omniverse/IsaacSim-dockerfiles
# Please check above link for license information.

# Base image
ARG ISAACSIM_VERSION
FROM nvcr.io/nvidia/isaac-sim:${ISAACSIM_VERSION} AS base

# Set default RUN shell to bash
SHELL ["/bin/bash", "-c"]

# Adds labels to the Dockerfile
LABEL version="1.0"
LABEL description="Dockerfile for building and running the Isaac Lab framework inside Isaac Sim container image."

# Arguments
# Path to Isaac Sim root folder
ARG ISAACSIM_ROOT_PATH
# Path to the Isaac Lab directory
ARG ISAACLAB_PATH
# Home dir of docker user, typically '/root'
ARG USER_HOME

# Install dependencies and remove cache
RUN --mount=type=cache,target=/var/cache/apt \
    apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    git \
    libglib2.0-0 \
    ncurses-term && \
    apt -y autoremove && apt clean autoclean && \
    rm -rf /var/lib/apt/lists/*

# Copy the Isaac Lab directory (files to exclude are defined in .dockerignore)
COPY ../ ${ISAACLAB_PATH}

# Set up a symbolic link between the installed Isaac Sim root folder and _isaac_sim in the Isaac Lab directory
RUN ln -sf ${ISAACSIM_ROOT_PATH} ${ISAACLAB_PATH}/_isaac_sim

# Install apt dependencies for extensions that declare them in their extension.toml
RUN --mount=type=cache,target=/var/cache/apt \
    ${ISAACLAB_PATH}/isaaclab.sh -p ${ISAACLAB_PATH}/tools/install_deps.py apt ${ISAACLAB_PATH}/source/extensions && \
    apt -y autoremove && apt clean autoclean && \
    rm -rf /var/lib/apt/lists/*

# for singularity usage, have to create the directories that will binded
RUN mkdir -p ${ISAACSIM_ROOT_PATH}/kit/cache && \
    mkdir -p ${USER_HOME}/.cache/ov && \
    mkdir -p ${USER_HOME}/.cache/pip && \
    mkdir -p ${USER_HOME}/.cache/nvidia/GLCache &&  \
    mkdir -p ${USER_HOME}/.nv/ComputeCache && \
    mkdir -p ${USER_HOME}/.nvidia-omniverse/logs && \
    mkdir -p ${USER_HOME}/.local/share/ov/data && \
    mkdir -p ${USER_HOME}/Documents

# for singularity usage, create NVIDIA binary placeholders
RUN touch /bin/nvidia-smi && \
    touch /bin/nvidia-debugdump && \
    touch /bin/nvidia-persistenced && \
    touch /bin/nvidia-cuda-mps-control && \
    touch /bin/nvidia-cuda-mps-server && \
    touch /etc/localtime && \
    mkdir -p /var/run/nvidia-persistenced && \
    touch /var/run/nvidia-persistenced/socket

# installing Isaac Lab dependencies
# use pip caching to avoid reinstalling large packages
RUN --mount=type=cache,target=${USER_HOME}/.cache/pip \
    ${ISAACLAB_PATH}/isaaclab.sh --install

# aliasing isaaclab.sh and python for convenience
RUN echo "alias isaaclab=${ISAACLAB_PATH}/isaaclab.sh" >> ${HOME}/.bashrc && \
    echo "alias python=${ISAACLAB_PATH}/_isaac_sim/python.sh" >> ${HOME}/.bashrc && \
    echo "alias python3=${ISAACLAB_PATH}/_isaac_sim/python.sh" >> ${HOME}/.bashrc && \
    echo "alias pip='${ISAACLAB_PATH}/_isaac_sim/python.sh -m pip'" >> ${HOME}/.bashrc && \
    echo "alias pip3='${ISAACLAB_PATH}/_isaac_sim/python.sh -m pip'" >> ${HOME}/.bashrc && \
    echo "alias tensorboard='${ISAACLAB_PATH}/_isaac_sim/python.sh ${ISAACLAB_PATH}/_isaac_sim/tensorboard'" >> ${HOME}/.bashrc && \
    echo "export TZ=$(date +%Z)" >> ${HOME}/.bashrc

# make working directory as the Isaac Lab directory
# this is the default directory when the container is run
WORKDIR ${ISAACLAB_PATH}

# Everything past this stage is to install
# ROS2 Humble
FROM base AS ros2

# Re-using ARGs from previous stage
ARG ISAACLAB_PATH
ARG USER_HOME
# Which ROS2 apt package to install
ARG ROS2_APT_PACKAGE

# ROS2 Humble Apt installations
RUN --mount=type=cache,target=/var/cache/apt \
    apt-get update && apt-get install -y --no-install-recommends \
    curl \
    # Install ROS2 Humble \
    software-properties-common && \
    add-apt-repository universe && \
    curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key -o /usr/share/keyrings/ros-archive-keyring.gpg && \
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] http://packages.ros.org/ros2/ubuntu $(. /etc/os-release && echo jammy) main" | tee /etc/apt/sources.list.d/ros2.list > /dev/null && \
    apt-get update && apt-get install -y --no-install-recommends \
    ros-humble-${ROS2_APT_PACKAGE} \
    ros-humble-vision-msgs \
    # Install both FastRTPS and CycloneDDS
    ros-humble-rmw-cyclonedds-cpp \
    ros-humble-rmw-fastrtps-cpp \
    # This includes various dev tools including colcon
    ros-dev-tools && \
    # Install rosdeps for extensions that declare a ros_ws in
    # their extension.toml
    ${ISAACLAB_PATH}/isaaclab.sh -p ${ISAACLAB_PATH}/tools/install_deps.py rosdep ${ISAACLAB_PATH}/source/extensions && \
    apt -y autoremove && apt clean autoclean && \
    rm -rf /var/lib/apt/lists/* && \
    # Add sourcing of setup.bash to .bashrc
    echo "source /opt/ros/humble/setup.bash" >> ${HOME}/.bashrc

# Copy the RMW specifications for ROS2
# https://docs.omniverse.nvidia.com/isaacsim/latest/installation/install_ros.html#enabling-the-ros-bridge-extension
COPY docker/.ros/ ${USER_HOME}/.ros/

# Add any customizations you would like to be present when you run `container.py start custom` below
# If you don't require ros2, you can change the underlying layer to base, ie "FROM base AS custom"
FROM ros2 AS custom

# Please make sure to re-declare any args which you require
# from previous stages, ie ARG ISAACLAB_PATH if you need ISAACLAB_PATH from base
# Re-using ARG ISAACLAB_PATH
ARG ISAACLAB_PATH
ARG CUSTOM_MESSAGE
RUN echo ${CUSTOM_MESSAGE} && \
    touch ${ISAACLAB_PATH}/TEST_FILE
