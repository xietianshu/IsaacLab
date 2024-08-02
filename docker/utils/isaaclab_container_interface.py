# Copyright (c) 2022-2024, The Isaac Lab Project Developers.
# All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause

import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, List, Optional, Union

from utils.statefile import Statefile


class IsaacLabContainerInterface:
    """
    Interface for managing Isaac Lab containers.
    """

    def __init__(
        self,
        dir: Path,
        target: str = "base",
        statefile: Optional[Statefile] = None,
        yamls: Optional[List[str]] = None,
        envs: Optional[List[str]] = None,
        isaacsim_volumes: bool = True,
        isaaclab_volumes: bool = True,
    ):
        """
        Initialize the IsaacLabContainerInterface with the given parameters.

        Args:
            context_dir : The directory for Docker operations.
            statefile : An instance of the Statefile class to manage state variables. If not provided, initializes a Statefile(path=self.dir/.container.yaml).
            target : The target name for the container. Defaults to "base".
            yamls : A list of yamls to extend docker-compose.yaml. They will be extended in the order they are provided.
            envs : A list of envs to extend .env.base. They will be extended in the order they are provided.
            isaacsim_volumes: Whether to inject the isaacsim volumes into the compose network, defined in IsaacLab/docker/cfgs/isaacsim_volumes.yaml. Defaults to True."
            isaaclab_volumes: Whether to inject the isaaclab volumes into the compose network, defined in IsaacLab/docker/cfgs/isaaclab_volumes.yaml. Defaults to True."
        """
        self.dir = dir
        self.compose_cfgs = Path(self.dir / "cfgs")
        if not self.compose_cfgs.is_dir():
            raise FileNotFoundError(f"Required directory {self.compose_cfgs} was not found.")
        if statefile is None:
            self.statefile = Statefile(path=self.dir / ".container.cfg")
        else:
            self.statefile = statefile
        self.target = target
        if self.target == "isaaclab":
            # Silently correct from isaaclab to base,
            # because isaaclab is a commonly passed arg
            # but not a real target
            self.target = "base"
        self.container_name = f"isaac-lab-{self.target}"
        self.image_name = f"isaac-lab-{self.target}:latest"
        self.environ = os.environ
        self.environ.update({"TARGET": self.target})
        self.resolve_compose_cfg(yamls, envs, isaacsim_volumes, isaaclab_volumes)
        self.load_dot_vars()

    def resolve_compose_cfg(
        self,
        yamls: Optional[List[str]] = None,
        envs: Optional[List[str]] = None,
        isaacsim_volumes: bool = True,
        isaaclab_volumes: bool = True,
    ):
        """
        Resolve the compose configuration by setting up YAML files and environment files for the Docker compose command.

        Args:
            yamls: A list of yamls to extend base.yaml. They will be extended in the order they are provided.
            envs: A list of envs to extend .env.base. They will be extended in the order they are provided.
            isaacsim_volumes: Whether to inject the isaacsim volumes into the compose network. Defaults to True.
            isaaclab_volumes: Whether to inject the isaaclab volumes into the compose network. Defaults to True.
        """
        self.yamls = []
        # Search cfgs for the 'target.yaml'. However, if it does not exist
        # there let it be supplied as an abs path by --files args
        if self.search_compose_cfgs(f"{self.target}.yaml", required=False):
            self.yamls.append(f"{self.target}.yaml")

        self.env_files = []
        root_env = Path(self.dir / ".env")
        # If there is a .env file in self.dir, load its values into the environ
        if os.path.isfile(root_env):
            self.env_files.append(root_env)

        if yamls is not None:
            self.yamls += yamls

        if envs is not None:
            self.env_files += envs

        if isaacsim_volumes:
            self.yamls.append("isaacsim_volumes.yaml")
        if isaaclab_volumes:
            self.yamls.append("isaaclab_volumes.yaml")

    @property
    def dot_vars(self):
        self.load_dot_vars()
        return self._dot_vars

    def load_dot_vars(self):
        """
        Load environment variables from .env files into a dictionary.

        The environment variables are read in order and overwritten if there are name conflicts,
        mimicking the behavior of Docker compose.
        """
        self._dot_vars: Dict[str, Any] = {}
        abs_env_files = [self.search_compose_cfgs(file) for file in self.env_files]
        for i in range(len(abs_env_files)):
            with open(str(self.dir / abs_env_files[i])) as f:
                self._dot_vars.update(dict(line.strip().split("=", 1) for line in f if "=" in line))

    def add_env_files(self) -> List[str]:
        """
        Put self.env_files into a state suitable for the docker compose CLI, with '--env-file' between
        every argument

        Returns:
            [str]: A list of strings, with '--env-file' first and then interpolated between the strings of
                   self.env_files
        """
        abs_env_files = [self.search_compose_cfgs(file) for file in self.env_files]
        return [abs_env_files[int(i / 2)] if i % 2 == 1 else "--env-file" for i in range(len(abs_env_files) * 2)]

    def add_yamls(self) -> List[str]:
        """
        Put self.yamls into a state suitable for the docker compose CLI, with '--file' between
        every argument

        Returns:
            [str]: A list of strings, with '--file' first and then interpolated between the strings of
                   self.yamls
        """
        abs_yaml_files = [self.search_compose_cfgs(file) for file in self.yamls]
        return [abs_yaml_files[int(i / 2)] if i % 2 == 1 else "--file" for i in range(len(abs_yaml_files) * 2)]

    def is_container_running(self) -> bool:
        """
        Check if the container is running.

        If the container is not running, return False.

        Returns:
            bool: True if the container is running, False otherwise.
        """
        status = subprocess.run(
            ["docker", "container", "inspect", "-f", "{{.State.Status}}", self.container_name],
            capture_output=True,
            text=True,
            check=False,
        ).stdout.strip()
        return status == "running"

    def does_image_exist(self) -> bool:
        """
        Check if the Docker image exists.

        If the image does not exist, return False.

        Returns:
            bool: True if the image exists, False otherwise.
        """
        result = subprocess.run(
            ["docker", "image", "inspect", self.image_name], capture_output=True, text=True, check=False
        )
        return result.returncode == 0

    def start(self):
        """
        Build and start the Docker container using the Docker compose 'up' command.
        """
        print(f"[INFO] Building the docker image and starting the container {self.container_name} in the background...")
        print(
            ["docker", "compose"]
            + self.add_yamls()
            + self.add_env_files()
            + ["up", "--detach", "--build", "--remove-orphans"]
        )
        subprocess.run(
            ["docker", "compose"]
            + self.add_yamls()
            + self.add_env_files()
            + ["up", "--detach", "--build", "--remove-orphans"],
            check=False,
            cwd=str(self.dir),
            env=self.environ,
        )

    def build(self):
        """
        Build the Docker container using the Docker compose 'build' command.
        """
        print(f"[INFO] Building the docker image {self.image_name}...")
        subprocess.run(
            ["docker", "compose"] + self.add_yamls() + self.add_env_files() + ["build"],
            check=False,
            cwd=str(self.dir),
            env=self.environ,
        )

    def enter(self):
        """
        Enter the running container by executing a bash shell.

        Raises:
            RuntimeError: If the container is not running.
        """
        if self.is_container_running():
            subprocess.run([
                "docker",
                "exec",
                "--interactive",
                "--tty",
                "-e",
                f"DISPLAY={os.environ['DISPLAY']}",
                f"{self.container_name}",
                "bash",
            ])
        else:
            raise RuntimeError(f"The container '{self.container_name}' is not running")

    def stop(self):
        """
        Stop the running container using the Docker compose command.

        Raises:
            RuntimeError: If the container is not running.
        """
        if self.is_container_running():
            print(f"[INFO] Stopping the launched docker container {self.container_name}...")
            subprocess.run(
                ["docker", "compose"] + self.add_yamls() + self.add_env_files() + ["down"],
                check=False,
                cwd=str(self.dir),
                env=self.environ,
            )
        else:
            raise RuntimeError(f"Can't stop container '{self.container_name}' as it is not running.")

    def copy(self, output_dir: Optional[Path] = None):
        """
        Copy artifacts from the running container to the host machine.

        Args:
            output_dir: The directory to copy the artifacts to. Defaults to self.dir.

        Raises:
            RuntimeError: If the container is not running.
        """
        if self.is_container_running():
            print(f"[INFO] Copying artifacts from the 'isaac-lab-{self.container_name}' container...")
            if output_dir is None:
                output_dir = self.dir
            output_dir = output_dir.joinpath("artifacts")
            if not output_dir.is_dir():
                output_dir.mkdir()
            artifacts = {
                Path(self.dot_vars["DOCKER_ISAACLAB_PATH"]).joinpath("logs"): output_dir.joinpath("logs"),
                Path(self.dot_vars["DOCKER_ISAACLAB_PATH"]).joinpath("docs/_build"): output_dir.joinpath("docs"),
                Path(self.dot_vars["DOCKER_ISAACLAB_PATH"]).joinpath("data_storage"): output_dir.joinpath(
                    "data_storage"
                ),
            }
            for container_path, host_path in artifacts.items():
                print(f"\t -{container_path} -> {host_path}")
            for path in artifacts.values():
                shutil.rmtree(str(path), ignore_errors=True)
            for container_path, host_path in artifacts.items():
                subprocess.run(
                    [
                        "docker",
                        "cp",
                        f"isaac-lab-{self.target}:{container_path}/",
                        f"{host_path}",
                    ],
                    check=False,
                )
            print("\n[INFO] Finished copying the artifacts from the container.")
        else:
            raise RuntimeError(f"The container '{self.container_name}' is not running")

    def config(self, output_yaml: Optional[Path] = None):
        """
        Generate a docker-compose.yaml from the passed yamls, .envs, and either print to the
        terminal or create a yaml at output_yaml

        Args:
            output_yaml: The absolute path of the yaml file to write the output to, if any. Defaults
            to None, and simply prints to the terminal
        """
        print("[INFO] Configuring the passed options into a yaml...")
        if output_yaml is not None:
            output = ["--output", str(output_yaml)]
        else:
            output = []
        subprocess.run(
            ["docker", "compose"] + self.add_yamls() + self.add_env_files() + ["config"] + output,
            check=False,
            cwd=str(self.dir),
            env=self.environ,
        )

    def search_compose_cfgs(self, file, required=True) -> Union[Path, None]:
        # Return if path to file is
        # absolute and file exists
        if os.path.isabs(file):
            if os.path.isfile(file):
                return Path(file)
            if required:
                raise FileNotFoundError(
                    "The absolute path to required file {file} was passed, but the file does not exist"
                )

        # Brute force search self.compose_cfgs if the hint path failed
        for root, _, files in os.walk(self.compose_cfgs):
            if file in files:
                return Path(os.path.abspath(os.path.join(root, file)))

        if required:
            raise FileNotFoundError(
                f"Couldn't find required {file} under the compose_cfgs directory {self.compose_cfgs}"
            )
        return None