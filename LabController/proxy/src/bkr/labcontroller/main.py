
import os
import time
import sys
import signal
from optparse import OptionParser
from threading import Thread

import SocketServer
import DocXMLRPCServer
import socket

from bkr.labcontroller.proxy import Proxy

import kobo.conf
from kobo.exceptions import ShutdownException
from kobo.process import daemonize
from kobo.tback import Traceback, set_except_hook
from kobo.log import add_stderr_logger
set_except_hook()

class Authenticate(Thread):
    def __init__ (self,proxy):
      Thread.__init__(self)
      self.proxy = proxy
      self.proxy.hub._transport.timeout = 120
      self.__serving = False

    def run(self):
        self.__serving = True
        time_of_last_check = 0
        while self.__serving:
            # every minute check that we are logged in.
            now = time.time()
            if now - time_of_last_check > 60:
                time_of_last_check = now
                try:
                    self.proxy.hub._login(verbose=self.proxy.hub._conf.get("DEBUG_XMLRPC"))
                except KeyboardInterrupt:
                    raise
                except socket.sslerror:
                    pass  #try again later 
                except Exception, e:
                    raise
            time.sleep(1)

    def stop(self):
        """Stops the thread"""
        self.__serving = False
            
class ForkingXMLRPCServer (SocketServer.ForkingMixIn,
                           DocXMLRPCServer.DocXMLRPCServer):
    allow_reuse_address = True


def daemon_shutdown(*args, **kwargs):
    login.stop()
    raise ShutdownException()

def main_loop(conf=None, foreground=False):
    """infinite daemon loop"""

    # define custom signal handlers
    signal.signal(signal.SIGTERM, daemon_shutdown)

    # initialize Proxy
    try:
        proxy = Proxy(conf=conf)
    except Exception, ex:
        sys.stderr.write("Error initializing Proxy: %s\n" % ex)
        sys.exit(1)

    login = Authenticate(proxy)
    login.start()
    server = ForkingXMLRPCServer(("", 8000))
    server.register_instance(proxy)
    try:
        server.serve_forever()
    except (ShutdownException, KeyboardInterrupt):
        login.stop()
        # ignore keyboard interrupts and sigterm
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        signal.signal(signal.SIGTERM, signal.SIG_IGN)


def main():
    parser = OptionParser()
    parser.add_option("-c", "--config", 
                      help="Full path to config file to use")
    parser.add_option("-f", "--foreground", default=False, action="store_true",
                      help="run in foreground (do not spawn a daemon)")
    parser.add_option("-p", "--pid-file",
                      help="specify a pid file")
    (opts, args) = parser.parse_args()

    conf = kobo.conf.PyConfigParser()
    config = opts.config
    if config is None:
        config = "/etc/beaker/proxy.conf"

    conf.load_from_file(config)

    pid_file = opts.pid_file
    if pid_file is None:
        pid_file = conf.get("PID_FILE", "/var/run/beaker-lab-controller/beaker-proxy.pid")
    
    if opts.foreground:
        main_loop(conf=conf, foreground=True)
    else:
        daemonize(main_loop, 
                  daemon_pid_file=pid_file,
                  conf=conf, 
                  foreground=False)

if __name__ == '__main__':
    main()
