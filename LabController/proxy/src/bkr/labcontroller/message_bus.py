from qpid.messaging import *
from qpid.log import enable, DEBUG, WARN, ERROR
from qpid import datatypes
enable("qpid.messaging", ERROR)
import ConfigParser, os
from bkr.common.message_bus import BeakerBus

class LabBeakerBus(BeakerBus):


    def __init__(self, *args, **kw):
        super(LabBeakerBus,self).__init__(*args, **kw)
        

    def run(self):
        pass

    class SendHandlers(BeakerBus.SendHandlers):
        pass


    class ListenHandlers(BeakerBus.ListenHandlers):
        pass    

