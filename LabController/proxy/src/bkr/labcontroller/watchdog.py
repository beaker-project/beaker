
import os
import sys
import signal
import logging
import time
import socket
from optparse import OptionParser

from bkr.labcontroller.proxy import Watchdog

import kobo.conf
from kobo.exceptions import ShutdownException
from kobo.process import daemonize
from kobo.tback import Traceback, set_except_hook
from kobo.log import add_stderr_logger, add_rotating_file_logger

VERBOSE_LOG_FORMAT = "%(asctime)s [%(levelname)-8s] {%(process)5d} %(name)s.%(module)s:%(lineno)4d %(message)s"

set_except_hook()


def daemon_shutdown(*args, **kwargs):
    raise ShutdownException()

def main_loop(conf=None, foreground=False):
    """infinite daemon loop"""

    # define custom signal handlers
    signal.signal(signal.SIGTERM, daemon_shutdown)

    config = kobo.conf.PyConfigParser()

    # load default config
    default_config = os.path.abspath(os.path.join(os.path.dirname(__file__), "default.conf"))
    config.load_from_file(default_config)

    logger = logging.getLogger("Watchdog")
    logger.setLevel(logging.DEBUG)
    log_level = logging._levelNames.get(config["LOG_LEVEL"].upper())
    log_file = config["WATCHDOG_LOG_FILE"]
    add_rotating_file_logger(logger,
                             log_file,
                             log_level=log_level,
                             format=VERBOSE_LOG_FORMAT)

    try:
        watchdog = Watchdog(conf=conf, logger=logger)
    except Exception, ex:
        sys.stderr.write("Error initializing Watchdog: %s\n" % ex)
        sys.exit(1)

    if foreground:
        add_stderr_logger(watchdog.logger)

    watchdog.hub._transport.timeout = 120 
    time_of_last_check = 0
    while True:
        try:
            now = time.time()
            # Poll the scheduler for watchdogs
            if now - time_of_last_check > 60:
                time_of_last_check = now
                watchdog.hub._login()
                watchdog.expire_watchdogs()
                watchdog.active_watchdogs()
            if not watchdog.run():
                watchdog.logger.debug(80 * '-')
                watchdog.sleep()

            # FIXME: Check for recipes that match systems under
            #        this lab controller, if so take recipe and provision
            #        system.

            # write to stdout / stderr
            sys.stdout.flush()
            sys.stderr.flush()

        except socket.sslerror:
            pass # try again later
        except (ShutdownException, KeyboardInterrupt):
            # ignore keyboard interrupts and sigterm
            signal.signal(signal.SIGINT, signal.SIG_IGN)
            signal.signal(signal.SIGTERM, signal.SIG_IGN)

            watchdog.logger.info('Exiting...')
            break

        except:
            # this is a little extreme: log the exception and continue
            traceback = Traceback()
            watchdog.logger.error(traceback.get_traceback())
            watchdog.sleep()



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
        pid_file = conf.get("WPID_FILE", "/var/run/beaker-lab-controller/beaker-watchdog.pid")

    if opts.foreground:
        main_loop(conf=conf, foreground=True)
    else:
        daemonize(main_loop, 
                  daemon_pid_file=pid_file,
                  conf=conf, 
                  foreground=False)

if __name__ == '__main__':
    main()
