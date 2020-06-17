
# -*- coding: utf-8 -*-

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# pkg_resources.requires() does not work if multiple versions are installed in
# parallel. This semi-supported hack using __requires__ is the workaround.
# http://bugs.python.org/setuptools/issue139
# (Fedora/EPEL has python-cherrypy2 = 2.3 and python-cherrypy = 3)
__requires__ = ['CherryPy < 3.0']

import sys
import os
import random
from bkr.common import __version__
from bkr.log import log_to_stream, log_to_syslog
from bkr.server import needpropertyxml, utilisation, metrics, dynamic_virt
from bkr.server.bexceptions import BX, \
    StaleTaskStatusException, InsufficientSystemPermissions, \
    StaleSystemUserException
from bkr.server.model import (Job, RecipeSet, Recipe, MachineRecipe,
        GuestRecipe, RecipeVirtStatus, TaskStatus, TaskPriority, LabController,
        Watchdog, System, DistroTree, LabControllerDistroTree, SystemStatus,
        SystemResource, GuestResource, Arch,
        SystemAccessPolicy, SystemPermission, ConfigItem, Command,
        Power, PowerType, DataMigration, SystemSchedulerStatus)
from bkr.server.model.scheduler import machine_guest_map
from bkr.server.needpropertyxml import XmlHost
from bkr.server.util import load_config_or_exit, log_traceback, \
        get_reports_engine
from bkr.server.recipetasks import RecipeTasks
from turbogears.database import session, get_engine
from turbogears import config
from turbomail.control import interface
from xmlrpclib import ProtocolError
from sqlalchemy.exc import OperationalError
from sqlalchemy.sql import exists
from sqlalchemy.sql.expression import func, select, and_, or_, not_
from sqlalchemy.orm import create_session

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
import concurrent.futures
import logging

log = logging.getLogger(__name__)
running = True
event = threading.Event()
_threadpool_executor = None

from optparse import OptionParser

__description__ = 'Beaker Scheduler'


def get_parser():
    usage = "usage: %prog [options]"
    parser = OptionParser(usage, description=__description__,
                          version=__version__)
    parser.add_option("-f", "--foreground", default=False, action="store_true",
                      help="run in foreground (do not spawn a daemon)")
    parser.add_option("-p", "--pid-file",
                      help="specify a pid file")
    parser.add_option("-c", "--config", action="store", type="string",
                      dest="configfile", help="location of config file.")
    return parser

def _virt_enabled():
    return bool(config.get('openstack.identity_api_url'))

def _virt_possible(recipe):
    return _virt_enabled() and recipe.virt_status == RecipeVirtStatus.possible

def get_virt_executor():
    global _threadpool_executor
    if _threadpool_executor is None:
       _threadpool_executor = concurrent.futures.ThreadPoolExecutor(max_workers=5)
    return _threadpool_executor

def update_dirty_jobs():
    work_done = False
    with session.begin():
        dirty_jobs = Job.query.filter(Job.is_dirty)
        job_ids = [job_id for job_id, in dirty_jobs.values(Job.id)]
    if job_ids:
        log.debug('Updating dirty jobs [%s ... %s] (%d total)',
                  job_ids[0], job_ids[-1], len(job_ids))
    for job_id in job_ids:
        session.begin()
        try:
            update_dirty_job(job_id)
            session.commit()
        except Exception as e:
            log.exception('Error in update_dirty_job(%s)', job_id)
            session.rollback()
        finally:
            session.close()
        work_done = True
        if event.is_set():
            break
    return work_done

def update_dirty_job(job_id):
    log.debug('Updating dirty job %s', job_id)
    job = Job.query.filter(Job.id == job_id).with_lockmode('update').one()
    job.update_status()

def process_new_recipes(*args):
    work_done = False
    with session.begin():
        recipes = MachineRecipe.query\
                .join(MachineRecipe.recipeset).join(RecipeSet.job)\
                .filter(Recipe.status == TaskStatus.new)
        recipe_ids = [recipe_id for recipe_id, in recipes.values(MachineRecipe.id)]
    if recipe_ids:
        log.debug('Processing new recipes [%s ... %s] (%d total)',
                  recipe_ids[0], recipe_ids[-1], len(recipe_ids))
    for recipe_id in recipe_ids:
        session.begin()
        try:
            process_new_recipe(recipe_id)
            session.commit()
        except Exception as e:
            log.exception('Error in process_new_recipe(%s)', recipe_id)
            session.rollback()
        finally:
            session.close()
        work_done = True
    return work_done

def process_new_recipe(recipe_id):
    recipe = MachineRecipe.by_id(recipe_id)
    recipe.systems = []

    # Do the query twice.

    # First query verifies that the distro tree
    # exists in at least one lab that has a matching system.
    # But if it's a user-supplied distro, we don't have a
    # distro tree to match the lab against - so it will return
    # all possible systems
    systems = recipe.candidate_systems(only_in_lab=True)
    # Second query picks up all possible systems so that as
    # trees appear in other labs those systems will be
    # available.
    all_systems = recipe.candidate_systems(only_in_lab=False)
    # based on above queries, condition on systems but add
    # all_systems.
    log.debug('Counting candidate systems for recipe %s', recipe.id)
    if systems.count():
        log.debug('Computing all candidate systems for recipe %s', recipe.id)
        for system in all_systems:
            # Add matched systems to recipe.
            recipe.systems.append(system)

    # If the recipe only matches one system then bump its priority.
    if config.get('beaker.priority_bumping_enabled', True) and len(recipe.systems) == 1:
        old_prio = recipe.recipeset.priority
        try:
            new_prio = TaskPriority.by_index(TaskPriority.index(old_prio) + 1)
        except IndexError:
            # We may already be at the highest priority
            pass
        else:
            log.info("recipe ID %s matches one system, bumping priority" % recipe.id)
            recipe.recipeset.record_activity(user=None, service=u'Scheduler',
                    action=u'Changed', field=u'Priority',
                    old=unicode(old_prio), new=unicode(new_prio))
            recipe.recipeset.priority = new_prio
    recipe.virt_status = recipe.check_virtualisability()
    if not recipe.systems and not _virt_possible(recipe):
        log.info("recipe ID %s moved from New to Aborted" % recipe.id)
        recipe.recipeset.abort(u'Recipe ID %s does not match any systems' % recipe.id)
        return
    recipe.process()
    log.info("recipe ID %s moved from New to Processed" % recipe.id)
    for guestrecipe in recipe.guests:
        guestrecipe.process()

def queue_processed_recipesets(*args):
    work_done = False
    with session.begin():
        recipesets = RecipeSet.by_recipe_status(TaskStatus.processed)\
                .order_by(RecipeSet.priority.desc())\
                .order_by(RecipeSet.id)
        recipeset_ids = [rs_id for rs_id, in recipesets.values(RecipeSet.id)]
    if recipeset_ids:
        log.debug('Queuing processed recipe sets [%s ... %s] (%d total)',
                  recipeset_ids[0], recipeset_ids[-1], len(recipeset_ids))
    for rs_id in recipeset_ids:
        session.begin()
        try:
            queue_processed_recipeset(rs_id)
            session.commit()
        except Exception as e:
            log.exception('Error in queue_processed_recipeset(%s)', rs_id)
            session.rollback()
        finally:
            session.close()
        work_done = True
    return work_done

def queue_processed_recipeset(recipeset_id):
    recipeset = RecipeSet.by_id(recipeset_id)

    # We only need to check "not enough systems" logic for multi-host recipe sets
    if len(list(recipeset.machine_recipes)) > 1:
        bad_l_controllers = set()
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
        # Make the removal of systems visible to subsequent queries which use .dyn_systems
        session.flush()

        # Are we left with any recipes having no candidate systems?
        dead_recipes = [recipe for recipe in recipeset.machine_recipes if not recipe.systems]
        if dead_recipes:
            # Set status to Aborted
            log.debug('Not enough systems logic for %s left %s with no candidate systems',
                    recipeset.t_id, ', '.join(recipe.t_id for recipe in dead_recipes))
            log.info('%s moved from Processed to Aborted' % recipeset.t_id)
            recipeset.abort(u'Recipe ID %s does not match any systems'
                    % ', '.join(str(recipe.id) for recipe in dead_recipes))
            return

    # Can we schedule any recipes immediately?
    for recipe in recipeset.machine_recipes:
        systems = recipe.matching_systems()
        if not systems: # may be None if we know there are no possible LCs
            continue
        system_count = systems.count()
        if not system_count:
            continue
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
        if True: #FIXME if pools are defined add them here in the order requested.
            systems = System.scheduler_ordering(recipeset.job.owner, query=systems)
        if recipe.autopick_random:
            system = systems[random.randrange(0, system_count)]
        else:
            system = systems.first()
        schedule_recipe_on_system(recipe, system)

    for recipe in recipeset.machine_recipes:
        if recipe.status == TaskStatus.processed:
            # Leave it Queued until a system becomes free
            log.info("recipe: %s moved from Processed to Queued" % recipe.id)
            recipe.queue()
            for guestrecipe in recipe.guests:
                guestrecipe.queue()

def abort_dead_recipes(*args):
    work_done = False
    with session.begin():
        filters = [not_(DistroTree.lab_controller_assocs.any())]
        if _virt_enabled():
            filters.append(and_(not_(Recipe.systems.any()),
                    Recipe.virt_status != RecipeVirtStatus.possible))
        else:
            filters.append(not_(Recipe.systems.any()))

        # Following query is looking for recipes stuck in Queued state.
        # This may be caused by no longer valid distribution in Lab Controller
        # or no machines available.
        # However, we have to account that custom distribution can be
        # used and this distribution is not stored in Database at all.
        recipes = MachineRecipe.query\
                .join(MachineRecipe.recipeset).join(RecipeSet.job)\
                .filter(not_(Job.is_dirty))\
                .outerjoin(Recipe.distro_tree)\
                .outerjoin(Recipe.systems) \
                .filter(Recipe.status == TaskStatus.queued)\
                .filter(or_(DistroTree.id.isnot(None), System.status == SystemStatus.broken)) \
                .filter(or_(*filters))
        recipe_ids = [recipe_id for recipe_id, in recipes.values(MachineRecipe.id)]
    if recipe_ids:
        log.debug('Aborting dead recipes [%s ... %s] (%d total)',
                  recipe_ids[0], recipe_ids[-1], len(recipe_ids))
    for recipe_id in recipe_ids:
        session.begin()
        try:
            abort_dead_recipe(recipe_id)
            session.commit()
        except exceptions.Exception as e:
            log.exception('Error in abort_dead_recipe(%s)', recipe_id)
            session.rollback()
        finally:
            session.close()
        work_done = True
    return work_done

def abort_dead_recipe(recipe_id):
    recipe = MachineRecipe.by_id(recipe_id)
    # There are two ways to have your recipe aborted;
    # no distros, or no automated systems available
    if recipe.distro_tree and len(recipe.distro_tree.lab_controller_assocs) == 0:
        msg = u"R:%s does not have a valid distro tree, aborting." % recipe.id
        log.info(msg)
        recipe.recipeset.abort(msg)
    else:
        msg = u"R:%s does not match any systems, aborting." % recipe.id
        log.info(msg)
        recipe.recipeset.abort(msg)

def schedule_pending_systems():
    work_done = False
    with session.begin():
        systems = System.query\
                .join(System.lab_controller)\
                .filter(LabController.disabled == False)\
                .filter(System.scheduler_status == SystemSchedulerStatus.pending)
        system_ids = [system_id for system_id, in systems.values(System.id)]
    if system_ids:
        log.debug('Scheduling pending systems (%d total)', len(system_ids))
    for system_id in system_ids:
        session.begin()
        try:
            schedule_pending_system(system_id)
            session.commit()
        except Exception as e:
            log.exception('Error in schedule_pending_system(%s)', system_id)
            session.rollback()
        finally:
            session.close()
        work_done = True
    return work_done

def schedule_pending_system(system_id):
    system = System.query.get(system_id)
    # Do we have any queued recipes which could run on this system?
    log.debug('Checking for queued recipes which are runnable on %s', system.fqdn)
    recipes = MachineRecipe.runnable_on_system(system)
    # Effective priority is given in the following order:
    # * Multi host recipes with already scheduled siblings
    # * Priority level (i.e Normal, High etc)
    # * RecipeSet id
    # * Recipe id
    recipes = recipes.order_by(RecipeSet.lab_controller == None)\
        .order_by(RecipeSet.priority.desc())\
        .order_by(RecipeSet.id)\
        .order_by(Recipe.id)
    recipe = recipes.first()
    if not recipe:
        log.debug('No recipes runnable on %s, returning to idle', system.fqdn)
        system.scheduler_status = SystemSchedulerStatus.idle
        return
    # Check to see if user still has proper permissions to use the system.
    # Remember the mapping of available systems could have happend hours or even
    # days ago and groups or loans could have been put in place since.
    if not recipe.candidate_systems().filter(System.id == system.id).first():
        log.debug("System : %s recipe: %s no longer has access. removing" % (system,
                                                                             recipe.id))
        recipe.systems.remove(system)
        # Try again on the next pass.
        return
    schedule_recipe_on_system(recipe, system)

def schedule_recipe_on_system(recipe, system):
    log.debug('Assigning recipe %s to system %s', recipe.id, system.fqdn)
    recipe.resource = SystemResource(system=system)
    # Reserving the system may fail here if someone stole it out from
    # underneath us, but that is fine...
    recipe.resource.allocate()
    recipe.schedule()
    recipe.createRepo()
    recipe.recipeset.lab_controller = system.lab_controller
    recipe.clear_candidate_systems()
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
    work_done = False
    with session.begin():
        recipes = MachineRecipe.query\
                .join(Recipe.recipeset).join(RecipeSet.job)\
                .join(Recipe.distro_tree, DistroTree.lab_controller_assocs, LabController)\
                .filter(Recipe.status == TaskStatus.queued)\
                .filter(Recipe.virt_status == RecipeVirtStatus.possible)\
                .filter(LabController.disabled == False)\
                .filter(or_(RecipeSet.lab_controller == None,
                    RecipeSet.lab_controller_id == LabController.id))\
                .order_by(RecipeSet.priority.desc(), Recipe.id.asc())
        recipe_ids = [recipe_id for recipe_id, in recipes.values(Recipe.id.distinct())]
    if recipe_ids:
        log.debug('Provisioning dynamic virt guests for recipes [%s ... %s] (%d total)',
                  recipe_ids[0], recipe_ids[-1], len(recipe_ids))
    futures = [get_virt_executor().submit(provision_virt_recipe, recipe_id)
               for recipe_id in recipe_ids]
    if futures:
        concurrent.futures.wait(futures)
        work_done = True
    return work_done

def provision_virt_recipe(recipe_id):
    log.debug('Attempting to provision dynamic virt guest for recipe %s', recipe_id)
    session.begin()
    try:
        recipe = Recipe.by_id(recipe_id)
        job_owner = recipe.recipeset.job.owner
        manager = dynamic_virt.VirtManager(job_owner)
        available_flavors = manager.available_flavors()
        # We want them in order of smallest to largest, so that we can pick the
        # smallest flavor that satisfies the recipe's requirements. Sorting by RAM
        # is a decent approximation.
        possible_flavors = XmlHost.from_string(recipe.host_requires)\
            .filter_openstack_flavors(available_flavors, manager.lab_controller)
        if not possible_flavors:
            log.info('No OpenStack flavors matched recipe %s, marking precluded',
                    recipe.id)
            recipe.virt_status = RecipeVirtStatus.precluded
            return
        # cheapest flavor has the smallest disk and ram
        # id guarantees consistency of our results
        flavor = min(possible_flavors, key=lambda flavor: (flavor.ram, flavor.disk, flavor.id))
        vm_name = '%srecipe-%s' % (
                ConfigItem.by_name(u'guest_name_prefix').current_value(u'beaker-'),
                recipe.id)
        log.debug('Creating VM named %s as flavor %s', vm_name, flavor)
        vm = manager.create_vm(vm_name, flavor)
        vm.instance_created = datetime.utcnow()
        try:
            recipe.createRepo()
            recipe.clear_candidate_systems()
            recipe.watchdog = Watchdog()
            recipe.resource = vm
            recipe.recipeset.lab_controller = manager.lab_controller
            recipe.virt_status = RecipeVirtStatus.succeeded
            recipe.schedule()
            log.info("recipe ID %s moved from Queued to Scheduled by provision_virt_recipe",
                     recipe.id)
            recipe.waiting()
            recipe.provision()
            log.info("recipe ID %s moved from Scheduled to Waiting by provision_virt_recipe",
                     recipe.id)
        except:
            exc_type, exc_value, exc_tb = sys.exc_info()
            try:
                manager.destroy_vm(vm)
            except Exception:
                log.exception('Failed to clean up VM %s during provision_virt_recipe, leaked!',
                              vm.instance_id)
                # suppress this exception so the original one is not masked
            raise exc_type, exc_value, exc_tb
        session.commit()
    except Exception as e:
        log.exception('Error in provision_virt_recipe(%s)', recipe_id)
        session.rollback()
        # As an added precaution, let's try and avoid this recipe in future
        with session.begin():
            recipe = Recipe.by_id(recipe_id)
            recipe.virt_status = RecipeVirtStatus.failed
    finally:
        session.close()

def provision_scheduled_recipesets(*args):
    """
    if All recipes in a recipeSet are in Scheduled state then move them to
     Running.
    """
    work_done = False
    with session.begin():
        recipesets = RecipeSet.by_recipe_status(TaskStatus.scheduled)
        recipeset_ids = [rs_id for rs_id, in recipesets.values(RecipeSet.id)]
    if recipeset_ids:
        log.debug('Provisioning scheduled recipe sets [%s ... %s] (%d total)',
                  recipeset_ids[0], recipeset_ids[-1], len(recipeset_ids))
    for rs_id in recipeset_ids:
        session.begin()
        try:
            provision_scheduled_recipeset(rs_id)
            session.commit()
        except exceptions.Exception:
            log.exception('Error in provision_scheduled_recipeset(%s)', rs_id)
            session.rollback()
        finally:
            session.close()
        work_done = True
    return work_done

def provision_scheduled_recipeset(recipeset_id):
    recipeset = RecipeSet.by_id(recipeset_id)
    # Go through each recipe in the recipeSet
    for recipe in recipeset.recipes:
        log.debug('Provisioning recipe %s in RS:%s', recipe.id, recipeset_id)
        try:
            recipe.waiting()
            recipe.provision()
        except Exception as e:
            # Make sure that rollback is first instruction here before touching ORM again
            # Otherwise, ORM will raise another exception
            session.rollback()
            log.exception("Failed to provision recipeid %s", recipe.id)
            session.begin()
            recipe.recipeset.abort(u"Failed to provision recipeid %s, %s" % (recipe.id, e))
            return

# Online data migration

# This is populated by schedule() on startup, and then updated by
# run_data_migrations() as migrations are completed.
_outstanding_data_migrations = []

def run_data_migrations():
    migration = _outstanding_data_migrations[0]
    log.debug('Performing online data migration %s (one batch)', migration.name)
    finished = migration.migrate_one_batch(get_engine())
    if finished:
        log.debug('Marking online data migration %s as finished', migration.name)
        with session.begin():
            migration.mark_as_finished()
        session.close()
        _outstanding_data_migrations.pop(0)
    return True

# Real-time metrics reporting

# Recipe queue
def _recipe_count_metrics_for_query(name, query=None):
    for status, count in MachineRecipe.get_queue_stats(query).items():
        metrics.measure('gauges.recipes_%s.%s' % (status, name), count)

def _recipe_count_metrics_for_query_grouped(name, grouping, query):
    group_counts = MachineRecipe.get_queue_stats_by_group(grouping, query)
    for group, counts in group_counts.iteritems():
        for status, count in counts.iteritems():
            metrics.measure('gauges.recipes_%s.%s.%s' %
                                   (status, name, group), count)

def recipe_count_metrics():
    _recipe_count_metrics_for_query('all')
    _recipe_count_metrics_for_query(
            'dynamic_virt_possible',
            MachineRecipe.query.filter(
                MachineRecipe.virt_status == RecipeVirtStatus.possible)
            )
    _recipe_count_metrics_for_query_grouped(
            'by_arch', Arch.arch,
            MachineRecipe.query.join(DistroTree).join(Arch))


# System utilisation
def _system_count_metrics_for_query(name, query):
    counts = utilisation.system_utilisation_counts(query)
    for state, count in counts.iteritems():
        if state != 'idle_removed':
            metrics.measure('gauges.systems_%s.%s' % (state, name), count)

def _system_count_metrics_for_query_grouped(name, grouping, query):
    group_counts = utilisation.system_utilisation_counts_by_group(grouping, query)
    for group, counts in group_counts.iteritems():
        for state, count in counts.iteritems():
            if state != 'idle_removed':
                metrics.measure('gauges.systems_%s.%s.%s' % (state, name,
                        group.replace('.', '_')), count)

def system_count_metrics():
    _system_count_metrics_for_query('all', System.query)
    _system_count_metrics_for_query('shared', System.query
            .outerjoin(System.active_access_policy)
            .filter(SystemAccessPolicy.grants_everybody(SystemPermission.reserve)))
    _system_count_metrics_for_query_grouped('by_arch', Arch.arch,
            System.query.join(System.arch))
    _system_count_metrics_for_query_grouped('by_lab', LabController.fqdn,
            System.query.join(System.lab_controller))

# System power commands
def _system_command_metrics_for_query(name, query):
    for status, count in Command.get_queue_stats(query).items():
        metrics.measure('gauges.system_commands_%s.%s' % (status, name), count)

def _system_command_metrics_for_query_grouped(name, grouping, query):
    group_counts = Command.get_queue_stats_by_group(grouping, query)
    for group, counts in group_counts.iteritems():
        for status, count in counts.iteritems():
            metrics.measure('gauges.system_commands_%s.%s.%s'
                    % (status, name, group.replace('.', '_')), count)

def system_command_metrics():
    _system_command_metrics_for_query('all', Command.query)
    _system_command_metrics_for_query_grouped('by_lab', LabController.fqdn,
            Command.query.join(Command.system).join(System.lab_controller))
    _system_command_metrics_for_query_grouped('by_arch', Arch.arch,
            Command.query.join(Command.system).join(System.arch))
    _system_command_metrics_for_query_grouped('by_power_type', PowerType.name,
            Command.query.join(Command.system).join(System.power)
                .join(Power.power_type))

# Dirty jobs
def dirty_job_metrics():
    metrics.measure('gauges.dirty_jobs', Job.query.filter(Job.is_dirty).count())

# These functions are run in separate threads, so we want to log any uncaught
# exceptions instead of letting them be written to stderr and lost to the ether

@log_traceback(log)
def metrics_loop(*args, **kwargs):
    # bind thread local session to reports_engine
    metrics_session = create_session(bind=get_reports_engine())
    session.registry.set(metrics_session)

    while running:
        start = time.time()
        try:
            session.begin()
            recipe_count_metrics()
            system_count_metrics()
            dirty_job_metrics()
            system_command_metrics()
        except Exception:
            log.exception('Exception in metrics loop')
        finally:
            session.close()
        end = time.time()
        duration = end - start
        if duration >= 30.0:
            log.debug("Metrics collection took %d seconds", duration)
        time.sleep(max(30.0 - duration, 5.0))

def _main_recipes():
    work_done = False
    if update_dirty_jobs():
        work_done = True
    if abort_dead_recipes():
        work_done = True
        update_dirty_jobs()
    if process_new_recipes():
        work_done = True
        update_dirty_jobs()
    if queue_processed_recipesets():
        work_done = True
        update_dirty_jobs()
    if _virt_enabled():
        if provision_virt_recipes():
            work_done = True
            update_dirty_jobs()
    if schedule_pending_systems():
        work_done = True
        update_dirty_jobs()
    if provision_scheduled_recipesets():
        work_done = True
        # update_dirty_jobs() will be done at the start of the next loop
        # iteration, so no need to do it here at the end as well
    if _outstanding_data_migrations:
        run_data_migrations()
        work_done = True
    return work_done

@log_traceback(log)
def main_recipes_loop(*args, **kwargs):
    while running:
        work_done = _main_recipes()
        if not work_done:
            event.wait()
    log.debug("main recipes thread exiting")

def schedule():
    global running
    global _outstanding_data_migrations

    _outstanding_data_migrations = [m for m in DataMigration.all() if not m.is_finished]
    if _outstanding_data_migrations:
        log.debug('Incomplete data migrations will be run: %s',
                ', '.join(m.name for m in _outstanding_data_migrations))

    interface.start(config)

    if config.get('carbon.address'):
        log.debug('starting metrics thread')
        metrics_thread = threading.Thread(target=metrics_loop, name='metrics')
        metrics_thread.daemon = True
        metrics_thread.start()

    beakerd_threads = set(["main_recipes"])

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

    if _threadpool_executor:
        _threadpool_executor.shutdown()
    interface.stop()
    main_recipes_thread.join(10)

    sys.exit(rc)

def sigterm_handler(signal, frame):
    raise SystemExit("received SIGTERM")

def main():
    global opts
    parser = get_parser()
    opts, args = parser.parse_args()

    load_config_or_exit(opts.configfile)

    signal.signal(signal.SIGINT, sigterm_handler)
    signal.signal(signal.SIGTERM, sigterm_handler)

    if opts.foreground:
        log_to_stream(sys.stderr, level=logging.DEBUG)
    else:
        log_to_syslog('beakerd')
        pid_file = opts.pid_file
        if pid_file is None:
            pid_file = config.get("PID_FILE", "/var/run/beaker/beakerd.pid")
        d = daemon.DaemonContext(pidfile=pidfile.TimeoutPIDLockFile(pid_file, acquire_timeout=0),
                                 detach_process=True)
        try:
            d.open()
        except pidlockfile.AlreadyLocked:
            log.fatal("could not acquire lock on %s, exiting" % pid_file)
            sys.stderr.write("could not acquire lock on %s" % pid_file)
            sys.exit(1)

    schedule()

if __name__ == "__main__":
    main()
