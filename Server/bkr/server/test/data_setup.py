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
import sqlalchemy
import turbogears.config, turbogears.database
from bkr.server.model import *

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
            session.flush()
            return lc
        else:
            raise
    log.debug('labcontroller %s already exists' % fqdn)
    return lc

def create_user(user_name=None, password=None):
    if user_name is None:
        display_name = user_name = u'user%d' % int(time.time() * 1000)
    else:
        display_name = user_name

    user = User(user_name=u'user%d' % int(time.time() * 1000),
            display_name=display_name)
    if password:
        user.password = password
    user.email_address = u'%s@example.com' % user.user_name
    log.debug('Created user %r', user)
    session.flush()
    return user

def create_group():
    group = Group(group_name=u'group%s' % str(int(time.time() * 1000))[5:9])
    session.flush()
    return group

def add_user_to_group(user,group):
    user.groups.append(group)
    session.flush()

def append_distro_to_lc(distro,lc):
    lcd = LabControllerDistro()
    lcd.distro = distro
    lc._distros.append(lcd)
    session.flush()

def create_distro(name=u'DAN6-Server-U9', breed=u'Dan',
        osmajor=u'DansAwesomeLinuxServer6', osminor=u'9',
        arch=u'i386', method=u'http', virt=False):
    install_name = u'%s-%d_%s-%s' % (name, int(time.time() * 1000), method, arch)
    distro = Distro(install_name=install_name)
    distro.name = name
    distro.method = method
    distro.breed = Breed.lazy_create(breed=breed)
    distro.virt = virt
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
    owner=None,fqdn=None, **kw):
    if fqdn is None:
        fqdn = u'system%d.testdata' % int(time.time() * 1000)
    system = System(fqdn=fqdn,type=SystemType.by_name(type), owner=owner, 
                status=SystemStatus.by_name(status), **kw)
    system.arch.append(Arch.by_name(arch))
    session.flush()
    log.debug('Created system %r', system)
    return system

def create_system_activity(user=None, **kw):
    if not user:
        user = create_user()
    activity = SystemActivity(user, 'WEBUI', 'Changed', 'Loaned To', 'random_%d' % int(time.time() * 1000) , '%s' % user)
    session.flush()
    return activity

def create_task(task_name=None):
    if task_name is None:
        task_name = u'/distribution/test_task_%d' % int(time.time() * 1000)
    task = Task.lazy_create(name=task_name)
    session.flush()
    return task

def create_job(owner, distro=None, task_name=u'/distribution/reservesys'):
    if owner is None:
        owner = create_user()
    job = Job(whiteboard=u'job %d' % int(time.time() * 1000), ttasks=1, owner=owner)
    recipe_set = RecipeSet(ttasks=1, priority=TaskPriority.default_priority())
    recipe = MachineRecipe(ttasks=1, distro=distro or Distro.query()[0])
    recipe.append_tasks(RecipeTask(task=create_task(task_name=task_name)))
    recipe_set.recipes.append(recipe)
    job.recipesets.append(recipe_set)
    log.debug('Created %s', job.t_id)
    return job

def create_completed_job(result=u'Pass', **kwargs):
    job = create_job(**kwargs)
    for recipe in job.all_recipes:
        recipe.system = create_system(arch=recipe.arch)
        for recipe_task in recipe.tasks:
            rtr = RecipeTaskResult(recipetask=recipe_task,
                    result=TaskResult.by_name(result))
            recipe_task.status = TaskStatus.by_name(u'Completed')
            recipe_task.results.append(rtr)
    job.update_status()
    log.debug('Marked %s as complete with result %s', job.t_id, result)
    return job

def create_device(**kw):
    device = Device(**kw)
    session.flush()

