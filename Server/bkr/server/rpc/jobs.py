
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import datetime
import logging
import lxml.etree
import pkg_resources

from formencode.api import Invalid
from formencode import validators
from sqlalchemy import and_, not_
from sqlalchemy.exc import InvalidRequestError
from sqlalchemy.orm.exc import NoResultFound
from bkr.server.database import session
from bkr.server import identity, metrics
from bkr.server.needpropertyxml import XmlHost
from bkr.server.installopts import InstallOptions
from bkr.common.bexceptions import BeakerException, BX
from bkr.server.util import parse_untrusted_xml
from bkr.server.job_utilities import Utility
from bkr.server.rpc import expose, register
import six
from bkr.server.model import (Job, RecipeSet, RetentionTag, TaskBase,
                              TaskPriority, User, Group, MachineRecipe,
                              DistroTree, TaskPackage, RecipeRepo,
                              RecipeKSAppend, Task, Product, GuestRecipe,
                              RecipeTask, RecipeTaskParam, Arch,
                              RecipeReservationRequest, System,
                              TaskStatus, RecipeReservationCondition,
                              Installation)


log = logging.getLogger(__name__)


@register('jobs')
class Jobs(object):
    # For XMLRPC methods in this class.
    exposed = True

    job_schema_doc = lxml.etree.parse(pkg_resources.resource_stream(
            'bkr.common', 'schema/beaker-job.rng'))

    @expose
    def list(self, tags, days_complete_for, family, product, **kw):
        """
        Lists Jobs, filtered by the given criteria.
        :param tags: limit to recipe sets which have one of these retention tags
        :type tags: string or array of strings
        :param days_complete_for: limit to recipe sets which completed at least this many days ago
        :type days_complete_for: integer
        :param family: limit to recipe sets which used distros with this family name
        :type family: string

        Returns a two-element array. The first element is an array of JobIDs
        of the form ``'J:123'``, suitable to be passed to the
        :meth:`jobs.delete_jobs` method. The second element is a human-readable
        count of the number of Jobs matched. Does not return deleted jobs.

        .. deprecated:: 0.9.4
            Use :meth:`jobs.filter` instead.
        """

        jobs = {'tags':tags,
                'daysComplete':days_complete_for,
                'family':family,
                'product':product}

        return self.filter(jobs)

    @expose
    def filter(self, filters):
        """
        Returns a list of details for jobs filtered by the given criteria.

        The *filter* argument must be a an XML-RPC structure (dict) specifying
        filter criteria. The following keys are recognised:

            'tags'
                List of job tags.
            'daysComplete'
                Number of days elapsed since the jobs completion.
            'family'
                Job distro family, for example ``'RedHatEnterpriseLinuxServer5'``.
            'product'
                Job product name
            'owner'
                Job owner username
            'mine'
                Inclusion is equivalent to including own username in 'owner'
            'group'
                Job group name
            'my-group'
                Jobs for any of the given user's groups.
            'whiteboard'
                Job whiteboard (substring match)
            'limit'
                Integer limit to number of jobs returned.
            'minid'
                Min JobID of the jobs to search
            'maxid'
                Maximum Job ID of the jobs to search
            'is_finished'
                If True, limit to jobs which are finished(completed, aborted, cancelled)
                If False, limit to jobs which are not finished.

        Returns an array of JobIDs of the form ``'J:123'``, suitable to be passed
        to the :meth:`jobs.delete_jobs` method. Does not return deleted jobs.
        """

        # if  min/max/both IDs have been specified, filter it right here
        minid = filters.get('minid', None)
        maxid = filters.get('maxid', None)
        jobs = session.query(Job)
        if minid:
            jobs = jobs.filter(Job.id >= minid)
        if maxid:
            jobs = jobs.filter(Job.id <= maxid)

        tags = filters.get('tags', None)
        complete_days = filters.get('daysComplete', None)
        family = filters.get('family', None)
        product = filters.get('product', None)
        owner = filters.get('owner', None)
        group = filters.pop('group', None)
        my_groups = filters.pop('my_groups', None)
        whiteboard = filters.get('whiteboard', None)
        mine = filters.get('mine', None)
        limit = filters.get('limit', None)
        is_finished = filters.get('is_finished', None)

        # identity.not_anonymous() wrongly returns True for anonymous XML-RPC
        if (mine or my_groups) and not identity.current.user:
            raise BX('You need to be authenticated to use the --mine or --my_groups filter.')

        if mine:
            if owner:
                if isinstance(owner, list):
                    owner.append(identity.current.user.user_name)
                else:
                    owner = [owner, identity.current.user.user_name]
            else:
                owner = identity.current.user.user_name

        if my_groups:
            if group:
                if isinstance(group, six.string_types):
                    group = [group]
                group.extend([g.group_name for g in identity.current.user.groups])
            else:
                group = [g.group_name for g in identity.current.user.groups]

        jobs = jobs.order_by(Job.id.desc())
        if tags:
            jobs = Job.by_tag(tags, jobs)
        if complete_days:
            jobs = jobs.filter(Job.completed_n_days_ago(int(complete_days)))
        if family:
            jobs = Job.has_family(family, jobs)
        if product:
            jobs = Job.by_product(product, jobs)
        if owner:
            jobs = Job.by_owner(owner, jobs)
        if group:
            try:
                jobs = Job.by_groups(group, jobs)
            except NoResultFound:
                raise BX('No such group %r' % group)
        if whiteboard:
            jobs = jobs.filter(Job.whiteboard.like(u'%%%s%%' % whiteboard))
        # is_finished is a tri-state value, True limit finished job, False limit unfinished job, None don't limit
        if is_finished:
            jobs = jobs.filter(and_(Job.is_finished(), not_(Job.is_dirty)))
        elif is_finished is False:
            jobs = jobs.filter(not_(Job.is_finished()))
        jobs = jobs.filter(not_(Job.is_deleted))

        if limit:
            limit = int(limit)
            jobs = jobs.limit(limit)

        jobs = jobs.values(Job.id)

        return_value = ['J:%s' % j[0] for j in jobs]
        return return_value

    @expose
    @identity.require(identity.not_anonymous())
    def delete_jobs(self, jobs=None, tag=None, complete_days=None, family=None, dryrun=False, product=None):
        """
        delete_jobs will mark the job to be deleted

        To select jobs by id, pass an array for the *jobs* argument. Elements
        of the array must be strings of the form ``'J:123'``.
        Alternatively, pass some combination of the *tag*, *complete_days*, or
        *family* arguments to select jobs for deletion. These arguments behave
        as per the :meth:`jobs.list` method.

        If *dryrun* is True, deletions will be reported but nothing will be
        modified.

        Admins are not be able to delete jobs which are not owned by
        themselves by using the tag, complete_days etc kwargs, instead, they
        should do that via the *jobs* argument.
        """
        deleted_jobs = []
        if jobs: #Turn them into job objects
            if not isinstance(jobs,list):
                jobs = [jobs]
            for j_id in jobs:
                job = TaskBase.get_by_t_id(j_id)
                if not isinstance(job,Job):
                    raise BeakerException('Incorrect task type passed %s' % j_id )
                if not job.can_delete(identity.current.user):
                    raise BeakerException("You don't have permission to delete job %s" % j_id)
                if not job.is_finished():
                    continue # skip it
                if job.is_deleted:
                    continue # skip it
                job.deleted = datetime.datetime.utcnow()
                deleted_jobs.append(job)
        else:
            # only allow people to delete their own jobs while using these kwargs
            query = Job.find_jobs(tag=tag,
                complete_days=complete_days,
                family=family, product=product,
                owner=identity.current.user.user_name)
            query = query.filter(Job.is_finished()).filter(not_(Job.is_deleted))
            for job in query:
                job.deleted = datetime.datetime.utcnow()
                deleted_jobs.append(job)

        msg = 'Jobs deleted'
        if dryrun:
            session.rollback()
            msg = 'Dryrun only. %s' % (msg)
        return '%s: %s' % (msg, [j.t_id for j in deleted_jobs])

    # XMLRPC method
    @expose
    @identity.require(identity.not_anonymous())
    def upload(self, jobxml, ignore_missing_tasks=False):
        """
        Queues a new job.

        :param jobxml: XML description of job to be queued
        :type jobxml: string
        :param ignore_missing_tasks: pass True for this parameter to cause
            unknown tasks to be silently discarded (default is False)
        :type ignore_missing_tasks: bool
        """
        if isinstance(jobxml, six.text_type):
            jobxml = jobxml.encode('utf8')
        xmljob = parse_untrusted_xml(jobxml)
        job = self.process_xmljob(xmljob, identity.current.user,
                                  ignore_missing_tasks=ignore_missing_tasks)
        session.flush()  # so that we get an id
        return "J:%s" % job.id

    @expose
    @identity.require(identity.not_anonymous())
    def set_retention_product(self, job_t_id, retention_tag_name, product_name):
        """
        XML-RPC method to update a job's retention tag, product, or both.

        There is an important distinction between product_name of None, which
        means do not change the existing value, vs. empty string, which means
        clear the existing product.
        """
        job = TaskBase.get_by_t_id(job_t_id)
        if job.can_change_product(identity.current.user) and \
            job.can_change_retention_tag(identity.current.user):
            if retention_tag_name and product_name:
                retention_tag = RetentionTag.by_name(retention_tag_name)
                product = Product.by_name(product_name)
                old_tag = job.retention_tag if job.retention_tag else None
                result = Utility.update_retention_tag_and_product(job,
                                                                  retention_tag, product)
                job.record_activity(user=identity.current.user, service=u'XMLRPC',
                                    field=u'Retention Tag', action='Changed',
                                    old=old_tag.tag, new=retention_tag.tag)
            elif retention_tag_name and product_name == '':
                retention_tag = RetentionTag.by_name(retention_tag_name)
                old_tag = job.retention_tag if job.retention_tag else None
                result = Utility.update_retention_tag_and_product(job,
                                                                  retention_tag, None)
                job.record_activity(user=identity.current.user, service=u'XMLRPC',
                                    field=u'Retention Tag', action='Changed',
                                    old=old_tag.tag, new=retention_tag.tag)
            elif retention_tag_name:
                retention_tag = RetentionTag.by_name(retention_tag_name)
                old_tag = job.retention_tag if job.retention_tag else None
                result = Utility.update_retention_tag(job, retention_tag)
                job.record_activity(user=identity.current.user, service=u'XMLRPC',
                                    field=u'Retention Tag', action='Changed',
                                    old=old_tag.tag, new=retention_tag.tag)
            elif product_name:
                product = Product.by_name(product_name)
                result = Utility.update_product(job, product)
            elif product_name == '':
                result = Utility.update_product(job, None)
            else:
                result = {'success': False, 'msg': 'Nothing to do'}

            if not result['success'] is True:
                raise BeakerException('Job %s not updated: %s' % (job.id, result.get('msg', 'Unknown reason')))
        else:
            raise BeakerException('No permission to modify %s' % job)

    @expose
    @identity.require(identity.not_anonymous())
    def set_response(self, taskid, response):
        """
        Updates the response (ack/nak) for a recipe set, or for all recipe sets
        in a job.

        Deprecated: setting 'nak' is a backwards compatibility alias for
        waiving a recipe set. Use the JSON API to set {waived: true} instead.

        :param taskid: see above
        :type taskid: string
        :param response: new response, either ``'ack'`` or ``'nak'``
        :type response: string
        """
        job = TaskBase.get_by_t_id(taskid)
        if not job.can_waive(identity.current.user):
            raise BeakerException('No permission to modify %s' % job)
        if response == 'nak':
            waived = True
        elif response == 'ack':
            waived = False
        else:
            raise ValueError('Unrecognised response %r' % response)
        job.set_waived(waived)

    @expose
    @identity.require(identity.not_anonymous())
    def stop(self, job_id, stop_type, msg=None):
        """
        Set job status to Completed
        """
        try:
            job = Job.by_id(job_id)
        except InvalidRequestError:
            raise BX('Invalid job ID: %s' % job_id)
        if not job.can_stop(identity.current.user):
            raise BX("You don't have permission to stop job %s" % job_id)
        if stop_type not in job.stop_types:
            raise BX('Invalid stop_type: %s, must be one of %s' %
                             (stop_type, job.stop_types))
        kwargs = dict(msg = msg)
        return getattr(job,stop_type)(**kwargs)

    def _handle_recipe_set(self, xmlrecipeSet, user, ignore_missing_tasks=False):
        """
        Handles the processing of recipesets into DB entries from their xml
        """
        recipeSet = RecipeSet(ttasks=0)
        recipeset_priority = xmlrecipeSet.get('priority')
        if recipeset_priority is not None:
            try:
                my_priority = TaskPriority.from_string(recipeset_priority)
            except InvalidRequestError:
                raise BX('You have specified an invalid recipeSet priority:%s' % recipeset_priority)
            allowed_priorities = RecipeSet.allowed_priorities_initial(user)
            if my_priority in allowed_priorities:
                recipeSet.priority = my_priority
            else:
                recipeSet.priority = TaskPriority.default_priority()
        else:
            recipeSet.priority = TaskPriority.default_priority()

        for xmlrecipe in xmlrecipeSet.iter('recipe'):
            recipe = self.handleRecipe(xmlrecipe, user,
                                       ignore_missing_tasks=ignore_missing_tasks)
            recipe.ttasks = len(recipe.tasks)
            recipeSet.ttasks += recipe.ttasks
            recipeSet.recipes.append(recipe)
            # We want the guests to be part of the same recipeSet
            for guest in recipe.guests:
                recipeSet.recipes.append(guest)
                guest.ttasks = len(guest.tasks)
                recipeSet.ttasks += guest.ttasks
        if not recipeSet.recipes:
            raise BX('No Recipes! You can not have a recipeSet with no recipes!')
        return recipeSet

    def _process_job_tag_product(self, retention_tag=None, product=None, *args, **kw):
        """
        Process job retention_tag and product
        """
        retention_tag = retention_tag or RetentionTag.get_default().tag
        try:
            tag = RetentionTag.by_tag(retention_tag.lower())
        except InvalidRequestError:
            raise BX("Invalid retention_tag attribute passed. Needs to be one of %s. You gave: %s" % (','.join([x.tag for x in RetentionTag.get_all()]), retention_tag))
        if product is None and tag.requires_product():
            raise BX("You've selected a tag which needs a product associated with it, \
            alternatively you could use one of the following tags %s" % ','.join([x.tag for x in RetentionTag.get_all() if not x.requires_product()]))
        elif product is not None and not tag.requires_product():
            raise BX("Cannot specify a product with tag %s, please use %s as a tag " % (retention_tag,','.join([x.tag for x in RetentionTag.get_all() if x.requires_product()])))
        else:
            pass

        if tag.requires_product():
            try:
                product = Product.by_name(product)

                return (tag, product)
            except ValueError:
                raise BX("You entered an invalid product name: %s" % product)
        else:
            return tag, None

    def process_xmljob(self, xmljob, user, ignore_missing_tasks=False):
        # We start with the assumption that the owner == 'submitting user', until
        # we see otherwise.
        submitter = user
        if user.rootpw_expired:
            raise BX('Your root password has expired, please change or clear it in order to submit jobs.')
        owner_name = xmljob.get('user')
        if owner_name:
            owner = User.by_user_name(owner_name)
            if owner is None:
                raise ValueError('%s is not a valid user name' % owner_name)
            if not submitter.is_delegate_for(owner):
                raise ValueError('%s is not a valid submission delegate for %s' % (submitter, owner))
        else:
            owner = user

        group_name = xmljob.get('group')
        group = None
        if group_name:
            try:
                group = Group.by_name(group_name)
            except NoResultFound as e:
                raise ValueError('%s is not a valid group' % group_name)
            if group not in owner.groups:
                raise BX(u'User %s is not a member of group %s' % (owner.user_name, group.group_name))
        job_retention = xmljob.get('retention_tag')
        job_product = xmljob.get('product')
        tag, product = self._process_job_tag_product(retention_tag=job_retention, product=job_product)
        job = Job(whiteboard=xmljob.findtext('whiteboard', default='').strip(),
                  ttasks=0,
                  owner=owner,
                  group=group,
                  submitter=submitter,
                  )
        extra_xml = xmljob.xpath('*[namespace-uri()]')
        if extra_xml is not None:
            job.extra_xml = u''.join([lxml.etree.tostring(x, encoding=six.text_type).strip() for x in extra_xml])
        job.product = product
        job.retention_tag = tag
        email_validator = validators.Email(not_empty=True)
        for addr in xmljob.xpath('notify/cc'):
            try:
                addr = email_validator.to_python(addr.text.strip())
                if addr not in job.cc:
                    job.cc.append(addr)
            except Invalid as e:
                raise BX('Invalid e-mail address %r in <cc/>: %s' % (addr, str(e)))
        for xmlrecipeSet in xmljob.iter('recipeSet'):
            recipe_set = self._handle_recipe_set(xmlrecipeSet, owner,
                                                 ignore_missing_tasks=ignore_missing_tasks)
            job.recipesets.append(recipe_set)
            job.ttasks += recipe_set.ttasks

        if not job.recipesets:
            raise BX('No RecipeSets! You can not have a Job with no recipeSets!')
        session.add(job)
        metrics.measure('counters.recipes_submitted', len(list(job.all_recipes)))
        return job

    def handleRecipe(self, xmlrecipe, user, guest=False, ignore_missing_tasks=False):
        if not guest:
            recipe = MachineRecipe(ttasks=0)
            for xmlguest in xmlrecipe.iter('guestrecipe'):
                guestrecipe = self.handleRecipe(xmlguest, user, guest=True,
                                                ignore_missing_tasks=ignore_missing_tasks)
                recipe.guests.append(guestrecipe)
        else:
            recipe = GuestRecipe(ttasks=0)
            recipe.guestname = xmlrecipe.get('guestname')
            recipe.guestargs = xmlrecipe.get('guestargs')
        recipe.host_requires = lxml.etree.tostring(xmlrecipe.find('hostRequires'), encoding=six.text_type)
        partitions = xmlrecipe.find('partitions')
        if partitions is not None:
            recipe.partitions = lxml.etree.tostring(partitions, encoding=six.text_type)
        if xmlrecipe.find('distroRequires') is not None:
            recipe.distro_requires = lxml.etree.tostring(xmlrecipe.find('distroRequires'), encoding=six.text_type)
            recipe.distro_tree = DistroTree.by_filter(recipe.distro_requires).first()
            if recipe.distro_tree is None:
                raise BX('No distro tree matches Recipe: %s' % recipe.distro_requires)
            # The attributes "tree", "initrd" and "kernel" in the installation table are populated later by the
            # scheduler during provisioning time, when the recipe has been allocated a system to provision
            recipe.installation = recipe.distro_tree.create_installation_from_tree()
        elif xmlrecipe.find('distro') is not None:
            recipe.installation = self.handle_distro(xmlrecipe.find('distro'))
        else:
            raise BX('You must define either <distroRequires/> or <distro/> element')
        try:
            # try evaluating the host_requires, to make sure it's valid
            XmlHost.from_string(recipe.host_requires).apply_filter(System.query)
        except StandardError as e:
            raise BX('Error in hostRequires: %s' % e)
        recipe.whiteboard = xmlrecipe.get('whiteboard')
        recipe.kickstart = xmlrecipe.findtext('kickstart')

        autopick = xmlrecipe.find('autopick')
        if autopick is not None:
            random = autopick.get('random', '')
            if random.lower() in ('true', '1'):
                recipe.autopick_random = True
            else:
                recipe.autopick_random = False
        watchdog = xmlrecipe.find('watchdog')
        if watchdog is not None:
            recipe.panic = watchdog.get('panic', u'None')
        recipe.ks_meta = xmlrecipe.get('ks_meta')
        recipe.kernel_options = xmlrecipe.get('kernel_options')
        recipe.kernel_options_post = xmlrecipe.get('kernel_options_post')
        # try parsing install options to make sure there is no syntax error
        try:
            InstallOptions.from_strings(recipe.ks_meta,
                                        recipe.kernel_options, recipe.kernel_options_post)
        except Exception as e:
            raise BX('Error parsing ks_meta: %s' % e)
        recipe.role = xmlrecipe.get('role', u'None')

        reservesys = xmlrecipe.find('reservesys')
        if reservesys is not None:
            recipe.reservation_request = RecipeReservationRequest()
            if 'duration' in reservesys.attrib:
                recipe.reservation_request.duration = int(reservesys.attrib['duration'])
            if 'when' in reservesys.attrib:
                recipe.reservation_request.when = \
                    RecipeReservationCondition.from_string(reservesys.attrib['when'])

        custom_packages = set()
        for xmlpackage in xmlrecipe.xpath('packages/package'):
            package = TaskPackage.lazy_create(package='%s' % xmlpackage.get('name', u'None'))
            custom_packages.add(package)
        for installPackage in xmlrecipe.iter('installPackage'):
            package = TaskPackage.lazy_create(package='%s' % installPackage.text)
            custom_packages.add(package)
        recipe.custom_packages = list(custom_packages)
        for xmlrepo in xmlrecipe.xpath('repos/repo'):
            recipe.repos.append(
                RecipeRepo(name=xmlrepo.get('name', u'None'), url=xmlrepo.get('url', u'None'))
            )

        for xmlksappend in xmlrecipe.xpath('ks_appends/ks_append'):
            recipe.ks_appends.append(RecipeKSAppend(ks_append=xmlksappend.text))
        xmltasks = []
        invalid_tasks = []
        for xmltask in xmlrecipe.xpath('task'):
            if xmltask.xpath('fetch'):
                # If fetch URL is given, the task doesn't need to exist.
                xmltasks.append(xmltask)
            elif Task.exists_by_name(xmltask.get('name'), valid=True):
                xmltasks.append(xmltask)
            else:
                invalid_tasks.append(xmltask.get('name', ''))
        if invalid_tasks and not ignore_missing_tasks:
            raise BX('Invalid task(s): %s' % ', '.join(invalid_tasks))
        for xmltask in xmltasks:
            fetch = xmltask.find('fetch')
            if fetch is not None:
                recipetask = RecipeTask.from_fetch_url(
                    fetch.get('url'), subdir=fetch.get('subdir', u''), name=xmltask.get('name'))
            else:
                recipetask = RecipeTask.from_task(Task.by_name(xmltask.get('name')))
            recipetask.role = xmltask.get('role', u'None')
            for xmlparam in xmltask.xpath('params/param'):
                param = RecipeTaskParam(name=xmlparam.get('name', u'None'),
                                        value=xmlparam.get('value', u'None'))
                recipetask.params.append(param)
            recipe.tasks.append(recipetask)
        if not recipe.tasks:
            raise BX('No Tasks! You can not have a recipe with no tasks!')
        return recipe

    @staticmethod
    def handle_distro(distro):
        try:
            arch = Arch.by_name(distro.find("arch").get("value"))
        except ValueError:
            raise BX('No arch matches: %s' % distro.find("arch").get("value"))
        missing_attribute = 'tree' if distro.find("tree") is None else 'initrd' if distro.find("initrd") is None else \
            'kernel' if distro.find("kernel") is None else 'osmajor' if distro.find("osversion") is None else None
        if missing_attribute:
            raise BX('<%s/> element is required' % missing_attribute)
        tree_url = distro.find("tree").get("url")
        initrd_path = distro.find("initrd").get("url")
        kernel_path = distro.find("kernel").get("url")
        image_path = distro.find("image").get("url") if distro.find("image") is not None else None
        osmajor = distro.find("osversion").get("major")
        osminor = distro.find("osversion").get("minor", "0")
        name = distro.find("name").get("value") if distro.find("name") is not None else None
        variant = distro.find("variant").get("value") if distro.find("variant") is not None else None
        return Installation(tree_url=tree_url, initrd_path=initrd_path, kernel_path=kernel_path,
                            arch=arch, distro_name=name, osmajor=osmajor, osminor=osminor,
                            variant=variant, image_path=image_path)
