# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import logging
import signal
import subprocess
import sys
from optparse import OptionParser

import daemon
import gevent
import gevent.event
import gevent.hub
import gevent.monkey
import lxml.etree
from daemon import pidfile
from six.moves import xmlrpc_client

from bkr.labcontroller.config import get_conf, load_conf
from bkr.labcontroller.proxy import Monitor, ProxyHelper
from bkr.log import log_to_stream, log_to_syslog

# Like beaker-provision and beaker-transfer, this daemon is structured as
# a polling loop. Each iteration of the loop, it asks Beaker for the list of
# "active watchdogs" (the corresponding recipe is running, thus we should be
# monitoring its console output) and "expired watchdogs" (the timer has expired
# so we need to abort the corresponding recipe).
#
# For each active watchdog, we also run a separate greenlet which has its own
# loop to watch the console log and upload it back to Beaker, and also check for
# kernel panic messages and installation failure messages if requested.

logger = logging.getLogger(__name__)

# This is a gevent.event.Event which will be set in a signal handler,
# indicating that all our loops should cleanly terminate.
# Note that we must construct it *after* we daemonize, inside the main loop below.
shutting_down = None


def shutdown_handler(signum, frame):
    logger.info("Received signal %s, shutting down", signum)
    shutting_down.set()


def run_monitor(monitor):
    while True:
        updated = monitor.run()
        # If the console was updated, yield and then check it again immediately.
        # If the console was not updated, yield and then sleep for SLEEP_TIME.
        if updated:
            if shutting_down.is_set():
                break
        else:
            if shutting_down.wait(timeout=monitor.conf.get("SLEEP_TIME", 20)):
                break


class Watchdog(ProxyHelper):
    def __init__(self, *args, **kwargs):
        super(Watchdog, self).__init__(*args, **kwargs)
        self.monitor_greenlets = (
            {}
        )  #: dict of (recipe id -> greenlet which is monitoring its console log)

    def get_active_watchdogs(self):
        logger.debug("Polling for active watchdogs")
        try:
            return self.hub.recipes.tasks.watchdogs("active")
        except xmlrpc_client.Fault as fault:
            if "not currently logged in" in fault.faultString:
                logger.debug("Session expired, re-authenticating")
                self.hub._login()
                return self.hub.recipes.tasks.watchdogs("active")
            else:
                raise

    def get_expired_watchdogs(self):
        logger.debug("Polling for expired watchdogs")
        try:
            return self.hub.recipes.tasks.watchdogs("expired")
        except xmlrpc_client.Fault as fault:
            if "not currently logged in" in fault.faultString:
                logger.debug("Session expired, re-authenticating")
                self.hub._login()
                return self.hub.recipes.tasks.watchdogs("expired")
            else:
                raise

    def abort(self, recipe_id, system):
        # Don't import this at global scope. It triggers gevent to create its default hub,
        # but we need to ensure the gevent hub is not created until *after* we have daemonized.
        from bkr.labcontroller.concurrency import MonitoredSubprocess

        logger.info(
            "External Watchdog Expired for recipe %s on system %s", recipe_id, system
        )
        if self.conf.get("WATCHDOG_SCRIPT"):
            job = lxml.etree.fromstring(self.get_my_recipe(dict(recipe_id=recipe_id)))
            recipe = job.find("recipeSet/guestrecipe")
            if recipe is None:
                recipe = job.find("recipeSet/recipe")
            task = None
            for task in recipe.iterfind("task"):
                if task.get("status") == "Running":
                    break

            if task is None:
                logger.error("Unable to find task for recipe %s\n", recipe_id)
                return

            task_id = task.get("id")
            args = [
                self.conf.get("WATCHDOG_SCRIPT"),
                str(system),
                str(recipe_id),
                str(task_id),
            ]
            logger.debug("Invoking external watchdog script %r", args)
            p = MonitoredSubprocess(
                args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=300
            )
            logger.debug("Waiting on external watchdog script pid %s", p.pid)
            p.dead.wait()
            output = p.stdout_reader.get()
            if p.returncode != 0:
                logger.error(
                    "External watchdog script exited with status %s:\n%s",
                    p.returncode,
                    output,
                )
            else:
                try:
                    extend_seconds = int(output)
                except ValueError:
                    logger.error(
                        "Expected external watchdog script to print number of seconds "
                        "to extend watchdog by, got:\n%s",
                        output,
                    )
                else:
                    logger.debug("Extending T:%s watchdog %d", task_id, extend_seconds)
                    self.extend_watchdog(task_id, extend_seconds)
                    # Don't abort it here, we assume the script took care of things.
                    return
        self.recipe_stop(recipe_id, "abort", "External Watchdog Expired")

    def spawn_monitor(self, watchdog):
        monitor = Monitor(watchdog, self)
        monitor_greenlet = gevent.spawn(run_monitor, monitor)
        self.monitor_greenlets[watchdog["recipe_id"]] = monitor_greenlet

        def completion_callback(greenlet):
            if greenlet.exception:
                logger.error(
                    "Monitor greenlet %r had unhandled exception: %r",
                    greenlet,
                    greenlet.exception,
                )
            del self.monitor_greenlets[watchdog["recipe_id"]]

        monitor_greenlet.link(completion_callback)

    def poll(self):
        for expired_watchdog in self.get_expired_watchdogs():
            try:
                recipe_id = expired_watchdog["recipe_id"]
                system = expired_watchdog["system"]
                self.abort(recipe_id, system)
            except Exception:  # noqa
                # catch and ignore here, so that we keep going through the loop
                logger.exception("Failed to abort expired watchdog")
            if shutting_down.is_set():
                return
        # Get active watchdogs *after* we finish running
        # expired_watchdogs, depending on the configuration
        # we may have extended the watchdog and it's therefore
        # no longer expired!
        active_watchdogs = self.get_active_watchdogs()
        # Start a new monitor for any active watchdog we are not already monitoring.
        for watchdog in active_watchdogs:
            if watchdog["recipe_id"] not in self.monitor_greenlets:
                self.spawn_monitor(watchdog)
        # Kill any running monitors that are gone from the list.
        active_recipes = set(w["recipe_id"] for w in active_watchdogs)
        for recipe_id, greenlet in list(self.monitor_greenlets.items()):
            if recipe_id not in active_recipes:
                logger.info("Stopping monitor for recipe %s", recipe_id)
                greenlet.kill()


def main_loop(watchdog, conf):
    global shutting_down
    shutting_down = gevent.event.Event()
    gevent.monkey.patch_all(thread=False)

    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)

    logger.debug("Entering main watchdog loop")
    while True:
        try:
            watchdog.poll()
        except Exception:  # noqa
            logger.exception("Failed to poll for watchdogs")
        if shutting_down.wait(timeout=conf.get("SLEEP_TIME", 20)):
            gevent.hub.get_hub().join()  # let running greenlets terminate
            break
    logger.debug("Exited main watchdog loop")


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
            "WATCHDOG_PID_FILE", "/var/run/beaker-lab-controller/beaker-watchdog.pid"
        )

    # HubProxy will try to log some stuff, even though we
    # haven't configured our logging handlers yet. So we send logs to stderr
    # temporarily here, and configure it again below.
    log_to_stream(sys.stderr, level=logging.WARNING)
    try:
        watchdog = Watchdog(conf=conf)
    except Exception as ex:
        sys.stderr.write("Error starting beaker-watchdog: %s\n" % ex)
        sys.exit(1)

    if opts.foreground:
        log_to_stream(sys.stderr, level=logging.DEBUG)
        main_loop(watchdog, conf)
    else:
        # See BZ#977269
        watchdog.close()
        with daemon.DaemonContext(
            pidfile=pidfile.TimeoutPIDLockFile(pid_file, acquire_timeout=0),
            detach_process=True,
        ):
            log_to_syslog("beaker-watchdog")
            try:
                main_loop(watchdog, conf)
            except Exception:
                logger.exception("Unhandled exception in main_loop")
                raise


if __name__ == "__main__":
    main()
