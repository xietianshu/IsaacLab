#!/usr/bin/env python3

# Copyright (c) 2022-2024, The Isaac Lab Project Developers.
# All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

from isaaclab_container_utils import apptainer_utils, x11_utils
from isaaclab_container_utils.isaaclab_container_interface import IsaacLabContainerInterface
from isaaclab_container_utils.statefile import Statefile


def main():
    parser = argparse.ArgumentParser(description="Utility for using Docker with Isaac Lab.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("start", help="Build the docker image and create the container in detached mode.")
    subparsers.add_parser("enter", help="Begin a new bash process within an existing Isaac Lab container.")
    subparsers.add_parser("copy", help="Copy build and logs artifacts from the container to the host machine.")
    subparsers.add_parser("stop", help="Stop the docker container and remove it.")
    subparsers.add_parser("push", help="Push the docker image to the cluster.")

    job_parser = subparsers.add_parser("job", help="Submit a job to the cluster.")
    job_parser.add_argument(
        "job_args", nargs=argparse.REMAINDER, help="Optional arguments specific to the executed script."
    )

    parser.add_argument("profile", nargs="?", help="Optional container profile specification.")

    args = parser.parse_args()

    if not shutil.which("docker"):
        print("[Error] Docker is not installed! Please check the 'Docker Guide' for instruction.", file=sys.stderr)
        sys.exit(1)

    base_dir = Path(__file__).resolve().parent
    # Creating statefile
    statefile = Statefile(statefile=base_dir / ".container.yaml")
    container_interface = IsaacLabContainerInterface(base_dir=base_dir, profile=args.profile, statefile=statefile)

    print(f"[INFO] Using container profile: {container_interface.profile}")

    if args.command == "start":
        print(
            f"[INFO] Building the docker image and starting the container {container_interface.container_name} in the"
            " background..."
        )
        os.chdir(container_interface.base_dir)
        container_interface.add_yamls += x11_utils.x11_check(statefile)
        subprocess.run(
            [
                "docker",
                "compose",
                "--file",
                "docker-compose.yaml",
                "--env-file",
                ".env.base",
                "build",
                "isaac-lab-base",
            ],
            check=True,
        )
        subprocess.run(
            ["docker", "compose"]
            + container_interface.add_yamls
            + container_interface.add_profiles
            + container_interface.add_envs
            + ["up", "--detach", "--build", "--remove-orphans"],
            check=True,
        )
    elif args.command == "enter":
        container_interface.is_container_running()
        print(f"[INFO] Entering the existing {container_interface.container_name} container in a bash session...")
        os.chdir(container_interface.base_dir)
        subprocess.run(
            ["docker", "exec", "--interactive", "--tty", f"{container_interface.container_name}", "bash"], check=True
        )
    elif args.command == "copy":
        container_interface.is_container_running()
        print(f"[INFO] Copying artifacts from the 'isaac-lab-{container_interface.profile}' container...")
        artifacts = {"logs": "logs", "docs/_build": "docs/_build", "data_storage": "data_storage"}
        for container_path, host_path in artifacts.items():
            print(f"\t - /workspace/isaaclab/{container_path} -> {container_interface.base_dir}/artifacts/{host_path}")
        os.chdir(container_interface.base_dir)
        for path in artifacts.values():
            shutil.rmtree(container_interface.base_dir / f"artifacts/{path}", ignore_errors=True)
        (container_interface.base_dir / "artifacts/docs").mkdir(parents=True, exist_ok=True)
        for container_path, host_path in artifacts.items():
            subprocess.run(
                [
                    "docker",
                    "cp",
                    f"isaac-lab-{container_interface.profile}:/workspace/isaaclab/{container_path}",
                    f"./artifacts/{host_path}",
                ],
                check=True,
            )
        print("\n[INFO] Finished copying the artifacts from the container.")
    elif args.command == "stop":
        container_interface.is_container_running()
        print(f"[INFO] Stopping the launched docker container {container_interface.container_name}...")
        os.chdir(container_interface.base_dir)
        subprocess.run(
            ["docker", "compose", "--file", "docker-compose.yaml"]
            + container_interface.add_profiles
            + container_interface.add_envs
            + ["down"],
            check=True,
        )
        x11_utils.x11_cleanup(statefile)
    elif args.command == "push":
        if not shutil.which("apptainer"):
            apptainer_utils.install_apptainer()
        container_interface.check_image_exists()
        apptainer_utils.check_docker_version_compatible()
        cluster_login = container_interface.dot_vars["CLUSTER_LOGIN"]
        cluster_isaaclab_dir = container_interface.dot_vars["CLUSTER_ISAACLAB_DIR"]
        cluster_sif_path = container_interface.dot_vars["CLUSTER_SIF_PATH"]
        exports_dir = container_interface.base_dir / "exports"
        exports_dir.mkdir(parents=True, exist_ok=True)
        for file in exports_dir.glob(f"{container_interface.container_name}*"):
            file.unlink()
        os.chdir(exports_dir)
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
        )
        subprocess.run(
            ["tar", "-cvf", f"{container_interface.container_name}.tar", f"{container_interface.container_name}.sif"],
            check=True,
        )
        subprocess.run(["ssh", cluster_login, f"mkdir -p {cluster_sif_path}"], check=True)
        subprocess.run(
            [
                "scp",
                f"{container_interface.container_name}.tar",
                f"{cluster_login}:{cluster_sif_path}/{container_interface.container_name}.tar",
            ],
            check=True,
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
                f"/{container_interface.base_dir}/..",
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
        print(f"[Error] Invalid command provided: {args.command}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
