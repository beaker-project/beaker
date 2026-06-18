
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import datetime
import logging
import cgi
import lxml.etree

import cherrypy
from cherrypy import response
from sqlalchemy.exc import InvalidRequestError
from turbogears import expose, flash, widgets, validate, validators, redirect, paginate
from bkr.server.database import session
from bkr.server.widgets import myPaginateDataGrid, \
    RecipeWidget, RecipeSetWidget, PriorityWidget, RetentionTagWidget, \
    SearchBar, JobWhiteboard, ProductWidget, JobActionWidget, JobPageActionWidget, \
    HorizontalForm, BeakerDataGrid
from bkr.server.xmlrpccontroller import RPCRoot
from bkr.server.helpers import make_link, markdown_first_paragraph
from bkr.server import search_utility, identity
from bkr.server.controller_utilities import _custom_status, _custom_result, \
    restrict_http_method
from bkr.common.bexceptions import BeakerException, BX
from bkr.server.util import url
from bkr.server.job_utilities import Utility
from bkr.server.rpc.jobs import Jobs as JobsRPC
import six
from bkr.server.model import (Job, RecipeSet, RetentionTag, TaskBase,
                              TaskPriority, Product,
                              StaleTaskStatusException,
                              RecipeSetActivity)


log = logging.getLogger(__name__)


class JobForm(widgets.Form):

    template = 'bkr.server.templates.job_form'
    name = 'job'
    submit_text = u'Queue'
    fields = [widgets.TextArea(name='textxml')]
    hidden_fields = [widgets.HiddenField(name='confirmed', validator=validators.StringBool())]
    params = ['xsd_errors']
    xsd_errors = None

    def update_params(self, d):
        super(JobForm, self).update_params(d)
        if 'xsd_errors' in d['options']:
            d['xsd_errors'] = d['options']['xsd_errors']
            d['submit_text'] = u'Queue despite validation errors'


class Jobs(RPCRoot, JobsRPC):
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
    message = widgets.TextArea(name='msg', label=u'Reason?', help_text=u'Optional')

    _upload = widgets.FileField(name='filexml', label='Job XML')
    form = HorizontalForm(
        'jobs',
        fields = [_upload],
        action = 'save_data',
        submit_text = u'Submit Data'
    )
    del _upload

    cancel_form = widgets.TableForm(
        'cancel_job',
        fields = [hidden_id, message, confirm],
        action = 'really_cancel',
        submit_text = u'Yes'
    )

    job_form = JobForm()

    @classmethod
    def success_redirect(cls, id, url='/jobs/mine', *args, **kw):
        flash(u'Success! job id: %s' % id)
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
            raise BeakerException(u'You do not have permission to delete %s' % t_id)

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
            flash(u'Succesfully deleted %s' % t_id)
        except (BeakerException, TypeError):
            flash(u'Unable to delete %s' % t_id)
            redirect('.')
        redirect('./mine')

    @expose()
    @identity.require(identity.not_anonymous())
    @restrict_http_method('post')
    def delete_job_row(self, t_id):
        try:
            self._delete_job(t_id)
            return [t_id]
        except (BeakerException, TypeError) as e:
            log.debug(str(e))
            response.status = 400
            return ['Unable to delete %s' % t_id]

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
                flash(u"Invalid job id %s" % job_id)
                redirect(".")
            textxml = lxml.etree.tostring(job.to_xml(clone=True),
                                          pretty_print=True, encoding=six.text_type)
        elif recipeset_id:
            title = 'Clone Recipeset %s' % recipeset_id
            try:
                recipeset = RecipeSet.by_id(recipeset_id)
            except InvalidRequestError:
                flash(u"Invalid recipeset id %s" % recipeset_id)
                redirect(".")
            textxml = lxml.etree.tostring(
                    recipeset.to_xml(clone=True, include_enclosing_job=True),
                    pretty_print=True, encoding=six.text_type)
        elif isinstance(filexml, cgi.FieldStorage):
            # Clone from file
            try:
                textxml = filexml.value.decode('utf8')
            except UnicodeDecodeError as e:
                flash(u'Invalid job XML: %s' % e)
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
                from bkr.server.util import parse_untrusted_xml
                xmljob = parse_untrusted_xml(textxml.encode('utf8'))
                job = self.process_xmljob(xmljob, identity.current.user)
                session.flush()
            except Exception as err:
                session.rollback()
                flash(u'Failed to import job because of: %s' % err)
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

    def jobs(self,jobs,action='.', title=u'Jobs', *args, **kw):
        from sqlalchemy import not_
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
                           label=u'Job Search',
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
            flash(u"Invalid job id %s" % id)
            redirect(".")
        if not job.can_cancel(identity.current.user):
            flash(u"You don't have permission to cancel job id %s" % id)
            redirect(".")

        try:
            job.cancel(msg)
        except StaleTaskStatusException as e:
            log.warn(str(e))
            session.rollback()
            flash(u"Could not cancel job id %s. Please try later" % id)
            redirect(".")
        else:
            job.record_activity(user=identity.current.user, service=u'WEBUI',
                                field=u'Status', action=u'Cancelled', old='', new='')
            flash(u"Successfully cancelled job %s" % id)
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
            flash(u"Invalid job id %s" % id)
            redirect(".")
        if not job.can_cancel(identity.current.user):
            flash(u"You don't have permission to cancel job id %s" % id)
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
            flash(u"Invalid job id %s" % id)
            redirect(".")

        if job.is_deleted:
            flash(u'Invalid %s, has been deleted' % job.t_id)
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
