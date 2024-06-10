# Copyright (c) 2022-2024, The Isaac Lab Project Developers.
# All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause

import os
import shutil
import subprocess
from pathlib import Path


def install_xauth():
    xauth_answer = input("[INFO] xauth is not installed. Would you like to install it via apt? (y/N) ")
    if xauth_answer.lower() == "y":
        subprocess.run(["sudo", "apt", "update"], check=True)
        subprocess.run(["sudo", "apt", "install", "xauth"], check=True)
    else:
        print("[INFO] Did not install xauth. Full X11 forwarding not enabled.")


# This method of x11 enabling forwarding was inspired by osrf/rocker
# https://github.com/osrf/rocker
def configure_x11(statefile):
    if not shutil.which("xauth"):
        install_xauth()
    __ISAACLAB_TMP_XAUTH = statefile.load_variable("__ISAACLAB_TMP_XAUTH")
    if __ISAACLAB_TMP_XAUTH == "null" or not Path(__ISAACLAB_TMP_XAUTH).exists():
        __ISAACLAB_TMP_XAUTH = Path(
            subprocess.run(["mktemp", "--suffix=.xauth"], capture_output=True, text=True).stdout.strip()
        )
        statefile.set_variable("__ISAACLAB_TMP_XAUTH", str(__ISAACLAB_TMP_XAUTH))
        xauth_cookie = subprocess.run(
            ["xauth", "nlist", os.environ["DISPLAY"]], capture_output=True, text=True
        ).stdout.replace("ffff", "")
        subprocess.run(["xauth", "-f", __ISAACLAB_TMP_XAUTH, "nmerge", "-"], input=xauth_cookie, text=True)
    os.environ["__ISAACLAB_TMP_XAUTH"] = str(__ISAACLAB_TMP_XAUTH)
    x11_yaml = ["--file", "x11.yaml"]
    return x11_yaml


def x11_check(statefile):
    __ISAACLAB_X11_FORWARDING_ENABLED = statefile.load_variable("__ISAACLAB_X11_FORWARDING_ENABLED")
    if __ISAACLAB_X11_FORWARDING_ENABLED == "null":
        print("[INFO] X11 forwarding from the Isaac Lab container is off by default.")
        print(
            "[INFO] It will fail if there is no display, or this script is being run via ssh without proper"
            " configuration."
        )
        x11_answer = input("Would you like to enable it? (y/N) ")
        if x11_answer.lower() == "y":
            __ISAACLAB_X11_FORWARDING_ENABLED = "1"
            statefile.set_variable("__ISAACLAB_X11_FORWARDING_ENABLED", "1")
            print("[INFO] X11 forwarding is enabled from the container.")
        else:
            __ISAACLAB_X11_FORWARDING_ENABLED = "0"
            statefile.set_variable("__ISAACLAB_X11_FORWARDING_ENABLED", "0")
            print("[INFO] X11 forwarding is disabled from the container.")
    else:
        print(f"[INFO] X11 Forwarding is configured as {__ISAACLAB_X11_FORWARDING_ENABLED} in .container.yaml")
        if __ISAACLAB_X11_FORWARDING_ENABLED == "1":
            print("[INFO] To disable X11 forwarding, set __ISAACLAB_X11_FORWARDING_ENABLED=0 in .container.yaml")
        else:
            print("[INFO] To enable X11 forwarding, set __ISAACLAB_X11_FORWARDING_ENABLED=1 in .container.yaml")

    if __ISAACLAB_X11_FORWARDING_ENABLED == "1":
        return configure_x11(statefile)
    return ""


def x11_cleanup(statefile):
    __ISAACLAB_TMP_XAUTH = statefile.load_variable("__ISAACLAB_TMP_XAUTH")
    if __ISAACLAB_TMP_XAUTH != "null" and Path(__ISAACLAB_TMP_XAUTH).exists():
        print(f"[INFO] Removing temporary Isaac Lab .xauth file {__ISAACLAB_TMP_XAUTH}.")
        Path(__ISAACLAB_TMP_XAUTH).unlink()
        statefile.delete_variable("__ISAACLAB_TMP_XAUTH")
