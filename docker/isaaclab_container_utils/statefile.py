# Copyright (c) 2022-2024, The Isaac Lab Project Developers.
# All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause

import configparser
from configparser import ConfigParser
from pathlib import Path
from typing import Any


def load_cfg_file(path: Path) -> ConfigParser:
    """
    Load the contents of a config file.

    If the file exists, read its contents and return them as a dictionary.
    If the file does not exist, create an empty file and return an empty dictionary.

    Args:
        statefile (Path): The path to the config file.

    Returns:
        dict: The contents of the config file as a dictionary.
    """
    cfg = ConfigParser()
    cfg.read(path)
    return cfg


def save_cfg_file(path: Path, cfg: ConfigParser) -> None:
    """
    Save a dictionary to a config file.

    Args:
        path (Path): The path to the config file.
        data (dict): The data to be saved to the config file.
    """
    with open(path, "w+") as file:
        cfg.write(file)


class Statefile:
    """
    A class to manage state variables stored in a cfg file.

    Attributes:
        statefile (Path): The path to the cfg file.
    """

    def __init__(self, path: Path, namespace: str | None = None):
        """
        Initialize the Statefile object with the path to the cfg file.

        Args:
            path (Path): The path to the cfg file.
            namespace (str): Namespace a section of the cfg.
            Defaults to None, and all member functions will have
            to specify section or else set Statefile.namespace directly.
            .
        """
        self.path = path
        self.namespace = namespace

    def set_variable(self, key: str, value: Any, section: str | None = None) -> None:
        """
        Set a variable in the cfg file.

        Args:
            key (str): The key of the variable to be set.
            value (any): The value of the variable to be set.
            section (str): section of the cfg. Defaults to the Statefile.namespace
        """
        cfg = load_cfg_file(self.path)
        if section is None:
            if self.namespace is None:
                raise configparser.Error("No section specified")
            section = self.namespace
        if section not in cfg.sections():
            cfg.add_section(section)
        cfg.set(section, key, value)
        save_cfg_file(self.path, cfg)

    def load_variable(self, key: str, section: str | None = None) -> Any:
        """
        Load a variable from the cfg file.

        Args:
            key (str): The key of the variable to be loaded.
            section (str): section of the cfg. Defaults to the Statefile.namespace

        Returns:
            any: The value of the variable, or None if the key does not exist.
        """

        cfg = load_cfg_file(self.path)
        if section is None:
            if self.namespace is None:
                raise configparser.Error("No section specified")
            section = self.namespace
        return cfg.get(section, key, fallback=None)

    def delete_variable(self, key: str, section: str | None = None) -> None:
        """
        Delete a variable from the cfg file.

        Args:
            key (str): The key of the variable to be deleted.
            section (str): section of the cfg. Defaults to the Statefile.namespace
        """
        cfg = load_cfg_file(self.path)
        if section is None:
            if self.namespace is None:
                raise configparser.Error("No section specified")
            section = self.namespace
        if section not in cfg.sections():
            raise configparser.NoSectionError(f"Section {section} does not exist in {self.path}")
        if cfg.has_option(section, key):
            cfg.remove_option(section, key)
        else:
            raise configparser.NoOptionError(option=key, section=section)
        save_cfg_file(self.path, cfg)
