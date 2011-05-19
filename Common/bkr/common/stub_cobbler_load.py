from bkr.common.stub_cobbler import StubCobbler, StubCobblerThread
from bkr.common.beah_dummy import BeahDummy
import logging
from socket import gethostname

log = logging.getLogger(__name__)

class StubCobblerLoadThread(StubCobblerThread):

    def __init__(self, *args, **kw):
        super(StubCobblerLoadThread, self).__init__(cobbler=StubCobblerLoad(), *args, **kw)


class StubCobblerLoad(StubCobbler):

    _hostname = gethostname()

    def __init__(self, *args, **kw):
        super(StubCobblerLoad, self).__init__(*args, **kw)

    def background_power_system(self, d, token):
        task_id =  super(StubCobblerLoad, self).background_power_system(d, token)
        if d['power'] == 'reboot':
            self.reboot()
        log.debug('Returning %s from background_power_system' % task_id)
        return task_id

    def reboot(self):
        beah = BeahDummy(self.current_system)
        log.info('Rebooting system')
        beah.start()

def main():
    stub_cobbler_thread = StubCobblerThread(addr=gethostname())
    stub_cobbler_thread.start()

