
import os
import sys
import signal
from optparse import OptionParser

import SocketServer
import DocXMLRPCServer

from beaker.labcontroller.proxy import Proxy

import kobo.conf
from kobo.exceptions import ShutdownException
from kobo.process import daemonize
from kobo.tback import Traceback, set_except_hook
from kobo.log import add_stderr_logger
set_except_hook()

proxy = None

class myHandler(DocXMLRPCServer.DocXMLRPCRequestHandler):
    def do_POST(self):
        global proxy
        proxy.clientIP, proxy.clientPort = self.client_address
        DocXMLRPCServer.DocXMLRPCRequestHandler.do_POST(self)

class ForkingXMLRPCServer (SocketServer.ForkingMixIn,
                           DocXMLRPCServer.DocXMLRPCServer):
    pass


def daemon_shutdown(*args, **kwargs):
    raise ShutdownException()

def main_loop(conf=None, foreground=False):
    """infinite daemon loop"""

    global proxy

    # define custom signal handlers
    signal.signal(signal.SIGTERM, daemon_shutdown)

    # initialize Proxy
    try:
        proxy = Proxy(conf=conf)
    except Exception, ex:
        sys.stderr.write("Error initializing Proxy: %s\n" % ex)
        sys.exit(1)


    server = ForkingXMLRPCServer(("", 8000),myHandler)
    server.register_instance(proxy)
    server.serve_forever()

def main():
    parser = OptionParser()
    parser.add_option("-c", "--config", 
                      help="Full path to config file to use")
    parser.add_option("-f", "--foreground", default=False, action="store_true",
                      help="run in foreground (do not spawn a daemon)")
    (opts, args) = parser.parse_args()

    conf = kobo.conf.PyConfigParser()
    config = opts.config
    if config is None:
        config = "/etc/beaker/proxy.conf"

    conf.load_from_file(config)
    
    if opts.foreground:
        main_loop(conf=conf, foreground=True)
    else:
        daemonize(main_loop, 
                  conf=conf, 
                  foreground=False)

if __name__ == '__main__':
    main()
