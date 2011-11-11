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
import os
import time
import datetime
import itertools
from sqlalchemy.orm.exc import NoResultFound
import turbogears.config, turbogears.database
from turbogears.database import session
from bkr.server.model import LabController, User, Group, Distro, Breed, Arch, \
        OSMajor, OSVersion, SystemActivity, Task, MachineRecipe, System, \
        SystemType, SystemStatus, Recipe, RecipeTask, RecipeTaskResult, \
        Device, TaskResult, TaskStatus, Job, RecipeSet, TaskPriority, \
        LabControllerDistro, Power, PowerType, TaskExcludeArch, TaskExcludeOSMajor, \
        Permission, RetentionTag, Product, Watchdog, Reservation, LogRecipe, \
        LogRecipeTask, ExcludeOSMajor, ExcludeOSVersion, Hypervisor

log = logging.getLogger(__name__)

ADMIN_USER = u'admin'
ADMIN_PASSWORD = u'testing'
ADMIN_EMAIL_ADDRESS = u'admin@example.com'

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
    init_db(user_name=ADMIN_USER, password=ADMIN_PASSWORD,
            user_email_address=ADMIN_EMAIL_ADDRESS)

_counter = itertools.count()
def unique_name(pattern):
    """
    Pass a %-format pattern, such as 'user%s', to generate a name that is 
    unique within this test run.
    """
    # time.time() * 1000 is no good, KVM guest wall clock is too dodgy
    # so we just use a global counter instead
    # http://29a.ch/2009/2/20/atomic-get-and-increment-in-python
    return pattern % _counter.next()

def create_product(product_name=None):
    if product_name is None:
        product_name = unique_name(u'product%s')
    return Product.lazy_create(name=product_name)
    

def create_labcontroller(fqdn=None, user=None):
    if fqdn is None:
        fqdn = unique_name(u'lab%s.testdata.invalid')
    try:
        lc = LabController.by_name(fqdn)  
    except NoResultFound:
        if user is None:
            user = create_user()
            session.flush()
        lc = LabController.lazy_create(fqdn=fqdn, user=user)
        # username/password to login into stub_cobbler
        # Doesn't matter what it is, just can't be None or we 
        # Will get cannot marshal none errors.
        lc.username = u"foo"
        lc.password = u"bar"
        return lc
    log.debug('labcontroller %s already exists' % fqdn)
    return lc

def create_user(user_name=None, password=None, display_name=None,
        email_address=None):
    if user_name is None:
        user_name = unique_name(u'user%s')
    if display_name is None:
        display_name = user_name
    if email_address is None:
        email_address = u'%s@example.com' % user_name
    # XXX use User.lazy_create
    user = User.by_user_name(user_name)
    if user is None:
        user = User(user_name=user_name)
    user.display_name = display_name
    user.email_address = email_address
    if password:
        user.password = password
    log.debug('Created user %r', user)
    return user

def create_admin(**kwargs):
    user = create_user(**kwargs)
    user.groups.append(Group.by_name(u'admin'))
    return user

def add_system_lab_controller(system,lc): 
    system.lab_controller = lc

def create_group(permissions=None):
    # tg_group.group_name column is VARCHAR(16)
    suffix = unique_name('%s')
    group = Group(group_name=u'group%s' % suffix, display_name=u'Group %s' % suffix)
    if permissions:
        group.permissions.extend(Permission.by_name(name) for name in permissions)
    return group

def add_user_to_group(user,group):
    user.groups.append(group)

def add_group_to_system(system,group):
    system.groups.append(group)

def create_distro(name=None, breed=u'Dan',
        osmajor=u'DansAwesomeLinux6', osminor=u'9',
        arch=u'i386', variant=u'Server', method=u'http', virt=False, tags=None):
    if not name:
        name = unique_name(u'DAN6.9-%s')
    install_name = u'%s_%s-%s-%s' % (name, method, variant, arch)
    distro = Distro(install_name=install_name)
    distro.name = name
    distro.method = method
    distro.breed = Breed.lazy_create(breed=breed)
    distro.variant = variant
    distro.virt = virt
    if tags:
        distro.tags.extend(tags)
    distro.arch = Arch.by_name(arch)
    osmajor = OSMajor.lazy_create(osmajor=osmajor)
    try:
        distro.osversion = OSVersion.by_name(osmajor, osminor)
    except NoResultFound:
        distro.osversion = OSVersion(osmajor, osminor, arches=[distro.arch])
    # make it available in all lab controllers
    for lc in LabController.query:
        distro.lab_controller_assocs.append(LabControllerDistro(lab_controller=lc))
    log.debug('Created distro %r', distro)
    harness_dir = os.path.join(turbogears.config.get('basepath.harness'), distro.osversion.osmajor.osmajor)
    if not os.path.exists(harness_dir):
        os.makedirs(harness_dir)
    return distro

def create_system(arch=u'i386', type=u'Machine', status=u'Automated',
        owner=None, fqdn=None, shared=False, exclude_osmajor=[],
        exclude_osversion=[], hypervisor=None, **kw):
    if owner is None:
        owner = create_user()
    if fqdn is None:
        fqdn = unique_name(u'system%s.testdata')
    if System.query.filter(System.fqdn == fqdn).count():
        raise ValueError('Attempted to create duplicate system %s' % fqdn)
    system = System(fqdn=fqdn,type=SystemType.by_name(type), owner=owner, 
                status=SystemStatus.by_name(status), **kw)
    system.shared = shared
    system.arch.append(Arch.by_name(arch))
    configure_system_power(system)
    system.excluded_osmajor.extend(ExcludeOSMajor(arch=Arch.by_name(arch),
            osmajor=osmajor) for osmajor in exclude_osmajor)
    system.excluded_osversion.extend(ExcludeOSVersion(arch=Arch.by_name(arch),
            osversion=osversion) for osversion in exclude_osversion)
    if hypervisor:
        system.hypervisor = Hypervisor.by_name(hypervisor)
    system.date_modified = datetime.datetime.utcnow()
    log.debug('Created system %r', system)
    return system

def configure_system_power(system, power_type=u'ilo', address=None,
        user=None, password=None, power_id=None):
    if address is None:
        address = u'%s_power_address' % system.fqdn
    if user is None:
        user = u'%s_power_user' % system.fqdn
    if password is None:
        password = u'%s_power_password' % system.fqdn
    if power_id is None:
        power_id = unique_name(u'%s')
    system.power = Power(power_type=PowerType.by_name(power_type),
            power_address=address, power_id=power_id,
            power_user=user, power_passwd=password)

def create_system_activity(user=None, **kw):
    if not user:
        user = create_user()
    activity = SystemActivity(user, u'WEBUI', u'Changed', u'Loaned To',
            unique_name(u'random_%s'), user.user_name)
    return activity

def create_task(name=None, exclude_arch=[],exclude_osmajor=[], version=u'1.0-1',
        uploader=None, owner=None, priority=u'Manual', valid=None):
    if name is None:
        name = unique_name(u'/distribution/test_task_%s')
    if uploader is None:
        uploader = create_user(user_name=u'task-uploader%s' % name.replace('/', '-'))
    if owner is None:
        owner = u'task-owner%s@example.invalid' % name.replace('/', '-')
    if valid is None:
        valid = True
    rpm = u'example%s-%s.noarch.rpm' % (name.replace('/', '-'), version)
    try:
        task = Task.by_name(name)
    except NoResultFound:
        task = Task(name=name)
    task.rpm = rpm
    task.version = version
    task.uploader = uploader
    task.owner = owner
    task.priority = priority
    task.valid = valid
    if exclude_arch:
       [TaskExcludeArch(arch_id=Arch.by_name(arch).id, task_id=task.id) for arch in exclude_arch]
    if exclude_osmajor:
        for osmajor in exclude_osmajor:
            distro = create_distro(osmajor=osmajor) 
            TaskExcludeOSMajor(task_id=task.id, osmajor_id=distro.osversion.osmajor.id)
        
    return task

def create_tasks(xmljob):
    # Add all tasks that the xml specifies
    names = set()
    for recipeset in xmljob.iter_recipeSets():
        for recipe in recipeset.iter_recipes():
            for task in recipe.iter_tasks():
                names.add(task.name)
    for name in names:
        create_task(name=name)

def create_recipe(system=None, distro=None, task_list=None, 
    task_name=u'/distribution/reservesys', whiteboard=None, server_log=False):
    recipe = MachineRecipe(ttasks=1, system=system, whiteboard=whiteboard,
            distro=distro or Distro.query.first())
    recipe.distro_requires = recipe.distro.to_xml().toxml()

    if not server_log:
        recipe.logs = [LogRecipe(path=u'/recipe_path',filename=u'dummy.txt', basepath=u'/beaker')]
    else:
        recipe.logs = [LogRecipe(server=u'http://dummy-archive-server/beaker/recipe_path', filename=u'dummy.txt' )]

    if not server_log:
        rt_log = lambda: LogRecipeTask(path=u'/tasks', filename=u'dummy.txt', basepath='/')
    else:
        rt_log = lambda: LogRecipeTask(server=u'http://dummy-archive-server/beaker/recipe_path/tasks', filename=u'dummy.txt')
    if task_list: #don't specify a task_list and a task_name...
        for t in task_list:
            rt = RecipeTask(task=t)
            rt.logs = [rt_log()]
            recipe.tasks.append(rt)

    else:
        rt = RecipeTask(task=create_task(name=task_name))
        rt.logs = [rt_log()]
        recipe.tasks.append(rt)
    return recipe

def create_retention_tag(name=None, default=False, needs_product=False):
    if name is None:
        name = unique_name(u'tag%s')
    new_tag = RetentionTag(name,is_default=default,needs_product=needs_product)
    return new_tag

def create_job_for_recipes(recipes, owner=None, whiteboard=None, cc=None,product=None,
        retention_tag=None):
    if retention_tag is None:
        retention_tag = RetentionTag.by_tag(u'scratch') # Don't use default, unpredictable
    else:
        retention_tag = RetentionTag.by_tag(retention_tag)
    
    if owner is None:
        owner = create_user()
    if whiteboard is None:
        whiteboard = unique_name(u'job %s')
    job = Job(whiteboard=whiteboard, ttasks=1, owner=owner,retention_tag = retention_tag, product=product)
    if cc is not None:
        job.cc = cc
    recipe_set = RecipeSet(ttasks=sum(r.ttasks for r in recipes),
            priority=TaskPriority.default_priority())
    recipe_set.recipes.extend(recipes)
    job.recipesets.append(recipe_set)
    log.debug('Created %s', job.t_id)
    session.flush()
    return job

def create_job(owner=None, cc=None, distro=None,product=None, 
        retention_tag=None, task_name=u'/distribution/reservesys', whiteboard=None,
        recipe_whiteboard=None, server_log=False, **kwargs):
    recipe = create_recipe(distro=distro, task_name=task_name,
            whiteboard=recipe_whiteboard, server_log=server_log)
    return create_job_for_recipes([recipe], owner=owner,
            whiteboard=whiteboard, cc=cc, product=product,retention_tag=retention_tag)

def create_completed_job(**kwargs):
    job = create_job(**kwargs)
    mark_job_complete(job, **kwargs)
    return job

def mark_recipe_complete(recipe, result=u'Pass', system=None,
        start_time=None, finish_time=None, **kwargs):
    if system is None:
        recipe.system = create_system(arch=recipe.arch)
    else:
        recipe.system = system
    recipe.start_time = start_time or datetime.datetime.utcnow()
    recipe.recipeset.queue_time = datetime.datetime.utcnow()
    reservation = Reservation(type=u'recipe',
            user=recipe.recipeset.job.owner, start_time=start_time)
    recipe.system.reservations.append(reservation)
    for recipe_task in recipe.tasks:
        recipe_task.start_time = start_time or datetime.datetime.utcnow()
        recipe_task.status = TaskStatus.by_name(u'Running')
    recipe.update_status()
    for recipe_task in recipe.tasks:
        rtr = RecipeTaskResult(recipetask=recipe_task,
                result=TaskResult.by_name(result))
        recipe_task.finish_time = finish_time or datetime.datetime.utcnow()
        recipe_task.status = TaskStatus.by_name(u'Completed')
        recipe_task.results.append(rtr)
    recipe.update_status()

    if finish_time:
        reservation.finish_time = finish_time
        recipe.finish_time = finish_time
    log.debug('Marked %s as complete with result %s', recipe.t_id, result)

def mark_job_complete(job, **kwargs):
    for recipe in job.all_recipes:
        mark_recipe_complete(recipe, **kwargs)

def mark_job_waiting(job, user=None):
    if user is None:
        user = create_user()
    for recipeset in job.recipesets:
        for recipe in recipeset.recipes:
            recipe.process()
            recipe.queue()
            recipe.schedule()
            recipe.system = create_system(owner=job.owner)
            recipe.system.reserve(service=u'testdata', user=job.owner,
                    reservation_type=u'recipe', recipe=recipe)
            recipe.watchdog = Watchdog(system=recipe.system)
            recipe.waiting()

def mark_job_running(job, user=None):
    mark_job_waiting(job, user=user)
    for recipe in job.all_recipes:
        for rt in recipe.tasks:
            rt.start()

def mark_job_queued(job):
    for recipe in job.all_recipes:
        recipe.process()
        recipe.queue()

def playback_task_results(task, xmltask):
    # Start task
    task.start()
    # Record Result
    task._result(xmltask.result, u'/', 0, u'(%s)' % xmltask.result)
    # Stop task
    if xmltask.status == u'Aborted':
        task.abort()
    elif xmltask.status == u'Cancelled':
        task.cancel()
    else:
        task.stop()

def playback_job_results(job, xmljob):
    for i, xmlrecipeset in enumerate(xmljob.iter_recipeSets()):
        for j, xmlrecipe in enumerate(xmlrecipeset.iter_recipes()):
            for l, xmlguest in enumerate(xmlrecipe.iter_guests()):
                for k, xmltask in enumerate(xmlguest.iter_tasks()):
                    playback_task_results(job.recipesets[i].recipes[j].guests[l].tasks[k], xmltask)
            for k, xmltask in enumerate(xmlrecipe.iter_tasks()):
                playback_task_results(job.recipesets[i].recipes[j].tasks[k], xmltask)

def create_manual_reservation(system, start, finish, user=None):
    if user is None:
        user = create_user()
    system.reservations.append(Reservation(start_time=start,
            finish_time=finish, type=u'manual', user=user))
    activity = SystemActivity(user=user,
            service=u'WEBUI', action=u'Reserved', field_name=u'User',
            old_value=u'', new_value=user.user_name)
    activity.created = start
    system.activity.append(activity)
    activity = SystemActivity(user=user,
            service=u'WEBUI', action=u'Returned', field_name=u'User',
            old_value=user.user_name, new_value=u'')
    activity.created = finish
    system.activity.append(activity)

def create_test_env(type):#FIXME not yet using different types
    """
    create_test_env() will populate the DB with no specific data.
    Useful when sheer volume of data is needed or the specifics of the
    actual data is not too important
    """

    arches = Arch.query.all()
    system_type = SystemType.by_name(u'Machine') #This could be extended into a list and looped over
    users = [create_user() for i in range(10)]
    lc = create_labcontroller()
    for arch in arches:
        create_distro(arch=arch)
        for user in users:
            system = create_system(owner=user, arch=arch.arch, type=system_type.type, status=u'Automated', shared=True)
            system.lab_controller = lc

def create_device(**kw):
    device = Device(**kw)
