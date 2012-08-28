
import sys
import os, os.path
import errno
import logging
import time
import random
import signal
from optparse import OptionParser
import pkg_resources
import subprocess
import gevent, gevent.hub, gevent.socket, gevent.event
from kobo.process import daemonize
from kobo.exceptions import ShutdownException
from bkr.log import add_stderr_logger
from bkr.labcontroller.utils import add_rotating_file_logger
from bkr.labcontroller.async import MonitoredSubprocess
from bkr.labcontroller.config import load_conf, get_conf
from bkr.labcontroller.proxy import ProxyHelper
from bkr.labcontroller import netboot

logger = logging.getLogger(__name__)

shutting_down = gevent.event.Event()

class CommandQueuePoller(ProxyHelper):

    def __init__(self, *args, **kwargs):
        super(CommandQueuePoller, self).__init__(*args, **kwargs)
        self.commands = {} #: dict of (id -> command info) for running commands
        self.greenlets = {} #: dict of (command id -> greenlet which is running it)

    def get_queued_commands(self):
        return self.hub.labcontrollers.get_queued_command_details()

    def mark_command_running(self, id):
        self.hub.labcontrollers.mark_command_running(id)

    def mark_command_completed(self, id):
        del self.commands[id]
        del self.greenlets[id]
        self.hub.labcontrollers.mark_command_completed(id)

    def mark_command_failed(self, id, message):
        del self.commands[id]
        del self.greenlets[id]
        self.hub.labcontrollers.mark_command_failed(id, message)

    def clear_running_commands(self, message):
        self.hub.labcontrollers.clear_running_commands(message)

    def poll(self):
        logger.debug('Polling for queued commands')
        for command in self.get_queued_commands():
            if command['id'] in self.commands:
                # We've already seen it, ignore
                continue
            # This command has to wait for any other existing commands against the
            # same system, to prevent collisions
            predecessors = [self.greenlets[c['id']]
                    for c in self.commands.itervalues()
                    if c['fqdn'] == command['fqdn']]
            if 'power' in command and command['power'].get('address'):
                # Also wait for other commands running against the same power address
                predecessors.extend(self.greenlets[c['id']]
                        for c in self.commands.itervalues()
                        if 'power' in c and c['power'].get('address')
                            == command['power']['address'])
            self.commands[command['id']] = command
            self.greenlets[command['id']] = gevent.spawn(self.handle, command, predecessors)

    def handle(self, command, predecessors):
        if command.get('delay'):
            # Before anything else, we need to wait for our delay period.
            # Instead of just doing time.sleep we do a timed wait on
            # shutting_down, so that our delay doesn't hold up the shutdown.
            logger.debug('Delaying %s seconds for command %s',
                    command['delay'], command['id'])
            if shutting_down.wait(timeout=command['delay']):
                return
        gevent.joinall(predecessors)
        if shutting_down.is_set():
            return
        logger.debug('Handling command %r', command)
        self.mark_command_running(command['id'])
        try:
            if command['action'] in (u'on', u'off', 'interrupt'):
                handle_power(command)
            elif command['action'] == u'reboot':
                handle_power(dict(command.items() + [('action', u'off')]))
                handle_power(dict(command.items() + [('action', u'on')]))
            elif command['action'] == u'clear_logs':
                handle_clear_logs(self.conf, command)
            elif command['action'] == u'configure_netboot':
                handle_configure_netboot(command)
            elif command['action'] == u'clear_netboot':
                handle_clear_netboot(command)
            else:
                raise ValueError('Unrecognised action %s' % command['action'])
                # XXX or should we just ignore it and leave it queued?
        except Exception, e:
            logger.exception('Error processing command %s', command['id'])
            self.mark_command_failed(command['id'],
                    '%s: %s' % (e.__class__.__name__, e))
        else:
            self.mark_command_completed(command['id'])
        logger.debug('Finished handling command %s', command['id'])

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
    env['power_address'] = (command['power'].get('address') or u'').encode('utf8')
    env['power_id'] = (command['power'].get('id') or u'').encode('utf8')
    env['power_user'] = (command['power'].get('user') or u'').encode('utf8')
    env['power_pass'] = (command['power'].get('passwd') or u'').encode('utf8')
    env['power_mode'] = command['action'].encode('utf8')
    return env

def handle_clear_logs(conf, command):
    console_log = os.path.join(conf['CONSOLE_LOGS'], command['fqdn'])
    logger.debug('Truncating console log %s', console_log)
    try:
        f = open(console_log, 'r+')
    except IOError, e:
        if e.errno != errno.ENOENT:
            raise
    else:
        f.truncate()

def handle_configure_netboot(command):
    netboot.fetch_images(command['netboot']['distro_tree_id'],
            command['netboot']['kernel_url'],
            command['netboot']['initrd_url'], command['fqdn'])
    fqdn = command['fqdn']
    arch = set(command['arch'])
    ko = command['netboot']['kernel_options']
    if 'i386' in arch or 'x86_64' in arch:
        netboot.configure_pxelinux(fqdn, ko)
        netboot.configure_efigrub(fqdn, ko)
    if 's390' in arch or 's390x' in arch:
        netboot.configure_zpxe(fqdn, ko)
    if 'ppc' in arch or 'ppc64' in arch:
        netboot.configure_yaboot(fqdn, ko)
        netboot.configure_efigrub(fqdn, ko)
    if 'ia64' in arch:
        netboot.configure_elilo(fqdn, ko)
    if 'armhfp' in arch:
        netboot.configure_armlinux(fqdn, ko)

def handle_clear_netboot(command):
    fqdn = command['fqdn']
    arch = set(command['arch'])
    netboot.clear_images(command['fqdn'])
    if 'i386' in arch or 'x86_64' in arch:
        netboot.clear_pxelinux(fqdn)
        netboot.clear_efigrub(fqdn)
    if 's390' in arch or 's390x' in arch:
        netboot.clear_zpxe(fqdn)
    if 'ppc' in arch or 'ppc64' in arch:
        netboot.clear_yaboot(fqdn)
        netboot.clear_efigrub(fqdn)
    if 'ia64' in arch:
        netboot.clear_elilo(fqdn)
    if 'armhfp' in arch:
        netboot.clear_pxelinux(fqdn)

def handle_power(command):
    script = find_power_script(command['power']['type'])
    env = build_power_env(command)
    # We try the command up to 5 times, because some power commands
    # are flakey (apparently)...
    for attempt in range(1, 6):
        if attempt > 1:
            # After the first attempt fails we do a randomised exponential
            # backoff in the style of Ethernet.
            # Instead of just doing time.sleep we do a timed wait on
            # shutting_down, so that our delay doesn't hold up the shutdown.
            delay = random.uniform(attempt, 2**attempt)
            logger.debug('Backing off %0.3f seconds for power command %s',
                    delay, command['id'])
            if shutting_down.wait(timeout=delay):
                break
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
        if p.returncode == 0 or shutting_down.is_set():
            break
    if p.returncode != 0:
        raise ValueError('Power script %s failed after %s attempts with exit status %s:\n%s'
                % (script, attempt, p.returncode, err[:150]))
    # TODO submit complete stdout and stderr?

def shutdown_handler(signum, frame):
    logger.info('Received signal %s, shutting down', signum)
    shutting_down.set()

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

    logger.debug('Clearing old running commands')
    poller.clear_running_commands(u'Stale command cleared on startup')

    logger.debug('Entering main provision loop')
    while True:
        try:
            poller.poll()
        except:
            logger.exception('Failed to poll for queued commands')
        if shutting_down.wait(timeout=conf.get('SLEEP_TIME', 20)):
            gevent.hub.get_hub().join() # let running greenlets terminate
            break
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
