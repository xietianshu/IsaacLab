# Copyright (c) 2022-2024, The Isaac Lab Project Developers.
# All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause

import subprocess
import sys

from isaaclab_container_utils.isaaclab_container_interface import IsaacLabContainerInterface


def install_apptainer() -> None:
    """
    Prompt the user to install Apptainer via apt if it is not already installed.

    If the user agrees, update the package list, add the Apptainer PPA, and install Apptainer.
    If the user declines, exit the program.
    """
    app_answer = input(
        "[INFO] Required 'apptainer' package could not be found. Would you like to install it via apt? (y/N)"
    )
    if app_answer.lower() == "y":
        subprocess.run(["sudo", "apt", "update"], check=True)
        subprocess.run(["sudo", "apt", "install", "-y", "software-properties-common"], check=True)
        subprocess.run(["sudo", "add-apt-repository", "-y", "ppa:apptainer/ppa"], check=True)
        subprocess.run(["sudo", "apt", "update"], check=True)
        subprocess.run(["sudo", "apt", "install", "-y", "apptainer"], check=True)
    else:
        print("[INFO] Exiting because apptainer was not installed")
        sys.exit()


def check_docker_version_compatible() -> None:
    """
    Check if the Docker version is compatible with Apptainer.

    If the Docker version is 25.x.x or higher, raise a RuntimeError.
    Print the Docker and Apptainer versions if they are compatible.
    """
    docker_version = subprocess.run(["docker", "--version"], capture_output=True, text=True).stdout.split()[2]
    apptainer_version = subprocess.run(["apptainer", "--version"], capture_output=True, text=True).stdout.split()[2]
    if int(docker_version.split(".")[0]) >= 25:
        raise RuntimeError(
            f"Docker version {docker_version} is not compatible with Apptainer version {apptainer_version}."
            " Docker version must be 24.x.x or lower. Exiting."
        )
    print(
        f"[INFO]: Building singularity with docker version: {docker_version} and Apptainer version:"
        f" {apptainer_version}."
    )


def check_singularity_image_exists(container_interface: IsaacLabContainerInterface) -> None:
    """
    Check if the Singularity image exists on the remote host.

    Args:
        container_interface (IsaacLabContainerInterface): An instance of IsaacLabContainerInterface to access configuration variables.

    Raises:
        RuntimeError: If the Singularity image does not exist on the remote host.
    """
    CLUSTER_LOGIN = container_interface.dot_vars["CLUSTER_LOGIN"]
    CLUSTER_SIF_PATH = container_interface.dot_vars["CLUSTER_SIF_PATH"]
    result = subprocess.run(
        ["ssh", CLUSTER_LOGIN, f"[ -f {CLUSTER_SIF_PATH}/{container_interface.image_name}.tar ]"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"The image '{container_interface.image_name}' does not exist on the remote host {CLUSTER_LOGIN}!",
        )
