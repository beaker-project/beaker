
import os
import sys
import signal
from optparse import OptionParser

import SocketServer
import SimpleXMLRPCServer

from beaker.labcontroller.proxy import Proxy

import kobo.conf
from kobo.exceptions import ShutdownException
from kobo.process import daemonize
from kobo.tback import Traceback, set_except_hook
from kobo.log import add_stderr_logger
set_except_hook()

proxy = None

class myHandler(SimpleXMLRPCServer.SimpleXMLRPCRequestHandler):
    def do_POST(self):
        global proxy
        proxy.clientIP, proxy.clientPort = self.client_address
        SimpleXMLRPCServer.SimpleXMLRPCRequestHandler.do_POST(self)

class ForkingXMLRPCServer (SocketServer.ForkingMixIn,
                           SimpleXMLRPCServer.SimpleXMLRPCServer):
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

    server = ForkingXMLRPCServer(("localhost", 8000),myHandler)
    server.register_instance(proxy)
    server.serve_forever()

def main():
    parser = OptionParser()
    parser.add_option("-c", "--config", 
                      help="Full path to config file to use")
    parser.add_option("-f", "--foreground", default=False, action="store_true",
                      help="run in foreground (do not spawn a daemon)")
    parser.add_option("-k", "--kill", default=False, action="store_true",
                      help="kill the daemon")
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
        pid_file = conf.get("PID_FILE", "/var/run/beaker-proxy.pid")

    if opts.kill:
        pid = open(pid_file, "r").read()
        os.kill(int(pid), 15)
        sys.exit(0)

    if opts.foreground:
        main_loop(conf=conf, foreground=True)
    else:
        daemonize(main_loop, 
                  daemon_pid_file=pid_file, 
                  conf=conf, 
                  foreground=False)

if __name__ == '__main__':
    main()
