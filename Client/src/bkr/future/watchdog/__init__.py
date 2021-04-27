# Copyright Contributors to the Beaker project.
# SPDX-License-Identifier: GPL-2.0-or-later

import click

from bkr.future.watchdog.extend import extend
from bkr.future.watchdog.list_watchdog import list_watchdog
from bkr.future.watchdog.set_watchdog import set_watchdog


@click.group("watchdog")
def watchdog():
    """Manage Beaker watchdog"""
    pass


watchdog.add_command(extend)
watchdog.add_command(list_watchdog)
watchdog.add_command(set_watchdog)
