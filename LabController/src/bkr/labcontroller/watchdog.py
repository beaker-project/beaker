
import os
import sys
import signal
import logging
import time
import socket
import xmlrpclib
import daemon
from daemon import pidfile
from optparse import OptionParser
from bkr.common.helpers import RepeatTimer
from bkr.labcontroller.proxy import Watchdog
from bkr.labcontroller.config import load_conf, get_conf

from kobo.exceptions import ShutdownException
from kobo.tback import Traceback, set_except_hook
from bkr.log import add_stderr_logger
from bkr.labcontroller.utils import add_rotating_file_logger

set_except_hook()

logger = logging.getLogger(__name__)

def daemon_shutdown(*args, **kwargs):
    raise ShutdownException()

def main_loop(watchdog, conf, foreground=False):
    """infinite daemon loop"""

    # define custom signal handlers
    signal.signal(signal.SIGTERM, daemon_shutdown)

    # set up logging
    log_level_string = conf.get("WATCHDOG_LOG_LEVEL") or conf["LOG_LEVEL"]
    log_level = getattr(logging, log_level_string.upper(), logging.DEBUG)
    logging.getLogger().setLevel(log_level)
    if foreground:
        add_stderr_logger(logging.getLogger(), log_level=log_level)
    else:
        log_file = conf["WATCHDOG_LOG_FILE"]
        add_rotating_file_logger(logging.getLogger(), log_file,
                log_level=log_level, format=conf["VERBOSE_LOG_FORMAT"])

    time_of_last_check = 0
    while True:
        try:
            now = time.time()
            # Poll for watchdogs
            if now - time_of_last_check > conf.get('SLEEP_TIME', 60):
                time_of_last_check = now
                watchdog.hub._login()

                try:
                    expired_watchdogs = watchdog.hub.recipes.tasks.watchdogs('expired')
                except xmlrpclib.Fault:
                    # catch any xmlrpc errors
                    expired_watchdogs = []
                    traceback = Traceback()
                    logger.error(traceback.get_traceback())
                watchdog.expire_watchdogs(expired_watchdogs)

                # Get active watchdogs *after* we finish running
                # expired_watchdogs, depending on the configuration
                # we may have extended the watchdog and its therefore
                # no longer expired!
                try:
                    active_watchdogs = watchdog.hub.recipes.tasks.watchdogs('active')
                except xmlrpclib.Fault:
                    # catch any xmlrpc errors
                    traceback = Traceback()
                    logger.error(traceback.get_traceback())
                    active_watchdogs = []
                watchdog.active_watchdogs(active_watchdogs)

            if not watchdog.run():
                logger.debug(80 * '-')
                watchdog.sleep()
            # FIXME: Check for recipes that match systems under
            #        this lab controller, if so take recipe and provision
            #        system.
            # write to stdout / stderr
            sys.stdout.flush()
            sys.stderr.flush()
        except socket.sslerror:
            traceback = Traceback()
            logger.error(traceback.get_traceback())
        except xmlrpclib.ProtocolError:
            traceback = Traceback()
            logger.error(traceback.get_traceback())
        except (ShutdownException, KeyboardInterrupt):
            # ignore keyboard interrupts and sigterm
            signal.signal(signal.SIGINT, signal.SIG_IGN)
            signal.signal(signal.SIGTERM, signal.SIG_IGN)
            logger.info('Exiting...')
            break

def main():
    parser = OptionParser()
    parser.add_option("-c", "--config", 
                      help="Full path to config file to use")
    parser.add_option("-f", "--foreground", default=False, action="store_true",
                      help="run in foreground (do not spawn a daemon)")
    parser.add_option("-p", "--pid-file",
                      help="specify a pid file")
    (opts, args) = parser.parse_args()
    if opts.config:
        load_conf(opts.config)

    conf = get_conf()
    pid_file = opts.pid_file
    if pid_file is None:
        pid_file = conf.get("WATCHDOG_PID_FILE", "/var/run/beaker-lab-controller/beaker-watchdog.pid")

    try:
        watchdog = Watchdog(conf=conf)
    except Exception, ex:
        sys.stderr.write("Error initializing Watchdog: %s\n" % ex)
        sys.exit(1)

    if opts.foreground:
        main_loop(watchdog, conf, foreground=True)
    else:
        # See BZ#977269
        watchdog.close()
        with daemon.DaemonContext(pidfile=pidfile.TimeoutPIDLockFile(
                pid_file, acquire_timeout=0)):
            main_loop(watchdog, conf, foreground=False)

    print 'exiting program'

if __name__ == '__main__':
    main()
