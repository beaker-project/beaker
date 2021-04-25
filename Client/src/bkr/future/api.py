# Copyright Contributors to the Beaker project.
# SPDX-License-Identifier: GPL-2.0-or-later

import click

from bkr.common.api import BeakerAPI


class ClientBeakerAPI(BeakerAPI):
    ...


# This will disable original pass_obj behavior
# because ctx.obj ref will be replaced with API object
pass_api = click.make_pass_decorator(ClientBeakerAPI, ensure=True)
