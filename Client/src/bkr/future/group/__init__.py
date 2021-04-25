# Copyright Contributors to the Beaker project.
# SPDX-License-Identifier: GPL-2.0-or-later

import click

from bkr.future.group.create import create
from bkr.future.group.list_groups import list_groups
from bkr.future.group.members import members
from bkr.future.group.modify import modify


@click.group("group")
def group():
    """Manage Beaker groups"""
    pass


group.add_command(create)
group.add_command(list_groups)
group.add_command(members)
group.add_command(modify)
