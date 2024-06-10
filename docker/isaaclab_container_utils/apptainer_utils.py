# Copyright (c) 2022-2024, The Isaac Lab Project Developers.
# All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause

import subprocess
import sys


def install_apptainer():
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


def check_docker_version_compatible():
    docker_version = subprocess.run(["docker", "--version"], capture_output=True, text=True).stdout.split()[2]
    apptainer_version = subprocess.run(["apptainer", "--version"], capture_output=True, text=True).stdout.split()[2]
    if int(docker_version.split(".")[0]) >= 25:
        print(
            f"[ERROR]: Docker version {docker_version} is not compatible with Apptainer version {apptainer_version}."
            " Docker version must be 25.x.x or lower. Exiting."
        )
        sys.exit(1)
    else:
        print(
            f"[INFO]: Building singularity with docker version: {docker_version} and Apptainer version:"
            f" {apptainer_version}."
        )


def check_singularity_image_exists(container_interface):
    CLUSTER_LOGIN = container_interface.dot_vars["CLUSTER_LOGIN"]
    CLUSTER_SIF_PATH = container_interface.dot_vars["CLUSTER_SIF_PATH"]
    result = subprocess.run(
        ["ssh", CLUSTER_LOGIN, f"[ -f {CLUSTER_SIF_PATH}/{container_interface.image_name}.tar ]"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(
            f"[Error] The '{container_interface.image_name}' image does not exist on the remote host {CLUSTER_LOGIN}!",
            file=sys.stderr,
        )
        sys.exit(1)
