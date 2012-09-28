from bkr.server.bexceptions import BeakerException
from bkr.server.recipetasks import RecipeTasks
import bkr.server.model as bkr_model
from bkr.server.model import TaskBase, LabController
from turbogears import config as tg_config
from bkr.common.message_bus import BeakerBus
from bkr.common.helpers import BkrThreadPool
from time import sleep
from threading import Thread
import Queue
import logging
log = logging.getLogger(__name__)

try:
    from qpid.messaging import *
    from qpid import datatypes
except ImportError, e:
    pass

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
