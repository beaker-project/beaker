
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
from bkr.log import log_to_stream, log_to_syslog
from bkr.server import needpropertyxml, utilisation, metrics, dynamic_virt
from bkr.server.bexceptions import BX, \
    StaleTaskStatusException, InsufficientSystemPermissions, \
    StaleSystemUserException
from bkr.server.model import (Job, RecipeSet, Recipe, MachineRecipe,
        GuestRecipe, RecipeVirtStatus, TaskStatus, TaskPriority, LabController,
        Watchdog, System, DistroTree, LabControllerDistroTree, SystemStatus,
        VirtResource, SystemResource, GuestResource, Arch,
        SystemAccessPolicy, SystemPermission, ConfigItem)
from bkr.server.model.scheduler import machine_guest_map
from bkr.server.needpropertyxml import XmlHost
from bkr.server.util import load_config_or_exit, log_traceback
from bkr.server.recipetasks import RecipeTasks
from turbogears.database import session
from turbogears import config
from turbomail.control import interface
from xmlrpclib import ProtocolError
from sqlalchemy.exc import OperationalError
from sqlalchemy.sql.expression import func, select, and_, or_, not_
from sqlalchemy.orm import aliased

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

log = logging.getLogger(__name__)
running = True
event = threading.Event()

from optparse import OptionParser

__version__ = '0.1'
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

def update_dirty_jobs():
    dirty_jobs = Job.query.filter(Job.dirty_version != Job.clean_version)
    if not dirty_jobs.count():
        return False
    log.debug("Entering update_dirty_jobs")
    for job_id, in dirty_jobs.values(Job.id):
        session.begin()
        try:
            update_dirty_job(job_id)
            session.commit()
        except Exception, e:
            log.exception('Error in update_dirty_job(%s)', job_id)
            session.rollback()
        finally:
            session.close()
        if event.is_set():
            break
    log.debug("Exiting update_dirty_jobs")
    return True

def update_dirty_job(job_id):
    log.debug('Updating dirty job %s', job_id)
    job = Job.by_id(job_id)
    job.update_status()

def process_new_recipes(*args):
    recipes = MachineRecipe.query\
            .join(MachineRecipe.recipeset).join(RecipeSet.job)\
            .filter(Job.dirty_version == Job.clean_version)\
            .filter(Recipe.status == TaskStatus.new)
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
    systems = recipe.candidate_systems(only_in_lab=True)
    # Second query picks up all possible systems so that as 
    # trees appear in other labs those systems will be 
    # available.
    all_systems = recipe.candidate_systems(only_in_lab=False)
    # based on above queries, condition on systems but add
    # all_systems.
    if systems.count():
        for system in all_systems:
            # Add matched systems to recipe.
            recipe.systems.append(system)

    # If the recipe only matches one system then bump its priority.
    if config.get('beaker.priority_bumping_enabled', True) and len(recipe.systems) == 1:
        try:
            log.info("recipe ID %s matches one system, bumping priority" % recipe.id)
            recipe.recipeset.priority = TaskPriority.by_index(
                    TaskPriority.index(recipe.recipeset.priority) + 1)
        except IndexError:
            # We may already be at the highest priority
            pass
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
    recipesets = RecipeSet.query.join(RecipeSet.job)\
            .filter(and_(Job.dirty_version == Job.clean_version, Job.deleted == None))\
            .filter(not_(RecipeSet.recipes.any(
                Recipe.status != TaskStatus.processed)))
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
    # Are we left with any recipes having no candidate systems?
    dead_recipes = [recipe for recipe in recipeset.machine_recipes if not recipe.systems]
    if dead_recipes:
        # Set status to Aborted
        log.debug('Not enough systems logic for %s left %s with no candidate systems',
                recipeset.t_id, ', '.join(recipe.t_id for recipe in dead_recipes))
        log.info('%s moved from Processed to Aborted' % recipeset.t_id)
        recipeset.abort(u'Recipe ID %s does not match any systems'
                % ', '.join(str(recipe.id) for recipe in dead_recipes))
    else:
        for recipe in recipeset.machine_recipes:
            # Set status to Queued
            log.info("recipe: %s moved from Processed to Queued" % recipe.id)
            recipe.queue()
            for guestrecipe in recipe.guests:
                guestrecipe.queue()

def abort_dead_recipes(*args):
    filters = [not_(DistroTree.lab_controller_assocs.any())]
    if _virt_enabled():
        filters.append(and_(not_(Recipe.systems.any()),
                Recipe.virt_status != RecipeVirtStatus.possible))
    else:
        filters.append(not_(Recipe.systems.any()))
    recipes = MachineRecipe.query\
            .join(MachineRecipe.recipeset).join(RecipeSet.job)\
            .filter(Job.dirty_version == Job.clean_version)\
            .outerjoin(Recipe.distro_tree)\
            .filter(Recipe.status == TaskStatus.queued)\
            .filter(or_(*filters))
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
    # There are two ways to have your recipe aborted;
    # no distros, or no automated systems available
    if len(recipe.distro_tree.lab_controller_assocs) == 0:
        msg = u"R:%s does not have a valid distro tree, aborting." % recipe.id
        log.info(msg)
        recipe.recipeset.abort(msg)
    else:
        msg = u"R:%s does not match any systems, aborting." % recipe.id
        log.info(msg)
        recipe.recipeset.abort(msg)

def schedule_queued_recipes(*args):
    session.begin()
    try:
        # This query returns a queued host recipe and and the guest which has
        # the most recent distro tree. It is to be used as a derived table.
        latest_guest_distro = select([machine_guest_map.c.machine_recipe_id.label('host_id'),
            func.max(DistroTree.date_created).label('latest_distro_date')],
            from_obj=[machine_guest_map.join(GuestRecipe.__table__,
                    machine_guest_map.c.guest_recipe_id==GuestRecipe.__table__.c.id). \
                join(Recipe.__table__).join(DistroTree.__table__)],
            whereclause=Recipe.status=='Queued',
            group_by=machine_guest_map.c.machine_recipe_id).alias()

        hosts_lab_controller_distro_map = aliased(LabControllerDistroTree)
        hosts_distro_tree = aliased(DistroTree)
        guest_recipe = aliased(Recipe)
        guests_distro_tree = aliased(DistroTree)
        guests_lab_controller = aliased(LabController)

        # This query will return queued recipes that are eligible to be scheduled.
        # They are determined to be eligible if:
        # * They are clean
        # * There are systems available (see the filter criteria) in lab controllers where
        #   the recipe's distro tree is available.
        # * If it is a host recipe, the most recently created distro of all
        #   the guest recipe's distros is available in at least one of the same
        #   lab controllers as that of the host's distro tree.
        #
        # Also note that we do not try to handle the situation where the guest and host never
        # have a common labcontroller. In that situation the host and guest would stay queued
        # until that situation was rectified.
        recipes = MachineRecipe.query\
            .join(Recipe.recipeset, RecipeSet.job)\
            .filter(Job.dirty_version == Job.clean_version)\
            .outerjoin((guest_recipe, MachineRecipe.guests))\
            .outerjoin((guests_distro_tree, guest_recipe.distro_tree_id == guests_distro_tree.id))\
            .outerjoin((latest_guest_distro,
                and_(latest_guest_distro.c.host_id == MachineRecipe.id,
                    latest_guest_distro.c.latest_distro_date == \
                    guests_distro_tree.date_created)))\
            .outerjoin(guests_distro_tree.lab_controller_assocs, guests_lab_controller)\
            .join(Recipe.systems)\
            .join((hosts_distro_tree, hosts_distro_tree.id == MachineRecipe.distro_tree_id))\
            .join((hosts_lab_controller_distro_map, hosts_distro_tree.lab_controller_assocs),
                (LabController, and_(
                    hosts_lab_controller_distro_map.lab_controller_id == LabController.id,
                    System.lab_controller_id == LabController.id)))\
            .filter(
                and_(Recipe.status == TaskStatus.queued,
                    System.user == None,
                    LabController.disabled == False,
                    or_(
                        RecipeSet.lab_controller == None,
                        RecipeSet.lab_controller_id == System.lab_controller_id,
                       ),
                    or_(
                        System.loan_id == None,
                        System.loan_id == Job.owner_id,
                       ),
                    or_(
                        # We either have no guest
                        guest_recipe.id == None,
                        # Or we have a guest of which the latest
                        # is in a common lab controller.
                        and_(guests_lab_controller.id == LabController.id,
                            latest_guest_distro.c.latest_distro_date != None
                            ),
                        ) # or
                    ) # and
                  )
        # Get out of here if we have no recipes
        if not recipes.count():
            return False
        # This should be the guest recipe with the latest distro.
        # We return it in this query, to save us from re-running the
        # derived table query in schedule_queued_recipe()
        recipes = recipes.add_column(guest_recipe.id)
        # Effective priority is given in the following order:
        # * Multi host recipes with already scheduled siblings
        # * Priority level (i.e Normal, High etc)
        # * RecipeSet id
        # * Recipe id
        recipes = recipes.order_by(RecipeSet.lab_controller == None). \
            order_by(RecipeSet.priority.desc()). \
            order_by(RecipeSet.id). \
            order_by(MachineRecipe.id)
        # Don't do a GROUP BY before here, it is not needed.
        recipes = recipes.group_by(MachineRecipe.id)
        log.debug("Entering schedule_queued_recipes")
        for recipe_id, guest_recipe_id in recipes.values(MachineRecipe.id, guest_recipe.id):
            session.begin(nested=True)
            try:
                schedule_queued_recipe(recipe_id, guest_recipe_id)
                session.commit()
            except (StaleSystemUserException, InsufficientSystemPermissions,
                 StaleTaskStatusException), e:
                # Either
                # System user has changed before
                # system allocation
                # or
                # System permissions have changed before
                # system allocation
                # or
                # Something has moved our status on from queued
                # already.
                log.warn(str(e))
                session.rollback()
            except Exception, e:
                log.exception('Error in schedule_queued_recipe(%s)', recipe_id)
                session.rollback()
                session.begin(nested=True)
                try:
                    recipe=MachineRecipe.by_id(recipe_id)
                    recipe.recipeset.abort("Aborted in schedule_queued_recipe: %s" % e)
                    session.commit()
                except Exception, e:
                    log.exception("Error during error handling in schedule_queued_recipe: %s" % e)
                    session.rollback()
        log.debug("Exiting schedule_queued_recipes")
        return True
    except Exception:
        log.exception('Uncaught exception in schedule_queued_recipes')
        raise
    finally:
        try:
            session.commit()
        except OperationalError:
            msg = 'Possible DB deadlock in schedule_queued_recipes. '
            msg += 'See https://bugzilla.redhat.com/show_bug.cgi?id=958362'
            log.exception(msg)
            session.rollback()
        session.close()

def schedule_queued_recipe(recipe_id, guest_recipe_id=None):
    guest_recipe = aliased(Recipe)
    guest_distros_map = aliased(LabControllerDistroTree)
    guest_labcontroller = aliased(LabController)
    # This query will return all the systems that a recipe is
    # able to run on. A system is deemed eligible if:
    # * If the recipe's distro tree is available to the system's lab controller
    # * The system is available (see the filter criteria).
    # * If it's a host recipe, then the system needs to be on a lab controller
    #   that can access the distro tree of both the host recipe,
    #   and the guest recipe.
    systems = System.query.join(System.queued_recipes) \
        .outerjoin(System.cpu) \
        .join(Recipe.recipeset, RecipeSet.job) \
        .join(System.lab_controller, LabController._distro_trees)\
        .join((DistroTree,
            and_(LabControllerDistroTree.distro_tree_id ==
                DistroTree.id, Recipe.distro_tree_id == DistroTree.id)))\
        .outerjoin((machine_guest_map,
            Recipe.id == machine_guest_map.c.machine_recipe_id))\
        .outerjoin((guest_recipe,
            machine_guest_map.c.guest_recipe_id == guest_recipe.id ))\
        .outerjoin((guest_distros_map,
            guest_recipe.distro_tree_id == guest_distros_map.distro_tree_id))\
        .outerjoin((guest_labcontroller,
            guest_distros_map.lab_controller_id == guest_labcontroller.id))\
        .filter(Recipe.id == recipe_id) \
        .filter(or_(guest_recipe.id == guest_recipe_id,
            guest_recipe.id == None))\
        .filter(and_(System.user == None,
                or_(guest_distros_map.id == None,
                    and_(guest_distros_map.id != None,
                        guest_labcontroller.id == LabController.id,
                        ),
                   ),
                LabController.disabled == False,
                or_(System.loan_id == None,
                    System.loan_id == Job.owner_id,
                   ),
                    ), # and
                )

    # We reapply this filter here in case a peer recipe has locked the recipe
    # set in to a particular lab controller earlier in this scheduling pass
    recipe = MachineRecipe.by_id(recipe_id)
    if recipe.recipeset.lab_controller:
        systems = systems.filter(
                     System.lab_controller==recipe.recipeset.lab_controller)

    # Something earlier in this pass meant we can't schedule this recipe
    # right now after all. We'll try again next pass.
    if not systems.count():
        return

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
        systems = System.scheduler_ordering(user, query=systems)
    if recipe.autopick_random:
        system = systems[random.randrange(0,systems.count())]
    else:
        system = systems.first()

    log.debug("System : %s is available for Recipe %s" % (system, recipe.id))
    # Check to see if user still has proper permissions to use the system.
    # Remember the mapping of available systems could have happend hours or even
    # days ago and groups or loans could have been put in place since.
    if not recipe.candidate_systems().filter(System.id == system.id).first():
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
    recipes = MachineRecipe.query\
            .join(Recipe.recipeset).join(RecipeSet.job)\
            .filter(Job.dirty_version == Job.clean_version)\
            .join(Recipe.distro_tree, DistroTree.lab_controller_assocs, LabController)\
            .filter(Recipe.status == TaskStatus.queued)\
            .filter(Recipe.virt_status == RecipeVirtStatus.possible)\
            .filter(LabController.disabled == False)\
            .filter(or_(RecipeSet.lab_controller == None,
                RecipeSet.lab_controller_id == LabController.id))\
            .order_by(RecipeSet.priority.desc(), Recipe.id.asc())
    if not recipes.count():
        return False
    log.debug("Entering provision_virt_recipes")
    for recipe_id, in recipes.values(Recipe.id.distinct()):
        session.begin()
        try:
            provision_virt_recipe(recipe_id)
            session.commit()
        except Exception, e:
            log.exception('Error in provision_virt_recipe(%s)', recipe_id)
            session.rollback()
            # As an added precaution, let's try and avoid this recipe in future
            with session.begin():
                recipe = Recipe.by_id(recipe_id)
                recipe.virt_status = RecipeVirtStatus.failed
        finally:
            session.close()
    log.debug("Exiting provision_virt_recipes")
    return True

def provision_virt_recipe(recipe_id):
    recipe = Recipe.by_id(recipe_id)
    manager = dynamic_virt.VirtManager(recipe.recipeset.job.owner)
    available_flavors = manager.available_flavors()
    # We want them in order of smallest to largest, so that we can pick the
    # smallest flavor that satisfies the recipe's requirements. Sorting by RAM
    # is a decent approximation.
    available_flavors = sorted(available_flavors, key=lambda flavor: flavor.ram)
    possible_flavors = XmlHost.from_string(recipe.host_requires)\
        .filter_openstack_flavors(available_flavors, manager.lab_controller)
    if not possible_flavors:
        log.debug('No OpenStack flavors matched recipe %s, marking precluded',
                recipe.id)
        recipe.virt_status = RecipeVirtStatus.precluded
        return
    flavor = possible_flavors[0]
    vm_name = '%srecipe-%s' % (
            ConfigItem.by_name(u'guest_name_prefix').current_value(u'beaker-'),
            recipe.id)
    # FIXME can we control use of virtio?
    #virtio_possible = True
    #if self.recipe.distro_tree.distro.osversion.osmajor.osmajor == "RedHatEnterpriseLinux3":
    #    virtio_possible = False
    instance_id = manager.create_vm(vm_name, flavor)
    try:
        recipe.createRepo()
        recipe.systems = []
        recipe.watchdog = Watchdog()
        recipe.resource = VirtResource(instance_id, manager.lab_controller)
        recipe.recipeset.lab_controller = manager.lab_controller
        recipe.virt_status = RecipeVirtStatus.succeeded
        recipe.schedule()
        log.info("recipe ID %s moved from Queued to Scheduled by provision_virt_recipe" % recipe.id)
        recipe.waiting()
        recipe.provision()
        log.info("recipe ID %s moved from Scheduled to Waiting by provision_virt_recipe" % recipe.id)
    except:
        exc_type, exc_value, exc_tb = sys.exc_info()
        try:
            manager.destroy_vm(instance_id)
        except Exception:
            log.exception('Failed to clean up instance %s '
                    'during provision_virt_recipe, leaked!', instance_id)
            # suppress this exception so the original one is not masked
        raise exc_type, exc_value, exc_tb

def provision_scheduled_recipesets(*args):
    """
    if All recipes in a recipeSet are in Scheduled state then move them to
     Running.
    """
    recipesets = RecipeSet.query.join(RecipeSet.job)\
            .filter(and_(Job.dirty_version == Job.clean_version, Job.deleted == None))\
            .filter(not_(RecipeSet.recipes.any(
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

# These functions are run in separate threads, so we want to log any uncaught 
# exceptions instead of letting them be written to stderr and lost to the ether

@log_traceback(log)
def metrics_loop(*args, **kwargs):
    while running:
        start = time.time()
        try:
            recipe_count_metrics()
            system_count_metrics()
        except Exception:
            log.exception('Exception in metrics loop')
        end = time.time()
        duration = end - start
        if duration >= 30.0:
            log.debug("Metrics collection took %d seconds", duration)
        time.sleep(max(30.0 - duration, 5.0))

def _main_recipes():
    work_done = update_dirty_jobs()
    work_done |= abort_dead_recipes()
    work_done |= update_dirty_jobs()
    work_done |= process_new_recipes()
    work_done |= update_dirty_jobs()
    work_done |= queue_processed_recipesets()
    if _virt_enabled():
        work_done |= update_dirty_jobs()
        work_done |= provision_virt_recipes()
    work_done |= update_dirty_jobs()
    work_done |= schedule_queued_recipes()
    work_done |= update_dirty_jobs()
    work_done |= provision_scheduled_recipesets()
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
