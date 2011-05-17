from bkr.server.test.stub_cobbler import StubCobbler, StubCobblerThread
from bkr.server.test.beah_dummy import BeahDummy
import logging

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)
log.addHandler(logging.StreamHandler())

class StubCobblerLoadThread(StubCobblerThread):

    def __init__(self, *args, **kw):
        super(StubCobblerLoadThread, self).__init__(cobbler=StubCobblerLoad())


class StubCobblerLoad(StubCobbler):

    def __init__(self, *args, **kw):
        super(StubCobblerLoad, self).__init__(*args, **kw)

    def background_power_system(self, d, token):
        #log.info('background_power_system')
        task_id =  super(StubCobblerLoad, self).background_power_system(d, token)
        if d['power'] == 'reboot':
            self.reboot()

        # FIXME if 'Wait' is True in auto_aciton_provision we need to return
        # this task_id after threading beah dummy
        #import pdb;pdb.set_trace()
        return task_id


    def reboot(self):
        beah = BeahDummy(self.current_system)
        beah.start()
        #beah.run(self.current_system)

