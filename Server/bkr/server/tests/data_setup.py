
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import logging
import re
import os
import time
import datetime
import uuid
import itertools
import lxml.etree
from sqlalchemy.orm.exc import NoResultFound
import turbogears.config, turbogears.database
from turbogears.database import session, metadata
from bkr.server.bexceptions import DatabaseLookupError
from bkr.server.model import LabController, User, Group, UserGroup, \
        Distro, DistroTree, Arch, OSMajor, OSVersion, \
        SystemActivity, Task, MachineRecipe, System, \
        SystemType, SystemStatus, Recipe, RecipeTask, RecipeTaskResult, \
        Device, TaskResult, TaskStatus, Job, RecipeSet, TaskPriority, \
        LabControllerDistroTree, Power, PowerType, TaskExcludeArch, TaskExcludeOSMajor, \
        Permission, RetentionTag, Product, Watchdog, Reservation, LogRecipe, \
        LogRecipeTask, ExcludeOSMajor, ExcludeOSVersion, Hypervisor, DistroTag, \
        DeviceClass, DistroTreeRepo, TaskPackage, KernelType, \
        LogRecipeTaskResult, TaskType, SystemResource, GuestRecipe, \
        GuestResource, VirtResource, SystemStatusDuration, SystemAccessPolicy, \
        SystemPermission, DistroTreeImage, ImageType, KernelType, \
        RecipeReservationRequest, OSMajorInstallOptions, SystemPool, \
        GroupMembershipType

log = logging.getLogger(__name__)

ADMIN_USER = u'admin'
ADMIN_PASSWORD = u'testing'
ADMIN_EMAIL_ADDRESS = u'admin@example.com'

def setup_model(override=True):
    from bkr.server.tools.init import init_db, populate_db
    engine = turbogears.database.get_engine()
    db_name = engine.url.database
    if db_name: # it will be None for in-memory sqlite
        connection = engine.connect()
        if override:
            log.info('Dropping database %s', db_name)
            connection.execute('DROP DATABASE IF EXISTS %s' % db_name)
        log.info('Creating database %s', db_name)
        connection.execute('CREATE DATABASE %s' % db_name)
        connection.invalidate() # can't reuse this one
        del connection
    log.info('Initialising model')
    init_db(metadata)
    populate_db(user_name=ADMIN_USER, password=ADMIN_PASSWORD,
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

def create_distro_tag(tag=None):
    if tag is None:
        tag = unique_name('tag%s')
    return DistroTag.lazy_create(tag=tag)

def create_labcontroller(fqdn=None, user=None):
    if fqdn is None:
        fqdn = unique_name(u'lab%s.testdata.invalid')
    try:
        lc = LabController.by_name(fqdn)  
    except NoResultFound:
        if user is None:
            user = User(user_name=u'host/%s' % fqdn,
                    email_address=u'root@%s' % fqdn)
        lc = LabController(fqdn=fqdn)
        lc.user = user
        session.add(lc)
        group = Group.by_name(u'lab_controller')
        group.add_member(user, service=u'testdata')
        # Need to ensure it is inserted now, since we aren't using lazy_create 
        # here so a subsequent call to create_labcontroller could try and 
        # create the same LC again.
        session.flush()
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
    user = User.lazy_create(user_name=user_name)
    user.display_name = display_name
    user.email_address = email_address
    if password:
        user.password = password
    user.openstack_username = user_name
    user.openstack_password = u'dummy_openstack_password_for_%s' % user_name
    user.openstack_tenant_name = u'Dummy Tenant for %s' % user_name
    log.debug('Created user %r', user)
    return user

def create_admin(user_name=None, **kwargs):
    if user_name is None:
        user_name = unique_name(u'admin%s')
    user = create_user(user_name=user_name, **kwargs)
    group = Group.by_name(u'admin')
    group.add_member(user, service=u'testdata')
    return user

def add_system_lab_controller(system,lc): 
    system.lab_controller = lc

def create_group(permissions=None, group_name=None, display_name=None,
        owner=None, membership_type=GroupMembershipType.normal, root_password=None):
    # tg_group.group_name column is VARCHAR(16)
    if group_name is None:
        group_name = unique_name(u'group%s')
    assert len(group_name) <= 16
    group = Group.lazy_create(group_name=group_name)
    group.root_password = root_password
    if display_name is None:
        group.display_name = u'Group %s' % group_name
    else:
        group.display_name = display_name

    group.membership_type = membership_type
    if group.membership_type == GroupMembershipType.ldap:
        assert owner is None, 'LDAP groups cannot have owners'
    if not owner:
        owner = create_user(user_name=unique_name(u'group_owner_%s'))
    group.add_member(owner, is_owner=True, service=u'testdata')

    if permissions:
        group.permissions.extend(Permission.by_name(name) for name in permissions)
    return group

def create_permission(name=None):
    if not name:
        name = unique_name('permission%s')
    permission = Permission(name)
    session.add(permission)
    return permission

def add_pool_to_system(system, pool):
    system.pools.append(pool)

def create_distro(name=None, osmajor=u'DansAwesomeLinux6', osminor=u'9',
                  arches=None, tags=None, harness_dir=True,
                  osmajor_installopts=None, date_created=None):
    osmajor = OSMajor.lazy_create(osmajor=osmajor)
    osversion = OSVersion.lazy_create(osmajor=osmajor, osminor=osminor)
    if arches:
        osversion.arches = [Arch.by_name(arch) for arch in arches]
    if not name:
        name = unique_name(u'%s.%s-%%s' % (osmajor, osminor))
    distro = Distro.lazy_create(name=name, osversion=osversion)
    if date_created is not None:
        distro.date_created = date_created
    for tag in (tags or []):
        distro.add_tag(tag)
    # add distro wide install options, if any
    if osmajor_installopts:
        for arch in arches:
            io = OSMajorInstallOptions.lazy_create(osmajor_id=osmajor.id,
                                                   arch_id=Arch.by_name(arch).id)
            io.ks_meta = osmajor_installopts.get('ks_meta', '')
            io.kernel_options = osmajor_installopts.get('kernel_options', '')
            io.kernel_options_post = osmajor_installopts.get('kernel_options_post', '')

    log.debug('Created distro %r', distro)
    if harness_dir:
        harness_dir = os.path.join(turbogears.config.get('basepath.harness'), distro.osversion.osmajor.osmajor)
        if not os.path.exists(harness_dir):
            os.makedirs(harness_dir)
    return distro

def create_distro_tree(distro=None, distro_name=None, osmajor=u'DansAwesomeLinux6',
        osminor=u'9', distro_tags=None, arch=u'i386', variant=u'Server',
        lab_controllers=None, urls=None,  harness_dir=True, osmajor_installopts_arch=None):
    if distro is None:
        distro = create_distro(name=distro_name, osmajor=osmajor, osminor=osminor,
                tags=distro_tags, harness_dir=harness_dir)
    distro_tree = DistroTree.lazy_create(distro=distro,
            arch=Arch.lazy_create(arch=arch), variant=variant)
    if distro_tree.arch not in distro.osversion.arches:
        distro.osversion.arches.append(distro_tree.arch)
    DistroTreeRepo.lazy_create(distro_tree=distro_tree,
            repo_id=variant, repo_type=u'variant', path=u'')
    DistroTreeImage.lazy_create(distro_tree=distro_tree,
            image_type=ImageType.kernel,
            kernel_type=KernelType.by_name(u'default'),
            path=u'pxeboot/vmlinuz')
    DistroTreeImage.lazy_create(distro_tree=distro_tree,
            image_type=ImageType.initrd,
            kernel_type=KernelType.by_name(u'default'),
            path=u'pxeboot/initrd')
    existing_urls = [lc_distro_tree.url for lc_distro_tree in distro_tree.lab_controller_assocs]
    # make it available in all lab controllers by default
    if lab_controllers is None:
        lab_controllers = LabController.query
    for lc in lab_controllers:
        default_urls = [u'%s://%s%s/distros/%s/%s/%s/os/' % (scheme, lc.fqdn,
                scheme == 'nfs' and ':' or '',
                distro_tree.distro.name, distro_tree.variant,
                distro_tree.arch.arch) for scheme in ['nfs', 'http', 'ftp']]
        for url in (urls or default_urls):
            if url in existing_urls:
                break
            lab_controller_distro_tree = LabControllerDistroTree(
                lab_controller=lc, url=url)
            distro_tree.lab_controller_assocs.append(lab_controller_distro_tree)

    if osmajor_installopts_arch:
        io = OSMajorInstallOptions.lazy_create(osmajor_id=distro_tree.distro.osversion.osmajor.id,
                                               arch_id=distro_tree.arch.id)
        io.ks_meta = osmajor_installopts_arch.get('ks_meta', '')
        io.kernel_options = osmajor_installopts_arch.get('kernel_options', '')
        io.kernel_options_post = osmajor_installopts_arch.get('kernel_options_post', '')

    log.debug('Created distro tree %r', distro_tree)
    return distro_tree

def create_system(arch=u'i386', type=SystemType.machine, status=SystemStatus.automated,
        owner=None, fqdn=None, shared=True, exclude_osmajor=[],
        exclude_osversion=[], hypervisor=None, kernel_type=None,
        date_added=None, return_existing=False, private=False, with_power=True, **kw):
    if owner is None:
        owner = create_user()
    if fqdn is None:
        fqdn = unique_name(u'system%s.testdata')

    if System.query.filter(System.fqdn == fqdn).count():
        if return_existing:
            system = System.query.filter(System.fqdn == fqdn).first()
            for property, value in kw.iteritems():
               setattr(system, property, value)
        else:
            raise ValueError('Attempted to create duplicate system %s' % fqdn)
    else:
        system = System(fqdn=fqdn,type=type, owner=owner,
            status=status, **kw)
        session.add(system)

    if date_added is not None:
        system.date_added = date_added
    system.custom_access_policy = SystemAccessPolicy()
    if not private:
        system.custom_access_policy.add_rule(SystemPermission.view, everybody=True)
    if shared:
        system.custom_access_policy.add_rule(
                permission=SystemPermission.reserve, everybody=True)
    if isinstance(arch, list):
        for a in arch:
            system.arch.append(Arch.by_name(a))
            system.excluded_osmajor.extend(ExcludeOSMajor(arch=Arch.by_name(a),
                                                          osmajor=osmajor) for osmajor in exclude_osmajor)
            system.excluded_osversion.extend(ExcludeOSVersion(arch=Arch.by_name(a),
                                                              osversion=osversion) for osversion in exclude_osversion)
    else:
        system.arch.append(Arch.by_name(arch))
        system.excluded_osmajor.extend(ExcludeOSMajor(arch=Arch.by_name(arch),
                                                      osmajor=osmajor) for osmajor in exclude_osmajor)
        system.excluded_osversion.extend(ExcludeOSVersion(arch=Arch.by_name(arch),
                                                          osversion=osversion) for osversion in exclude_osversion)
    if with_power:
        configure_system_power(system)
    if hypervisor:
        system.hypervisor = Hypervisor.by_name(hypervisor)
    if kernel_type:
        system.kernel_type = KernelType.by_name(kernel_type)
    system.date_modified = datetime.datetime.utcnow()
    log.debug('Created system %r', system)
    return system

def create_system_pool(name=None, description='A system Pool',
                       owning_group=None, owning_user=None, systems=[]):
    if owning_group and owning_user:
        raise ValueError('Must supply either an owning user or an owning group')
    if not owning_group and not owning_user:
        owning_user = create_user()
    if name is None:
        name = unique_name(u'test-system-pool-%s')
    pool = SystemPool(name=name, description=description,
                      owning_group=owning_group,
                      owning_user=owning_user,
                      systems=systems)
    pool.access_policy = SystemAccessPolicy()
    pool.access_policy.add_rule(SystemPermission.view, everybody=True)
    session.add(pool)
    log.debug('Created System Pool %s', pool.name)
    return pool

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
    session.add(activity)
    return activity

def create_system_status_history(system, statuses):
    """ For *statuses* pass a list of tuples of (status, start_time). """
    ssd = SystemStatusDuration(status=statuses[0][0], start_time=statuses[0][1])
    for status, start_time in statuses[1:]:
        ssd.finish_time = start_time
        system.status_durations.append(ssd)
        ssd = SystemStatusDuration(status=status, start_time=start_time)
    ssd.finish_time = datetime.datetime.utcnow()
    system.status_durations.append(ssd)
    # last one should be its current status
    system.status_durations.append(SystemStatusDuration(status=system.status,
            start_time=ssd.finish_time))

def create_task(name=None, exclude_arch=None, exclude_osmajor=None, version=u'1.0-1',
        uploader=None, owner=None, priority=u'Manual', valid=None, path=None, 
        description=None, requires=None, runfor=None, type=None):
    if name is None:
        name = unique_name(u'/distribution/test_task_%s')
    if path is None:
        path = u'/mnt/tests/%s' % name
    if description is None:
        description = unique_name(u'description%s')
    if uploader is None:
        uploader = create_user(user_name=u'task-uploader%s' % name.replace('/', '-'))
    if owner is None:
        owner = u'task-owner%s@example.invalid' % name.replace('/', '-')
    if valid is None:
        valid = True
    rpm = u'example%s-%s.noarch.rpm' % (name.replace('/', '-'), version)

    task = Task.lazy_create(name=name)
    task.rpm = rpm
    task.version = version
    task.uploader = uploader
    task.owner = owner
    task.priority = priority
    task.valid = valid
    task.path = path
    task.description = description
    task.avg_time = 1200
    if type:
        for t in type:
            task.types.append(TaskType.lazy_create(type=t))
    if exclude_arch:
       for arch in exclude_arch:
           task.excluded_arch.append(TaskExcludeArch(arch_id=Arch.by_name(arch).id))
    if exclude_osmajor:
        for osmajor in exclude_osmajor:
            task.excluded_osmajor.append(TaskExcludeOSMajor(osmajor=OSMajor.lazy_create(osmajor=osmajor)))
    if requires:
        for require in requires:
            tp = TaskPackage.lazy_create(package=require)
            task.required.append(tp)
    if runfor:
        for run in runfor:
            task.runfor.append(TaskPackage.lazy_create(package=run))
    return task

def create_tasks(xmljob):
    # Add all tasks that the xml specifies
    names = set()
    for task in xmljob.xpath('recipeSet/recipe/task'):
        names.add(task.get('name'))
    for name in names:
        create_task(name=name)

def create_recipe(distro_tree=None, task_list=None,
        task_name=u'/distribution/reservesys', num_tasks=None, whiteboard=None,
        role=None, cls=MachineRecipe, **kwargs):
    if not distro_tree:
        distro_tree = create_distro_tree()
    recipe = cls(ttasks=1)
    recipe.whiteboard = whiteboard
    recipe.distro_tree = distro_tree
    recipe.role = role or u'STANDALONE'
    recipe.distro_requires = lxml.etree.tostring(recipe.distro_tree.to_xml())

    if kwargs.get('reservesys', False):
        duration=kwargs.get('reservesys_duration', 86400)
        recipe.reservation_request = RecipeReservationRequest(duration)

    if num_tasks:
        task_list = [create_task() for i in range(0, num_tasks)]
    if task_list: #don't specify a task_list and a task_name...
        for t in task_list:
            rt = RecipeTask.from_task(t)
            rt.role = u'STANDALONE'
            recipe.tasks.append(rt)
        recipe.ttasks = len(task_list)
    else:
        rt = RecipeTask.from_task(create_task(name=task_name))
        rt.role = u'STANDALONE'
        recipe.tasks.append(rt)
    return recipe

def create_guestrecipe(host, guestname=None, **kwargs):
    guestrecipe = create_recipe(cls=GuestRecipe, **kwargs)
    guestrecipe.guestname = guestname
    host.guests.append(guestrecipe)
    return guestrecipe

def create_retention_tag(name=None, default=False, needs_product=False):
    if name is None:
        name = unique_name(u'tag%s')
    new_tag = RetentionTag(name,is_default=default,needs_product=needs_product)
    session.add(new_tag)
    return new_tag

def create_job_for_recipes(recipes, **kwargs):
    recipeset = create_recipeset_for_recipes(recipes, **kwargs)
    return create_job_for_recipesets([recipeset], **kwargs)

def create_job_for_recipesets(recipesets, owner=None, whiteboard=None, cc=None,
        product=None, retention_tag=None, group=None, submitter=None, **kwargs):
    if retention_tag is None:
        retention_tag = RetentionTag.by_tag(u'scratch') # Don't use default, unpredictable
    else:
        retention_tag = RetentionTag.by_tag(retention_tag)

    if owner is None:
        owner = create_user()
    if whiteboard is None:
        whiteboard = unique_name(u'job %s')
    job = Job(whiteboard=whiteboard, ttasks=sum(rs.ttasks for rs in recipesets),
        owner=owner, retention_tag=retention_tag, group=group, product=product,
        submitter=submitter)
    if cc is not None:
        job.cc = cc
    job.recipesets.extend(recipesets)
    session.add(job)
    session.flush()
    log.debug('Created %s', job.t_id)
    return job

def create_recipeset_for_recipes(recipes, priority=None, queue_time=None, **kwargs):
    if priority is None:
        priority = TaskPriority.default_priority()
    recipe_set = RecipeSet(ttasks=sum(r.ttasks for r in recipes),
            priority=priority)
    if queue_time is not None:
        recipe_set.queue_time = queue_time
    recipe_set.recipes.extend(recipes)
    return recipe_set

def create_job(num_recipesets=1, num_recipes=1, num_guestrecipes=0, whiteboard=None,
        recipe_whiteboard=None, **kwargs):
    if kwargs.get('distro_tree', None) is None:
        kwargs['distro_tree'] = create_distro_tree()
    recipesets = []
    for _ in range(num_recipesets):
        recipes = [create_recipe(whiteboard=recipe_whiteboard, **kwargs)
                for _ in range(num_recipes)]
        guestrecipes = [create_guestrecipe(host=recipes[0],
                whiteboard=recipe_whiteboard, **kwargs)
                for _ in range(num_guestrecipes)]
        recipesets.append(create_recipeset_for_recipes(
                recipes + guestrecipes, **kwargs))
    return create_job_for_recipesets(recipesets, whiteboard=whiteboard, **kwargs)

def create_running_job(**kwargs):
    job = create_job(**kwargs)
    mark_job_running(job, **kwargs)
    return job

def create_completed_job(**kwargs):
    job = create_job(**kwargs)
    mark_job_complete(job, **kwargs)
    return job

def mark_recipe_complete(recipe, result=TaskResult.pass_,
                         task_status=TaskStatus.completed,
                         finish_time=None, only=False,
                         server_log=False, **kwargs):

    mark_recipe_tasks_finished(recipe, result=result,
                               task_status=task_status,
                               finish_time=finish_time,
                               only=only,
                               server_log=server_log,
                               **kwargs)
    recipe.recipeset.job.update_status()
    log.debug('Marked %s as complete with result %s', recipe.t_id, result)

def mark_recipe_tasks_finished(recipe, result=TaskResult.pass_,
                               task_status=TaskStatus.completed,
                               finish_time=None, only=False,
                               server_log=False,
                               num_tasks=None, **kwargs):

    # we accept result=None to mean: don't add any results to recipetasks
    assert result is None or result in TaskResult
    finish_time = finish_time or datetime.datetime.utcnow()
    if not only:
        mark_recipe_running(recipe, **kwargs)
        mark_recipe_installation_finished(recipe)

    # Need to make sure recipe.watchdog has been persisted, since we delete it 
    # below when the recipe completes and sqlalchemy will barf on deleting an 
    # instance that hasn't been persisted.
    session.flush()

    if not server_log:
        recipe.log_server = recipe.recipeset.lab_controller.fqdn
        recipe.logs = [LogRecipe(path=u'recipe_path',filename=u'dummy.txt')]
    else:
        recipe.log_server = u'dummy-archive-server'
        recipe.logs = [LogRecipe(server=u'http://dummy-archive-server/beaker/',
                path=u'recipe_path', filename=u'dummy.txt' )]

    if not server_log:
        rt_log = lambda: LogRecipeTask(path=u'tasks', filename=u'dummy.txt')
    else:
        rt_log = lambda: LogRecipeTask(server=u'http://dummy-archive-server/beaker/',
                path=u'tasks', filename=u'dummy.txt')
    if not server_log:
        rtr_log = lambda: LogRecipeTaskResult(path=u'/', filename=u'result.txt')
    else:
        rtr_log = lambda: LogRecipeTaskResult(server=u'http://dummy-archive-server/beaker/',
                path=u'/', filename=u'result.txt')

    for recipe_task in recipe.tasks[:num_tasks]:
        if result is not None:
            rtr = RecipeTaskResult(path=recipe_task.name, result=result,
                    log=u'(%s)' % result, score=0)
            rtr.logs = [rtr_log()]
            recipe_task.results.append(rtr)
        recipe_task.logs = [rt_log()]
        recipe_task.finish_time = finish_time
        recipe_task._change_status(task_status)
    log.debug('Marked %s tasks in %s as %s with result %s',
              num_tasks or 'all', recipe.t_id, task_status, result)

def mark_job_complete(job, finish_time=None, only=False, **kwargs):
    if not only:
        for recipe in job.all_recipes:
            mark_recipe_running(recipe, **kwargs)
            mark_recipe_installation_finished(recipe, **kwargs)
    for recipe in job.all_recipes:
        mark_recipe_complete(recipe, finish_time=finish_time, only=True, **kwargs)
        if finish_time:
            recipe.resource.reservation.finish_time = finish_time
            recipe.finish_time = finish_time

def mark_recipe_waiting(recipe, start_time=None, system=None, fqdn=None,
        lab_controller=None, virt=False, instance_id=None, **kwargs):
    if start_time is None:
        start_time = datetime.datetime.utcnow()
    recipe.process()
    recipe.queue()
    recipe.schedule()
    if not recipe.resource:
        if isinstance(recipe, MachineRecipe):
            if virt:
                if not lab_controller:
                    lab_controller = create_labcontroller(fqdn=u'dummylab.example.invalid')
                if not instance_id:
                    instance_id = uuid.uuid4()
                recipe.resource = VirtResource(instance_id, lab_controller)
                recipe.recipeset.lab_controller = lab_controller
            else:
                if not system:
                    if not lab_controller:
                        lab_controller = create_labcontroller(fqdn=u'dummylab.example.invalid')
                    system = create_system(arch=recipe.arch.arch,
                            fqdn=fqdn, lab_controller=lab_controller)
                recipe.resource = SystemResource(system=system)
                recipe.resource.allocate()
                recipe.resource.reservation.start_time = start_time
                recipe.recipeset.lab_controller = system.lab_controller
        elif isinstance(recipe, GuestRecipe):
            recipe.resource = GuestResource()
            recipe.resource.allocate()
    recipe.start_time = start_time
    recipe.watchdog = Watchdog()
    recipe.waiting()
    recipe.resource.rebooted = start_time
    recipe.recipeset.job.update_status()
    log.debug('Marked %s as waiting with system %s', recipe.t_id, recipe.resource.fqdn)

def mark_job_waiting(job, **kwargs):
    for recipeset in job.recipesets:
        for recipe in recipeset.recipes:
            mark_recipe_waiting(recipe, **kwargs)

def mark_recipe_running(recipe, fqdn=None, only=False, **kwargs):
    if not only:
        mark_recipe_waiting(recipe, fqdn=fqdn, **kwargs)
    recipe.resource.install_started = datetime.datetime.utcnow()
    recipe.tasks[0].start()
    if isinstance(recipe, GuestRecipe):
        if not fqdn:
            fqdn = unique_name(u'guest_fqdn_%s')
        recipe.resource.fqdn = fqdn
    recipe.recipeset.job.update_status()
    log.debug('Started %s', recipe.tasks[0].t_id)

def mark_recipe_installation_finished(recipe, fqdn=None, **kwargs):
    if not recipe.resource.fqdn:
        # system reports its FQDN to Beaker in kickstart %post
        if fqdn is None:
            fqdn = '%s-for-recipe-%s' % (recipe.resource.__class__.__name__, recipe.id)
        recipe.resource.fqdn = fqdn
    recipe.resource.install_finished = datetime.datetime.utcnow()
    recipe.resource.postinstall_finished = datetime.datetime.utcnow()
    recipe.recipeset.job.update_status()

def mark_job_running(job, **kw):
    for recipe in job.all_recipes:
        mark_recipe_running(recipe, **kw)

def mark_job_queued(job):
    for recipe in job.all_recipes:
        recipe.process()
        recipe.queue()
    job.update_status()

def playback_task_results(task, xmltask):
    # Start task
    task.start()
    # Record Result
    task._result(TaskResult.from_string(xmltask.get('result')), u'/', 0, u'(%s)' % xmltask.get('result'))
    # Stop task
    if xmltask.get('status') == u'Aborted':
        task.abort()
    elif xmltask.get('status') == u'Cancelled':
        task._abort_cancel(TaskStatus.cancelled)
    else:
        task.stop()

def playback_job_results(job, xmljob):
    for i, xmlrecipeset in enumerate(xmljob.xpath('recipeSet')):
        for j, xmlrecipe in enumerate(xmlrecipeset.xpath('recipe')):
            for l, xmlguest in enumerate(xmlrecipe.xpath('guestrecipe')):
                for k, xmltask in enumerate(xmlguest.xpath('task')):
                    playback_task_results(job.recipesets[i].recipes[j].guests[l].tasks[k], xmltask)
                    job.update_status()
            for k, xmltask in enumerate(xmlrecipe.xpath('task')):
                playback_task_results(job.recipesets[i].recipes[j].tasks[k], xmltask)
                job.update_status()

def create_manual_reservation(system, start, finish=None, user=None):
    if user is None:
        user = create_user()
    system.reservations.append(Reservation(start_time=start,
            finish_time=finish, type=u'manual', user=user))
    activity = SystemActivity(user=user,
            service=u'WEBUI', action=u'Reserved', field_name=u'User',
            old_value=u'', new_value=user.user_name)
    activity.created = start
    system.activity.append(activity)
    if finish:
        activity = SystemActivity(user=user,
                service=u'WEBUI', action=u'Returned', field_name=u'User',
                old_value=user.user_name, new_value=u'')
        activity.created = finish
        system.activity.append(activity)

def unreserve_manual(system, finish=None):
    if finish is None:
        finish = datetime.datetime.utcnow()
    user = system.open_reservation.user
    activity = SystemActivity(user=user,
            service=u'WEBUI', action=u'Returned', field_name=u'User',
            old_value=user.user_name, new_value=u'')
    activity.created = finish
    system.activity.append(activity)
    system.open_reservation.finish_time = finish

def create_test_env(type):#FIXME not yet using different types
    """
    create_test_env() will populate the DB with no specific data.
    Useful when sheer volume of data is needed or the specifics of the
    actual data is not too important
    """

    arches = Arch.query.all()
    system_type = SystemType.machine #This could be extended into a list and looped over
    users = [create_user() for i in range(10)]
    lc = create_labcontroller()
    for arch in arches:
        create_distro_tree(arch=arch)
        for user in users:
            system = create_system(owner=user, arch=arch.arch, type=system_type, status=u'Automated', shared=True)
            system.lab_controller = lc

def create_device_class(device_class):
    return DeviceClass.lazy_create(device_class=device_class)

def create_device(device_class=None, **kwargs):
    if device_class is not None:
        kwargs['device_class_id'] = create_device_class(device_class).id
    return Device.lazy_create(**kwargs)

def create_recipe_reservation(user, task_name=u'/distribution/reservesys', kill_time=0):
    recipe = create_recipe(task_name=task_name)
    create_job_for_recipes([recipe], owner=user)
    mark_recipe_running(recipe)
    recipe.extend(kill_time)
    return recipe
