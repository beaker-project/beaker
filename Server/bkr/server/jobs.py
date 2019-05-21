
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import datetime
from turbogears.database import session
from turbogears import expose, flash, widgets, validate, validators, redirect, paginate, url
from cherrypy import response
from formencode.api import Invalid
from sqlalchemy import and_, not_
from sqlalchemy.exc import InvalidRequestError
from sqlalchemy.orm.exc import NoResultFound
from bkr.server.widgets import myPaginateDataGrid, \
    RecipeWidget, RecipeSetWidget, PriorityWidget, RetentionTagWidget, \
    SearchBar, JobWhiteboard, ProductWidget, JobActionWidget, JobPageActionWidget, \
    HorizontalForm, BeakerDataGrid
from bkr.server.xmlrpccontroller import RPCRoot
from bkr.server.helpers import make_link, markdown_first_paragraph
from bkr.server.junitxml import job_to_junit_xml
from bkr.server import search_utility, identity, metrics
from bkr.server.needpropertyxml import XmlHost
from bkr.server.installopts import InstallOptions
from bkr.server.controller_utilities import _custom_status, _custom_result, \
    restrict_http_method
from bkr.server.app import app
import pkg_resources
import lxml.etree
import logging

import cherrypy

from bkr.server.model import (Job, RecipeSet, RetentionTag, TaskBase,
                              TaskPriority, User, Group, MachineRecipe,
                              DistroTree, TaskPackage, RecipeRepo,
                              RecipeKSAppend, Task, Product, GuestRecipe,
                              RecipeTask, RecipeTaskParam, Arch,
                              StaleTaskStatusException,
                              RecipeSetActivity, System, RecipeReservationRequest,
                              TaskStatus, RecipeSetComment,
                              RecipeReservationCondition)

from bkr.common.bexceptions import BeakerException, BX
from bkr.server.flask_util import auth_required, convert_internal_errors, \
    BadRequest400, NotFound404, Forbidden403, Conflict409, request_wants_json, \
    read_json_request, render_tg_template, stringbool
from flask import request, jsonify, make_response
from bkr.server.util import parse_untrusted_xml
import cgi
from bkr.server.job_utilities import Utility
from bkr.server.bexceptions import DatabaseLookupError
from bkr.server.model import Installation

log = logging.getLogger(__name__)

__all__ = ['JobForm', 'Jobs']

class JobForm(widgets.Form):

    template = 'bkr.server.templates.job_form'
    name = 'job'
    submit_text = _(u'Queue')
    fields = [widgets.TextArea(name='textxml')]
    hidden_fields = [widgets.HiddenField(name='confirmed', validator=validators.StringBool())]
    params = ['xsd_errors']
    xsd_errors = None

    def update_params(self, d):
        super(JobForm, self).update_params(d)
        if 'xsd_errors' in d['options']:
            d['xsd_errors'] = d['options']['xsd_errors']
            d['submit_text'] = _(u'Queue despite validation errors')

class Jobs(RPCRoot):
    # For XMLRPC methods in this class.
    exposed = True 
    job_list_action_widget = JobActionWidget()
    job_page_action_widget = JobPageActionWidget()
    recipeset_widget = RecipeSetWidget()
    recipe_widget = RecipeWidget()
    priority_widget = PriorityWidget() #FIXME I have a feeling we don't need this as the RecipeSet widget declares an instance of it
    product_widget = ProductWidget()
    retention_tag_widget = RetentionTagWidget()
    job_type = { 'RS' : RecipeSet,
                 'J'  : Job
               }
    whiteboard_widget = JobWhiteboard()

    hidden_id = widgets.HiddenField(name='id')
    confirm = widgets.Label(name='confirm', default="Are you sure you want to cancel?")
    message = widgets.TextArea(name='msg', label=_(u'Reason?'), help_text=_(u'Optional'))

    _upload = widgets.FileField(name='filexml', label='Job XML')
    form = HorizontalForm(
        'jobs',
        fields = [_upload],
        action = 'save_data',
        submit_text = _(u'Submit Data')
    )
    del _upload

    cancel_form = widgets.TableForm(
        'cancel_job',
        fields = [hidden_id, message, confirm],
        action = 'really_cancel',
        submit_text = _(u'Yes')
    )

    job_form = JobForm()

    job_schema_doc = lxml.etree.parse(pkg_resources.resource_stream(
            'bkr.common', 'schema/beaker-job.rng'))

    @classmethod
    def success_redirect(cls, id, url='/jobs/mine', *args, **kw):
        flash(_(u'Success! job id: %s' % id))
        redirect('%s' % url)

    @expose(template='bkr.server.templates.form-post')
    @identity.require(identity.not_anonymous())
    def new(self, **kw):
        return dict(
            title = 'New Job',
            form = self.form,
            action = './clone',
            options = {},
            value = kw,
        )

    def _check_job_deletability(self, t_id, job):
        if not isinstance(job, Job):
            raise TypeError('%s is not of type %s' % (t_id, Job.__name__))
        if not job.can_delete(identity.current.user):
            raise BeakerException(_(u'You do not have permission to delete %s' % t_id))

    def _delete_job(self, t_id):
        job = TaskBase.get_by_t_id(t_id)
        self._check_job_deletability(t_id, job)
        if job.is_finished() and not job.is_deleted:
            job.deleted = datetime.datetime.utcnow()
        return [t_id]

    @expose()
    @identity.require(identity.not_anonymous())
    @restrict_http_method('post')
    def delete_job_page(self, t_id):
        try:
            self._delete_job(t_id)
            flash(_(u'Succesfully deleted %s' % t_id))
        except (BeakerException, TypeError):
            flash(_(u'Unable to delete %s' % t_id))
            redirect('.')
        redirect('./mine')

    @expose()
    @identity.require(identity.not_anonymous())
    @restrict_http_method('post')
    def delete_job_row(self, t_id):
        try:
            self._delete_job(t_id)
            return [t_id]
        except (BeakerException, TypeError), e:
            log.debug(str(e))
            response.status = 400
            return ['Unable to delete %s' % t_id]

    @cherrypy.expose
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

    @cherrypy.expose
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
            raise BX(_('You need to be authenticated to use the --mine or --my_groups filter.'))

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
                if isinstance(group, basestring):
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
                raise BX(_('No such group %r' % group))
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

    @cherrypy.expose
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
    @cherrypy.expose
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
        if isinstance(jobxml, unicode):
            jobxml = jobxml.encode('utf8')
        xmljob = parse_untrusted_xml(jobxml)
        job = self.process_xmljob(xmljob, identity.current.user,
                                  ignore_missing_tasks=ignore_missing_tasks)
        session.flush()  # so that we get an id
        return "J:%s" % job.id

    @identity.require(identity.not_anonymous())
    @expose(template="bkr.server.templates.form-post")
    @validate(validators={'confirmed': validators.StringBool()})
    def clone(self, job_id=None, recipe_id=None, recipeset_id=None,
            textxml=None, filexml=None, confirmed=False, **kw):
        """
        Review cloned xml before submitting it.
        """
        title = 'Clone Job'
        if job_id:
            # Clone from Job ID
            title = 'Clone Job %s' % job_id
            try:
                job = Job.by_id(job_id)
            except InvalidRequestError:
                flash(_(u"Invalid job id %s" % job_id))
                redirect(".")
            textxml = lxml.etree.tostring(job.to_xml(clone=True),
                                          pretty_print=True, encoding=unicode)
        elif recipeset_id:
            title = 'Clone Recipeset %s' % recipeset_id
            try:
                recipeset = RecipeSet.by_id(recipeset_id)
            except InvalidRequestError:
                flash(_(u"Invalid recipeset id %s" % recipeset_id))
                redirect(".")
            textxml = lxml.etree.tostring(
                    recipeset.to_xml(clone=True, include_enclosing_job=True),
                    pretty_print=True, encoding=unicode)
        elif isinstance(filexml, cgi.FieldStorage):
            # Clone from file
            try:
                textxml = filexml.value.decode('utf8')
            except UnicodeDecodeError, e:
                flash(_(u'Invalid job XML: %s') % e)
                redirect('.')
        elif textxml:
            try:
                if not confirmed:
                    job_schema = lxml.etree.RelaxNG(self.job_schema_doc)
                    if not job_schema.validate(lxml.etree.fromstring(textxml.encode('utf8'))):
                        log.debug('Job failed validation, with errors: %r',
                                job_schema.error_log)
                        return dict(
                            title = title,
                            form = self.job_form,
                            action = 'clone',
                            options = {'xsd_errors': job_schema.error_log},
                            value = dict(textxml=textxml, confirmed=True),
                        )
                xmljob = parse_untrusted_xml(textxml.encode('utf8'))
                job = self.process_xmljob(xmljob, identity.current.user)
                session.flush()
            except Exception,err:
                session.rollback()
                flash(_(u'Failed to import job because of: %s' % err))
                return dict(
                    title = title,
                    form = self.job_form,
                    action = './clone',
                    options = {},
                    value = dict(textxml = "%s" % textxml, confirmed=confirmed),
                )
            else:
                self.success_redirect(job.id)
        return dict(
            title = title,
            form = self.job_form,
            action = './clone',
            options = {},
            value = dict(textxml = "%s" % textxml, confirmed=confirmed),
        )


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
                raise BX(_('You have specified an invalid recipeSet priority:%s' % recipeset_priority))
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
            raise BX(_('No Recipes! You can not have a recipeSet with no recipes!'))
        return recipeSet

    def _process_job_tag_product(self, retention_tag=None, product=None, *args, **kw):
        """
        Process job retention_tag and product
        """
        retention_tag = retention_tag or RetentionTag.get_default().tag
        try:
            tag = RetentionTag.by_tag(retention_tag.lower())
        except InvalidRequestError:
            raise BX(_("Invalid retention_tag attribute passed. Needs to be one of %s. You gave: %s" % (','.join([x.tag for x in RetentionTag.get_all()]), retention_tag)))
        if product is None and tag.requires_product():
            raise BX(_("You've selected a tag which needs a product associated with it, \
            alternatively you could use one of the following tags %s" % ','.join([x.tag for x in RetentionTag.get_all() if not x.requires_product()])))
        elif product is not None and not tag.requires_product():
            raise BX(_("Cannot specify a product with tag %s, please use %s as a tag " % (retention_tag,','.join([x.tag for x in RetentionTag.get_all() if x.requires_product()]))))
        else:
            pass

        if tag.requires_product():
            try:
                product = Product.by_name(product)

                return (tag, product)
            except ValueError:
                raise BX(_("You entered an invalid product name: %s" % product))
        else:
            return tag, None

    def process_xmljob(self, xmljob, user, ignore_missing_tasks=False):
        # We start with the assumption that the owner == 'submitting user', until
        # we see otherwise.
        submitter = user
        if user.rootpw_expired:
            raise BX(_('Your root password has expired, please change or clear it in order to submit jobs.'))
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
            except NoResultFound, e:
                raise ValueError('%s is not a valid group' % group_name)
            if group not in owner.groups:
                raise BX(_(u'User %s is not a member of group %s' % (owner.user_name, group.group_name)))
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
            job.extra_xml = u''.join([lxml.etree.tostring(x, encoding=unicode).strip() for x in extra_xml])
        job.product = product
        job.retention_tag = tag
        email_validator = validators.Email(not_empty=True)
        for addr in xmljob.xpath('notify/cc'):
            try:
                addr = email_validator.to_python(addr.text.strip())
                if addr not in job.cc:
                    job.cc.append(addr)
            except Invalid, e:
                raise BX(_('Invalid e-mail address %r in <cc/>: %s') % (addr, str(e)))
        for xmlrecipeSet in xmljob.iter('recipeSet'):
            recipe_set = self._handle_recipe_set(xmlrecipeSet, owner,
                                                 ignore_missing_tasks=ignore_missing_tasks)
            job.recipesets.append(recipe_set)
            job.ttasks += recipe_set.ttasks

        if not job.recipesets:
            raise BX(_('No RecipeSets! You can not have a Job with no recipeSets!'))
        session.add(job)
        metrics.measure('counters.recipes_submitted', len(list(job.all_recipes)))
        return job

    def _jobs(self,job,**kw):
        return_dict = {}
        # We can do a quick search, or a regular simple search. If we have done neither of these,
        # it will fall back to an advanced search and look in the 'jobsearch'

        # simplesearch set to None will display the advanced search, otherwise in the simplesearch
        # textfield it will display the value assigned to it
        simplesearch = None
        if kw.get('simplesearch'):
            value = kw['simplesearch']
            if value.startswith('J:'):
                kw['jobsearch'] = [{'table' : 'Id',
                                     'operation' : 'is',
                                     'value' : value.strip("J:")}]
            else:
                kw['jobsearch'] = [{'table' : 'Whiteboard',
                                     'operation' : 'contains',
                                     'value' : value}]
            simplesearch = value
        if kw.get("jobsearch"):
            if 'quick_search' in kw['jobsearch']:
                table,op,value = kw['jobsearch']['quick_search'].split('-')
                kw['jobsearch'] = [{'table' : table,
                                    'operation' : op,
                                    'value' : value}]
                simplesearch = ''
            log.debug(kw['jobsearch'])
            searchvalue = kw['jobsearch']
            jobs_found = self._job_search(job,**kw)
            return_dict.update({'jobs_found':jobs_found})
            return_dict.update({'searchvalue':searchvalue})
            return_dict.update({'simplesearch':simplesearch})
        return return_dict

    def _job_search(self,task,**kw):
        job_search = search_utility.Job.search(task)
        for search in kw['jobsearch']:
            col = search['table'] 
            job_search.append_results(search['value'],col,search['operation'],**kw)
        return job_search.return_results()

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
        recipe.host_requires = lxml.etree.tostring(xmlrecipe.find('hostRequires'), encoding=unicode)
        partitions = xmlrecipe.find('partitions')
        if partitions is not None:
            recipe.partitions = lxml.etree.tostring(partitions, encoding=unicode)
        if xmlrecipe.find('distroRequires') is not None:
            recipe.distro_requires = lxml.etree.tostring(xmlrecipe.find('distroRequires'), encoding=unicode)
            recipe.distro_tree = DistroTree.by_filter(recipe.distro_requires).first()
            if recipe.distro_tree is None:
                raise BX(_('No distro tree matches Recipe: %s') % recipe.distro_requires)
            # The attributes "tree", "initrd" and "kernel" in the installation table are populated later by the
            # scheduler during provisioning time, when the recipe has been allocated a system to provision
            recipe.installation = recipe.distro_tree.create_installation_from_tree()
        elif xmlrecipe.find('distro') is not None:
            recipe.installation = self.handle_distro(xmlrecipe.find('distro'))
        else:
            raise BX(_('You must define either <distroRequires/> or <distro/> element'))
        try:
            # try evaluating the host_requires, to make sure it's valid
            XmlHost.from_string(recipe.host_requires).apply_filter(System.query)
        except StandardError, e:
            raise BX(_('Error in hostRequires: %s' % e))
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
            raise BX(_('Error parsing ks_meta: %s' % e))
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
            raise BX(_('Invalid task(s): %s') % ', '.join(invalid_tasks))
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
            raise BX(_('No Tasks! You can not have a recipe with no tasks!'))
        return recipe

    @staticmethod
    def handle_distro(distro):
        try:
            arch = Arch.by_name(distro.find("arch").get("value"))
        except ValueError:
            raise BX(_('No arch matches: %s') % distro.find("arch").get("value"))
        missing_attribute = 'tree' if distro.find("tree") is None else 'initrd' if distro.find("initrd") is None else \
            'kernel' if distro.find("kernel") is None else 'osmajor' if distro.find("osversion") is None else None
        if missing_attribute:
            raise BX(_('<%s/> element is required' % missing_attribute))
        tree_url = distro.find("tree").get("url")
        initrd_path = distro.find("initrd").get("url")
        kernel_path = distro.find("kernel").get("url")
        osmajor = distro.find("osversion").get("major")
        osminor = distro.find("osversion").get("minor", "0")
        name = distro.find("name").get("value") if distro.find("name") is not None else None
        variant = distro.find("variant").get("value") if distro.find("variant") is not None else None
        return Installation(tree_url=tree_url, initrd_path=initrd_path, kernel_path=kernel_path,
                            arch=arch, distro_name=name, osmajor=osmajor, osminor=osminor, variant=variant)

    @expose('json')
    def update_recipe_set_response(self, recipe_set_id, response_id):
        rs = RecipeSet.by_id(recipe_set_id)
        response = {'1': 'ack', '2': 'nak'}[response_id]
        old_response = {False: 'ack', True: 'nak'}[rs.waived]
        if old_response != response:
            rs.waived = {'ack': False, 'nak': True}[response]
            rs.record_activity(user=identity.current.user, service=u'WEBUI',
                               field=u'Ack/Nak', action=u'Changed', old=old_response,
                               new=response)
        return {'success': 1, 'rs_id': recipe_set_id}

    @cherrypy.expose
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


    @cherrypy.expose
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

    @cherrypy.expose
    @identity.require(identity.not_anonymous())
    def stop(self, job_id, stop_type, msg=None):
        """
        Set job status to Completed
        """
        try:
            job = Job.by_id(job_id)
        except InvalidRequestError:
            raise BX(_('Invalid job ID: %s' % job_id))
        if stop_type not in job.stop_types:
            raise BX(_('Invalid stop_type: %s, must be one of %s' %
                             (stop_type, job.stop_types)))
        kwargs = dict(msg = msg)
        return getattr(job,stop_type)(**kwargs)

    @expose(format='json')
    def to_xml(self, id):
        jobxml = Job.by_id(id).to_xml().toxml()
        return dict(xml=jobxml)

    @expose(template='bkr.server.templates.grid')
    @paginate('list',default_order='-id', limit=50)
    def index(self,*args,**kw): 
        return self.jobs(jobs=session.query(Job).join('owner'),*args,**kw)

    @identity.require(identity.not_anonymous())
    @expose(template='bkr.server.templates.grid')
    @paginate('list',default_order='-id', limit=50)
    def mine(self, *args, **kw):
        query = Job.mine(identity.current.user)
        return self.jobs(jobs=query, action='./mine', title=u'My Jobs', *args, **kw)

    @identity.require(identity.not_anonymous())
    @expose(template='bkr.server.templates.grid')
    @paginate('list',default_order='-id', limit=50)
    def mygroups(self, *args, **kw):
        query = Job.my_groups(identity.current.user)
        return self.jobs(jobs=query, action='./mygroups', title=u'My Group Jobs',
                *args, **kw)

    def jobs(self,jobs,action='.', title=u'Jobs', *args, **kw):
        jobs = jobs.filter(not_(Job.is_deleted))
        jobs_return = self._jobs(jobs, **kw)
        searchvalue = None
        search_options = {}
        if jobs_return:
            if 'jobs_found' in jobs_return:
                jobs = jobs_return['jobs_found']
            if 'searchvalue' in jobs_return:
                searchvalue = jobs_return['searchvalue']
            if 'simplesearch' in jobs_return:
                search_options['simplesearch'] = jobs_return['simplesearch']

        def get_group(x):
            if x.group:
                return make_link(url = '../groups/edit?group_id=%d' % x.group.group_id, text=x.group.group_name)
            else:
                return None

        PDC = widgets.PaginateDataGrid.Column
        jobs_grid = myPaginateDataGrid(
            fields=[
                PDC(name='id',
                    getter=lambda x:make_link(url = './%s' % x.id, text = x.t_id),
                    title='ID', options=dict(sortable=True)),
                PDC(name='whiteboard',
                    getter=lambda x: markdown_first_paragraph(x.whiteboard), title='Whiteboard',
                    options=dict(sortable=True)),
                PDC(name='group',
                    getter=get_group, title='Group',
                    options=dict(sortable=True)),
                PDC(name='owner',
                    getter=lambda x:x.owner.email_link, title='Owner',
                    options=dict(sortable=True)),
                PDC(name='progress',
                    getter=lambda x: x.progress_bar, title='Progress',
                    options=dict(sortable=False)),
                PDC(name='status',
                    getter= _custom_status, title='Status',
                    options=dict(sortable=True)),
                PDC(name='result',
                    getter=_custom_result, title='Result',
                    options=dict(sortable=True)),
                PDC(name='action',
                    getter=lambda x: \
                        self.job_list_action_widget.display(
                        task=x, type_='joblist',
                        delete_action=url('/jobs/delete_job_row'),
                        export=url('/to_xml?taskid=%s' % x.t_id),
                        title='Action', options=dict(sortable=False)))])

        search_bar = SearchBar(name='jobsearch',
                           label=_(u'Job Search'),    
                           simplesearch_label = 'Search',
                           table = search_utility.Job.search.create_complete_search_table(without=('Owner')),
                           search_controller=url("/get_search_options_job"),
                           quick_searches = [('Status-is-Queued','Queued'),('Status-is-Running','Running'),('Status-is-Completed','Completed')])
                            

        return dict(title=title,
                    grid=jobs_grid,
                    list=jobs,
                    action_widget = self.job_list_action_widget,  #Hack,inserts JS for us.
                    search_bar=search_bar,
                    action=action,
                    options=search_options,
                    searchvalue=searchvalue)

    @identity.require(identity.not_anonymous())
    @expose()
    def really_cancel(self, id, msg=None):
        """
        Confirm cancel job
        """
        try:
            job = Job.by_id(id)
        except InvalidRequestError:
            flash(_(u"Invalid job id %s" % id))
            redirect(".")
        if not job.can_cancel(identity.current.user):
            flash(_(u"You don't have permission to cancel job id %s" % id))
            redirect(".")

        try:
            job.cancel(msg)
        except StaleTaskStatusException, e:
            log.warn(str(e))
            session.rollback()
            flash(_(u"Could not cancel job id %s. Please try later" % id))
            redirect(".")
        else:
            job.record_activity(user=identity.current.user, service=u'WEBUI',
                                field=u'Status', action=u'Cancelled', old='', new='')
            flash(_(u"Successfully cancelled job %s" % id))
            redirect('/jobs/mine')

    @identity.require(identity.not_anonymous())
    @expose(template="bkr.server.templates.form")
    def cancel(self, id):
        """
        Confirm cancel job
        """
        try:
            job = Job.by_id(id)
        except InvalidRequestError:
            flash(_(u"Invalid job id %s" % id))
            redirect(".")
        if not job.can_cancel(identity.current.user):
            flash(_(u"You don't have permission to cancel job id %s" % id))
            redirect(".")
        return dict(
            title = 'Cancel Job %s' % id,
            form = self.cancel_form,
            action = './really_cancel',
            options = {},
            value = dict(id = job.id,
                         confirm = 'really cancel job %s?' % id),
        )

    @identity.require(identity.not_anonymous())
    @expose(format='json')
    def update(self, id, **kw):
        # XXX Thus function is awkward and needs to be cleaned up.
        try:
            job = Job.by_id(id)
        except InvalidRequestError:
            raise cherrypy.HTTPError(status=400, message='Invalid job id %s' % id)
        if not job.can_change_product(identity.current.user) or not \
            job.can_change_retention_tag(identity.current.user):
            raise cherrypy.HTTPError(status=403,
                    message="You don't have permission to update job id %s" % id)
        returns = {'success' : True, 'vars':{}}
        if 'retentiontag' in kw and 'product' in kw:
            retention_tag = RetentionTag.by_id(kw['retentiontag'])
            if int(kw['product']) == ProductWidget.product_deselected:
                product = None
            else:
                product = Product.by_id(kw['product'])
            old_tag = job.retention_tag if job.retention_tag else None
            returns.update(Utility.update_retention_tag_and_product(job,
                           retention_tag, product))
            job.record_activity(user=identity.current.user, service=u'WEBUI',
                                field=u'Retention Tag', action='Changed',
                                old=old_tag.tag, new=retention_tag.tag)
        elif 'retentiontag' in kw:
            retention_tag = RetentionTag.by_id(kw['retentiontag'])
            old_tag = job.retention_tag if job.retention_tag else None
            returns.update(Utility.update_retention_tag(job, retention_tag))
            job.record_activity(user=identity.current.user, service=u'WEBUI',
                                field=u'Retention Tag', action='Changed',
                                old=old_tag.tag, new=retention_tag.tag)
        elif 'product' in kw:
            if int(kw['product']) == ProductWidget.product_deselected:
                product = None
            else:
                product = Product.by_id(kw['product'])
            returns.update(Utility.update_product(job, product))
        if 'whiteboard' in kw:
            job.whiteboard = kw['whiteboard']
        return returns

    @expose(template="bkr.server.templates.job-old")
    def default(self, id):
        if cherrypy.request.path.endswith('/'):
            raise cherrypy.HTTPError(404)
        if cherrypy.request.method not in ['GET', 'HEAD']:
            raise cherrypy.HTTPError(404)

        try:
            job = Job.by_id(id)
        except InvalidRequestError:
            flash(_(u"Invalid job id %s" % id))
            redirect(".")

        if job.is_deleted:
            flash(_(u'Invalid %s, has been deleted' % job.t_id))
            redirect(".")

        recipe_set_history = [RecipeSetActivity.query.with_parent(elem,"activity") for elem in job.recipesets]
        recipe_set_data = []
        for query in recipe_set_history:
            for d in query:
                recipe_set_data.append(d)

        recipe_set_data += job.activity
        recipe_set_data = sorted(recipe_set_data, key=lambda x: x.created, reverse=True)

        job_history_grid = BeakerDataGrid(name='job_history_datagrid', fields= [
                               BeakerDataGrid.Column(name='user', getter= lambda x: x.user, title='User', options=dict(sortable=True)),
                               BeakerDataGrid.Column(name='service', getter= lambda x: x.service, title='Via', options=dict(sortable=True)),
                               BeakerDataGrid.Column(name='created', title='Created', getter=lambda x: x.created, options = dict(sortable=True)),
                               BeakerDataGrid.Column(name='object_name', getter=lambda x: x.object_name(), title='Object', options=dict(sortable=True)),
                               BeakerDataGrid.Column(name='field_name', getter=lambda x: x.field_name, title='Field Name', options=dict(sortable=True)),
                               BeakerDataGrid.Column(name='action', getter=lambda x: x.action, title='Action', options=dict(sortable=True)),
                               BeakerDataGrid.Column(name='old_value', getter=lambda x: x.old_value, title='Old value', options=dict(sortable=True)),
                               BeakerDataGrid.Column(name='new_value', getter=lambda x: x.new_value, title='New value', options=dict(sortable=True)),])

        return_dict = dict(title = 'Job',
                           recipeset_widget = self.recipeset_widget,
                           recipe_widget = self.recipe_widget,
                           hidden_id = widgets.HiddenField(name='job_id',value=job.id),
                           job_history = recipe_set_data,
                           job_history_grid = job_history_grid,
                           whiteboard_widget = self.whiteboard_widget,
                           action_widget = self.job_page_action_widget,
                           delete_action = url('delete_job_page'),
                           job = job,
                           product_widget = self.product_widget,
                           retention_tag_widget = self.retention_tag_widget,
                          )
        return return_dict

def _get_job_by_id(id):
    """Get job by ID, reporting HTTP 404 if the job is not found"""
    try:
        return Job.by_id(id)
    except NoResultFound:
        raise NotFound404('Job not found')

@app.route('/jobs/<int:id>', methods=['GET'])
def get_job(id):
    """
    Provides detailed information about a job in JSON format.

    :param id: ID of the job.
    """
    job = _get_job_by_id(id)
    if request_wants_json():
        return jsonify(job.__json__())
    if identity.current.user and identity.current.user.use_old_job_page:
        return NotFound404('Fall back to old job page')
    return render_tg_template('bkr.server.templates.job', {
        'title': job.t_id, # N.B. JobHeaderView in JS updates the page title
        'job': job,
    })

@app.route('/jobs/<int:id>.xml', methods=['GET'])
def job_xml(id):
    """
    Returns the job in Beaker results XML format.

    :status 200: The job xml file was successfully generated.
    """
    job = _get_job_by_id(id)
    include_logs = request.args.get('include_logs', type=stringbool, default=True)
    xmlstr = lxml.etree.tostring(
            job.to_xml(clone=False, include_logs=include_logs),
            pretty_print=True, encoding='utf8')
    response = make_response(xmlstr)
    response.status_code = 200
    response.headers.add('Content-Type', 'text/xml; charset=utf-8')
    return response

@app.route('/jobs/<int:id>.junit.xml', methods=['GET'])
def job_junit_xml(id):
    """
    Returns the job in JUnit-compatible XML format.
    """
    job = _get_job_by_id(id)
    response = make_response(job_to_junit_xml(job))
    response.status_code = 200
    response.headers.add('Content-Type', 'text/xml; charset=utf-8')
    return response

@app.route('/jobs/<int:id>', methods=['PATCH'])
@auth_required
def update_job(id):
    """
    Updates metadata of an existing job including retention settings and comments.
    The request body must be a JSON object containing one or more of the following
    keys.

    :param id: Job's id.
    :jsonparam string retention_tag: Retention tag of the job.
    :jsonparam string product: Product of the job.
    :jsonparam string whiteboard: Whiteboard of the job.
    :status 200: Job was updated.
    :status 400: Invalid data was given.
    """
    job = _get_job_by_id(id)
    if not job.can_edit(identity.current.user):
        raise Forbidden403('Cannot edit job %s' % job.id)
    data = read_json_request(request)
    def record_activity(field, old, new, action=u'Changed'):
        job.record_activity(user=identity.current.user, service=u'HTTP',
                action=action, field=field, old=old, new=new)
    with convert_internal_errors():
        if 'whiteboard' in data:
            new_whiteboard = data['whiteboard']
            if new_whiteboard != job.whiteboard:
                record_activity(u'Whiteboard', job.whiteboard, new_whiteboard)
                job.whiteboard = new_whiteboard
        if 'retention_tag' in data:
            retention_tag = RetentionTag.by_name(data['retention_tag'])
            if retention_tag.requires_product() and not data.get('product') and not job.product:
                raise BadRequest400('Cannot change retention tag as it requires a product')
            if not retention_tag.requires_product() and (data.get('product') or
                    'product' not in data and job.product):
                raise BadRequest400('Cannot change retention tag as it does not support a product')
            if retention_tag != job.retention_tag:
                record_activity(u'Retention Tag', job.retention_tag, retention_tag)
                job.retention_tag = retention_tag
        if 'product' in data:
            if data['product'] is None:
                product = None
                if job.retention_tag.requires_product():
                    raise BadRequest400('Cannot change product as the current '
                            'retention tag requires a product')
            else:
                product = Product.by_name(data['product'])
                if not job.retention_tag.requires_product():
                    raise BadRequest400('Cannot change product as the current '
                            'retention tag does not support a product')
            if product != job.product:
                record_activity(u'Product', job.product, product)
                job.product = product
        if 'cc' in data:
            if isinstance(data['cc'], basestring):
                # Supposed to be a list, fix it up for them.
                data['cc'] = [data['cc']]
            email_validator = validators.Email(not_empty=True)
            for addr in data['cc']:
                try:
                    email_validator.to_python(addr)
                except Invalid as e:
                    raise BadRequest400('Invalid email address %r in cc: %s'
                            % (addr, str(e)))
            new_addrs = set(data['cc'])
            existing_addrs = set(job.cc)
            for addr in new_addrs.difference(existing_addrs):
                record_activity(u'Cc', None, addr, action=u'Added')
            for addr in existing_addrs.difference(new_addrs):
                record_activity(u'Cc', addr, None, action=u'Removed')
            job.cc[:] = list(new_addrs)
    return jsonify(job.__json__())

@app.route('/jobs/<int:id>', methods=['DELETE'])
@auth_required
def delete_job(id):
    """
    Delete a job.

    :param id: Job's id
    """
    job = _get_job_by_id(id)
    if not job.can_delete(identity.current.user):
        raise Forbidden403('Cannot delete job')
    if not job.is_finished():
        raise BadRequest400('Cannot delete running job')
    if job.is_deleted:
        raise Conflict409('Job has already been deleted')
    job.deleted = datetime.datetime.utcnow()
    return '', 204

@app.route('/jobs/<int:id>/activity/', methods=['GET'])
def get_job_activity(id):
    """
    Returns a JSON array of the historical activity records for a job.
    """
    # Not a "pageable JSON collection" like other activity APIs, because there 
    # is typically zero or a very small number of activity entries for any 
    # given job.
    # Also note this returns both JobActivity as well as RecipeSetActivity for 
    # the recipe sets in the job.
    job = _get_job_by_id(id)
    return jsonify({'entries': job.all_activity})

@app.route('/jobs/<int:id>/status', methods=['POST'])
@auth_required
def update_job_status(id):
    """
    Updates the status of a job. The request must be :mimetype:`application/json`.

    Currently the only allowed value for status is 'Cancelled', which has the 
    effect of cancelling all recipes in the job that have not finished yet.

    :param id: Job's id
    :jsonparam string status: The new status. Must be 'Cancelled'.
    :jsonparam string msg: A message describing the reason for updating the status.
    """
    job = _get_job_by_id(id)
    if not job.can_cancel(identity.current.user):
        raise Forbidden403('Cannot update job status')
    data = read_json_request(request)
    if 'status' not in data:
        raise BadRequest400('Missing status')
    status = TaskStatus.from_string(data['status'])
    msg = data.get('msg', None) or None
    if status != TaskStatus.cancelled:
        raise BadRequest400('Status must be "Cancelled"')
    with convert_internal_errors():
        job.record_activity(user=identity.current.user, service=u'HTTP',
                field=u'Status', action=u'Cancelled')
        job.cancel(msg=msg)
    return '', 204

@app.route('/jobs/+inventory', methods=['POST'])
@auth_required
def submit_inventory_job():
    """
    Submit a inventory job with the most suitable distro selected automatically.

    Returns a dictionary consisting of the job_id, recipe_id, status (recipe status) 
    and the job XML. If ``dryrun`` is set to ``True`` in the request, the first three 
    are set to ``None``.

    :jsonparam string fqdn: Fully-qualified domain name for the system.
    :jsonparam bool dryrun: If True, do not submit the job
    """
    if 'fqdn' not in request.json:
        raise BadRequest400('Missing the fqdn parameter')
    fqdn = request.json['fqdn']
    if 'dryrun' in request.json:
        dryrun = request.json['dryrun']
    else:
        dryrun = False
    try:
        system = System.by_fqdn(fqdn, identity.current.user)
    except DatabaseLookupError:
        raise BadRequest400('System not found: %s' % fqdn)
    if not dryrun and system.find_current_hardware_scan_recipe():
        raise Conflict409('Hardware scanning already in progress')
    distro = system.distro_tree_for_inventory()
    if not distro:
        raise BadRequest400('Could not find a compatible distro for hardware scanning available to this system')
    job_details = {}
    job_details['system'] = system
    job_details['whiteboard'] = 'Update Inventory for %s' % fqdn
    with convert_internal_errors():
        job_xml = Job.inventory_system_job(distro, dryrun=dryrun, **job_details)
    r = {}
    if not dryrun:
        r = system.find_current_hardware_scan_recipe().__json__()
    else:
        r = {'recipe_id': None,
             'status': None,
             'job_id': None,
        }
    r['job_xml'] = job_xml
    r = jsonify(r)
    return r
# for sphinx
jobs = Jobs
