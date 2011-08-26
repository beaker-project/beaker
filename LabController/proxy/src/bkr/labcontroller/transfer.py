
import os
import sys
import signal
import logging
import time
import socket
from optparse import OptionParser

from bkr.labcontroller.proxy import Watchdog
from bkr.labcontroller.config import get_conf

from kobo.exceptions import ShutdownException
from kobo.process import daemonize
from kobo.tback import Traceback, set_except_hook
from bkr.log import add_stderr_logger, add_rotating_file_logger

set_except_hook()

def daemon_shutdown(*args, **kwargs):
    raise ShutdownException()

def main_loop(conf=None, foreground=False):
    """infinite daemon loop"""

    # define custom signal handlers
    signal.signal(signal.SIGTERM, daemon_shutdown)
    logger = logging.getLogger("Transfer")
    log_level_string = conf.get("TRANSFER_LOG_LEVEL") or conf["LOG_LEVEL"]
    log_level = getattr(logging, log_level_string.upper(), logging.DEBUG)
    logger.setLevel(log_level)
    log_file = conf["TRANSFER_LOG_FILE"]

    add_rotating_file_logger(logger,
                             log_file,
                             log_level=log_level,
                             format=conf['VERBOSE_LOG_FORMAT'])

    try:
        transfer = Watchdog(conf=conf, logger=logger)
    except Exception, ex:
        sys.stderr.write("Error initializing Watchdog: %s\n" % ex)
        sys.exit(1)

    if foreground:
        add_stderr_logger(transfer.logger)

    time_of_last_check = 0
    while True:
        try:
            now = time.time()
            # Look for logs to transfer every 30 minutes
            if now - time_of_last_check > 1800:
                time_of_last_check = now
                transfer.hub._login()
                transfer.transfer_logs()
            else:
                transfer.logger.debug(80 * '-')
                transfer.sleep()

            # write to stdout / stderr
            sys.stdout.flush()
            sys.stderr.flush()

        except socket.sslerror:
            pass # will try again..

        except (ShutdownException, KeyboardInterrupt):
            # ignore keyboard interrupts and sigterm
            signal.signal(signal.SIGINT, signal.SIG_IGN)
            signal.signal(signal.SIGTERM, signal.SIG_IGN)

            transfer.logger.info('Exiting...')
            break

        except:
            # this is a little extreme: log the exception and continue
            traceback = Traceback()
            transfer.logger.error(traceback.get_traceback())
            transfer.sleep()



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
        pid_file = conf.get("WPID_FILE", "/var/run/beaker-lab-controller/beaker-transfer.pid")

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
