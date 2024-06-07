import subprocess
import os
import sys

def install_apptainer():
    app_answer = input("[INFO] Required 'apptainer' package could not be found. Would you like to install it via apt? (y/N)")
    if app_answer.lower() == 'y':
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
    if int(docker_version.split('.')[0]) >= 25:
        print(f"[ERROR]: Docker version {docker_version} is not compatible with Apptainer version {apptainer_version}. Exiting.")
        sys.exit(1)
    else:
        print(f"[INFO]: Building singularity with docker version: {docker_version} and Apptainer version: {apptainer_version}.")

def check_singularity_image_exists(image_name):
    CLUSTER_LOGIN = os.getenv("CLUSTER_LOGIN", None)
    if CLUSTER_LOGIN is None:
        print(f"[Error] Environment variable CLUSTER_LOGIN cannot be None", file=sys.stderr)
        sys.exit(1)
    CLUSTER_SIF_PATH = os.getenv("CLUSTER_SIF_PATH", None)
    if CLUSTER_SIF_PATH is None:
        print(f"[Error] Environment variable CLUSTER_SIF_PATH cannot be None", file=sys.stderr)
        sys.exit(1)
    result = subprocess.run(["ssh", CLUSTER_LOGIN, f"[ -f {CLUSTER_SIF_PATH}/{image_name}.tar ]"], capture_output=True, text=True)
    if result.returncode != 0:
        print(f"[Error] The '{image_name}' image does not exist on the remote host {CLUSTER_LOGIN}!", file=sys.stderr)
        sys.exit(1)