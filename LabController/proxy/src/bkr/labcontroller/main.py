
import os
import time
import sys
import signal
from optparse import OptionParser
from threading import Thread

from datetime import datetime

import SocketServer
import DocXMLRPCServer
import socket

from bkr.labcontroller.proxy import Proxy, RepeatTimer
from bkr.labcontroller.config import get_conf
from bkr.labcontroller.utils import add_rotating_file_logger
from kobo.exceptions import ShutdownException
from kobo.process import daemonize
from kobo.tback import Traceback, set_except_hook
from bkr.log import add_stderr_logger
import logging
logger = logging.getLogger(__name__)

set_except_hook()

class XMLRPCRequestHandler(DocXMLRPCServer.DocXMLRPCRequestHandler):
    rpc_paths = ('/', '/RPC2', '/server')
    def do_POST(self):
        """
        This is a replacement for the real do_POST, to work around RHBZ#789790.
        """

        # Check that the path is legal
        if not self.is_rpc_path_valid():
            self.report_404()
            return

        try:
            data = self.rfile.read(int(self.headers["content-length"]))
            if len(data) < int(self.headers["content-length"]):
                self.connection.shutdown(1)
                return

            # In previous versions of SimpleXMLRPCServer, _dispatch
            # could be overridden in this class, instead of in
            # SimpleXMLRPCDispatcher. To maintain backwards compatibility,
            # check to see if a subclass implements _dispatch and dispatch
            # using that method if present.
            response = self.server._marshaled_dispatch(
                    data, getattr(self, '_dispatch', None)
                )
        except Exception, e: # This should only happen if the module is buggy
            # internal error, report as HTTP server error
            self.send_response(500)

            # Send information about the exception if requested
            if hasattr(self.server, '_send_traceback_header') and \
                    self.server._send_traceback_header:
                self.send_header("X-exception", str(e))
                self.send_header("X-traceback", traceback.format_exc())

            self.end_headers()
        else:
            # got a valid XML RPC response
            self.send_response(200)
            self.send_header("Content-type", "text/xml")
            self.send_header("Content-length", str(len(response)))
            self.end_headers()
            self.wfile.write(response)

            # shut down the connection
            self.wfile.flush()
            self.connection.shutdown(1)

            
class ForkingXMLRPCServer (SocketServer.ForkingMixIn,
                           DocXMLRPCServer.DocXMLRPCServer):
    allow_reuse_address = True

    def __init__(self, *args, **kwargs):
        DocXMLRPCServer.DocXMLRPCServer.__init__(self, *args,
                requestHandler=XMLRPCRequestHandler, **kwargs)

    def _dispatch(self, method, params):
        """ Custom _dispatch so we can log time used to execute method.
        """
        start = datetime.utcnow()
        try:
            result=DocXMLRPCServer.DocXMLRPCServer._dispatch(self, method, params)
        except:
            logger.debug('Time: %s %s %s', datetime.utcnow() - start, str(method), str(params)[0:50])
            raise
        logger.debug('Time: %s %s %s', datetime.utcnow() - start, str(method), str(params)[0:50])
        return result
        

def daemon_shutdown(*args, **kwargs):
    login.stop()
    raise ShutdownException()

def main_loop(conf=None, foreground=False):
    """infinite daemon loop"""

    # define custom signal handlers
    signal.signal(signal.SIGTERM, daemon_shutdown)

    # set up logging
    log_level_string = conf["LOG_LEVEL"]
    log_level = getattr(logging, log_level_string.upper(), logging.DEBUG)
    logging.getLogger().setLevel(log_level)
    if foreground:
        add_stderr_logger(logging.getLogger(), log_level=log_level)
    else:
        log_file = conf["LOG_FILE"]
        add_rotating_file_logger(logging.getLogger(), log_file,
                log_level=log_level, format=conf["VERBOSE_LOG_FORMAT"])

    # initialize Proxy
    try:
        proxy = Proxy(conf=conf)
    except Exception, ex:
        sys.stderr.write("Error initializing Proxy: %s\n" % ex)
        sys.exit(1)

    login = RepeatTimer(conf['RENEW_SESSION_INTERVAL'], proxy.hub._login,
        stop_on_exception=False)
    login.daemon = True
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

    conf = get_conf()
    config = opts.config
    if config is not None:
        conf.load_from_file(config)

    pid_file = opts.pid_file
    if pid_file is None:
        pid_file = conf.get("PROXY_PID_FILE", "/var/run/beaker-lab-controller/beaker-proxy.pid")
     
    if opts.foreground:
        main_loop(conf=conf, foreground=True)
    else:
        daemonize(main_loop, 
                  daemon_pid_file=pid_file,
                  daemon_start_dir="/",
                  conf=conf, 
                  foreground=False)

if __name__ == '__main__':
    main()
