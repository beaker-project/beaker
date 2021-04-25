# Copyright Contributors to the Beaker project.
# SPDX-License-Identifier: GPL-2.0-or-later

import os
import sys
from typing import Optional

from bkr.common.pyconfig import PyConfigParser


def get_user_config() -> Optional[str]:
    """Return path to user config if exists."""
    user_config_file: Optional[str] = os.environ.get("BEAKER_CLIENT_CONF", None)

    if not user_config_file:
        user_conf: str = os.path.expanduser("~/.beaker_client/config")
        old_conf: str = os.path.expanduser("~/.beaker")
        if os.path.exists(user_conf):
            user_config_file = user_conf
        elif os.path.exists(old_conf):
            user_config_file = old_conf
            sys.stderr.write(
                f"{old_conf} is deprecated for config, please use {user_conf} instead\n"
            )
    return user_config_file


def get_system_config() -> Optional[str]:
    """Return path to system config if exists."""
    system_config_file: Optional[str] = None
    if os.path.exists("/etc/beaker/client.conf"):
        system_config_file = "/etc/beaker/client.conf"
    return system_config_file


def read_configurations() -> PyConfigParser:
    config: PyConfigParser = PyConfigParser()

    system_conf: str = get_system_config()
    if system_conf:
        config.load_from_file(system_conf)

    user_conf: str = get_user_config()
    if user_conf:
        config.load_from_file(user_conf)

    return config


def read_user_override(user_configuration: dict) -> PyConfigParser:
    base_configuration: PyConfigParser = read_configurations()
    base_configuration.load_from_dict(user_configuration)

    return base_configuration
