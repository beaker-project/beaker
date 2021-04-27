# Copyright Contributors to the Beaker project.
# SPDX-License-Identifier: GPL-2.0-or-later

import click

from bkr.future.user.delegate import delegate
from bkr.future.user.remove import remove
from bkr.future.user.update import update


@click.group("user")
def user():
    """Manage Beaker users"""
    pass


user.add_command(remove)
user.add_command(delegate)
user.add_command(update)
