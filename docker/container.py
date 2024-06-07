#!/usr/bin/env python3

import os
import argparse
import sys
import subprocess
import shutil
from pathlib import Path
from statefile import Statefile
import x11_utils
import apptainer_utils
from isaaclab_container_interface import IsaacLabContainerInterface

def main():
    parser = argparse.ArgumentParser(description="Utility for handling Docker in Isaac Lab.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("start", help="Build the docker image and create the container in detached mode.")
    subparsers.add_parser("enter", help="Begin a new bash process within an existing Isaac Lab container.")
    subparsers.add_parser("copy", help="Copy build and logs artifacts from the container to the host machine.")
    subparsers.add_parser("stop", help="Stop the docker container and remove it.")
    subparsers.add_parser("push", help="Push the docker image to the cluster.")
    
    job_parser = subparsers.add_parser("job", help="Submit a job to the cluster.")
    job_parser.add_argument("job_args", nargs=argparse.REMAINDER, help="Optional arguments specific to the executed script.")
    
    parser.add_argument("profile", nargs='?', help="Optional container profile specification.")
    
    args = parser.parse_args()

    if not shutil.which("docker"):
        print("[Error] Docker is not installed! Please check the 'Docker Guide' for instruction.", file=sys.stderr)
        sys.exit(1)

    base_dir=Path(__file__).resolve().parent
    statefile = Statefile(statefile=base_dir / ".container.yaml")
    ilci = IsaacLabContainerInterface(base_dir=base_dir, 
                                      profile=args.profile,
                                      statefile=statefile)

    print(f"[INFO] Using container profile: {ilci.profile}")

    if args.command == "start":
        print(f"[INFO] Building the docker image and starting the container {ilci.container_name} in the background...")
        os.chdir(ilci.base_dir)
        ilci.add_yamls += x11_utils.x11_check(statefile)
        subprocess.run(["docker", "compose", "--file", "docker-compose.yaml", "--env-file", ".env.base", "build", "isaac-lab-base"], check=True)
        subprocess.run(["docker", "compose"] + ilci.add_yamls + ilci.add_profiles + ilci.add_envs + ["up", "--detach", "--build", "--remove-orphans"], check=True)
    elif args.command == "enter":
        ilci.is_container_running()
        print(f"[INFO] Entering the existing {ilci.container_name} container in a bash session...")
        os.chdir(ilci.base_dir)
        subprocess.run(["docker", "exec", "--interactive", "--tty", f"{ilci.container_name}", "bash"], check=True)
    elif args.command == "copy":
        ilci.copy_artifacts()
    elif args.command == "stop":
        ilci.is_container_running()
        print(f"[INFO] Stopping the launched docker container {ilci.container_name}...")
        os.chdir(ilci.base_dir)
        subprocess.run(["docker", "compose", "--file", "docker-compose.yaml"] + ilci.add_profiles + ilci.add_envs + ["down"], check=True)
        x11_utils.x11_cleanup(statefile)
    elif args.command == "push":
        if not shutil.which("apptainer"):
            apptainer_utils.install_apptainer()
        ilci.check_image_exists()
        apptainer_utils.check_docker_version_compatible()
        with open(ilci.base_dir / ".env.base") as f:
            env_vars = dict(line.strip().split('=', 1) for line in f if '=' in line)
        cluster_login = env_vars['CLUSTER_LOGIN']
        cluster_sif_path = env_vars['CLUSTER_SIF_PATH']
        exports_dir = ilci.base_dir / "exports"
        exports_dir.mkdir(parents=True, exist_ok=True)
        for file in exports_dir.glob(f"{ilci.container_name}*"):
            file.unlink()
        os.chdir(exports_dir)
        subprocess.run(["APPTAINER_NOHTTPS=1", "apptainer", "build", "--sandbox", "--fakeroot", f"{ilci.container_name}.sif", f"docker-daemon://{ilci.image_name}"], check=True, shell=True)
        subprocess.run(["tar", "-cvf", f"{ilci.container_name}.tar", f"{ilci.container_name}.sif"], check=True)
        subprocess.run(["ssh", cluster_login, f"mkdir -p {cluster_sif_path}"], check=True)
        subprocess.run(["scp", f"{ilci.container_name}.tar", f"{cluster_login}:{cluster_sif_path}/{ilci.container_name}.tar"], check=True)
    elif args.command == "job":
        with open(ilci.base_dir / ".env.base") as f:
            env_vars = dict(line.strip().split('=', 1) for line in f if '=' in line)
        cluster_login = env_vars['CLUSTER_LOGIN']
        cluster_isaaclab_dir = env_vars['CLUSTER_ISAACLAB_DIR']
        apptainer_utils.check_singularity_image_exists(ilci.container_name)
        subprocess.run(["ssh", cluster_login, f"mkdir -p {cluster_isaaclab_dir}"], check=True)
        print("[INFO] Syncing Isaac Lab code...")
        subprocess.run(["rsync", "-rh", "--exclude","*.git*","--filter=:- .dockerignore", f"/{ilci.base_dir}/..", f"{cluster_login}:{cluster_isaaclab_dir}"], check=True)
        print("[INFO] Executing job script...")
        subprocess.run(["ssh", cluster_login, f"cd {cluster_isaaclab_dir} && sbatch {cluster_isaaclab_dir}/docker/cluster/submit_job.sh", cluster_isaaclab_dir, f"{ilci.container_name}"] + args.job_args, check=True)
    else:
        print(f"[Error] Invalid command provided: {mode}", file=sys.stderr)
        print_help()
        sys.exit(1)

if __name__ == "__main__":
    main()