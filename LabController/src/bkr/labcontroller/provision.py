# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import datetime
import errno
import logging
import os
import os.path
import random
import signal
import subprocess
import sys
import time
from optparse import OptionParser

import daemon
import gevent
import gevent.event
import gevent.hub
import gevent.monkey
import gevent.socket
import pkg_resources
import six
from daemon import pidfile
from six.moves import xmlrpc_client

from bkr.common.helpers import SensitiveUnicode
from bkr.labcontroller import netboot
from bkr.labcontroller.config import get_conf, load_conf
from bkr.labcontroller.proxy import ProxyHelper
from bkr.labcontroller.utils import get_console_files
from bkr.log import log_to_stream, log_to_syslog

logger = logging.getLogger(__name__)


class CommandQueuePoller(ProxyHelper):
    def __init__(self, *args, **kwargs):
        super(CommandQueuePoller, self).__init__(*args, **kwargs)
        self.commands = {}  #: dict of (id -> command info) for running commands
        self.greenlets = {}  #: dict of (command id -> greenlet which is running it)
        self.last_command_datetime = {}  # Last time a command was run against a system.

    def get_queued_commands(self):
        try:
            commands = self.hub.labcontrollers.get_queued_command_details()
        except xmlrpc_client.Fault as fault:
            if "Anonymous access denied" in fault.faultString:
                logger.debug("Session expired, re-authenticating")
                self.hub._login()
                commands = self.hub.labcontrollers.get_queued_command_details()
            else:
                raise
        for command in commands:
            # The 'is not None' check is important as we do not want to
            # stringify the None type
            if (
                "power" in command
                and "passwd" in command["power"]
                and command["power"]["passwd"] is not None
            ):
                command["power"]["passwd"] = SensitiveUnicode(
                    command["power"]["passwd"]
                )
        return commands

    def get_running_command_ids(self):
        try:
            ids = self.hub.labcontrollers.get_running_command_ids()
        except xmlrpc_client.Fault as fault:
            if "Anonymous access denied" in fault.faultString:
                logger.debug("Session expired, re-authenticating")
                self.hub._login()
                ids = self.hub.labcontrollers.get_running_command_ids()
            else:
                raise
        return ids

    def mark_command_running(self, id):
        self.hub.labcontrollers.mark_command_running(id)

    def mark_command_completed(self, id):
        self.hub.labcontrollers.mark_command_completed(id)

    def mark_command_failed(self, id, message, system_broken):
        self.hub.labcontrollers.mark_command_failed(id, message, system_broken)

    def mark_command_aborted(self, id, message):
        self.hub.labcontrollers.mark_command_aborted(id, message)

    def clear_running_commands(self, message):
        self.hub.labcontrollers.clear_running_commands(message)

    def clear_orphaned_commands(self):
        running_command_ids = self.get_running_command_ids()
        orphaned_command_ids = set(running_command_ids).difference(self.commands.keys())
        for id in orphaned_command_ids:
            self.mark_command_aborted(id, "Command orphaned, aborting")

    def poll(self):
        logger.debug("Clearing orphaned commands")
        self.clear_orphaned_commands()

        logger.debug("Polling for queued commands")
        for command in self.get_queued_commands():
            if command["id"] in self.commands:
                # We've already seen it, ignore
                continue
            # This command has to wait for any other existing commands against the
            # same system, to prevent collisions
            predecessors = [
                self.greenlets[c["id"]]
                for c in six.itervalues(self.commands)
                if c["fqdn"] == command["fqdn"]
            ]
            if "power" in command and command["power"].get("address"):
                # Also wait for other commands running against the same power address
                predecessors.extend(
                    self.greenlets[c["id"]]
                    for c in six.itervalues(self.commands)
                    if "power" in c
                    and c["power"].get("address") == command["power"]["address"]
                )
            self.spawn_handler(command, predecessors)

    def spawn_handler(self, command, predecessors):
        self.commands[command["id"]] = command
        greenlet = gevent.spawn(self.handle, command, predecessors)
        self.greenlets[command["id"]] = greenlet

        def completion_callback(greenlet):
            if greenlet.exception:
                logger.error(
                    "Command handler %r had unhandled exception: %r",
                    greenlet,
                    greenlet.exception,
                )
            del self.commands[command["id"]]
            del self.greenlets[command["id"]]

        greenlet.link(completion_callback)

    def handle(self, command, predecessors):
        if command.get("delay"):
            # Before anything else, we need to wait for our delay period.
            # Instead of just doing time.sleep we do a timed wait on
            # shutting_down, so that our delay doesn't hold up the shutdown.
            logger.debug(
                "Delaying %s seconds for command %s", command["delay"], command["id"]
            )
            if shutting_down.wait(timeout=command["delay"]):
                return
        gevent.joinall(predecessors)
        if shutting_down.is_set():
            return
        quiescent_period = command.get("quiescent_period")
        if quiescent_period:
            system_fqdn = command.get("fqdn")
            last_command_finished_at = self.last_command_datetime.get(system_fqdn)
            if last_command_finished_at:
                # Get the difference between the time now and the number of
                # seconds until we can run another command
                seconds_to_wait = (
                    (
                        last_command_finished_at
                        + datetime.timedelta(seconds=quiescent_period)
                    )
                    - datetime.datetime.utcnow()
                ).total_seconds()
            else:
                # Play it safe, wait for the whole period.
                seconds_to_wait = quiescent_period
            if seconds_to_wait > 0:
                logger.debug(
                    "Entering quiescent period, delaying %s seconds for"
                    " command %s" % (seconds_to_wait, command["id"])
                )
                if shutting_down.wait(timeout=seconds_to_wait):
                    return
        logger.debug("Handling command %r", command)
        self.mark_command_running(command["id"])
        try:
            if command["action"] in ("on", "off", "interrupt"):
                handle_power(self.conf, command)
            elif command["action"] == "reboot":
                # For backwards compatibility only. The server now splits
                # reboots into 'off' followed by 'on'.
                handle_power(
                    self.conf, dict(list(command.items()) + [("action", "off")])
                )
                time.sleep(5)
                handle_power(
                    self.conf, dict(list(command.items()) + [("action", "on")])
                )
            elif command["action"] == "clear_logs":
                handle_clear_logs(self.conf, command)
            elif command["action"] == "configure_netboot":
                handle_configure_netboot(command)
            elif command["action"] == "clear_netboot":
                handle_clear_netboot(command)
            else:
                raise ValueError("Unrecognised action %s" % command["action"])
                # XXX or should we just ignore it and leave it queued?
        except netboot.ImageFetchingError as e:
            logger.exception("Error processing command %s", command["id"])
            # It's not the system's fault so don't mark it as broken
            self.mark_command_failed(command["id"], six.text_type(e), False)
        except Exception as e:
            logger.exception("Error processing command %s", command["id"])
            self.mark_command_failed(
                command["id"], "%s: %s" % (e.__class__.__name__, e), True
            )
        else:
            self.mark_command_completed(command["id"])
        finally:
            if quiescent_period:
                self.last_command_datetime[command["fqdn"]] = datetime.datetime.utcnow()
        logger.debug("Finished handling command %s", command["id"])


def find_power_script(power_type):
    customised = "/etc/beaker/power-scripts/%s" % power_type
    if os.path.exists(customised) and os.access(customised, os.X_OK):
        return customised
    resource = "power-scripts/%s" % power_type
    if pkg_resources.resource_exists("bkr.labcontroller", resource):
        return pkg_resources.resource_filename("bkr.labcontroller", resource)
    raise ValueError("Invalid power type %r" % power_type)


def _decode(value):
    # Decode if we are running python2 and value is unicode
    if six.PY2 and isinstance(value, six.text_type):
        return value.encode("utf8")
    return value


def build_power_env(command):
    env = dict(os.environ)
    power_mapping = {
        "address": "power_address",
        "id": "power_id",
        "user": "power_user",
        "passwd": "power_pass",
    }

    for k, v in six.iteritems(power_mapping):
        env[v] = _decode(command["power"].get(k, ""))

    env["power_mode"] = _decode(command["action"])

    return env


def handle_clear_logs(conf, command):
    for filename, _ in get_console_files(
        console_logs_directory=conf["CONSOLE_LOGS"], system_name=command["fqdn"]
    ):
        truncate_logfile(filename)


def truncate_logfile(console_log):
    logger.debug("Truncating console log %s", console_log)
    try:
        f = open(console_log, "r+")
    except IOError as e:
        if e.errno != errno.ENOENT:
            raise
    else:
        f.truncate()


def handle_configure_netboot(command):
    netboot.configure_all(
        command["fqdn"],
        command["netboot"]["arch"],
        command["netboot"]["distro_tree_id"],
        command["netboot"]["kernel_url"],
        command["netboot"]["initrd_url"],
        command["netboot"]["kernel_options"],
        command["netboot"]["image_url"],
    )


def handle_clear_netboot(command):
    netboot.clear_all(command["fqdn"])


def handle_power(conf, command):
    from bkr.labcontroller.concurrency import MonitoredSubprocess

    script = find_power_script(command["power"]["type"])
    env = build_power_env(command)
    # We try the command up to 5 times, because some power commands
    # are flakey (apparently)...
    for attempt in range(1, conf["POWER_ATTEMPTS"] + 1):
        if attempt > 1:
            # After the first attempt fails we do a randomised exponential
            # backoff in the style of Ethernet.
            # Instead of just doing time.sleep we do a timed wait on
            # shutting_down, so that our delay doesn't hold up the shutdown.
            delay = random.uniform(attempt, 2**attempt)
            logger.debug(
                "Backing off %0.3f seconds for power command %s", delay, command["id"]
            )
            if shutting_down.wait(timeout=delay):
                break
        logger.debug(
            "Launching power script %s (attempt %s) with env %r", script, attempt, env
        )
        # N.B. the timeout value used here affects daemon shutdown time,
        # make sure the init script is kept up to date!
        p = MonitoredSubprocess(
            [script],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=300,
        )
        logger.debug("Waiting on power script pid %s", p.pid)
        p.dead.wait()
        output = p.stdout_reader.get()
        if p.returncode == 0 or shutting_down.is_set():
            break
    if p.returncode != 0:
        sanitised_output = output[:150].strip()
        if command["power"].get("passwd"):
            sanitised_output = sanitised_output.replace(
                command["power"]["passwd"], "********"
            )
        raise ValueError(
            "Power script %s failed after %s attempts with exit status %s:\n%s"
            % (script, attempt, p.returncode, sanitised_output)
        )
    # TODO submit complete stdout and stderr?


def shutdown_handler(signum, frame):
    logger.info("Received signal %s, shutting down", signum)
    shutting_down.set()


def main_loop(poller=None, conf=None):
    global shutting_down
    shutting_down = gevent.event.Event()
    gevent.monkey.patch_all(thread=False)

    # define custom signal handlers
    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)

    logger.debug("Copying default boot loader images")
    netboot.copy_default_loader_images()

    logger.debug("Clearing old running commands")
    poller.clear_running_commands("Stale command cleared on startup")

    logger.debug("Entering main provision loop")
    while True:
        try:
            poller.poll()
        except:  # noqa
            logger.exception("Failed to poll for queued commands")
        if shutting_down.wait(timeout=conf.get("SLEEP_TIME", 20)):
            gevent.hub.get_hub().join()  # let running greenlets terminate
            break
    logger.debug("Exited main provision loop")


def main():
    parser = OptionParser()
    parser.add_option("-c", "--config", help="Full path to config file to use")
    parser.add_option(
        "-f",
        "--foreground",
        default=False,
        action="store_true",
        help="run in foreground (do not spawn a daemon)",
    )
    parser.add_option("-p", "--pid-file", help="specify a pid file")
    (opts, args) = parser.parse_args()
    if opts.config:
        load_conf(opts.config)
    logging.getLogger().setLevel(logging.DEBUG)

    conf = get_conf()
    pid_file = opts.pid_file
    if pid_file is None:
        pid_file = conf.get(
            "PROVISION_PID_FILE", "/var/run/beaker-lab-controller/beaker-provision.pid"
        )

    # HubProxy will try to log some stuff, even though we
    # haven't configured our logging handlers yet. So we send logs to stderr
    # temporarily here, and configure it again below.
    log_to_stream(sys.stderr, level=logging.WARNING)
    try:
        poller = CommandQueuePoller(conf=conf)
    except Exception as ex:
        sys.stderr.write("Error starting beaker-provision: %s\n" % ex)
        sys.exit(1)

    if opts.foreground:
        log_to_stream(sys.stderr, level=logging.DEBUG)
        main_loop(poller=poller, conf=conf)
    else:
        # See BZ#977269
        poller.close()
        with daemon.DaemonContext(
            pidfile=pidfile.TimeoutPIDLockFile(pid_file, acquire_timeout=0),
            detach_process=True,
        ):
            log_to_syslog("beaker-provision")
            try:
                main_loop(poller=poller, conf=conf)
            except Exception:
                logger.exception("Unhandled exception in main_loop")
                raise


if __name__ == "__main__":
    main()
