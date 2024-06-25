# Copyright (c) 2022-2024, The Isaac Lab Project Developers.
# All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause

# Nvidia Dockerfiles: https://github.com/NVIDIA-Omniverse/IsaacSim-dockerfiles
# Please check above link for license information.

# Base image
ARG ISAACSIM_VERSION_ARG
FROM nvcr.io/nvidia/isaac-sim:${ISAACSIM_VERSION_ARG} AS base
ENV ISAACSIM_VERSION=${ISAACSIM_VERSION_ARG}

# Set default RUN shell to bash
SHELL ["/bin/bash", "-c"]

# Adds labels to the Dockerfile
LABEL version="1.0"
LABEL description="Dockerfile for building and running the Isaac Lab framework inside Isaac Sim container image."

# Arguments
# We also make them envars for convenience/.bashrc injection
# Path to Isaac Sim root folder
ARG ISAACSIM_ROOT_PATH_ARG
ENV ISAACSIM_ROOT_PATH=${ISAACSIM_ROOT_PATH_ARG}
# Path to the Isaac Lab directory
ARG ISAACLAB_PATH_ARG
ENV ISAACLAB_PATH=${ISAACLAB_PATH_ARG}
# Home dir of docker user, typically '/root'
ARG DOCKER_USER_HOME_ARG
ENV DOCKER_USER_HOME=${DOCKER_USER_HOME_ARG}

# Set environment variables
ENV LANG=C.UTF-8
ENV DEBIAN_FRONTEND=noninteractive

USER root

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
COPY ../ ${ISAACLAB_PATH_ARG}

# Set up a symbolic link between the installed Isaac Sim root folder and _isaac_sim in the Isaac Lab directory
RUN ln -sf ${ISAACSIM_ROOT_PATH_ARG} ${ISAACLAB_PATH_ARG}/_isaac_sim

# Install apt dependencies for extensions that declare them in their extension.toml
RUN --mount=type=cache,target=/var/cache/apt \
    ${ISAACLAB_PATH_ARG}/isaaclab.sh -p ${ISAACLAB_PATH_ARG}/tools/install_deps.py apt ${ISAACLAB_PATH_ARG}/source/extensions && \
    apt -y autoremove && apt clean autoclean && \
    rm -rf /var/lib/apt/lists/*

# for singularity usage, have to create the directories that will binded
RUN mkdir -p ${ISAACSIM_ROOT_PATH_ARG}/kit/cache && \
    mkdir -p ${DOCKER_USER_HOME_ARG}/.cache/ov && \
    mkdir -p ${DOCKER_USER_HOME_ARG}/.cache/pip && \
    mkdir -p ${DOCKER_USER_HOME_ARG}/.cache/nvidia/GLCache &&  \
    mkdir -p ${DOCKER_USER_HOME_ARG}/.nv/ComputeCache && \
    mkdir -p ${DOCKER_USER_HOME_ARG}/.nvidia-omniverse/logs && \
    mkdir -p ${DOCKER_USER_HOME_ARG}/.local/share/ov/data && \
    mkdir -p ${DOCKER_USER_HOME_ARG}/Documents

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
RUN --mount=type=cache,target=${DOCKER_USER_HOME_ARG}/.cache/pip \
    ${ISAACLAB_PATH_ARG}/isaaclab.sh --install

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
WORKDIR ${ISAACLAB_PATH_ARG}

# Everything past this stage is to install
# ROS2 Humble
FROM base AS ros2

# Re-using ARG from previous stage
ARG ISAACLAB_PATH_ARG
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
    ${ISAACLAB_PATH_ARG}/isaaclab.sh -p ${ISAACLAB_PATH_ARG}/tools/install_deps.py rosdep ${ISAACLAB_PATH_ARG}/source/extensions && \
    apt -y autoremove && apt clean autoclean && \
    rm -rf /var/lib/apt/lists/* && \
    # Add sourcing of setup.bash to .bashrc
    echo "source /opt/ros/humble/setup.bash" >> ${HOME}/.bashrc

# Copy the RMW specifications for ROS2
# https://docs.omniverse.nvidia.com/isaacsim/latest/installation/install_ros.html#enabling-the-ros-bridge-extension
COPY docker/.ros/ ${DOCKER_USER_HOME}/.ros/

# Add any customizations you would like to be present when you run `container.py start custom` below
# If you don't require ros2, you can change the underlying layer to base, ie "FROM base AS custom"
FROM ros2 AS custom

ARG CUSTOM_MESSAGE_ARG
RUN echo ${CUSTOM_MESSAGE_ARG}
