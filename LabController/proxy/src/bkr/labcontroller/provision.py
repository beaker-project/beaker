
import sys
import os, os.path
import logging
import time
import signal
from optparse import OptionParser
import pkg_resources
import subprocess
import gevent, gevent.hub, gevent.socket
from kobo.process import daemonize
from kobo.exceptions import ShutdownException
from bkr.log import add_stderr_logger
from bkr.labcontroller.utils import add_rotating_file_logger
from bkr.labcontroller.async import MonitoredSubprocess
from bkr.labcontroller.config import load_conf, get_conf
from bkr.labcontroller.proxy import ProxyHelper

logger = logging.getLogger(__name__)

class CommandQueuePoller(ProxyHelper):

    def get_queued_commands(self):
        return self.hub.labcontrollers.get_queued_command_details()

    def mark_command_running(self, id):
        self.hub.labcontrollers.mark_command_running(id)

    def mark_command_completed(self, id):
        self.hub.labcontrollers.mark_command_completed(id)

    def mark_command_failed(self, id, message):
        self.hub.labcontrollers.mark_command_failed(id, message)

def find_power_script(power_type):
    customised = '/etc/beaker/power-scripts/%s' % power_type
    if os.path.exists(customised) and os.access(customised, os.X_OK):
        return customised
    resource = 'power-scripts/%s' % power_type
    if pkg_resources.resource_exists('bkr.labcontroller', resource):
        return pkg_resources.resource_filename('bkr.labcontroller', resource)
    raise ValueError('Invalid power type %r' % power_type)

def build_power_env(command):
    env = dict(os.environ)
    env['power_address'] = (command.get('power_address') or u'').encode('utf8')
    env['power_id'] = (command.get('power_id') or u'').encode('utf8')
    env['power_user'] = (command.get('power_user') or u'').encode('utf8')
    env['power_pass'] = (command.get('power_passwd') or u'').encode('utf8')
    env['power_mode'] = (command.get('action') or u'').encode('utf8')
    return env

shutting_down = False

def handle_power(command):
    script = find_power_script(command['power_type'])
    env = build_power_env(command)
    # We try the command up to 5 times, because some power commands
    # are flakey (apparently)...
    for attempt in range(1, 6):
        logger.debug('Launching power script %s (attempt %s) with env %r',
                script, attempt, env)
        # N.B. the timeout value used here affects daemon shutdown time,
        # make sure the init script is kept up to date!
        p = MonitoredSubprocess([script], env=env,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                timeout=300)
        logger.debug('Waiting on power script pid %s', p.pid)
        p.dead.wait()
        out = p.stdout_reader.get()
        err = p.stderr_reader.get()
        if p.returncode == 0 or shutting_down:
            break
    if p.returncode != 0:
        raise ValueError('Power script %s failed after %s attempts with exit status %s:\n%s'
                % (script, attempt, p.returncode, err[:150]))

def handle_command(poller, command):
    poller.mark_command_running(command['id'])
    try:
        if command['action'] in (u'on', u'off'):
            handle_power(command)
        elif command['action'] == u'reboot':
            handle_power(dict(command.items() + [('action', u'off')]))
            handle_power(dict(command.items() + [('action', u'on')]))
        else:
            raise ValueError('Unrecognised action %s' % command['action'])
            # XXX or should we just ignore it and leave it queued?
    except Exception, e:
        logger.exception('Error processing command %s', command['id'])
        poller.mark_command_failed(command['id'],
                '%s: %s' % (e.__class__.__name__, e))
    else:
        # TODO submit complete stdout and stderr?
        poller.mark_command_completed(command['id'])
    logger.debug('Finished handling power command %s', command['id'])

def shutdown_handler(signum, frame):
    logger.info('Received signal %s, shutting down', signum)
    raise ShutdownException() # gevent prints this to stderr, just ignore it

def main_loop(poller=None, conf=None, foreground=False):
    # define custom signal handlers
    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)

    # set up logging
    log_level_string = conf.get("PROVISION_LOG_LEVEL") or conf["LOG_LEVEL"]
    log_level = getattr(logging, log_level_string.upper(), logging.DEBUG)
    logging.getLogger().setLevel(log_level)
    if foreground:
        add_stderr_logger(logging.getLogger(), log_level=log_level)
    else:
        log_file = conf["PROVISION_LOG_FILE"]
        add_rotating_file_logger(logging.getLogger(), log_file,
                log_level=log_level, format=conf["VERBOSE_LOG_FORMAT"])

    logger.debug('Entering main provision loop')
    while True:
        try:
            logger.debug('Polling for queued commands')
            for command in poller.get_queued_commands():
                logger.debug('Handling command %r', command)
                gevent.spawn(handle_command, poller, command)
            time.sleep(conf.get('SLEEP_TIME', 20))
        except ShutdownException:
            global shutting_down
            shutting_down = True
            gevent.hub.get_hub().join() # let running greenlets terminate
            break
        except:
            logger.exception('Failed to poll for queued commands')
            time.sleep(conf.get('SLEEP_TIME', 20))
    logger.debug('Exited main provision loop')

def main():
    parser = OptionParser()
    parser.add_option("-c", "--config", 
                      help="Full path to config file to use")
    parser.add_option("-f", "--foreground", default=False, action="store_true",
                      help="run in foreground (do not spawn a daemon)")
    parser.add_option("-p", "--pid-file",
                      help="specify a pid file")
    (opts, args) = parser.parse_args()

    import gevent.monkey
    gevent.monkey.patch_all(thread=False)

    if opts.config:
        load_conf(opts.config)
    conf = get_conf()

    pid_file = opts.pid_file
    if pid_file is None:
        pid_file = conf.get("PROVISION_PID_FILE", "/var/run/beaker-lab-controller/beaker-provision.pid")

    try:
        poller = CommandQueuePoller(conf=conf)
    except Exception, ex:
        sys.stderr.write('Error initializing CommandQueuePoller: %s\n' % ex)
        sys.exit(1)

    if opts.foreground:
        main_loop(poller=poller, conf=conf, foreground=True)
    else:
        daemonize(main_loop, daemon_pid_file=pid_file, daemon_start_dir="/",
                poller=poller, conf=conf, foreground=False)

if __name__ == '__main__':
    main()
