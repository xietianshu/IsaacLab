# Copyright (c) 2022-2024, The Isaac Lab Project Developers.
# All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause

import yaml
from pathlib import Path
from typing import Any


def load_yaml_file(path: Path) -> dict[str, Any]:
    """
    Load the contents of a YAML file.

    If the file exists, read its contents and return them as a dictionary.
    If the file does not exist, create an empty file and return an empty dictionary.

    Args:
        statefile (Path): The path to the YAML file.

    Returns:
        dict: The contents of the YAML file as a dictionary.
    """
    if path.exists():
        with open(path) as file:
            return yaml.safe_load(file) or {}
    else:
        path.touch()
        return {}


def save_yaml_file(path: Path, data: dict[str, Any]) -> None:
    """
    Save a dictionary to a YAML file.

    Args:
        path (Path): The path to the YAML file.
        data (dict): The data to be saved to the YAML file.
    """
    with open(path, "w") as file:
        yaml.safe_dump(data, file)


class Statefile:
    """
    A class to manage state variables stored in a YAML file.

    Attributes:
        statefile (Path): The path to the YAML file.
    """

    def __init__(self, path: Path):
        """
        Initialize the Statefile object with the path to the YAML file.

        Args:
            path (Path): The path to the YAML file.
        """
        self.path = path

    def set_variable(self, key: str, value: Any) -> None:
        """
        Set a variable in the YAML file.

        Args:
            key (str): The key of the variable to be set.
            value (any): The value of the variable to be set.
        """
        data = load_yaml_file(self.path)
        data[key] = value
        save_yaml_file(self.path, data)

    def load_variable(self, key: str) -> Any:
        """
        Load a variable from the YAML file.

        Args:
            key (str): The key of the variable to be loaded.

        Returns:
            any: The value of the variable, or None if the key does not exist.
        """
        data = load_yaml_file(self.path)
        return data.get(key)

    def delete_variable(self, key: str) -> None:
        """
        Delete a variable from the YAML file.

        Args:
            key (str): The key of the variable to be deleted.
        """
        data = load_yaml_file(self.path)
        if key in data:
            del data[key]
        save_yaml_file(self.path, data)
