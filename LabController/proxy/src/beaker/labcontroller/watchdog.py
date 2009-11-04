
import os
import sys
import signal
from optparse import OptionParser

from beaker.labcontroller.proxy import Watchdog

import kobo.conf
from kobo.exceptions import ShutdownException
from kobo.process import daemonize
from kobo.tback import Traceback, set_except_hook
from kobo.log import add_stderr_logger
set_except_hook()


def daemon_shutdown(*args, **kwargs):
    raise ShutdownException()

def main_loop(conf=None, foreground=False):
    """infinite daemon loop"""

    # define custom signal handlers
    signal.signal(signal.SIGTERM, daemon_shutdown)

    try:
        watchdog = Watchdog(conf=conf)
    except Exception, ex:
        sys.stderr.write("Error initializing Watchdog: %s\n" % ex)
        sys.exit(1)

    if foreground:
        add_stderr_logger(watchdog.logger)

    while True:
        try:
            watchdog.logger.debug(80 * '-')
            # Poll the scheduler for watchdogs
            watchdog.hub._login()
            watchdog.expire_watchdogs()
            watchdog.active_watchdogs()

            # FIXME: Check for recipes that match systems under
            #        this lab controller, if so take recipe and provision
            #        system.

            # write to stdout / stderr
            sys.stdout.flush()
            sys.stderr.flush()

            # sleep for some time
            watchdog.sleep()

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
