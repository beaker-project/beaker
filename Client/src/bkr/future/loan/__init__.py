# Copyright Contributors to the Beaker project.
# SPDX-License-Identifier: GPL-2.0-or-later

import click

from bkr.future.loan.grant import grant
from bkr.future.loan.request import request
from bkr.future.loan.return_grant import return_grant


@click.group("loan")
def loan():
    """Manage Beaker loans"""
    pass


loan.add_command(grant)
loan.add_command(request)
loan.add_command(return_grant)
