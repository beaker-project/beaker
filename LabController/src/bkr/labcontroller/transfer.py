
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os
import sys
import signal
import logging
import time
import socket
import daemon
from daemon import pidfile
from optparse import OptionParser
from bkr.labcontroller.proxy import LogArchiver
from bkr.labcontroller.config import get_conf, load_conf
from bkr.labcontroller.exceptions import ShutdownException
from bkr.log import log_to_stream, log_to_syslog

logger = logging.getLogger(__name__)

def daemon_shutdown(*args, **kwargs):
    raise ShutdownException()

def main_loop(logarchiver, conf=None):
    """infinite daemon loop"""

    # define custom signal handlers
    signal.signal(signal.SIGTERM, daemon_shutdown)

    while True:
        try:
            # Look for logs to transfer if none transfered then sleep
            if not logarchiver.transfer_logs():
                logarchiver.sleep()

            # write to stdout / stderr
            sys.stdout.flush()
            sys.stderr.flush()

        except socket.sslerror:
            pass # will try again..

        except (ShutdownException, KeyboardInterrupt):
            # ignore keyboard interrupts and sigterm
            signal.signal(signal.SIGINT, signal.SIG_IGN)
            signal.signal(signal.SIGTERM, signal.SIG_IGN)

            logger.info('Exiting...')
            break

        except:
            # this is a little extreme: log the exception and continue
            logger.exception('Error in main loop')
            logarchiver.sleep()



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
    logging.getLogger().setLevel(logging.DEBUG)

    pid_file = opts.pid_file
    if pid_file is None:
        pid_file = conf.get("WPID_FILE", "/var/run/beaker-lab-controller/beaker-transfer.pid")

    if not conf.get('ARCHIVE_SERVER'):
        sys.stderr.write('Archive server settings are missing from config file\n')
        sys.exit(1)
    # HubProxy will try to log some stuff, even though we 
    # haven't configured our logging handlers yet. So we send logs to stderr 
    # temporarily here, and configure it again below.
    log_to_stream(sys.stderr, level=logging.WARNING)
    try:
        logarchiver = LogArchiver(conf=conf)
    except Exception, ex:
        sys.stderr.write("Error starting beaker-transfer: %s\n" % ex)
        sys.exit(1)

    if opts.foreground:
        log_to_stream(sys.stderr, level=logging.DEBUG)
        main_loop(logarchiver=logarchiver, conf=conf)
    else:
        # See BZ#977269
        logarchiver.close()
        with daemon.DaemonContext(pidfile=pidfile.TimeoutPIDLockFile(
                pid_file, acquire_timeout=0), detach_process=True):
            log_to_syslog('beaker-transfer')
            main_loop(logarchiver=logarchiver, conf=conf)

if __name__ == '__main__':
    main()
