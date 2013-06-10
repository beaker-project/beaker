# - Logan is the scheduling piece of the Beaker project
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
from turbogears.database import session
from turbogears import controllers, expose, flash, widgets, validate, error_handler, validators, redirect, paginate, url
from cherrypy import request, response
from kid import Element
from formencode.api import Invalid
from sqlalchemy.exc import InvalidRequestError
from sqlalchemy.orm.exc import NoResultFound
from bkr.server.widgets import myPaginateDataGrid, AckPanel, JobQuickSearch, \
    RecipeWidget,RecipeTasksWidget, RecipeSetWidget, PriorityWidget, RetentionTagWidget, \
    SearchBar, JobWhiteboard, ProductWidget, JobActionWidget, JobPageActionWidget
from bkr.server.xmlrpccontroller import RPCRoot
from bkr.server.helpers import *
from bkr.server import search_utility, identity
from bkr.server.controller_utilities import _custom_status, _custom_result, \
    restrict_http_method
import datetime
import pkg_resources
import lxml.etree
import logging

import cherrypy

from model import *
import string

from bexceptions import *

import xmltramp
from jobxml import *
import cgi
from bkr.server.job_utilities import Utility

log = logging.getLogger(__name__)

__all__ = ['JobForm', 'Jobs']

class JobForm(widgets.Form):

    template = 'bkr.server.templates.job_form'
    name = 'job'
    submit_text = _(u'Queue')
    fields = [widgets.TextArea(name='textxml', label=_(u'Job XML'), attrs=dict(rows=40, cols=155))]
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
    recipe_tasks_widget = RecipeTasksWidget()
    job_type = { 'RS' : RecipeSet,
                 'J'  : Job
               }
    whiteboard_widget = JobWhiteboard()

    upload = widgets.FileField(name='filexml', label='Job XML')
    hidden_id = widgets.HiddenField(name='id')
    confirm = widgets.Label(name='confirm', default="Are you sure you want to cancel?")
    message = widgets.TextArea(name='msg', label=_(u'Reason?'), help_text=_(u'Optional'))

    form = widgets.TableForm(
        'jobs',
        fields = [upload],
        action = 'save_data',
        submit_text = _(u'Submit Data')
    )

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

    def _check_job_deletability(self, job):
        if not isinstance(job, Job):
            raise TypeError('%s is not of type %s' % (t_id, Job.__name__))
        if not job.can_delete(identity.current.user):
            raise BeakerException(_(u'You do not have permission to delete %s' % t_id))

    def _delete_job(self, t_id):
        job = TaskBase.get_by_t_id(t_id)
        self._check_job_deletability(job)
        Job.delete_jobs([job])
        return [t_id]

    @expose()
    @identity.require(identity.not_anonymous())
    @restrict_http_method('post')
    def delete_job_page(self, t_id):
        try:
            self._delete_job(t_id)
            flash(_(u'Succesfully deleted %s' % t_id))
        except (BeakerException, TypeError), e:
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
            'whiteboard'
                Job whiteboard
            'limit'
                Integer limit to number of jobs returned.
            'minid'
                Min JobID of the jobs to search
            'maxid'
                Maximum Job ID of the jobs to search

        Returns a two-element array. The first element is an array of JobIDs
        of the form ``'J:123'``, suitable to be passed to the
        :meth:`jobs.delete_jobs` method. The second element is a human-readable
        count of the number of Jobs matched. Does not return deleted jobs.
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
        whiteboard = filters.get('whiteboard', None)
        mine = filters.get('mine', None)
        limit = filters.get('limit', None)

        if mine and not identity.not_anonymous():
            raise BX(_('You should be authenticated to use the --mine filter.'))

        if mine and identity.not_anonymous():
            if owner:
                if type(owner) is list:
                    owner.append(identity.current.user.user_name)
                else:
                    owner = [owner, identity.current.user.user_name]
            else:
                owner = identity.current.user.user_name

        jobs = jobs.order_by(Job.id.desc())
        if tags:
            jobs = Job.by_tag(tags, jobs)
        if complete_days:
            jobs = Job.complete_delta({'days':int(complete_days)}, jobs)
        if family:
            jobs = Job.has_family(family, jobs)
        if product:
            jobs = Job.by_product(product, jobs)
        if owner:
            jobs = Job.by_owner(owner, jobs)
        if whiteboard:
            jobs = Job.by_whiteboard(whiteboard, jobs)

        jobs = Job.sanitise_jobs(jobs)

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
        if jobs: #Turn them into job objects
            if not isinstance(jobs,list):
                jobs = [jobs]
            jobs_to_try_to_del = []
            for j_id in jobs:
                job = TaskBase.get_by_t_id(j_id)
                if not isinstance(job,Job):
                    raise BeakerException('Incorrect task type passed %s' % j_id )
                if not job.can_delete(identity.current.user):
                    raise BeakerException("You don't have permission to delete job %s" % j_id)
                jobs_to_try_to_del.append(job)
            delete_jobs_kw = dict(jobs=jobs_to_try_to_del)
        else:
            # only allow people to delete their own jobs while using these kwargs
            delete_jobs_kw = dict(query=Job.find_jobs(tag=tag,
                complete_days=complete_days,
                family=family, product=product,
                owner=identity.current.user.user_name))

        deleted_jobs = Job.delete_jobs(**delete_jobs_kw)

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
        # xml.sax (and thus, xmltramp) expect raw bytes, not unicode
        if isinstance(jobxml, unicode):
            jobxml = jobxml.encode('utf8')
        xml = xmltramp.parse(jobxml)
        xmljob = XmlJob(xml)
        job = self.process_xmljob(xmljob,identity.current.user,
                ignore_missing_tasks=ignore_missing_tasks)
        session.flush() # so that we get an id
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
            textxml = job.to_xml(clone=True).toprettyxml()
        elif recipeset_id:
            title = 'Clone Recipeset %s' % recipeset_id
            try:
                recipeset = RecipeSet.by_id(recipeset_id)
            except InvalidRequestError:
                flash(_(u"Invalid recipeset id %s" % recipeset_id))
                redirect(".")
            textxml = recipeset.to_xml(clone=True,from_job=False).toprettyxml()
        elif isinstance(filexml, cgi.FieldStorage):
            # Clone from file
            try:
                textxml = filexml.value.decode('utf8')
            except UnicodeDecodeError, e:
                flash(_(u'Invalid job XML: %s') % e)
                redirect('.')
        elif textxml:
            try:
                # xml.sax (and thus, xmltramp) expect raw bytes, not unicode
                textxml = textxml.encode('utf8')
                if not confirmed:
                    job_schema = lxml.etree.RelaxNG(self.job_schema_doc)
                    if not job_schema.validate(lxml.etree.fromstring(textxml)):
                        log.debug('Job failed validation, with errors: %r',
                                job_schema.error_log)
                        return dict(
                            title = title,
                            form = self.job_form,
                            action = 'clone',
                            options = {'xsd_errors': job_schema.error_log},
                            value = dict(textxml=textxml, confirmed=True),
                        )
                xmljob = XmlJob(xmltramp.parse(textxml))
                job = self.process_xmljob(xmljob,identity.current.user)
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
        recipeset_priority = xmlrecipeSet.get_xml_attr('priority',unicode,None) 
        if recipeset_priority is not None:
            try:
                my_priority = TaskPriority.from_string(recipeset_priority)
            except InvalidRequestError, (e):
                raise BX(_('You have specified an invalid recipeSet priority:%s' % recipeset_priority))
            allowed_priorities = RecipeSet.allowed_priorities_initial(user)
            if my_priority in allowed_priorities:
                recipeSet.priority = my_priority
            else:
                recipeSet.priority = TaskPriority.default_priority() 
        else:
            recipeSet.priority = TaskPriority.default_priority() 

        for xmlrecipe in xmlrecipeSet.iter_recipes():
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
            except NoResultFound:
                raise BX(_("You entered an invalid product name: %s" % product))
        else:
            return tag, None

    def process_xmljob(self, xmljob, user, ignore_missing_tasks=False):
        # We start with the assumption that the owner == 'submitting user', until
        # we see otherwise.
        submitter = user
        if user.rootpw_expired:
            raise BX(_('Your root password has expired, please change or clear it in order to submit jobs.'))
        owner_name = xmljob.get_xml_attr('user', unicode, None)
        if owner_name:
            try:
                owner = User.by_user_name(owner_name)
            except NoResultFound, e:
                raise ValueError('%s is not a valid user name' % owner_name)
            if not submitter.is_delegate_for(owner):
                raise ValueError('%s is not a valid submission delegate for %s' % (submitter, owner))
        else:
            owner = user

        group_name =  xmljob.get_xml_attr('group', unicode, None)
        group = None
        if group_name:
            try:
                group = Group.by_name(group_name)
            except NoResultFound, e:
                raise ValueError('%s is not a valid group' % group_name)
            if group not in owner.groups:
                raise BX(_(u'User %s is not a member of group %s' % (owner.user_name, group.group_name)))
        job_retention = xmljob.get_xml_attr('retention_tag',unicode,None)
        job_product = xmljob.get_xml_attr('product',unicode,None)
        tag, product = self._process_job_tag_product(retention_tag=job_retention, product=job_product)
        job = Job(whiteboard=unicode(xmljob.whiteboard), ttasks=0, owner=owner,
            group=group, submitter=submitter)
        job.product = product
        job.retention_tag = tag
        email_validator = validators.Email(not_empty=True)
        for addr in set(xmljob.iter_cc()):
            try:
                job.cc.append(email_validator.to_python(addr))
            except Invalid, e:
                raise BX(_('Invalid e-mail address %r in <cc/>: %s') % (addr, str(e)))
        for xmlrecipeSet in xmljob.iter_recipeSets():
            recipe_set = self._handle_recipe_set(xmlrecipeSet, owner,
                    ignore_missing_tasks=ignore_missing_tasks)
            job.recipesets.append(recipe_set)
            job.ttasks += recipe_set.ttasks

        if not job.recipesets:
            raise BX(_('No RecipeSets! You can not have a Job with no recipeSets!'))
        session.add(job)
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
            kw['jobsearch'] = [{'table' : 'Id',
                                 'operation' : 'is',
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
            for xmlguest in xmlrecipe.iter_guests():
                guestrecipe = self.handleRecipe(xmlguest, user, guest=True,
                        ignore_missing_tasks=ignore_missing_tasks)
                recipe.guests.append(guestrecipe)
        else:
            recipe = GuestRecipe(ttasks=0)
            recipe.guestname = xmlrecipe.guestname
            recipe.guestargs = xmlrecipe.guestargs
        recipe.host_requires = xmlrecipe.hostRequires()
        recipe.distro_requires = xmlrecipe.distroRequires()
        recipe.partitions = xmlrecipe.partitions()
        try:
            recipe.distro_tree = DistroTree.by_filter("%s" %
                                           recipe.distro_requires)[0]
        except IndexError:
            raise BX(_('No distro tree matches Recipe: %s') % recipe.distro_requires)
        try:
            # try evaluating the host_requires, to make sure it's valid
            recipe.distro_tree.systems_filter(user, recipe.host_requires)
        except StandardError, e:
            raise BX(_('Error in hostRequires: %s' % e))
        recipe.whiteboard = xmlrecipe.whiteboard or None #'' -> NULL for DB
        recipe.kickstart = xmlrecipe.kickstart
        if xmlrecipe.autopick:
            recipe.autopick_random = xmlrecipe.autopick.random
        if xmlrecipe.watchdog:
            recipe.panic = xmlrecipe.watchdog.panic
        recipe.ks_meta = xmlrecipe.ks_meta
        recipe.kernel_options = xmlrecipe.kernel_options
        recipe.kernel_options_post = xmlrecipe.kernel_options_post
        recipe.role = xmlrecipe.role
        for xmlpackage in xmlrecipe.packages():
            package = TaskPackage.lazy_create(package='%s' % xmlpackage.name)
            recipe.custom_packages.append(package)
        for installPackage in xmlrecipe.installPackages():
            package = TaskPackage.lazy_create(package='%s' % installPackage)
            recipe.custom_packages.append(package)
        for xmlrepo in xmlrecipe.iter_repos():
            recipe.repos.append(RecipeRepo(name=xmlrepo.name, url=xmlrepo.url))
        for xmlksappend in xmlrecipe.iter_ksappends():
            recipe.ks_appends.append(RecipeKSAppend(ks_append=xmlksappend))
        xmltasks = []
        invalid_tasks = []
        for xmltask in xmlrecipe.iter_tasks():
            try:
                Task.by_name(xmltask.name, valid=1)
            except InvalidRequestError, e:
                invalid_tasks.append(xmltask.name)
            else:
                xmltasks.append(xmltask)
        if invalid_tasks and not ignore_missing_tasks:
            raise BX(_('Invalid task(s): %s') % ', '.join(invalid_tasks))
        for xmltask in xmltasks:
            task = Task.by_name(xmltask.name)
            recipetask = RecipeTask(task=task)
            recipetask.role = xmltask.role
            for xmlparam in xmltask.iter_params():
                param = RecipeTaskParam( name=xmlparam.name, 
                                        value=xmlparam.value)
                recipetask.params.append(param)
            recipe.tasks.append(recipetask)
        if not recipe.tasks:
            raise BX(_('No Tasks! You can not have a recipe with no tasks!'))
        return recipe

    @expose('json')
    def update_recipe_set_response(self,recipe_set_id,response_id):
        rs = RecipeSet.by_id(recipe_set_id)
        if rs.nacked is None:
            rs.nacked = RecipeSetResponse(response_id=response_id)
        else:
            rs.nacked.response = Response.by_id(response_id)

        return {'success' : 1, 'rs_id' : recipe_set_id }

    @cherrypy.expose
    @identity.require(identity.not_anonymous())
    def set_retention_product(self, job_t_id, retention_tag_name, product_name):
        job = TaskBase.get_by_t_id(job_t_id)
        if job.can_change_product(identity.current.user) and \
            job.can_change_retention_tag(identity.current.user):
            if retention_tag_name:
                try:
                    retention_tag = RetentionTag.by_name(retention_tag_name)
                except NoResultFound:
                    raise ValueError('%s is not a valid tag' % retention_tag_name)
            else:
                retention_tag = None
            if product_name:
                try:
                    product = Product.by_name(product_name)
                    product_id = product.id
                except NoResultFound:
                    raise ValueError('%s is not a valid product' % product_name)
            elif product_name == "":
                product = ProductWidget.product_deselected
                product_id = product
            else:
                product = None
                product_id = product

            retentiontag_id = getattr(retention_tag, 'id', None)
            result = Utility.update_task_product(job,
                retentiontag_id=retentiontag_id, product_id=product_id)
            if not result['success'] is True:
                raise BeakerException('Job %s not updated: %s' % (job.id, result.get('msg', 'Unknown reason')))

            if product == ProductWidget.product_deselected and \
                job.product != None:
                job.product = None
            elif product is not None and product != job.product:
                job.product = product

            if retention_tag is not None and retention_tag != job.retention_tag:
                job.retention_tag = retention_tag

        else:
            raise BeakerException('No permission to modify %s' % job)


    @cherrypy.expose
    @identity.require(identity.not_anonymous())
    def set_response(self, job_t_id, response):
        job = TaskBase.get_by_t_id(job_t_id)
        if job.can_set_response(identity.current.user):
            job.set_response(response)
        else:
            raise BeakerException('No permission to modify %s' % job)

    @expose(format='json')
    def save_response_comment(self,rs_id,comment):
        try:
            rs = RecipeSetResponse.by_id(rs_id)
            rs.comment = comment
            session.flush() 
            return {'success' : True, 'rs_id' : rs_id }
        except Exception, e:
            log.error(e)
            return {'success' : False, 'rs_id' : rs_id }

    @expose(format='json')
    def get_response_comment(self,rs_id):      
        rs_nacked = RecipeSetResponse.by_id(rs_id)
        comm = rs_nacked.comment

        if comm:
            return {'comment' : comm, 'rs_id' : rs_id }
        else:
            return {'comment' : 'No comment', 'rs_id' : rs_id }
    
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
        jobs = jobs.filter(and_(Job.deleted == None, Job.to_delete == None))
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
                    getter=lambda x:x.whiteboard, title='Whiteboard',
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
                           simplesearch_label = 'Lookup ID',
                           table = search_utility.Job.search.create_search_table(without=('Owner')),
                           complete_data = search_utility.Job.search.create_complete_search_table(),
                           search_controller=url("/get_search_options_job"),
                           quick_searches = [('Status-is-Queued','Queued'),('Status-is-Running','Running'),('Status-is-Completed','Completed')])
                            

        return dict(title=title,
                    object_count = jobs.count(),
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
        if 'retentiontag' in kw or 'product' in kw:
            #convert them to int and  correct Job attribute name
            if 'retentiontag' in kw:
                kw['retention_tag_id'] = int(kw['retentiontag'])
                del kw['retentiontag']
            if 'product' in kw:
                kw['product_id'] = int(kw['product'])
                del kw['product']
            retention_tag_id = kw.get('retention_tag_id')
            product_id = kw.get('product_id')
            #update_task_product should also ensure that our id's are valid
            returns.update(Utility.update_task_product(job,retention_tag_id,product_id))
            if returns['success'] is False:
                return returns
        #kw should be santised and correct by the time it gets here
        for attr in kw:
            try:
                setattr(job, attr, kw[attr])
            except AttributeError, e:
                return {'success' : False }
                # FIXME I think job_whiteboard will need a status non 200
                # raised to catch an error 
        return returns

    @expose(template="bkr.server.templates.job") 
    def default(self, id):
        try:
            job = Job.by_id(id)
        except InvalidRequestError:
            flash(_(u"Invalid job id %s" % id))
            redirect(".")

        if job.counts_as_deleted():
            flash(_(u'Invalid %s, has been deleted' % job.t_id))
            redirect(".")

        recipe_set_history = [RecipeSetActivity.query.with_parent(elem,"activity") for elem in job.recipesets]
        recipe_set_data = []
        for query in recipe_set_history:
            for d in query: 
                recipe_set_data.append(d)   
 
        job_history_grid = widgets.DataGrid(fields= [
                               widgets.DataGrid.Column(name='recipeset', 
                                                               getter=lambda x: make_link(url='#RS_%s' % x.recipeset_id,text ='RS:%s' % x.recipeset_id), 
                                                               title='RecipeSet', options=dict(sortable=True)), 
                               widgets.DataGrid.Column(name='user', getter= lambda x: x.user, title='User', options=dict(sortable=True)), 
                               widgets.DataGrid.Column(name='created', title='Created', getter=lambda x: x.created, options = dict(sortable=True)),
                               widgets.DataGrid.Column(name='field', getter=lambda x: x.field_name, title='Field Name', options=dict(sortable=True)),
                               widgets.DataGrid.Column(name='action', getter=lambda x: x.action, title='Action', options=dict(sortable=True)),
                               widgets.DataGrid.Column(name='old_value', getter=lambda x: x.old_value, title='Old value', options=dict(sortable=True)),
                               widgets.DataGrid.Column(name='new_value', getter=lambda x: x.new_value, title='New value', options=dict(sortable=True)),])

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

# for sphinx
jobs = Jobs
