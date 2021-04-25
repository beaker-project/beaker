# Copyright Contributors to the Beaker project.
# SPDX-License-Identifier: GPL-2.0-or-later

import click


@click.group("policy")
def policy():
    """Manage Beaker access policy"""
    pass
