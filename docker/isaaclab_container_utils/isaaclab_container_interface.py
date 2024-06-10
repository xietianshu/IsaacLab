# Copyright (c) 2022-2024, The Isaac Lab Project Developers.
# All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause

import subprocess
import sys


class IsaacLabContainerInterface:
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
        self.load_dot_vars()

    def resolve_image_extension(self):
        self.add_yamls = ["--file", "docker-compose.yaml"]
        self.add_profiles = ["--profile", f"{self.profile}"]
        self.add_envs = ["--env-file", ".env.base"]
        if self.profile != "base":
            self.add_envs += ["--env-file", f".env.{self.profile}"]

    def load_dot_vars(self):
        # Load the dot vars that will be loaded from .env files
        # by reading them in order and overwriting name conflicts,
        # just how docker compose does
        self.dot_vars = {}
        for i in range(1, len(self.add_envs), 2):
            with open(self.base_dir / self.add_envs[i]) as f:
                self.dot_vars.update(dict(line.strip().split("=", 1) for line in f if "=" in line))

    def is_container_running(self):
        status = subprocess.run(
            ["docker", "container", "inspect", "-f", "{{.State.Status}}", self.container_name],
            capture_output=True,
            text=True,
        ).stdout.strip()
        if status != "running":
            print(f"[Error] The '{self.container_name}' container is not running!", file=sys.stderr)
            sys.exit(1)

    def check_image_exists(self):
        result = subprocess.run(["docker", "image", "inspect", self.image_name], capture_output=True, text=True)
        if result.returncode != 0:
            print(f"[Error] The '{self.image_name}' image does not exist!", file=sys.stderr)
            sys.exit(1)
