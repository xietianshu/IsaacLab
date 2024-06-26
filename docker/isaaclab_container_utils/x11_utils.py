# Copyright (c) 2022-2024, The Isaac Lab Project Developers.
# All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause

import os
import shutil
import subprocess
from pathlib import Path

from isaaclab_container_utils.statefile import Statefile


def install_xauth() -> None:
    """
    Prompt the user to install xauth via apt if it is not already installed.

    If the user agrees, update the package list and install xauth.
    """
    xauth_answer = input("[INFO] xauth is not installed. Would you like to install it via apt? (y/N) ")
    if xauth_answer.lower() == "y":
        subprocess.run(["sudo", "apt", "update"], check=True)
        subprocess.run(["sudo", "apt", "install", "xauth"], check=True)
    else:
        print("[INFO] Did not install xauth. X11 forwarding not enabled.")


# This method of x11 enabling forwarding was inspired by osrf/rocker
# https://github.com/osrf/rocker
def configure_x11(statefile: Statefile) -> dict[str, str]:
    """
    Configure X11 forwarding by creating and managing a temporary .xauth file.

    If xauth is not installed, prompt the user to install it. If the .xauth file
    does not exist, create it and configure it with the necessary xauth cookie.

    Args:
        statefile (Statefile): An instance of the Statefile class to manage state variables.

    Returns:
        dict: A dictionary where the key is __ISAACLAB_TMP_XAUTH (referenced in x11.yaml)
              and the value is the corresponding tmp file which has been created.
    """
    if not shutil.which("xauth"):
        install_xauth()
    __ISAACLAB_TMP_XAUTH = statefile.load_variable("__ISAACLAB_TMP_XAUTH")
    if __ISAACLAB_TMP_XAUTH is None or not Path(__ISAACLAB_TMP_XAUTH).exists():
        __ISAACLAB_TMP_XAUTH = Path(
            subprocess.run(["mktemp", "--suffix=.xauth"], capture_output=True, text=True).stdout.strip()
        )
        statefile.set_variable("__ISAACLAB_TMP_XAUTH", str(__ISAACLAB_TMP_XAUTH))
        xauth_cookie = subprocess.run(
            ["xauth", "nlist", os.environ["DISPLAY"]], capture_output=True, text=True
        ).stdout.replace("ffff", "")
        subprocess.run(["xauth", "-f", __ISAACLAB_TMP_XAUTH, "nmerge", "-"], input=xauth_cookie, text=True)
    return {"__ISAACLAB_TMP_XAUTH": str(__ISAACLAB_TMP_XAUTH)}


def x11_check(statefile: Statefile) -> tuple[list[str], dict[str, str]] | str:
    """
    Check and configure X11 forwarding based on user input and existing state.

    Prompt the user to enable or disable X11 forwarding if not already configured.
    Configure X11 forwarding if enabled.

    Args:
        statefile (Statefile): An instance of the Statefile class to manage state variables.

    Returns:
        list or str: A list containing the x11.yaml file configuration option if X11 forwarding is enabled,
                     otherwise None
    """
    __ISAACLAB_X11_FORWARDING_ENABLED = statefile.load_variable("__ISAACLAB_X11_FORWARDING_ENABLED")
    if __ISAACLAB_X11_FORWARDING_ENABLED is None:
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
        x11_envar = configure_x11(statefile)
        # If X11 forwarding is enabled, return the proper args to
        # compose the x11.yaml file. Else, return an empty string.
        return (["--file", "x11.yaml"], x11_envar)

    return None


def x11_cleanup(statefile: Statefile) -> None:
    """
    Clean up the temporary .xauth file used for X11 forwarding.

    If the .xauth file exists, delete it and remove the corresponding state variable.

    Args:
        statefile (Statefile): An instance of the Statefile class to manage state variables.
    """
    __ISAACLAB_TMP_XAUTH = statefile.load_variable("__ISAACLAB_TMP_XAUTH")
    if __ISAACLAB_TMP_XAUTH is not None and Path(__ISAACLAB_TMP_XAUTH).exists():
        print(f"[INFO] Removing temporary Isaac Lab .xauth file {__ISAACLAB_TMP_XAUTH}.")
        Path(__ISAACLAB_TMP_XAUTH).unlink()
        statefile.delete_variable("__ISAACLAB_TMP_XAUTH")
