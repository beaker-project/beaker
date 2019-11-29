
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import inspect
import itertools
import logging
import os
import unittest

import datetime
import lxml.etree
import mock
import netaddr
import turbogears.config
import turbogears.database
import uuid
from sqlalchemy.orm.exc import NoResultFound
from turbogears.database import session, metadata

from bkr.server import dynamic_virt
from bkr.server.model import (
    LabController, User, Group, Distro, DistroTree, Arch, OSMajor, OSVersion,
    SystemActivity, Task, MachineRecipe, System, SystemType, SystemStatus,
    RecipeTask, RecipeTaskResult, Device, TaskResult, TaskStatus, Job,
    RecipeSet, TaskPriority, LabControllerDistroTree, Power, PowerType,
    Permission, RetentionTag, Product, Watchdog, Reservation, LogRecipe,
    LogRecipeTask, ExcludeOSMajor, ExcludeOSVersion, Hypervisor, DistroTag,
    DeviceClass, DistroTreeRepo, TaskPackage, LogRecipeTaskResult, TaskType,
    SystemResource, GuestRecipe, GuestResource, VirtResource,
    SystemStatusDuration, SystemAccessPolicy, SystemPermission, DistroTreeImage,
    ImageType, KernelType, RecipeReservationRequest, OSMajorInstallOptions,
    SystemPool, GroupMembershipType, Installation, CommandStatus,
    OpenStackRegion, SystemSchedulerStatus)
from bkr.server.model.types import mac_unix_padded_dialect

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
        email_address=None, notify_job_completion=True, notify_broken_system=True,
        notify_group_membership=True, notify_reservesys=True):
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
    user.notify_job_completion = notify_job_completion
    user.notify_broken_system = notify_broken_system
    user.notify_group_membership = notify_group_membership
    user.notify_reservesys = notify_reservesys
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
    if group_name is None:
        group_name = unique_name(u'group%s')
    group = Group.lazy_create(group_name=group_name)
    group.root_password = root_password
    if display_name is None:
        group.display_name = u'Group %s display name' % group_name
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
        name = unique_name(u'permission%s')
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
        # list arches may contains unicode name or instance
        # Comparing instance to attribute is prohibited in SQLAlchemy 1.1 and later
        osversion.arches = [Arch.by_name(arch.arch if isinstance(arch, Arch) else arch)
                            for arch in arches]
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
        lab_controllers=None, urls=None,  harness_dir=True,
        osmajor_installopts_arch=None, date_created=None, **kwargs):
    if distro is None:
        distro = create_distro(name=distro_name, osmajor=osmajor, osminor=osminor,
                tags=distro_tags, harness_dir=harness_dir, date_created=date_created)
    distro_tree = DistroTree(distro=distro, arch=Arch.lazy_create(arch=arch), variant=variant)
    if date_created is not None:
        distro_tree.date_created = date_created
    if distro_tree.arch not in distro.osversion.arches:
        distro.osversion.arches.append(distro_tree.arch)
    distro_tree.repos.append(DistroTreeRepo(repo_id=variant, repo_type=u'variant', path=u''))
    distro_tree.images.append(DistroTreeImage(
            image_type=ImageType.kernel,
            kernel_type=KernelType.by_name(u'default'),
            path=u'pxeboot/vmlinuz'))
    distro_tree.images.append(DistroTreeImage(
            image_type=ImageType.initrd,
            kernel_type=KernelType.by_name(u'default'),
            path=u'pxeboot/initrd'))
    session.flush() # to get an id
    # make it available in all lab controllers by default
    if lab_controllers is None:
        lab_controllers = LabController.query
    for lc in lab_controllers:
        add_distro_tree_to_lab(distro_tree, lc, urls=urls)

    if osmajor_installopts_arch:
        io = OSMajorInstallOptions.lazy_create(osmajor_id=distro_tree.distro.osversion.osmajor.id,
                                               arch_id=distro_tree.arch.id)
        io.ks_meta = osmajor_installopts_arch.get('ks_meta', '')
        io.kernel_options = osmajor_installopts_arch.get('kernel_options', '')
        io.kernel_options_post = osmajor_installopts_arch.get('kernel_options_post', '')

    log.debug('Created distro tree %r', distro_tree)
    return distro_tree

def add_distro_tree_to_lab(distro_tree, lab_controller, urls=None):
    if urls is None:
        urls = [u'%s://%s%s/distros/%s/%s/%s/os/' % (scheme,
                lab_controller.fqdn, scheme == 'nfs' and ':' or '',
                distro_tree.distro.name, distro_tree.variant,
                distro_tree.arch.arch) for scheme in ['nfs', 'http', 'ftp']]
    # Instead of using the LabControllerDistroTree model like normal,
    # we hack the rows directly into the database. This is specifically to
    # avoid firing the mark_systems_pending_when_distro_tree_added_to_lab
    # event listener, which is not necessary when we are setting up test data,
    # and can be potentially quite expensive.
    session.execute(LabControllerDistroTree.__table__.insert().values([
            {'distro_tree_id': distro_tree.id, 'lab_controller_id': lab_controller.id, 'url': url}
            for url in urls]))
    session.expire(distro_tree, ['lab_controller_assocs'])

def get_test_name():
    """Inspects the stack and guess the possible caller name from our test suite."""
    # Explicitly delete references to frames to avoid cycles
    try:
        curframe = inspect.currentframe()
        outerframes = inspect.getouterframes(curframe, 2)
        test_name = 'testdata'
        for outerframe in outerframes:  # to the top!!
            try:
                possible_testframe = outerframe[0]
                locals = inspect.getargvalues(possible_testframe)[3]
                if 'self' in locals:
                    test_case = locals['self']
                    if isinstance(test_case, unittest.TestCase):
                        # Trim for test class and test name to avoid
                        # unrealistic long names
                        test_name = '.'.join(test_case.id().split('.')[-2:])
                        break
            finally:
                del possible_testframe
    finally:
        del curframe
    return test_name


def create_system(arch=u'i386', type=SystemType.machine, status=None,
        owner=None, fqdn=None, shared=True, exclude_osmajor=[],
        exclude_osversion=[], hypervisor=None, kernel_type=None,
        date_added=None, return_existing=False, private=False, with_power=True,
        lab_controller=None, **kw):
    if owner is None:
        owner = create_user()
    if fqdn is None:
        name = get_test_name()
        fqdn = unique_name(u'system%s.' + name.replace('_', '.'))
    if status is None:
        status = SystemStatus.automated if lab_controller is not None else SystemStatus.manual

    if System.query.filter(System.fqdn == fqdn).count():
        if return_existing:
            system = System.query.filter(System.fqdn == fqdn).first()
            for property, value in kw.iteritems():
               setattr(system, property, value)
        else:
            raise ValueError('Attempted to create duplicate system %s' % fqdn)
    else:
        system = System(fqdn=fqdn,type=type, owner=owner, status=status,
                        lab_controller=lab_controller, **kw)
        session.add(system)

    # Normally the system would be "idle" when first added, and then becomes
    # "pending" when a user flips it to Automated status. But for simplicity in
    # the tests, we will just force it back to "idle" here since we know we
    # just created it. This lets a subsequent call to the scheduler pick it up
    # immediately, without going through an iteration of
    # schedule_pending_systems() first.
    system.scheduler_status = SystemSchedulerStatus.idle

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
    elif arch is not None:
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

def create_system_pool(name=None, description=u'A system Pool',
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

def create_task(name=None, exclude_arches=None, exclusive_arches=None,
        exclude_osmajors=None, exclusive_osmajors=None, version=u'1.0-1',
        uploader=None, owner=None, priority=u'Manual', valid=None, path=None,
        description=None, requires=None, runfor=None, type=None, avg_time=1200):
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

    task = Task(name=name)
    task.rpm = rpm
    task.version = version
    task.uploader = uploader
    task.owner = owner
    task.priority = priority
    task.valid = valid
    task.path = path
    task.description = description
    task.avg_time = avg_time
    task.license = u'GPLv99+'
    if type:
        for t in type:
            task.types.append(TaskType.lazy_create(type=t))
    if exclude_arches:
       for arch in exclude_arches:
           task.excluded_arches.append(Arch.by_name(arch))
    if exclusive_arches:
        for arch in exclusive_arches:
            task.exclusive_arches.append(Arch.by_name(arch))
    if exclude_osmajors:
        for osmajor in exclude_osmajors:
            task.excluded_osmajors.append(OSMajor.lazy_create(osmajor=osmajor))
    if exclusive_osmajors:
        for osmajor in exclusive_osmajors:
            task.exclusive_osmajors.append(OSMajor.lazy_create(osmajor=osmajor))
    if requires:
        for require in requires:
            tp = TaskPackage.lazy_create(package=require)
            task.required.append(tp)
    if runfor:
        for run in runfor:
            task.runfor.append(TaskPackage.lazy_create(package=run))
    session.add(task)
    session.flush()
    log.debug('Created task %s', task.name)
    return task

def create_tasks(xmljob):
    # Add all tasks that the xml specifies
    names = set()
    for task in xmljob.xpath('recipeSet/recipe/task'):
        names.add(task.get('name'))
    for name in names:
        if not Task.query.filter(Task.name == name).count():
            create_task(name=name)

def create_recipe(distro_tree=None, task_list=None,
        task_name=u'/distribution/reservesys', num_tasks=None, whiteboard=None,
        role=None, ks_meta=None, cls=MachineRecipe, **kwargs):
    recipe = cls(ttasks=1)
    recipe.ks_meta = ks_meta
    recipe.whiteboard = whiteboard
    recipe.distro_tree = distro_tree
    recipe.role = role or u'STANDALONE'
    custom_distro = kwargs.get('custom_distro', False)

    if not custom_distro:
        if not distro_tree:
            distro_tree = create_distro_tree(**kwargs)
        recipe.distro_tree = distro_tree
        recipe.installation = recipe.distro_tree.create_installation_from_tree()
        recipe.distro_requires = lxml.etree.tostring(recipe.distro_tree.to_xml(), encoding=unicode)
    else:
        name = kwargs.get('distro_name', u'MyAwesomeLinux1.0')
        tree_url = kwargs.get('tree_url', u'ftp://dummylab.example.com/distros/MyAwesomeLinux1/')
        initrd_path = kwargs.get('initrd_path', u'pxeboot/initrd')
        kernel_path = kwargs.get('kernel_path', u'pxeboot/vmlinuz')
        arch = kwargs.get('arch', u'i386')
        variant = kwargs.get('variant', u'Server')
        osmajor = kwargs.get('osmajor', u'DansAwesomeLinux6')
        osminor = kwargs.get('osminor', u'0')
        arch = Arch.by_name(arch)
        recipe.installation = Installation(tree_url=tree_url, initrd_path=initrd_path, kernel_path=kernel_path, arch=arch,
                                           distro_name=name, osmajor=osmajor, osminor=osminor, variant=variant)

    if kwargs.get('reservesys', False):
        recipe.reservation_request = RecipeReservationRequest()
        if kwargs.get('reservesys_duration'):
            recipe.reservation_request.duration = kwargs['reservesys_duration']

    if num_tasks:
        task_list = [create_task() for i in range(0, num_tasks)]
    if not task_list: #don't specify a task_list and a task_name...
        try:
            task = Task.by_name(task_name)
        except LookupError:
            task = create_task(name=task_name)
        task_list = [task]
    for t in task_list:
        rt = RecipeTask.from_task(t)
        rt.role = u'STANDALONE'
        recipe.tasks.append(rt)
    recipe.ttasks = len(task_list)
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
        kwargs['distro_tree'] = create_distro_tree(**kwargs)
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

def create_installing_job(**kwargs):
    job = create_job(**kwargs)
    mark_job_installing(job, **kwargs)
    return job

def create_scheduled_job(**kwargs):
    job = create_job(**kwargs)
    mark_job_scheduled(job, **kwargs)
    return job

def create_queued_job(**kwargs):
    job = create_job(**kwargs)
    mark_job_queued(job, **kwargs)
    return job

def create_waiting_job(**kwargs):
    job = create_job(**kwargs)
    mark_job_waiting(job, **kwargs)
    return job

def mark_recipe_complete(recipe, result=TaskResult.pass_,
                         task_status=TaskStatus.completed,
                         start_time=None, finish_time=None, only=False,
                         server_log=False, **kwargs):

    mark_recipe_tasks_finished(recipe, result=result,
                               task_status=task_status,
                               start_time=start_time,
                               finish_time=finish_time,
                               only=only,
                               server_log=server_log,
                               **kwargs)
    recipe.recipeset.job.update_status()
    if finish_time:
        recipe.finish_time = finish_time
    if recipe.reservation_request:
        recipe.extend(0)
        recipe.recipeset.job.update_status()
    if isinstance(recipe.resource, VirtResource):
        recipe.resource.instance_deleted = datetime.datetime.utcnow()
    if hasattr(recipe.resource, 'system'):
        # Similar to the hack in mark_recipe_waiting, we do not want beaker-provision
        # to try and run the power commands that were just enqueued.
        session.flush()
        for cmd in recipe.resource.system.command_queue:
            if cmd.status == CommandStatus.queued:
                cmd.change_status(CommandStatus.running)
                cmd.change_status(CommandStatus.completed)
    log.debug('Marked %s as complete with result %s', recipe.t_id, result)

def mark_recipe_tasks_finished(recipe, result=TaskResult.pass_,
                               task_status=TaskStatus.completed,
                               start_time=None, finish_time=None, only=False,
                               server_log=False,
                               num_tasks=None, **kwargs):

    # we accept result=None to mean: don't add any results to recipetasks
    assert result is None or result in TaskResult
    start_time = start_time or datetime.datetime.utcnow()
    finish_time = finish_time or datetime.datetime.utcnow()
    if not only:
        mark_recipe_running(recipe, start_time=start_time,
                task_start_time=start_time, **kwargs)

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
        if recipe_task.start_time is None:
            recipe_task.start_time = start_time
        if result is not None:
            rtr = RecipeTaskResult(path=recipe_task.name, result=result,
                    log=u'(%s)' % result, score=0)
            rtr.start_time = start_time
            rtr.logs = [rtr_log()]
            recipe_task.results.append(rtr)
        recipe_task.logs = [rt_log()]
        recipe_task.finish_time = finish_time
        recipe_task._change_status(task_status)
        recipe.recipeset.job._mark_dirty()
    log.debug('Marked %s tasks in %s as %s with result %s',
              num_tasks or 'all', recipe.t_id, task_status, result)

def mark_job_complete(job, finish_time=None, only=False, **kwargs):
    if not only:
        for recipe in job.all_recipes:
            mark_recipe_running(recipe, **kwargs)
    for recipe in job.all_recipes:
        mark_recipe_complete(recipe, finish_time=finish_time, only=True, **kwargs)
        if finish_time:
            recipe.resource.reservation.finish_time = finish_time
            recipe.finish_time = finish_time

def mark_recipe_scheduled(recipe, start_time=None, system=None, fqdn=None,
        mac_address=None, lab_controller=None, virt=False, instance_id=None,
        network_id=None, subnet_id=None, router_id=None, floating_ip=None, **kwargs):
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
                if not network_id:
                    network_id = uuid.uuid4()
                if not subnet_id:
                    subnet_id = uuid.uuid4()
                if not router_id:
                    router_id = uuid.uuid4()
                if not floating_ip:
                    floating_ip = netaddr.IPAddress('169.254.0.0')
                recipe.resource = VirtResource(instance_id,network_id, subnet_id,
                        router_id, floating_ip, lab_controller)
                recipe.resource.instance_created = datetime.datetime.utcnow()
                recipe.recipeset.lab_controller = lab_controller
            else:
                if not system:
                    if not lab_controller:
                        lab_controller = create_labcontroller(fqdn=u'dummylab.example.invalid')
                    system = create_system(arch=recipe.arch.arch,
                            fqdn=fqdn, lab_controller=lab_controller)
                recipe.resource = SystemResource(system=system)
                recipe.resource.allocate()
                recipe.resource.reservation.start_time = start_time or datetime.datetime.utcnow()
                recipe.recipeset.lab_controller = system.lab_controller
        elif isinstance(recipe, GuestRecipe):
            recipe.resource = GuestResource()
            recipe.resource.allocate()
            if mac_address is not None:
                recipe.resource.mac_address = netaddr.EUI(mac_address,
                        dialect=mac_unix_padded_dialect)
    if recipe.distro_tree and not recipe.distro_tree.url_in_lab(recipe.recipeset.lab_controller):
        add_distro_tree_to_lab(recipe.distro_tree, recipe.recipeset.lab_controller)
    recipe.watchdog = Watchdog()
    log.debug('Marked %s as scheduled with system %s', recipe.t_id, recipe.resource.fqdn)

def mark_job_scheduled(job, **kwargs):
    for recipeset in job.recipesets:
        for recipe in recipeset.recipes:
            mark_recipe_scheduled(recipe, **kwargs)

def mark_recipe_waiting(recipe, start_time=None, only=False, **kwargs):
    if start_time is None:
        start_time = datetime.datetime.utcnow()
    if not only:
        mark_recipe_scheduled(recipe, start_time=start_time, **kwargs)
    recipe.start_time = start_time
    with mock.patch('bkr.server.dynamic_virt.VirtManager', autospec=True):
        recipe.provision()
    if recipe.installation.commands:
        # Because we run a real beaker-provision in the dogfood tests, it will pick
        # up the freshly created configure_netboot commands and try pulling down
        # non-existent kernel+initrd images. When that fails, it will abort our
        # newly created recipe which we don't want. To work around this, we hack
        # the commands to be already completed so that beaker-provision skips them.
        # I would like to have a better solution here...
        session.flush()
        for cmd in recipe.installation.commands:
            cmd.change_status(CommandStatus.running)
            cmd.change_status(CommandStatus.completed)
    else:
        # System without power control, there are no power commands. In the
        # real world the recipe sits in Waiting with no watchdog kill time
        # until someone powers on the system.
        pass
    recipe.waiting()
    recipe.recipeset.job.update_status()
    log.debug('Provisioned %s', recipe.t_id)

def mark_job_waiting(job, **kwargs):
    for recipeset in job.recipesets:
        for recipe in recipeset.recipes:
            mark_recipe_waiting(recipe, **kwargs)

def mark_job_installing(job, **kwargs):
    for recipeset in job.recipesets:
        for recipe in recipeset.recipes:
            mark_recipe_installing(recipe, **kwargs)

def mark_recipe_installing(recipe, only=False, install_started=None, **kwargs):
    if install_started is None:
        install_started = datetime.datetime.utcnow()
    if not only:
        mark_recipe_waiting(recipe, **kwargs)
    if recipe.installation.commands:
        recipe.installation.rebooted = recipe.start_time
    recipe.installation.install_started = install_started
    recipe.extend(10800)
    recipe.recipeset.job.update_status()
    assert recipe.status == TaskStatus.installing
    log.debug('Started installation for %s', recipe.t_id)

def mark_recipe_installation_finished(recipe, fqdn=None, install_finished=None,
        postinstall_finished=None, **kwargs):
    if not recipe.resource.fqdn:
        # system reports its FQDN to Beaker in kickstart %post
        if fqdn is None:
            fqdn = u'%s-for-recipe-%s' % (recipe.resource.__class__.__name__, recipe.id)
        recipe.resource.fqdn = fqdn
    recipe.installation.install_finished = install_finished or datetime.datetime.utcnow()
    recipe.installation.postinstall_finished = postinstall_finished or datetime.datetime.utcnow()
    recipe.recipeset.job.update_status()
    log.debug('Finished installation for %s', recipe.t_id)

def mark_recipe_running(recipe, only=False, task_start_time=None, **kwargs):
    if not only:
        mark_recipe_installing(recipe, **kwargs)
        mark_recipe_installation_finished(recipe, **kwargs)
    recipe.tasks[0].start()
    recipe.tasks[0].start_time = task_start_time or datetime.datetime.utcnow()
    recipe.recipeset.job.update_status()
    assert recipe.status == TaskStatus.running
    log.debug('Started %s', recipe.tasks[0].t_id)

def mark_job_running(job, **kw):
    for recipe in job.all_recipes:
        mark_recipe_running(recipe, **kw)

def mark_job_queued(job):
    for recipe in job.all_recipes:
        recipe.process()
        recipe.queue()
    job.update_status()
    assert job.status == TaskStatus.queued

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

def create_manual_reservation(system, start=None, finish=None, user=None):
    if start is None:
        start = datetime.datetime.utcnow()
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
    else:
        system.user = user

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

def create_system_loan(system, start=None, finish=None, user=None,
        comment=u'Test loan'):
    if user is None:
        user = create_user()
    loan_activity = system.record_activity(user=user, service=u'testdata',
            action=u'Changed', field=u'Loaned To',
            old=system.loaned or u'', new=user)
    loan_comment_activity = system.record_activity(user=user, service=u'testdata',
            action=u'Changed', field=u'Loan Comment',
            old=system.loan_comment, new=comment)
    if start is not None:
        loan_activity.created = start
        loan_comment_activity = start
    if finish is None:
        system.loaned = user
        system.loan_comment = comment
    else:
        return_activity = system.record_activity(user=user, service=u'testdata',
                action=u'Changed', field=u'Loaned To', old=user, new=u'')
        return_activity.created = finish
        return_comment_activity = system.record_activity(user=user, service=u'testdata',
                action=u'Changed', field=u'Loan Comment', old=comment, new=u'')
        return_comment_activity.created = finish

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

def create_openstack_region():
    # For now we are just assuming there is always one region.
    region = OpenStackRegion.query.first()
    if not region:
        region = OpenStackRegion()
        region.lab_controller = LabController.query.first()

def create_keystone_trust(user):
    trust_id = dynamic_virt.create_keystone_trust(
        trustor_username=os.environ['OPENSTACK_DUMMY_USERNAME'],
        trustor_password=os.environ['OPENSTACK_DUMMY_PASSWORD'],
        trustor_project_name=os.environ['OPENSTACK_DUMMY_PROJECT_NAME'],
        trustor_user_domain_name=os.environ.get('OPENSTACK_DUMMY_USER_DOMAIN_NAME'),
        trustor_project_domain_name=os.environ.get('OPENSTACK_DUMMY_PROJECT_DOMAIN_NAME'))
    user.openstack_trust_id = trust_id
    log.debug('Created OpenStack trust %s for %s', trust_id, user)
