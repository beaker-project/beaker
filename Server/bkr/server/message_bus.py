
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from turbogears import config as tg_config
from bkr.common.message_bus import BeakerBus

import logging
log = logging.getLogger(__name__)

class ServerBeakerBus(BeakerBus):

    _shared_state = {}

    def __init__(self, *args, **kw):
        if not self._shared_state:
            state = dict(topic_exchange=tg_config.get('beaker.qpid_topic_exchange'),
                _broker=tg_config.get('beaker.qpid_broker'),
                stopped = True)
            self._shared_state.update(state)
        self.__dict__.update(self._shared_state)
        super(ServerBeakerBus, self).__init__(*args, **kw)

    def do_krb_auth(self):
        from bkr.common.krb_auth import AuthManager
        if not self.principal:
            self.principal = tg_config.get('identity.krb_auth_qpid_principal')
        if not self.keytab:
            self.keytab = tg_config.get('identity.krb_auth_qpid_keytab')
        self.auth_mgr = AuthManager(primary_principal=self.principal, keytab=self.keytab)
