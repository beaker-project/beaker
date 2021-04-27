# Copyright Contributors to the Beaker project.
# SPDX-License-Identifier: GPL-2.0-or-later

import click

from bkr.future.user.delegate.remove import remove
from bkr.future.user.delegate.add import add


@click.group("delegate")
def delegate():
    """Allows the adding or removing of submission delegates of the currently logged in user."""
    pass


delegate.add_command(add)
delegate.add_command(remove)
