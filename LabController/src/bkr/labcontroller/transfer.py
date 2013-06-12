
import os
import sys
import signal
import logging
import time
import socket
import daemon
from daemon import pidfile
from optparse import OptionParser
from bkr.labcontroller.proxy import Watchdog
from bkr.labcontroller.config import get_conf, load_conf
from kobo.exceptions import ShutdownException
from kobo.tback import Traceback, set_except_hook
from bkr.log import log_to_stream, log_to_syslog

set_except_hook()

logger = logging.getLogger(__name__)

def daemon_shutdown(*args, **kwargs):
    raise ShutdownException()

def main_loop(transfer, conf=None):
    """infinite daemon loop"""

    # define custom signal handlers
    signal.signal(signal.SIGTERM, daemon_shutdown)

    while True:
        try:
            transfer.hub._login()
            # Look for logs to transfer if none transfered then sleep
            if not transfer.transfer_logs():
                logger.debug(80 * '-')
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

            logger.info('Exiting...')
            break

        except:
            # this is a little extreme: log the exception and continue
            traceback = Traceback()
            logger.error(traceback.get_traceback())
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
    # kobo.client.HubProxy will try to log some stuff, even though we 
    # haven't configured our logging handlers yet. So we send logs to stderr 
    # temporarily here, and configure it again below.
    log_to_stream(sys.stderr, level=logging.WARNING)
    try:
        transfer = Watchdog(conf=conf)
    except Exception, ex:
        sys.stderr.write("Error initializing Watchdog: %s\n" % ex)
        sys.exit(1)

    if opts.foreground:
        log_to_stream(sys.stderr, level=logging.DEBUG)
        main_loop(transfer=transfer, conf=conf)
    else:
        # See BZ#977269
        transfer.close()
        with daemon.DaemonContext(pidfile=pidfile.TimeoutPIDLockFile(
                pid_file, acquire_timeout=0)):
            log_to_syslog('beaker-transfer')
            main_loop(transfer=transfer, conf=conf)

if __name__ == '__main__':
    main()
