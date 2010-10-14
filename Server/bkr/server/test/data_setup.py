# Beaker
#
# Copyright (C) 2010 rmancy@redhat.com
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

import logging
import re
import time
import datetime
import sqlalchemy
import turbogears.config, turbogears.database
from bkr.server.model import LabController, User, Group, Distro, Breed, Arch, \
        OSMajor, OSVersion, SystemActivity, Task, MachineRecipe, System, \
        SystemType, SystemStatus, Recipe, RecipeTask, RecipeTaskResult, \
        Device, TaskResult, TaskStatus, Job, RecipeSet, TaskPriority, \
        LabControllerDistro

log = logging.getLogger(__name__)

ADMIN_USER = u'admin'
ADMIN_PASSWORD = u'testing'

def setup_model(override=True):
    from bkr.server.tools.init import init_db
    engine = turbogears.database.get_engine()
    db_name = engine.url.database
    connection = engine.connect()
    if override:
        log.info('Dropping database %s', db_name)
        connection.execute('DROP DATABASE IF EXISTS %s' % db_name)
    log.info('Creating database %s', db_name)
    connection.execute('CREATE DATABASE %s' % db_name)
    connection.invalidate() # can't reuse this one
    del connection
    log.info('Initialising model')
    init_db(user_name=ADMIN_USER, password=ADMIN_PASSWORD)

def create_labcontroller(fqdn=None):
    if fqdn is None:
        fqdn=u'lab-devel.rhts.eng.bos.redhat.com'
    try:
        lc = LabController.by_name(fqdn)  
    except sqlalchemy.exceptions.InvalidRequestError, e: #Doesn't exist ?
        if e.args[0] == 'No rows returned for one()':
            lc = LabController(fqdn=fqdn)
            return lc
        else:
            raise
    log.debug('labcontroller %s already exists' % fqdn)
    return lc

def create_user(user_name=None, password=None, display_name=None):
    if user_name is None:
        user_name = u'user%d' % int(time.time() * 1000)
    if display_name is None:
        display_name = user_name
    user = User(user_name=user_name, display_name=display_name,
            email_address=u'%s@example.com' % user_name)
    if password:
        user.password = password
    log.debug('Created user %r', user)
    return user

def add_system_lab_controller(system,lc): 
    system.lab_controller = lc

def create_group():
    # tg_group.group_name column is VARCHAR(16)
    group = Group(group_name=u'group%s' % str(int(time.time() * 1000))[-11:])
    return group

def add_user_to_group(user,group):
    user.groups.append(group)

def add_group_to_system(system,group):
    system.groups.append(group)

def create_distro(name=u'DAN6-Server-U9', breed=u'Dan',
        osmajor=u'DansAwesomeLinuxServer6', osminor=u'9',
        arch=u'i386', method=u'http', virt=False, tags=None):
    install_name = u'%s-%d_%s-%s' % (name, int(time.time() * 1000), method, arch)
    distro = Distro(install_name=install_name)
    distro.name = name
    distro.method = method
    distro.breed = Breed.lazy_create(breed=breed)
    distro.virt = virt
    if tags:
        distro.tags.extend(tags)
    osmajor = OSMajor.lazy_create(osmajor=osmajor)
    try:
        distro.osversion = OSVersion.by_name(osmajor, osminor)
    except sqlalchemy.exceptions.InvalidRequestError:
        distro.osversion = OSVersion(osmajor, osminor, arches=[])
    distro.arch = Arch.by_name(arch)
    # make it available in all lab controllers
    for lc in LabController.query():
        distro.lab_controller_assocs.append(LabControllerDistro(lab_controller=lc))
    log.debug('Created distro %r', distro)
    return distro

def create_system(arch=u'i386', type=u'Machine', status=u'Automated',
        owner=None, fqdn=None, **kw):
    if owner is None:
        owner = create_user()
    if fqdn is None:
        fqdn = u'system%d.testdata' % int(time.time() * 1000)
    system = System(fqdn=fqdn,type=SystemType.by_name(type), owner=owner, 
                status=SystemStatus.by_name(status), **kw)
    system.arch.append(Arch.by_name(arch))
    log.debug('Created system %r', system)
    return system

def create_system_activity(user=None, **kw):
    if not user:
        user = create_user()
    activity = SystemActivity(user, 'WEBUI', 'Changed', 'Loaned To', 'random_%d' % int(time.time() * 1000) , '%s' % user)
    return activity

def create_task(name=None):
    if name is None:
        name = u'/distribution/test_task_%d' % int(time.time() * 1000)
    task = Task.lazy_create(name=name)
    return task

def create_recipe(system=None, distro=None, task_name=u'/distribution/reservesys'):
    recipe = MachineRecipe(ttasks=1, system=system,
            distro=distro or Distro.query()[0])
    recipe.append_tasks(RecipeTask(task=create_task(name=task_name)))
    return recipe

def create_job_for_recipes(recipes, owner=None, cc=None):
    if owner is None:
        owner = create_user()
    job = Job(whiteboard=u'job %d' % int(time.time() * 1000), ttasks=1,
            owner=owner)
    if cc is not None:
        job.cc = cc
    recipe_set = RecipeSet(ttasks=sum(r.ttasks for r in recipes),
            priority=TaskPriority.default_priority())
    recipe_set.recipes.extend(recipes)
    job.recipesets.append(recipe_set)
    log.debug('Created %s', job.t_id)
    return job

def create_job(owner=None, cc=None, distro=None,
        task_name=u'/distribution/reservesys', **kwargs):
    recipe = create_recipe(distro=distro, task_name=task_name)
    return create_job_for_recipes([recipe], owner=owner, cc=cc)

def create_completed_job(**kwargs):
    job = create_job(**kwargs)
    mark_job_complete(job, **kwargs)
    return job

def mark_job_complete(job, result=u'Pass', system=None, **kwargs):
    for recipe in job.all_recipes:
        if system is None:
            recipe.system = create_system(arch=recipe.arch)
        else:
            recipe.system = system
        for recipe_task in recipe.tasks:
            recipe_task.status = TaskStatus.by_name(u'Running')
        recipe.update_status()
        for recipe_task in recipe.tasks:
            rtr = RecipeTaskResult(recipetask=recipe_task,
                    result=TaskResult.by_name(result))
            recipe_task.status = TaskStatus.by_name(u'Completed')
            recipe_task.results.append(rtr)
        recipe.update_status()
    log.debug('Marked %s as complete with result %s', job.t_id, result)

def create_device(**kw):
    device = Device(**kw)
