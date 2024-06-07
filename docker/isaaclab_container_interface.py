import sys
import os
import subprocess
import shutil

class IsaacLabContainerInterface(object):
    def __init__(self, base_dir, profile=None, statefile=None):
        self.base_dir = base_dir
        self.profile = profile or "base"
        if self.profile == "isaaclab":
            # Silently correct from isaaclab to base,
            # because isaaclab is a commonly passed arg
            # but not a real profile
            self.profile = "base"
        self.container_name = f"isaac-lab-{self.profile}"
        self.image_name = f"isaac-lab-{self.profile}:latest"
        self.statefile = statefile
        self.resolve_image_extension()

    def resolve_image_extension(self):
        self.add_yamls = ["--file", "docker-compose.yaml"]
        self.add_profiles = ["--profile", f"{self.profile}"]
        self.add_envs = ["--env-file", ".env.base"]
        if self.profile != "base":
            self.add_envs += ["--env-file", f".env.{self.profile}"]

    def is_container_running(self):
        status = subprocess.run(["docker", "container", "inspect", "-f", "{{.State.Status}}", self.container_name], capture_output=True, text=True).stdout.strip()
        if status != "running":
            print(f"[Error] The '{self.container_name}' container is not running!", file=sys.stderr)
            sys.exit(1)

    def check_image_exists(self):
        result = subprocess.run(["docker", "image", "inspect", self.image_name], capture_output=True, text=True)
        if result.returncode != 0:
            print(f"[Error] The '{self.image_name}' image does not exist!", file=sys.stderr)
            sys.exit(1)

    def copy_artifacts(self):
        self.is_container_running()
        print(f"[INFO] Copying artifacts from the 'isaac-lab-{self.profile}' container...")
        artifacts = {
            "logs": "logs",
            "docs/_build": "docs/_build",
            "data_storage": "data_storage"
        }
        for container_path, host_path in artifacts.items():
            print(f"\t - /workspace/isaaclab/{container_path} -> {self.base_dir}/artifacts/{host_path}")
        os.chdir(self.base_dir)
        for path in artifacts.values():
            shutil.rmtree(self.base_dir / f"artifacts/{path}", ignore_errors=True)
        (self.base_dir / "artifacts/docs").mkdir(parents=True, exist_ok=True)
        for container_path, host_path in artifacts.items():
            subprocess.run(["docker", "cp", f"isaac-lab-{self.profile}:/workspace/isaaclab/{container_path}", f"./artifacts/{host_path}"], check=True)
        print("\n[INFO] Finished copying the artifacts from the container.")
