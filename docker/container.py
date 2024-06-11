#!/usr/bin/env python3

# Copyright (c) 2022-2024, The Isaac Lab Project Developers.
# All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause

import argparse
import shutil
import subprocess
from pathlib import Path

from isaaclab_container_utils import apptainer_utils, x11_utils
from isaaclab_container_utils.isaaclab_container_interface import IsaacLabContainerInterface
from isaaclab_container_utils.statefile import Statefile


def main():
    parser = argparse.ArgumentParser(description="Utility for using Docker with Isaac Lab.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # We have to create a separate parent parser for common options to our subparsers
    parent_parser = argparse.ArgumentParser(add_help=False)
    parent_parser.add_argument("profile", nargs="?", default="base", help="Optional container profile specification.")

    subparsers.add_parser(
        "start", help="Build the docker image and create the container in detached mode.", parents=[parent_parser]
    )
    subparsers.add_parser(
        "enter", help="Begin a new bash process within an existing Isaac Lab container.", parents=[parent_parser]
    )
    subparsers.add_parser(
        "copy", help="Copy build and logs artifacts from the container to the host machine.", parents=[parent_parser]
    )
    subparsers.add_parser("stop", help="Stop the docker container and remove it.", parents=[parent_parser])
    subparsers.add_parser("push", help="Push the docker image to the cluster.", parents=[parent_parser])

    job_parser = subparsers.add_parser("job", help="Submit a job to the cluster.", parents=[parent_parser])
    job_parser.add_argument(
        "job_args", nargs=argparse.REMAINDER, help="Optional arguments specific to the executed script."
    )

    args = parser.parse_args()

    if not shutil.which("docker"):
        raise RuntimeError("Docker is not installed! Please check the 'Docker Guide' for instruction.")

    context_dir = Path(__file__).resolve().parent
    # Creating statefile
    statefile = Statefile(statefile=context_dir / ".container.yaml")
    container_interface = IsaacLabContainerInterface(context_dir=context_dir, profile=args.profile, statefile=statefile)

    print(f"[INFO] Using container profile: {container_interface.profile}")
    if args.command == "start":
        print(
            f"[INFO] Building the docker image and starting the container {container_interface.container_name} in the"
            " background..."
        )
        x11_yaml, x11_envar = x11_utils.x11_check(container_interface.statefile)
        container_interface.add_yamls += x11_yaml
        container_interface.environ.update(x11_envar)
        container_interface.start()
    elif args.command == "enter":
        print(f"[INFO] Entering the existing {container_interface.container_name} container in a bash session...")
        container_interface.enter()
    elif args.command == "copy":
        print(f"[INFO] Copying artifacts from the 'isaac-lab-{container_interface.container_name}' container...")
        container_interface.copy()
        print("\n[INFO] Finished copying the artifacts from the container.")
    elif args.command == "stop":
        print(f"[INFO] Stopping the launched docker container {container_interface.container_name}...")
        container_interface.stop()
        x11_utils.x11_cleanup(statefile)
    elif args.command == "push":
        if not shutil.which("apptainer"):
            apptainer_utils.install_apptainer()
        if not container_interface.does_image_exist():
            raise RuntimeError(f"The image '{container_interface.image_name}' does not exist!")
        apptainer_utils.check_docker_version_compatible()
        cluster_login = container_interface.dot_vars["CLUSTER_LOGIN"]
        cluster_isaaclab_dir = container_interface.dot_vars["CLUSTER_ISAACLAB_DIR"]
        cluster_sif_path = container_interface.dot_vars["CLUSTER_SIF_PATH"]
        exports_dir = container_interface.context_dir / "exports"
        exports_dir.mkdir(parents=True, exist_ok=True)
        for file in exports_dir.glob(f"{container_interface.container_name}*"):
            file.unlink()
        subprocess.run(
            [
                "APPTAINER_NOHTTPS=1",
                "apptainer",
                "build",
                "--sandbox",
                "--fakeroot",
                f"{container_interface.container_name}.sif",
                f"docker-daemon://{container_interface.image_name}",
            ],
            check=True,
            shell=True,
            cwd=exports_dir,
        )
        subprocess.run(
            ["tar", "-cvf", f"{container_interface.container_name}.tar", f"{container_interface.container_name}.sif"],
            check=True,
            cwd=exports_dir,
        )
        subprocess.run(["ssh", cluster_login, f"mkdir -p {cluster_sif_path}"], check=True, cwd=exports_dir)
        subprocess.run(
            [
                "scp",
                f"{container_interface.container_name}.tar",
                f"{cluster_login}:{cluster_sif_path}/{container_interface.container_name}.tar",
            ],
            check=True,
            cwd=exports_dir,
        )
    elif args.command == "job":
        cluster_login = container_interface.dot_vars["CLUSTER_LOGIN"]
        cluster_isaaclab_dir = container_interface.dot_vars["CLUSTER_ISAACLAB_DIR"]
        apptainer_utils.check_singularity_image_exists(container_interface)
        subprocess.run(["ssh", cluster_login, f"mkdir -p {cluster_isaaclab_dir}"], check=True)
        print("[INFO] Syncing Isaac Lab code...")
        subprocess.run(
            [
                "rsync",
                "-rh",
                "--exclude",
                "*.git*",
                "--filter=:- .dockerignore",
                f"/{container_interface.context_dir}/..",
                f"{cluster_login}:{cluster_isaaclab_dir}",
            ],
            check=True,
        )
        print("[INFO] Executing job script...")
        subprocess.run(
            [
                "ssh",
                cluster_login,
                f"cd {cluster_isaaclab_dir} && sbatch {cluster_isaaclab_dir}/docker/cluster/submit_job.sh",
                cluster_isaaclab_dir,
                f"{container_interface.container_name}",
            ]
            + args.job_args,
            check=True,
        )
    else:
        raise RuntimeError(f"Invalid command provided: {args.command}")


if __name__ == "__main__":
    main()
