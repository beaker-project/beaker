# -*- coding: utf-8 -*-

import os
from kobo.client import ClientCommand

class BeakerCommand(ClientCommand):
    enabled = False
    conf_environ_key = 'beaker_config'
    user_conf = os.path.expanduser('~/.beaker')
    if os.path.exists(user_conf):
        conf = user_conf
    else:
        conf = "/etc/beaker/client.conf"
    os.environ['beaker_config'] = conf
