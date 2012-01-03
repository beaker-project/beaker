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

import sys
import os
import random
from bkr.server.bexceptions import BX, CobblerTaskFailedException
from bkr.server.model import *
from bkr.server.util import load_config, log_traceback
from bkr.server.recipetasks import RecipeTasks
from bkr.server.message_bus import ServerBeakerBus
from turbogears.database import session
from turbogears import config
from turbomail.control import interface
from xmlrpclib import ProtocolError

from os.path import dirname, exists, join
from os import getcwd
import bkr.server.scheduler
from bkr.server.scheduler import add_onetime_task
import socket
from socket import gethostname
import exceptions
from datetime import datetime, timedelta
import time

import logging
#logging.basicConfig()
#logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
#logging.getLogger('sqlalchemy.orm.unitofwork').setLevel(logging.DEBUG)

log = logging.getLogger("beakerd")

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


def new_recipes(*args):
    recipes = Recipe.query.filter(Recipe.status == TaskStatus.new)
    if not recipes.count():
        return False
    log.debug("Entering new_recipes routine")
    for recipe_id, in recipes.values(Recipe.id):
        session.begin()
        try:
            recipe = Recipe.by_id(recipe_id)
            if recipe.distro:
                recipe.systems = []

                # Do the query twice. 

                # First query verifies that the distro
                # exists in at least one lab that has a macthing system.
                systems = recipe.distro.systems_filter(
                                            recipe.recipeset.job.owner,
                                            recipe.host_requires,
                                            join=['lab_controller',
                                                  '_distros',
                                                  'distro'],
                                                      )\
                                       .filter(Distro.install_name==
                                               recipe.distro.install_name)
                # Second query picksup all possible systems so that as 
                # distros appear in other labs those systems will be 
                # available.
                all_systems = recipe.distro.systems_filter(
                                            recipe.recipeset.job.owner,
                                            recipe.host_requires,
                                            join=['lab_controller'],
                                                      )
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
                if recipe.systems:
                    recipe.process()
                    log.info("recipe ID %s moved from New to Processed" % recipe.id)
                else:
                    log.info("recipe ID %s moved from New to Aborted" % recipe.id)
                    recipe.recipeset.abort(u'Recipe ID %s does not match any systems' % recipe.id)
            else:
                recipe.recipeset.abort(u'Recipe ID %s does not have a distro' % recipe.id)
            session.commit()
        except exceptions.Exception:
            session.rollback()
            log.exception("Failed to commit in new_recipes")
        session.close()
    log.debug("Exiting new_recipes routine")
    return True

def processed_recipesets(*args):
    recipesets = RecipeSet.query.filter(RecipeSet.status == TaskStatus.processed)
    if not recipesets.count():
        return False
    log.debug("Entering processed_recipes routine")
    for rs_id, in recipesets.values(RecipeSet.id):
        session.begin()
        try:
            recipeset = RecipeSet.by_id(rs_id)
            bad_l_controllers = set()
            # We only need to do this processing on multi-host recipes
            if len(recipeset.recipes) == 1:
                log.info("recipe ID %s moved from Processed to Queued" % recipeset.recipes[0].id)
                recipeset.recipes[0].queue()
            else:
                # Find all the lab controllers that this recipeset may run.
                rsl_controllers = set(LabController.query\
                                              .join(['systems',
                                                     'queued_recipes',
                                                     'recipeset'])\
                                              .filter(RecipeSet.id==recipeset.id).all())
    
                # Any lab controllers that are not associated to all recipes in the
                # recipe set must have those systems on that lab controller removed
                # from any recipes.  For multi-host all recipes must be schedulable
                # on one lab controller
                for recipe in recipeset.recipes:
                    rl_controllers = set(LabController.query\
                                               .join(['systems',
                                                      'queued_recipes'])\
                                               .filter(Recipe.id==recipe.id).all())
                    bad_l_controllers = bad_l_controllers.union(rl_controllers.difference(rsl_controllers))
        
                for l_controller in rsl_controllers:
                    enough_systems = False
                    for recipe in recipeset.recipes:
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
                        for recipe in recipeset.recipes_orderby(l_controller)[:]:
                            for tmprecipe in recipeset.recipes:
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
                        for recipe in recipeset.recipes:
                            count = 0
                            systems = recipe.dyn_systems.filter(
                                              System.lab_controller==l_controller
                                                               ).all()
                            for tmprecipe in recipeset.recipes:
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
                for recipe in recipeset.recipes:
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
                    else:
                        # Set status to Aborted 
                        log.info("recipe ID %s moved from Processed to Aborted" % recipe.id)
                        recipe.recipeset.abort(u'Recipe ID %s does not match any systems' % recipe.id)
                        
            session.commit()
        except exceptions.Exception:
            session.rollback()
            log.exception("Failed to commit in processed_recipes")
        session.close()
    log.debug("Exiting processed_recipes routine")
    return True

def dead_recipes(*args):
    recipes = Recipe.query\
                    .outerjoin(['systems'])\
                    .outerjoin(['distro',
                                'lab_controller_assocs',
                                'lab_controller'])\
                    .filter(
                         or_(
                         and_(Recipe.status==TaskStatus.queued,
                              System.id==None,
                             ),
                         and_(Recipe.status==TaskStatus.queued,
                              LabController.id==None,
                             ),
                            )
                           )

    if not recipes.count():
        return False
    log.debug("Entering dead_recipes routine")
    for recipe_id, in recipes.values(Recipe.id):
        session.begin()
        try:
            recipe = Recipe.by_id(recipe_id)
            if len(recipe.systems) == 0:
                msg = u"R:%s does not match any systems, aborting." % recipe.id
                log.info(msg)
                recipe.recipeset.abort(msg)
            if len(recipe.distro.lab_controller_assocs) == 0:
                msg = u"R:%s does not have a valid distro, aborting." % recipe.id
                log.info(msg)
                recipe.recipeset.abort(msg)
            session.commit()
        except exceptions.Exception, e:
            session.rollback()
            log.exception("Failed to commit due to :%s" % e)
        session.close()
    log.debug("Exiting dead_recipes routine")
    return True

def queued_recipes(*args):
    recipes = Recipe.query\
                    .join(Recipe.recipeset, RecipeSet.job)\
                    .join(Recipe.systems)\
                    .join(Recipe.distro)\
                    .join(Distro.lab_controller_assocs,
                        (LabController, and_(
                            LabControllerDistro.lab_controller_id == LabController.id,
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
        recipes = recipes.join(Recipe.recipeset)\
                .order_by(RecipeSet.priority.desc())
    if not recipes.count():
        return False
    log.debug("Entering queued_recipes routine")
    for recipe_id, in recipes.values(Recipe.id):
        session.begin()
        try:
            recipe = Recipe.by_id(recipe_id)
            systems = recipe.dyn_systems\
                       .join(System.lab_controller,
                             LabController._distros,
                             LabControllerDistro.distro)\
                       .filter(and_(System.user==None,
                                  Distro.id==recipe.distro_id,
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
            if system:
                log.debug("System : %s is available for Recipe %s" % (system, recipe.id))
                # Check to see if user still has proper permissions to use system
                # Remember the mapping of available systems could have happend hours or even
                # days ago and groups or loans could have been put in place since.
                if not System.free(user).filter(System.id == system.id).first():
                    log.debug("System : %s recipe: %s no longer has access. removing" % (system, 
                                                                                         recipe.id))
                    recipe.systems.remove(system)
                else:
                    recipe.schedule()
                    recipe.createRepo()
                    system.reserve(service=u'Scheduler', user=recipe.recipeset.job.owner,
                            reservation_type=u'recipe', recipe=recipe)
                    recipe.system = system
                    recipe.recipeset.lab_controller = system.lab_controller
                    recipe.systems = []
                    # Create the watchdog without an Expire time.
                    log.debug("Created watchdog for recipe id: %s and system: %s" % (recipe.id, system))
                    recipe.watchdog = Watchdog(system=recipe.system)
                    # If we start ok, we need to send event active watchdog event
                    if config.get('beaker.qpid_enabled'):
                        bb = ServerBeakerBus()
                        bb.send_action('watchdog_notify', 'active',
                            [{'recipe_id' : recipe.id, 
                            'system' : recipe.watchdog.system.fqdn}], 
                            recipe.watchdog.system.lab_controller.fqdn)
                    log.info("recipe ID %s moved from Queued to Scheduled" % recipe.id)
            session.commit()
        except exceptions.Exception:
            session.rollback()
            log.exception("Failed to commit in queued_recipes")
        session.close()
    log.debug("Exiting queued_recipes routine")
    return True

def scheduled_recipes(*args):
    """
    if All recipes in a recipeSet are in Scheduled state then move them to
     Running.
    """
    recipesets = RecipeSet.query.filter(not_(RecipeSet.recipes.any(
            Recipe.status != TaskStatus.scheduled)))
    if not recipesets.count():
        return False
    log.debug("Entering scheduled_recipes routine")
    for rs_id, in recipesets.values(RecipeSet.id):
        log.info("scheduled_recipes: RS:%s" % rs_id)
        session.begin()
        try:
            recipeset = RecipeSet.by_id(rs_id)
            # Go through each recipe in the recipeSet
            for recipe in recipeset.recipes:
                # If one of the recipes gets aborted then don't try and run
                if recipe.status != TaskStatus.scheduled:
                    break
                recipe.waiting()

                # Go Through each recipe and find out everyone's role.
                for peer in recipe.recipeset.recipes:
                    recipe.roles[peer.role].append(peer.system)

                # Go Through each task and find out the roles of everyone else
                for i, task in enumerate(recipe.tasks):
                    for peer in recipe.recipeset.recipes:
                        # Roles are only shared amongst like recipe types
                        if type(recipe) == type(peer):
                            try:
                                task.roles[peer.tasks[i].role].append(peer.system)
                            except IndexError:
                                # We have uneven tasks
                                pass
      
                harness_repo_details = recipe.harness_repo()
                task_repo_details = recipe.task_repo()
                repo_fail = []
                if not harness_repo_details:
                    repo_fail.append(u'harness')
                if not task_repo_details:
                    repo_fail.append(u'task')

                if repo_fail:
                    repo_fail_msg ='Failed to find repo for %s' % ','.join(repo_fail)
                    log.error(repo_fail_msg)
                    recipe.recipeset.abort(repo_fail_msg)
                    break
                else:
                    harnessrepo = '%s,%s' % harness_repo_details
                    taskrepo = '%s,%s' % task_repo_details

                # Start the first task in the recipe
                try:
                    recipe.tasks[0].start()
                except exceptions.Exception, e:
                    log.error("Failed to Start recipe %s, due to %s" % (recipe.id,e))
                    recipe.recipeset.abort(u"Failed to provision recipeid %s, %s" %
                                                                             (
                                                                         recipe.id,
                                                                            e))
                    break

                ks_meta = "recipeid=%s packages=%s" % (recipe.id,
                                                       ":".join([p.package for p in recipe.packages]))
                customrepos= "|".join(["%s,%s" % (r.name, r.url) for r in recipe.repos])
                ks_meta = "%s customrepos=%s harnessrepo=%s taskrepo=%s" % (ks_meta, customrepos, harnessrepo, taskrepo)
                user = recipe.recipeset.job.owner
                if user.root_password:
                    ks_meta = "password=%s %s" % (user.root_password, ks_meta)
                # If ks_meta is defined from recipe pass it along.
                # add it last to allow for overriding previous settings.
                if recipe.ks_meta:
                    ks_meta = "%s %s" % (ks_meta, recipe.ks_meta)
                if recipe.partitionsKSMeta:
                    ks_meta = "%s partitions=%s" % (ks_meta, recipe.partitionsKSMeta)
                if user.sshpubkeys:
                    end = recipe.distro and (recipe.distro.osversion.osmajor.osmajor.startswith("Fedora") or \
                                             recipe.distro.osversion.osmajor.osmajor.startswith("RedHatEnterpriseLinux7"))
                    key_ks = [user.ssh_keys_ks(end)]
                else:
                    key_ks = []
                try:
                    recipe.system.action_auto_provision(recipe.distro,
                                                     ks_meta,
                                                     recipe.kernel_options,
                                                     recipe.kernel_options_post,
                                                     recipe.kickstart,
                                                     recipe.ks_appends + key_ks)
                    recipe.system.activity.append(
                         SystemActivity(recipe.recipeset.job.owner, 
                                        u'Scheduler',
                                        u'Provision',
                                        u'Distro',
                                        u'',
                                        unicode(recipe.distro)))
                except CobblerTaskFailedException, e:
                    log.error('Cobbler task failed for recipe %s: %s' % (recipe.id, e))
                    recipe.system.mark_broken(reason=str(e), recipe=recipe)
                    recipe.recipeset.abort(_(u'Cobbler task failed for recipe %s: %s')
                            % (recipe.id, e))
                except Exception, e:
                    log.error(u"Failed to provision recipeid %s, %s" % (
                                                                         recipe.id,
                                                                            e))
                    recipe.recipeset.abort(u"Failed to provision recipeid %s, %s" % 
                                                                             (
                                                                             recipe.id,
                                                                            e))
       
            session.commit()
        except exceptions.Exception:
            session.rollback()
            log.exception("Failed to commit in scheduled_recipes")
        session.close()
    log.debug("Exiting scheduled_recipes routine")
    return True


COMMAND_TIMEOUT = 600
def running_commands(*args):
    commands = CommandActivity.query\
                              .filter(CommandActivity.status==CommandStatus.running)\
                              .order_by(CommandActivity.updated.asc())
    if not commands.count():
        return False
    log.debug('Entering running_commands routine')
    for cmd_id, in commands.values(CommandActivity.id):
        session.begin()
        cmd = CommandActivity.query.get(cmd_id)
        if not cmd:
            log.error('Command %d get() failed. Deleted?' % (cmd_id))
        else:
            try:
                for line in cmd.system.remote.get_event_log(cmd.task_id).split('\n'):
                    if line.find("### TASK COMPLETE ###") != -1:
                        log.info('Power %s command (%d) completed on machine: %s' %
                                 (cmd.action, cmd.id, cmd.system))
                        cmd.status = CommandStatus.completed
                        cmd.log_to_system_history()
                        break
                    if line.find("### TASK FAILED ###") != -1:
                        log.error('Cobbler power task %s (command %d) failed for machine: %s' %
                                  (cmd.task_id, cmd.id, cmd.system))
                        cmd.status = CommandStatus.failed
                        cmd.new_value = u'Cobbler task failed'
                        if cmd.system.status == SystemStatus.automated:
                            cmd.system.mark_broken(reason='Cobbler power task failed')
                        cmd.log_to_system_history()
                        break
                if (cmd.status == CommandStatus.running) and \
                   (datetime.utcnow() >= cmd.updated + timedelta(seconds=COMMAND_TIMEOUT)):
                        log.error('Cobbler power task %s (command %d) timed out on machine: %s' %
                                  (cmd.task_id, cmd.id, cmd.system))
                        cmd.status = CommandStatus.aborted
                        cmd.new_value = u'Timeout of %d seconds exceeded' % COMMAND_TIMEOUT
                        cmd.log_to_system_history()
            except ProtocolError, err:
                log.warning('Error (%d) querying power command (%d) for %s, will retry: %s' %
                            (err.errcode, cmd.id, cmd.system, err.errmsg))
            except socket.error, err:
                log.warning('Socket error (%d) querying power command (%d) for %s, will retry: %s' %
                            (err.errno, cmd.id, cmd.system, err.strerror))
            except Exception, msg:
                log.error('Cobbler power exception processing command %d for machine %s: %s' %
                          (cmd.id, cmd.system, msg))
                cmd.status = CommandStatus.failed
                cmd.new_value = unicode(msg)
                cmd.log_to_system_history()
        session.commit()
        session.close()
    log.debug('Exiting running_commands routine')
    return True

def queued_commands(*args):
    # The following throttle code was put in place in an attempt to
    # keep cobblerd from falling over.
    #
    # Integer value stating max number of commands running
    MAX_RUNNING_COMMANDS = config.get("beaker.MAX_RUNNING_COMMANDS", 0)
    commands = CommandActivity.query\
                              .filter(CommandActivity.status==CommandStatus.queued)\
                              .order_by(CommandActivity.created.asc())
    if not commands.count():
        return
    # Throttle total number of Running commands if set.
    if MAX_RUNNING_COMMANDS != 0:
        running_commands = CommandActivity.query\
                         .filter(CommandActivity.status==CommandStatus.running)
        if running_commands.count() >= MAX_RUNNING_COMMANDS:
            log.debug('Throttling Commands: %s >= %s' % (running_commands.count(), 
                                                        MAX_RUNNING_COMMANDS))
            return
        # limit is an int between 1 and MAX_RUNNING_COMMANDS
        limit = MAX_RUNNING_COMMANDS - running_commands.count()
        commands = commands.limit(limit > 0 and limit or 1)
    log.debug('Entering queued_commands routine')
    for cmd_id, in commands.values(CommandActivity.id):
        with session.begin():
            cmd = CommandActivity.query.get(cmd_id)
            log.debug("cmd=%s" % cmd)
            # if get() is given an invalid id it will return None.
            # I'm not sure how this would happen since id came from the above
            # query, maybe a race condition?
            if not cmd:
                log.error('Command %d get() failed. Deleted?', cmd_id)
                continue
            # Skip queued commands if something is already running on that system
            if CommandActivity.query.filter(and_(CommandActivity.status==CommandStatus.running,
                                                   CommandActivity.system==cmd.system))\
                                    .count():
                log.info('Skipping power %s (command %d), command already running on machine: %s' %
                         (cmd.action, cmd.id, cmd.system))
                continue
            if not cmd.system.lab_controller or not cmd.system.power:
                log.error('Command %d aborted, power control not available for machine: %s' %
                          (cmd.id, cmd.system))
                cmd.status = CommandStatus.aborted
                cmd.new_value = u'Power control unavailable'
                cmd.log_to_system_history()
            else:
                try:
                    log.info('Executing power %s command (%d) on machine: %s' %
                             (cmd.action, cmd.id, cmd.system))
                    cmd.task_id = cmd.system.remote.power(cmd.action)
                    cmd.updated = datetime.utcnow()
                    cmd.status = CommandStatus.running
                except ProtocolError, err:
                    log.warning('Error (%d) submitting power command (%d) for %s, will retry: %s' %
                                (err.errcode, cmd.id, cmd.system, err.errmsg))
                except socket.error, err:
                    log.warning('Socket error (%d) submitting power command (%d) for %s, will retry: %s' %
                                (err.errno, cmd.id, cmd.system, err.strerror))
                except Exception, msg:
                    log.error('Cobbler power exception submitting \'%s\' command (%d) for machine %s: %s' %
                              (cmd.action, cmd.id, cmd.system, msg))
                    cmd.new_value = unicode(msg)
                    cmd.status = CommandStatus.failed
                    cmd.log_to_system_history()
    log.debug('Exiting queued_commands routine')
    return

# These functions are run in separate threads, so we want to log any uncaught 
# exceptions instead of letting them be written to stderr and lost to the ether

@log_traceback(log)
def new_recipes_loop(*args, **kwargs):
    while True:
        if not new_recipes():
            time.sleep(20)

@log_traceback(log)
def processed_recipesets_loop(*args, **kwargs):
    while True:
        if not processed_recipesets():
            time.sleep(20)

@log_traceback(log)
def command_queue_loop(*args, **kwargs):
    while True:
        running_commands()
        queued_commands()
        time.sleep(20)

@log_traceback(log)
def main_loop():
    while True:
        dead_recipes()
        queued = queued_recipes()
        scheduled = scheduled_recipes()
        if not queued and not scheduled:
            time.sleep(20)

def schedule():
    bkr.server.scheduler._start_scheduler()
    if config.get('beaker.qpid_enabled') is True: 
       bb = ServerBeakerBus()
       bb.run()
    log.debug("starting new recipes Thread")
    # Create new_recipes Thread
    add_onetime_task(action=new_recipes_loop,
                      args=[lambda:datetime.now()])
    log.debug("starting processed recipes Thread")
    # Create processed_recipes Thread
    add_onetime_task(action=processed_recipesets_loop,
                      args=[lambda:datetime.now()],
                      initialdelay=5)
    log.debug("starting power commands Thread")
    # Create command_queue Thread
    add_onetime_task(action=command_queue_loop,
                      args=[lambda:datetime.now()],
                      initialdelay=10)
    main_loop()

def daemonize(daemon_func, daemon_pid_file=None, daemon_start_dir="/", daemon_out_log="/dev/null", daemon_err_log="/dev/null", *args, **kwargs):
    """Robustly turn into a UNIX daemon, running in daemon_start_dir."""

    if daemon_pid_file and os.path.exists(daemon_pid_file):
        try:
            f = open(daemon_pid_file, "r")
            pid = f.read()
            f.close()
        except:
            pid = None

        if pid:
            try:
                fn = os.path.join("/proc", pid, "cmdline")
                f = open(fn, "r")
                cmdline = f.read()
                f.close()
            except:
                cmdline = None

        if cmdline and cmdline.find(sys.argv[0]) >=0:
            sys.stderr.write("A proces is still running, pid: %s\n" % pid)
            sys.exit(1)

    # first fork
    try:
        if os.fork() > 0:
            # exit from first parent
            sys.exit(0)
    except OSError, ex:
        sys.stderr.write("fork #1 failed: (%d) %s\n" % (ex.errno, ex.strerror))
        sys.exit(1)

    # decouple from parent environment
    os.setsid()
    os.chdir(daemon_start_dir)
    os.umask(0)

    # second fork
    try:
        pid = os.fork()
        if pid > 0:
            # write pid to pid_file
            if daemon_pid_file is not None:
                f = open(daemon_pid_file, "w")
                f.write("%s" % pid)
                f.close()
            # exit from second parent
            sys.exit(0)
    except OSError, ex:
        sys.stderr.write("fork #2 failed: (%d) %s\n" % (ex.errno, ex.strerror))
        sys.exit(1)

    # redirect stdin, stdout and stderr
    stdin = open("/dev/null", "r")
    stdout = open(daemon_out_log, "a+", 0)
    stderr = open(daemon_err_log, "a+", 0)
    os.dup2(stdin.fileno(), sys.stdin.fileno())
    os.dup2(stdout.fileno(), sys.stdout.fileno())
    os.dup2(stderr.fileno(), sys.stderr.fileno())

    # run the daemon loop
    daemon_func(*args, **kwargs)
    sys.exit(0)

def main():
    parser = get_parser()
    opts, args = parser.parse_args()
    setupdir = dirname(dirname(__file__))
    curdir = getcwd()

    # First look on the command line for a desired config file,
    # if it's not on the command line, then look for 'setup.py'
    # in the current directory. If there, load configuration
    # from a file called 'dev.cfg'. If it's not there, the project
    # is probably installed and we'll look first for a file called
    # 'prod.cfg' in the current directory and then for a default
    # config file called 'default.cfg' packaged in the egg.
    load_config(opts.configfile)

    interface.start(config)

    config.update({'identity.krb_auth_qpid_principal' : config.get('identity.krb_auth_beakerd_principal') })
    config.update({'identity.krb_auth_qpid_keytab' : config.get('identity.krb_auth_beakerd_keytab') } )

    pid_file = opts.pid_file
    if pid_file is None:
        pid_file = config.get("PID_FILE", "/var/run/beaker/beakerd.pid")


    if opts.foreground:
        schedule()
    else:
        daemonize(schedule, daemon_pid_file=pid_file)

if __name__ == "__main__":
    main()
