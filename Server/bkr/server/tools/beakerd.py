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
import pkg_resources
pkg_resources.require("SQLAlchemy>=0.3.10")
from bkr.server.bexceptions import BX, CobblerTaskFailedException
from bkr.server.model import *
from bkr.server.util import load_config
from turbogears.database import session
from turbogears import config
from turbomail.control import interface

from os.path import dirname, exists, join
from os import getcwd
import bkr.server.scheduler
from bkr.server.scheduler import add_onetime_task
from socket import gethostname
import exceptions
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
    recipes = Recipe.query().filter(
            Recipe.status==TaskStatus.by_name(u'New'))
    if not recipes.count():
        return False
    log.debug("Entering new_recipes routine")
    for _recipe in recipes:
        session.begin()
        try:
            recipe = Recipe.by_id(_recipe.id)
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
                        recipe.recipeset.priority = TaskPriority.by_id(recipe.recipeset.priority.id + 1)
                    except InvalidRequestError:
                        # We may already be at the highest priority
                        pass
                if recipe.systems:
                    recipe.process()
                    log.info("recipe ID %s moved from New to Processed" % recipe.id)
                else:
                    log.info("recipe ID %s moved from New to Aborted" % recipe.id)
                    recipe.recipeset.abort('Recipe ID %s does not match any systems' % recipe.id)
            else:
                recipe.recipeset.abort('Recipe ID %s does not have a distro' % recipe.id)
            session.commit()
        except exceptions.Exception:
            session.rollback()
            log.exception("Failed to commit in new_recipes")
        session.close()
    log.debug("Exiting new_recipes routine")
    return True

def processed_recipesets(*args):
    recipesets = RecipeSet.query()\
                       .join(['status'])\
                       .filter(RecipeSet.status==TaskStatus.by_name(u'Processed'))
    if not recipesets.count():
        return False
    log.debug("Entering processed_recipes routine")
    for _recipeset in recipesets:
        session.begin()
        try:
            recipeset = RecipeSet.by_id(_recipeset.id)
            bad_l_controllers = set()
            # We only need to do this processing on multi-host recipes
            if len(recipeset.recipes) == 1:
                log.info("recipe ID %s moved from Processed to Queued" % recipeset.recipes[0].id)
                recipeset.recipes[0].queue()
            else:
                # Find all the lab controllers that this recipeset may run.
                rsl_controllers = set(LabController.query()\
                                              .join(['systems',
                                                     'queued_recipes',
                                                     'recipeset'])\
                                              .filter(RecipeSet.id==recipeset.id).all())
    
                # Any lab controllers that are not associated to all recipes in the
                # recipe set must have those systems on that lab controller removed
                # from any recipes.  For multi-host all recipes must be schedulable
                # on one lab controller
                for recipe in recipeset.recipes:
                    rl_controllers = set(LabController.query()\
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
                        recipe.recipeset.abort('Recipe ID %s does not match any systems' % recipe.id)
                        
            session.commit()
        except exceptions.Exception:
            session.rollback()
            log.exception("Failed to commit in processed_recipes")
        session.close()
    log.debug("Exiting processed_recipes routine")
    return True

def dead_recipes(*args):
    recipes = Recipe.query()\
                    .join('status')\
                    .outerjoin(['systems'])\
                    .outerjoin(['distro',
                                'lab_controller_assocs',
                                'lab_controller'])\
                    .filter(
                         or_(
                         and_(Recipe.status==TaskStatus.by_name(u'Queued'),
                              System.id==None,
                             ),
                         and_(Recipe.status==TaskStatus.by_name(u'Queued'),
                              LabController.id==None,
                             ),
                            )
                           )

    if not recipes.count():
        return False
    log.debug("Entering dead_recipes routine")
    for _recipe in recipes:
        session.begin()
        try:
            recipe = Recipe.by_id(_recipe.id)
            if len(recipe.systems) == 0:
                msg = "R:%s does not match any systems, aborting." % recipe.id
                log.info(msg)
                recipe.recipeset.abort(msg)
            if len(recipe.distro.lab_controller_assocs) == 0:
                msg = "R:%s does not have a valid distro, aborting." % recipe.id
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
    automated = SystemStatus.by_name(u'Automated')
    recipes = Recipe.query()\
                    .join('status')\
                    .join(['systems','lab_controller','_distros','distro'])\
                    .join(['recipeset','priority'])\
                    .join(['recipeset','job'])\
                    .join(['distro','lab_controller_assocs','lab_controller'])\
                    .filter(
                         and_(Recipe.status==TaskStatus.by_name(u'Queued'),
                              System.user==None,
                              System.status==automated,
                              Recipe.distro_id==Distro.id,
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
        recipes = recipes.order_by(TaskPriority.id.desc())
    if not recipes.count():
        return False
    log.debug("Entering queued_recipes routine")
    for _recipe in recipes:
        session.begin()
        try:
            recipe = Recipe.by_id(_recipe.id)
            systems = recipe.dyn_systems.join(['lab_controller','_distros','distro']).\
                      filter(and_(System.user==None,
                                  Distro.id==recipe.distro_id,
                                  LabController.disabled==False,
                                  System.status==automated))
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
                          (System.owner!=user and Group.systems==None, 2)],
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
                if not System.free(user).filter(System.fqdn == system).first():
                    log.debug("System : %s recipe: %s no longer has access. removing" % (system, 
                                                                                         recipe.id))
                    recipe.systems.remove(system)
                else:
                    recipe.schedule()
                    recipe.createRepo()
                    system.reserve(service=u'Scheduler', user=recipe.recipeset.job.owner,
                            reservation_type=u'recipe')
                    recipe.system = system
                    recipe.recipeset.lab_controller = system.lab_controller
                    recipe.systems = []
                    # Create the watchdog without an Expire time.
                    log.debug("Created watchdog for recipe id: %s and system: %s" % (recipe.id, system))
                    recipe.watchdog = Watchdog(system=recipe.system)
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
    recipesets = RecipeSet.query().from_statement(
                        select([recipe_set_table.c.id, 
                                func.min(recipe_table.c.status_id)],
                               from_obj=[recipe_set_table.join(recipe_table)])\
                               .group_by(RecipeSet.id)\
                               .having(func.min(recipe_table.c.status_id) == TaskStatus.by_name(u'Scheduled').id)).all()
   
    if not recipesets:
        return False
    log.debug("Entering scheduled_recipes routine")
    for _recipeset in recipesets:
        log.info("scheduled_recipes: RS:%s" % _recipeset.id)
        session.begin()
        try:
            recipeset = RecipeSet.by_id(_recipeset.id)
            # Go through each recipe in the recipeSet
            for recipe in recipeset.recipes:
                # If one of the recipes gets aborted then don't try and run
                if recipe.status != TaskStatus.by_name(u'Scheduled'):
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
                harnessrepos="|".join(["%s,%s" % (r["name"], r["url"]) for r in recipe.harness_repos()])
                customrepos= "|".join(["%s,%s" % (r.name, r.url) for r in recipe.repos])
                ks_meta = "%s customrepos=%s harnessrepos=%s" % (ks_meta, customrepos, harnessrepos)
                # If ks_meta is defined from recipe pass it along.
                # add it last to allow for overriding previous settings.
                if recipe.ks_meta:
                    ks_meta = "%s %s" % (ks_meta, recipe.ks_meta)
                if recipe.partitionsKSMeta:
                    ks_meta = "%s partitions=%s" % (ks_meta, recipe.partitionsKSMeta)
                try:
                    recipe.system.action_auto_provision(recipe.distro,
                                                     ks_meta,
                                                     recipe.kernel_options,
                                                     recipe.kernel_options_post,
                                                     recipe.kickstart,
                                                     recipe.ks_appends,
                                                     wait=True)
                    recipe.system.activity.append(
                         SystemActivity(recipe.recipeset.job.owner, 
                                        'Scheduler', 
                                        'Provision', 
                                        'Distro',
                                        '',
                                        '%s' % recipe.distro))
                except CobblerTaskFailedException, e:
                    log.error('Cobbler task failed for recipe %s: %s' % (recipe.id, e))
                    old_status = recipe.system.status
                    recipe.system.mark_broken(reason=str(e), recipe=recipe)
                    recipe.system.activity.append(SystemActivity(service='Scheduler',
                            action='Changed', field_name='Status',
                            old_value=old_status, new_value=recipe.system.status))
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

def new_recipes_loop(*args, **kwargs):
    while True:
        if not new_recipes():
            time.sleep(20)

def processed_recipesets_loop(*args, **kwargs):
    while True:
        if not processed_recipesets():
            time.sleep(20)

def queued_recipes_loop(*args, **kwargs):
    while True:
        if not queued_recipes():
            time.sleep(20)

def schedule():
    bkr.server.scheduler._start_scheduler()
    log.debug("starting new recipes Thread")
    # Create new_recipes Thread
    add_onetime_task(action=new_recipes_loop,
                      args=[lambda:datetime.now()])
    log.debug("starting processed recipes Thread")
    # Create processed_recipes Thread
    add_onetime_task(action=processed_recipesets_loop,
                      args=[lambda:datetime.now()],
                      initialdelay=5)
    #log.debug("starting queued recipes Thread")
    # Create queued_recipes Thread
    #add_onetime_task(action=queued_recipes_loop,
    #                  args=[lambda:datetime.now()],
    #                  initialdelay=10)
    log.debug("starting scheduled recipes Thread")
    # Run scheduled_recipes in this process
    while True:
        dead_recipes()
        queued = queued_recipes()
        scheduled = scheduled_recipes()
        if not queued and not scheduled:
            time.sleep(20)

def daemonize(daemon_func, daemon_pid_file=None, daemon_start_dir=".", daemon_out_log="/dev/null", daemon_err_log="/dev/null", *args, **kwargs):
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

    pid_file = opts.pid_file
    if pid_file is None:
        pid_file = config.get("PID_FILE", "/var/run/beaker/beakerd.pid")


    if opts.foreground:
        schedule()
    else:
        daemonize(schedule, daemon_pid_file=pid_file)

if __name__ == "__main__":
    main()
