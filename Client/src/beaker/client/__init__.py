# -*- coding: utf-8 -*-

import os
from kobo.client import ClientCommand

class BeakerCommand(ClientCommand):
    enabled = False
    user_conf = os.path.expanduser('~/.beaker')
    if os.path.exists(user_conf):
        conf_environ_key = user_conf
    else:
        conf_environ_key = "/etc/beaker/client.conf"
