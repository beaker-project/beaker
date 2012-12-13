#!/usr/bin/env python
# Beaker - 
#
# Copyright (C) 2008 bpeck@redhat.com
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

# -*- coding: utf-8 -*-

__requires__ = ['TurboGears']

import sys
import os
import random
from bkr.server import needpropertyxml, utilisation
from bkr.server.bexceptions import BX, VMCreationFailedException
from bkr.server.model import *
from bkr.server.util import load_config, log_traceback
from bkr.server.recipetasks import RecipeTasks
from turbogears.database import session
from turbogears import config
from turbomail.control import interface
from xmlrpclib import ProtocolError

import socket
import exceptions
from datetime import datetime, timedelta
import time
import daemon
import atexit
import signal
from lockfile import pidlockfile
from daemon import pidfile
import threading
import os

import logging

log = logging.getLogger("beakerd")
running = True
event = threading.Event()

from optparse import OptionParser

__version__ = '0.1'
__description__ = 'Beaker Scheduler'


def get_parser():
    usage = "usage: %prog [options]"
    parser = OptionParser(usage, description=__description__,
                          version=__version__)

    ## Defaults
    parser.set_defaults(daemonize=True, log_level=None)
    ## Actions
    parser.add_option("-f", "--foreground", default=False, action="store_true",
                      help="run in foreground (do not spawn a daemon)")
    parser.add_option("-p", "--pid-file",
                      help="specify a pid file")
    parser.add_option('-l', '--log-level', dest='log_level', metavar='LEVEL',
                      help='log level (ie. INFO, WARNING, ERROR, CRITICAL)')
    parser.add_option("-c", "--config", action="store", type="string",
                      dest="configfile", help="location of config file.")
    parser.add_option("-u", "--user", action="store", type="string",
                      dest="user_name", help="username of Admin account")

    return parser


def process_new_recipes(*args):
    recipes = MachineRecipe.query.filter(Recipe.status == TaskStatus.new)
    if not recipes.count():
        return False
    log.debug("Entering process_new_recipes")
    for recipe_id, in recipes.values(MachineRecipe.id):
        session.begin()
        try:
            process_new_recipe(recipe_id)
            session.commit()
        except Exception, e:
            log.exception('Error in process_new_recipe(%s)', recipe_id)
            session.rollback()
        finally:
            session.close()
    log.debug("Exiting process_new_recipes")
    return True

def process_new_recipe(recipe_id):
    recipe = MachineRecipe.by_id(recipe_id)
    if not recipe.distro_tree:
        log.info("recipe ID %s moved from New to Aborted", recipe.id)
        recipe.recipeset.abort(u'Recipe ID %s does not have a distro tree' % recipe.id)
        return
    recipe.systems = []

    # Do the query twice.

    # First query verifies that the distro tree 
    # exists in at least one lab that has a matching system.
    systems = recipe.distro_tree.systems_filter(
                                recipe.recipeset.job.owner,
                                recipe.host_requires,
                                only_in_lab=True)
    # Second query picks up all possible systems so that as 
    # trees appear in other labs those systems will be 
    # available.
    all_systems = recipe.distro_tree.systems_filter(
                                recipe.recipeset.job.owner,
                                recipe.host_requires,
                                only_in_lab=False)
    # based on above queries, condition on systems but add
    # all_systems.
    if systems.count():
        for system in all_systems:
            # Add matched systems to recipe.
            recipe.systems.append(system)

    # If the recipe only matches one system then bump its priority.
    if len(recipe.systems) == 1:
        try:
            log.info("recipe ID %s matches one system, bumping priority" % recipe.id)
            recipe.recipeset.priority = TaskPriority.by_index(
                    TaskPriority.index(recipe.recipeset.priority) + 1)
        except IndexError:
            # We may already be at the highest priority
            pass
    recipe.virt_status = recipe.check_virtualisability()
    if not recipe.systems:
        log.info("recipe ID %s moved from New to Aborted" % recipe.id)
        recipe.recipeset.abort(u'Recipe ID %s does not match any systems' % recipe.id)
        return
    recipe.process()
    log.info("recipe ID %s moved from New to Processed" % recipe.id)
    for guestrecipe in recipe.guests:
        guestrecipe.process()

def queue_processed_recipesets(*args):
    recipesets = RecipeSet.query.filter(RecipeSet.status == TaskStatus.processed)
    if not recipesets.count():
        return False
    log.debug("Entering queue_processed_recipesets")
    for rs_id, in recipesets.values(RecipeSet.id):
        session.begin()
        try:
            queue_processed_recipeset(rs_id)
            session.commit()
        except Exception, e:
            log.exception('Error in queue_processed_recipeset(%s)', rs_id)
            session.rollback()
        finally:
            session.close()
    log.debug("Exiting queue_processed_recipesets")
    return True

def queue_processed_recipeset(recipeset_id):
    recipeset = RecipeSet.by_id(recipeset_id)
    bad_l_controllers = set()
    # We only need to do this processing on multi-host recipes
    if len(list(recipeset.machine_recipes)) == 1:
        recipe = recipeset.machine_recipes.next()
        recipe.queue()
        log.info("recipe ID %s moved from Processed to Queued", recipe.id)
        for guestrecipe in recipe.guests:
            guestrecipe.queue()
        return
    # Find all the lab controllers that this recipeset may run.
    rsl_controllers = set(LabController.query\
                                  .join('systems',
                                        'queued_recipes',
                                        'recipeset')\
                                  .filter(RecipeSet.id==recipeset.id).all())

    # Any lab controllers that are not associated to all recipes in the
    # recipe set must have those systems on that lab controller removed
    # from any recipes.  For multi-host all recipes must be schedulable
    # on one lab controller
    for recipe in recipeset.machine_recipes:
        rl_controllers = set(LabController.query\
                                   .join('systems',
                                         'queued_recipes')\
                                   .filter(Recipe.id==recipe.id).all())
        bad_l_controllers = bad_l_controllers.union(rl_controllers.difference(rsl_controllers))

    for l_controller in rsl_controllers:
        enough_systems = False
        for recipe in recipeset.machine_recipes:
            systems = recipe.dyn_systems.filter(
                                      System.lab_controller==l_controller
                                               ).all()
            if len(systems) < len(recipeset.recipes):
                break
        else:
            # There are enough choices We don't need to worry about dead
            # locks
            enough_systems = True
        if not enough_systems:
            log.debug("recipe: %s labController:%s entering not enough systems logic" % 
                                  (recipe.id, l_controller))
            # Eliminate bad choices.
            for recipe in recipeset.machine_recipes_orderby(l_controller)[:]:
                for tmprecipe in recipeset.machine_recipes:
                    systemsa = set(recipe.dyn_systems.filter(
                                      System.lab_controller==l_controller
                                                            ).all())
                    systemsb = set(tmprecipe.dyn_systems.filter(
                                      System.lab_controller==l_controller
                                                               ).all())

                    if systemsa.difference(systemsb):
                        for rem_system in systemsa.intersection(systemsb):
                            if rem_system in recipe.systems:
                                log.debug("recipe: %s labController:%s Removing system %s" % (recipe.id, l_controller, rem_system))
                                recipe.systems.remove(rem_system)
            for recipe in recipeset.machine_recipes:
                count = 0
                systems = recipe.dyn_systems.filter(
                                  System.lab_controller==l_controller
                                                   ).all()
                for tmprecipe in recipeset.machine_recipes:
                    tmpsystems = tmprecipe.dyn_systems.filter(
                                      System.lab_controller==l_controller
                                                             ).all()
                    if recipe != tmprecipe and \
                       systems == tmpsystems:
                        count += 1
                if len(systems) <= count:
                    # Remove all systems from this lc on this rs.
                    log.debug("recipe: %s labController:%s %s <= %s Removing lab" % (recipe.id, l_controller, len(systems), count))
                    bad_l_controllers = bad_l_controllers.union([l_controller])

    # Remove systems that are on bad lab controllers
    # This means one of the recipes can be fullfilled on a lab controller
    # but not the rest of the recipes in the recipeSet.
    # This could very well remove ALL systems from all recipes in this
    # recipeSet.  If that happens then the recipeSet cannot be scheduled
    # and will be aborted by the abort process.
    for recipe in recipeset.machine_recipes:
        for l_controller in bad_l_controllers:
            systems = (recipe.dyn_systems.filter(
                                      System.lab_controller==l_controller
                                            ).all()
                          )
            log.debug("recipe: %s labController: %s Removing lab" % (recipe.id, l_controller))
            for system in systems:
                if system in recipe.systems:
                    log.debug("recipe: %s labController: %s Removing system %s" % (recipe.id, l_controller, system))
                    recipe.systems.remove(system)
        if recipe.systems:
            # Set status to Queued
            log.info("recipe: %s moved from Processed to Queued" % recipe.id)
            recipe.queue()
            for guestrecipe in recipe.guests:
                guestrecipe.queue()
        else:
            # Set status to Aborted
            log.info("recipe ID %s moved from Processed to Aborted" % recipe.id)
            recipe.recipeset.abort(u'Recipe ID %s does not match any systems' % recipe.id)

def abort_dead_recipes(*args):
    recipes = MachineRecipe.query\
                    .outerjoin(Recipe.distro_tree)\
                    .filter(
                         or_(
                         and_(Recipe.status==TaskStatus.queued,
                              not_(Recipe.systems.any()),
                             ),
                         and_(Recipe.status==TaskStatus.queued,
                              not_(DistroTree.lab_controller_assocs.any()),
                             ),
                            )
                           )

    if not recipes.count():
        return False
    log.debug("Entering abort_dead_recipes")
    for recipe_id, in recipes.values(MachineRecipe.id):
        session.begin()
        try:
            abort_dead_recipe(recipe_id)
            session.commit()
        except exceptions.Exception, e:
            log.exception('Error in abort_dead_recipe(%s)', recipe_id)
            session.rollback()
        finally:
            session.close()
    log.debug("Exiting abort_dead_recipes")
    return True

def abort_dead_recipe(recipe_id):
    recipe = MachineRecipe.by_id(recipe_id)
    if len(recipe.systems) == 0:
        msg = u"R:%s does not match any systems, aborting." % recipe.id
        log.info(msg)
        recipe.recipeset.abort(msg)
    elif len(recipe.distro_tree.lab_controller_assocs) == 0:
        msg = u"R:%s does not have a valid distro tree, aborting." % recipe.id
        log.info(msg)
        recipe.recipeset.abort(msg)

def schedule_queued_recipes(*args):
    recipes = MachineRecipe.query\
                    .join(Recipe.recipeset, RecipeSet.job)\
                    .join(Recipe.systems)\
                    .join(Recipe.distro_tree)\
                    .join(DistroTree.lab_controller_assocs,
                        (LabController, and_(
                            LabControllerDistroTree.lab_controller_id == LabController.id,
                            System.lab_controller_id == LabController.id)))\
                    .filter(
                         and_(Recipe.status==TaskStatus.queued,
                              System.user==None,
                              System.status==SystemStatus.automated,
                              LabController.disabled==False,
                              or_(
                                  RecipeSet.lab_controller==None,
                                  RecipeSet.lab_controller_id==System.lab_controller_id,
                                 ),
                              or_(
                                  System.loan_id==None,
                                  System.loan_id==Job.owner_id,
                                 ),
                             )
                           )
    # Order recipes by priority.
    # FIXME Add secondary order by number of matched systems.
    if True:
        recipes = recipes.order_by(RecipeSet.priority.desc())
    # order recipes by id
    recipes = recipes.order_by(MachineRecipe.id)
    if not recipes.count():
        return False
    log.debug("Entering schedule_queued_recipes")
    for recipe_id, in recipes.values(MachineRecipe.id.distinct()):
        session.begin()
        try:
            schedule_queued_recipe(recipe_id)
            session.commit()
        except Exception, e:
            log.exception('Error in schedule_queued_recipe(%s)', recipe_id)
            session.rollback()
        finally:
            session.close()
    log.debug("Exiting schedule_queued_recipes")
    return True

def schedule_queued_recipe(recipe_id):
    recipe = MachineRecipe.by_id(recipe_id)
    systems = recipe.dyn_systems\
               .join(System.lab_controller)\
               .filter(and_(System.user==None,
                          LabController._distro_trees.any(
                            LabControllerDistroTree.distro_tree == recipe.distro_tree),
                          LabController.disabled==False,
                          System.status==SystemStatus.automated,
                          or_(
                              System.loan_id==None,
                              System.loan_id==recipe.recipeset.job.owner_id,
                             ),
                           )
                      )
    # Order systems by owner, then Group, finally shared for everyone.
    # FIXME Make this configurable, so that a user can specify their scheduling
    # Implemented order, still need to do pool
    # preference from the job.
    # <recipe>
    #  <autopick order='sequence|random'>
    #   <pool>owner</pool>
    #   <pool>groups</pool>
    #   <pool>public</pool>
    #  </autopick>
    # </recipe>
    user = recipe.recipeset.job.owner
    if True: #FIXME if pools are defined add them here in the order requested.
        systems = systems.order_by(case([(System.owner==user, 1),
                  (and_(System.owner!=user, System.group_assocs != None), 2)],
                      else_=3))
    if recipe.recipeset.lab_controller:
        # First recipe of a recipeSet determines the lab_controller
        systems = systems.filter(
                     System.lab_controller==recipe.recipeset.lab_controller
                              )
    if recipe.autopick_random:
        try:
            system = systems[random.randrange(0,systems.count())]
        except (IndexError, ValueError):
            system = None
    else:
        system = systems.first()
    if not system:
        return
    log.debug("System : %s is available for Recipe %s" % (system, recipe.id))
    # Check to see if user still has proper permissions to use system
    # Remember the mapping of available systems could have happend hours or even
    # days ago and groups or loans could have been put in place since.
    if not System.free(user).filter(System.id == system.id).first():
        log.debug("System : %s recipe: %s no longer has access. removing" % (system, 
                                                                             recipe.id))
        recipe.systems.remove(system)
        return

    recipe.resource = SystemResource(system=system)
    # Reserving the system may fail here if someone stole it out from
    # underneath us, but that is fine...
    recipe.resource.allocate()
    recipe.schedule()
    recipe.createRepo()
    recipe.recipeset.lab_controller = system.lab_controller
    recipe.systems = []
    # Create the watchdog without an Expire time.
    log.debug("Created watchdog for recipe id: %s and system: %s" % (recipe.id, system))
    recipe.watchdog = Watchdog()
    log.info("recipe ID %s moved from Queued to Scheduled" % recipe.id)

    for guestrecipe in recipe.guests:
        guestrecipe.resource = GuestResource()
        guestrecipe.resource.allocate()
        guestrecipe.schedule()
        guestrecipe.createRepo()
        guestrecipe.watchdog = Watchdog()
        log.info('recipe ID %s guest %s moved from Queued to Scheduled',
                recipe.id, guestrecipe.id)

def provision_virt_recipes(*args):
    # We limit to labs where the tree is available by NFS because RHEV needs to 
    # use autofs to grab the images. See VirtManager.start_install.
    recipes = MachineRecipe.query\
            .join(Recipe.recipeset)\
            .join(Recipe.distro_tree, DistroTree.lab_controller_assocs, LabController)\
            .filter(Recipe.status == TaskStatus.queued)\
            .filter(Recipe.virt_status == RecipeVirtStatus.possible)\
            .filter(LabController.disabled == False)\
            .filter(or_(RecipeSet.lab_controller == None,
                RecipeSet.lab_controller_id == LabController.id))\
            .filter(LabControllerDistroTree.url.like(u'nfs://%'))\
            .order_by(RecipeSet.priority.desc(), Recipe.id.asc())
    if not recipes.count():
        return False
    log.debug("Entering provision_virt_recipes")
    for recipe_id, in recipes.values(Recipe.id.distinct()):
        system_name = "guest_for_recipe_%d" % recipe_id
        session.begin()
        try:
            provision_virt_recipe(system_name, recipe_id)
            session.commit()
        except needpropertyxml.NotVirtualisable:
            session.rollback()
            session.begin()
            recipe = Recipe.by_id(recipe_id)
            recipe.virt_status = RecipeVirtStatus.precluded
            session.commit()
        except VMCreationFailedException:
            session.rollback()
            session.begin()
            recipe = Recipe.by_id(recipe_id)
            recipe.virt_status = RecipeVirtStatus.skipped
            session.commit()
        except Exception, e: # This will get ovirt RequestErrors from recipe.provision()
            log.exception('Error in provision_virt_recipe(%s)', recipe_id)
            session.rollback()
            try:
                # Don't leak the vm if it was created
                with VirtManager() as manager:
                    manager.destroy_vm(system_name)
                # As an added precaution, let's try and avoid this recipe in future
                session.begin()
                recipe = Recipe.by_id(recipe_id)
                recipe.virt_status = RecipeVirtStatus.failed
                session.commit()
            except Exception:
                log.exception('Exception in exception handler :-(')
        finally:
            session.close()
    log.debug("Exiting provision_virt_recipes")
    return True

def provision_virt_recipe(system_name, recipe_id):
    recipe = Recipe.by_id(recipe_id)
    # vm_params is a throwaway var. We only call vm_params()
    # method to see if we throw NotVirtualisable exception
    vm_params = needpropertyxml.vm_params(recipe.host_requires)
    recipe.createRepo()
    # Figure out the "data centers" where we can run the recipe
    if recipe.recipeset.lab_controller:
        # First recipe of a recipeSet determines the lab_controller
        lab_controllers = [recipe.recipeset.lab_controller]
    else:
        # NB the same criteria are also expressed above
        lab_controllers = LabController.query.filter_by(disabled=False, removed=None)
        lab_controllers = needpropertyxml.apply_lab_controller_filter(
                recipe.host_requires, lab_controllers)

    lab_controllers = [lc for lc in lab_controllers.all()
            if recipe.distro_tree.url_in_lab(lc, 'nfs')]
    recipe.systems = []
    recipe.watchdog = Watchdog()
    recipe.resource = VirtResource(system_name=system_name)
    with VirtManager() as manager:
        recipe.resource.allocate(manager, lab_controllers)
    recipe.recipeset.lab_controller = recipe.resource.lab_controller
    recipe.schedule()
    log.info("recipe ID %s moved from Queued to Scheduled by provision_virt_recipe" % recipe.id)
    recipe.waiting()
    recipe.provision()
    log.info("recipe ID %s moved from Scheduled to Waiting by provision_virt_recipe" % recipe.id)

def provision_scheduled_recipesets(*args):
    """
    if All recipes in a recipeSet are in Scheduled state then move them to
     Running.
    """
    recipesets = RecipeSet.query.filter(not_(RecipeSet.recipes.any(
            Recipe.status != TaskStatus.scheduled)))
    if not recipesets.count():
        return False
    log.debug("Entering provision_scheduled_recipesets")
    for rs_id, in recipesets.values(RecipeSet.id):
        log.info("scheduled_recipesets: RS:%s" % rs_id)
        session.begin()
        try:
            provision_scheduled_recipeset(rs_id)
            session.commit()
        except exceptions.Exception:
            log.exception('Error in provision_scheduled_recipeset(%s)', rs_id)
            session.rollback()
        finally:
            session.close()
    log.debug("Exiting provision_scheduled_recipesets")
    return True

def provision_scheduled_recipeset(recipeset_id):
    recipeset = RecipeSet.by_id(recipeset_id)
    # Go through each recipe in the recipeSet
    for recipe in recipeset.recipes:
        try:
            recipe.waiting()
            recipe.provision()
        except Exception, e:
            log.exception("Failed to provision recipeid %s", recipe.id)
            recipe.recipeset.abort(u"Failed to provision recipeid %s, %s"
                    % (recipe.id, e))
            return

def recipe_count_metrics():
    query = Recipe.query.group_by(Recipe.status)\
            .having(Recipe.status.in_([s for s in TaskStatus if not s.finished]))\
            .values(Recipe.status, func.count(Recipe.id))
    for status, count in query:
        metrics.measure('gauges.recipes_%s' % status.name, count)

def system_count_metrics():
    all = System.query
    for state, count in utilisation.system_utilisation_counts(all).iteritems():
        if state != 'idle_removed':
            metrics.measure('gauges.systems_%s.total' % state, count)
    shared = System.query.filter(System.private == False)\
            .filter(System.shared == True)\
            .filter(System.group_assocs == None)
    for state, count in utilisation.system_utilisation_counts(shared).iteritems():
        if state != 'idle_removed':
            metrics.measure('gauges.systems_%s.shared' % state, count)

# These functions are run in separate threads, so we want to log any uncaught 
# exceptions instead of letting them be written to stderr and lost to the ether

@log_traceback(log)
def new_recipes_loop(*args, **kwargs):
    while running:
        if not process_new_recipes():
            event.wait()
    log.debug("new recipes thread exiting")

@log_traceback(log)
def processed_recipesets_loop(*args, **kwargs):
    while running:
        if not queue_processed_recipesets():
            event.wait()
    log.debug("processed recipesets thread exiting")

@log_traceback(log)
def metrics_loop(*args, **kwargs):
    while running:
        try:
            start = time.time()
            recipe_count_metrics()
            system_count_metrics()
        except Exception:
            log.exception('Exception in metrics loop')
        time.sleep(max(30.0 + start - time.time(), 5.0))

@log_traceback(log)
def main_recipes_loop(*args, **kwargs):
    while running:
        abort_dead_recipes()
        if config.get('ovirt.enabled', False):
            virt = provision_virt_recipes()
        else:
            virt = False
        queued = schedule_queued_recipes()
        scheduled = provision_scheduled_recipesets()
        if not virt and not queued and not scheduled:
            event.wait()
    log.debug("main recipes thread exiting")

def schedule():
    global running

    reload_config()

    if config.get('carbon.address'):
        log.debug('starting metrics thread')
        metrics_thread = threading.Thread(target=metrics_loop, name='metrics')
        metrics_thread.daemon = True
        metrics_thread.start()

    beakerd_threads = set(["new_recipes", "processed_recipesets",\
                           "main_recipes"])

    log.debug("starting new recipes thread")
    new_recipes_thread = threading.Thread(target=new_recipes_loop,
                                          name="new_recipes")
    new_recipes_thread.daemon = True
    new_recipes_thread.start()

    log.debug("starting processed_recipes thread")
    processed_recipesets_thread = threading.Thread(target=processed_recipesets_loop,
                                                   name="processed_recipesets")
    processed_recipesets_thread.daemon = True
    processed_recipesets_thread.start()

    log.debug("starting main recipes thread")
    main_recipes_thread = threading.Thread(target=main_recipes_loop,
                                           name="main_recipes")
    main_recipes_thread.daemon = True
    main_recipes_thread.start()

    try:
        while True:
            time.sleep(20)
            running_threads = set([t.name for t in threading.enumerate()])
            if not running_threads.issuperset(beakerd_threads):
                log.critical("a thread has died, shutting down")
                rc = 1
                running = False
                event.set()
                break
            event.set()
            event.clear()
    except (SystemExit, KeyboardInterrupt):
       log.info("shutting down")
       running = False
       event.set()
       rc = 0

    new_recipes_thread.join(10)
    processed_recipesets_thread.join(10)
    main_recipes_thread.join(10)

    sys.exit(rc)

@atexit.register
def stop_interface():
    interface.stop()

def sighup_handler(signal, frame):
    log.info("received SIGHUP, reloading")
    reload_config()
    log.info("configuration reloaded")

def sigterm_handler(signal, frame):
    raise SystemExit("received SIGTERM")

def purge_handlers():
    #shutdown logging subsystem
    logging.shutdown()

    # Remove handlers
    for (_, logger) in logging.root.manager.loggerDict.items():
        if hasattr(logger, 'handlers'):
            for handler in logger.handlers:
                logger.removeHandler(handler)

    #clear out logging's internal handler list
    logging._handlerList = []


def reload_config():
    purge_handlers()

    if interface.running:
        interface.stop()

    load_config(opts.configfile)
    interface.start(config)

def main():
    global opts
    parser = get_parser()
    opts, args = parser.parse_args()

    # First look on the command line for a desired config file,
    # if it's not on the command line, then look for 'setup.py'
    # in the current directory. If there, load configuration
    # from a file called 'dev.cfg'. If it's not there, the project
    # is probably installed and we'll look first for a file called
    # 'prod.cfg' in the current directory and then for a default
    # config file called 'default.cfg' packaged in the egg.
    load_config(opts.configfile)

    signal.signal(signal.SIGHUP, sighup_handler)
    signal.signal(signal.SIGINT, sigterm_handler)
    signal.signal(signal.SIGTERM, sigterm_handler)

    if not opts.foreground:
        log.debug("Launching beakerd daemon")
        pid_file = opts.pid_file
        if pid_file is None:
            pid_file = config.get("PID_FILE", "/var/run/beaker/beakerd.pid")
        d = daemon.DaemonContext(pidfile=pidfile.TimeoutPIDLockFile(pid_file, acquire_timeout=0),)
        util_logger = logging.getLogger('bkr.server.util')
        util_logger.disabled = True

        purge_handlers()

        try:
            d.open()
        except pidlockfile.AlreadyLocked:
            reload_config() # reopen logfiles
            log.fatal("could not acquire lock on %s, exiting" % pid_file)
            sys.stderr.write("could not acquire lock on %s" % pid_file)
            sys.exit(1)
    else:
        signal.signal(signal.SIGHUP, sighup_handler)
        signal.signal(signal.SIGTERM, sigterm_handler)
        signal.signal(signal.SIGINT, sigterm_handler)

    schedule()

if __name__ == "__main__":
    main()
