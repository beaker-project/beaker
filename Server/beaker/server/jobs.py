# Logan - Logan is the scheduling piece of the Beaker project
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
from turbogears import controllers, expose, flash, widgets, validate, error_handler, validators, redirect, paginate
from turbogears import identity, redirect
from cherrypy import request, response
from kid import Element
from beaker.server.widgets import myPaginateDataGrid
from beaker.server.widgets import myDataGrid
from beaker.server.xmlrpccontroller import RPCRoot
from beaker.server.helpers import *
from beaker.server.widgets import RecipeWidget
from beaker.server.widgets import RecipeTasksWidget
from beaker.server.widgets import RecipeSetWidget
from beaker.server.widgets import PriorityWidget
import datetime

import cherrypy

from model import *
import string

from bexceptions import *

import xmltramp
from jobxml import *
import cgi

class Jobs(RPCRoot):
    # For XMLRPC methods in this class.
    exposed = True 
    recipeset_widget = RecipeSetWidget()
    recipe_widget = RecipeWidget()
    priority_widget = PriorityWidget()
    recipe_tasks_widget = RecipeTasksWidget()

    upload = widgets.FileField(name='filexml', label='Job XML')
    hidden_id = widgets.HiddenField(name='id')
    confirm = widgets.Label(name='confirm', default="Are you sure you want to cancel?")
    message = widgets.TextArea(name='msg', label=_(u'Reason?'), help=_(u'Optional'))
    job_input = widgets.TextArea(name='textxml', label=_(u'Job XML'), attrs=dict(rows=40, cols=155))

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

    job_form = widgets.TableForm(
        'job',
        fields = [job_input],
        submit_text = _(u'Queue')
    )

    @expose(template='beaker.server.templates.form-post')
    @identity.require(identity.not_anonymous())
    def new(self, **kw):
        return dict(
            title = 'New Job',
            form = self.form,
            action = './clone',
            options = {},
            value = kw,
        )

    @cherrypy.expose
    def upload(self, jobxml):
        """
        XMLRPC method to upload job
        """
        xml = xmltramp.parse(jobxml)
        xmljob = XmlJob(xml)
        try:
            job = self.process_xmljob(xmljob,identity.current.user)
        except BeakerException, err:
            session.rollback()
            raise
        except ValueError, err:
            session.rollback()
            raise
        session.save(job)
        session.flush()
        return "j:%s" % job.id

    @identity.require(identity.not_anonymous())
    @expose(template="beaker.server.templates.form-post")
    def clone(self, job_id=None, recipe_id=None, textxml=None, filexml=None, **kw):
        """
        Review cloned xml before submitting it.
        """
        if job_id:
            # Clone from Job ID
            try:
                job = Job.by_id(job_id)
            except InvalidRequestError:
                flash(_(u"Invalid job id %s" % job_id))
                redirect(".")
            textxml = job.to_xml(clone=True).toprettyxml()
        elif recipe_id:
            # Clone from Recipe ID
            try:
                recipe = Recipe.by_id(recipe_id)
            except InvalidRequestError:
                flash(_(u"Invalid recipe id %s" % recipe_id))
                redirect(".")
            textxml = recipe.to_xml(clone=True).toprettyxml()
        elif isinstance(filexml, cgi.FieldStorage):
            # Clone from file
            textxml = filexml.file.read()
        elif textxml:
            xmljob = XmlJob(xmltramp.parse(textxml))
            try:
                job = self.process_xmljob(xmljob,identity.current.user)
            except BeakerException, err:
                session.rollback()
                flash(_(u'Failed to import job because of %s' % err ))
                return dict(
                    title = 'Clone Job %s' % id,
                    form = self.job_form,
                    action = './clone',
                    options = {},
                    value = dict(textxml = "%s" % textxml),
                )
            except ValueError, err:
                session.rollback()
                flash(_(u'Failed to import job because of %s' % err ))
                return dict(
                    title = 'Clone Job %s' % id,
                    form = self.job_form,
                    action = './clone',
                    options = {},
                    value = dict(textxml = "%s" % textxml),
                )
            session.save(job)
            session.flush()
            flash(_(u'Success! job id: %s' % job.id))
            redirect(".")
        return dict(
            title = 'Clone Job %s' % id,
            form = self.job_form,
            action = './clone',
            options = {},
            value = dict(textxml = "%s" % textxml),
        )

    def process_xmljob(self, xmljob, user):
        job = Job(whiteboard='%s' % xmljob.whiteboard, ttasks=0,
                  owner=user)
        for xmlrecipeSet in xmljob.iter_recipeSets():
            recipeSet = RecipeSet(ttasks=0)
            recipeset_priority = xmlrecipeSet.get_xml_attr('priority',str,None)
            if recipeset_priority is not None:
                try:
                    my_priority = TaskPriority.query().filter_by(priority = recipeset_priority).one()
                except InvalidRequestError, (e):
                    raise BX(_('You have specified an invalid recipeSet priority:%s' % recipeset_priority))
                allowed_priorities = RecipeSet.allowed_priorities_initial(identity.current.user)
                allowed = [elem for elem in allowed_priorities if elem.priority == recipeset_priority]
                if allowed:
                    recipeSet.priority = allowed[0]
                else:
                    recipeSet.priority = TaskPriority.query().filter_by(priority = TaskPriority.default_priority).one()
            else:
                recipeSet.priority = TaskPriority.query().filter(priority = TaskPriority.default_priority).one() 

            for xmlrecipe in xmlrecipeSet.iter_recipes(): 
                recipe = self.handleRecipe(xmlrecipe)
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
            job.recipesets.append(recipeSet)    
            job.ttasks += recipeSet.ttasks
        if not job.recipesets:
            raise BX(_('No RecipeSets! You can not have a Job with no recipeSets!'))
        return job

    def handleRecipe(self, xmlrecipe, guest=False):
        if not guest:
            recipe = MachineRecipe(ttasks=0)
            for xmlguest in xmlrecipe.iter_guests():
                guestrecipe = self.handleRecipe(xmlguest, guest=True)
                recipe.guests.append(guestrecipe)
        else:
            recipe = GuestRecipe(ttasks=0)
            recipe.guestname = xmlrecipe.guestname
            recipe.guestargs = xmlrecipe.guestargs
        recipe.host_requires = xmlrecipe.hostRequires()
        recipe.distro_requires = xmlrecipe.distroRequires()
        try:
            recipe.distro = Distro.by_filter("%s" % 
                                           recipe.distro_requires)[0]
        except IndexError:
            raise BX(_('No Distro matches Recipe: %s' % recipe.distro_requires))
        recipe.whiteboard = xmlrecipe.whiteboard
        recipe.kickstart = xmlrecipe.kickstart
        recipe.ks_meta = xmlrecipe.ks_meta
        recipe.kernel_options = xmlrecipe.kernel_options
        recipe.kernel_options_post = xmlrecipe.kernel_options_post
        for xmlrepo in xmlrecipe.iter_repos():
            recipe.repos.append(RecipeRepo(name=xmlrepo.name, url=xmlrepo.url))
        for xmltask in xmlrecipe.iter_tasks():
            recipetask = RecipeTask()
            try:
                task = Task.by_name(xmltask.name)
            except:
                raise BX(_('Invalid Task: %s' % xmltask.name))
            recipetask.task = task
            recipetask.role = xmltask.role
            for xmlparam in xmltask.iter_params():
                param = RecipeTaskParam( name=xmlparam.name, 
                                        value=xmlparam.value)
                recipetask.params.append(param)
            #FIXME Filter Tasks based on distro selected.
            recipe.append_tasks(recipetask)
        if not recipe.tasks:
            raise BX(_('No Tasks! You can not have a recipe with no tasks!'))
        return recipe

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

    @expose(template='beaker.server.templates.grid')
    @paginate('list',default_order='-id', limit=50)
    def index(self, *args, **kw):
        jobs = session.query(Job).join('status').join('owner').outerjoin('result')
        jobs_grid = myPaginateDataGrid(fields=[
		     widgets.PaginateDataGrid.Column(name='id', getter=lambda x:make_link(url = './%s' % x.id, text = x.t_id), title='ID', options=dict(sortable=True)),
		     widgets.PaginateDataGrid.Column(name='whiteboard', getter=lambda x:x.whiteboard, title='Whiteboard', options=dict(sortable=True)),
		     widgets.PaginateDataGrid.Column(name='owner.email_address', getter=lambda x:x.owner.email_address, title='Owner', options=dict(sortable=True)),
                     widgets.PaginateDataGrid.Column(name='progress', getter=lambda x: x.progress_bar, title='Progress', options=dict(sortable=False)),
		     widgets.PaginateDataGrid.Column(name='status.status', getter=lambda x:x.status, title='Status', options=dict(sortable=True)),
		     widgets.PaginateDataGrid.Column(name='result.result', getter=lambda x:x.result, title='Result', options=dict(sortable=True)),
		     widgets.PaginateDataGrid.Column(name='action', getter=lambda x:x.action_link, title='Action', options=dict(sortable=False)),
                    ])
        return dict(title="Jobs", grid=jobs_grid, list=jobs, search_bar=None)

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
        if not identity.current.user.is_admin() and job.owner != identity.current.user:
            flash(_(u"You don't have permission to cancel job id %s" % id))
            redirect(".")
        job.cancel(msg)
        flash(_(u"Successfully cancelled job %s" % id))
        redirect(".")

    @identity.require(identity.not_anonymous())
    @expose(template="beaker.server.templates.form")
    def cancel(self, id):
        """
        Confirm cancel job
        """
        try:
            job = Job.by_id(id)
        except InvalidRequestError:
            flash(_(u"Invalid job id %s" % id))
            redirect(".")
        if not identity.current.user.is_admin() and job.owner != identity.current.user:
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

    @expose(template="beaker.server.templates.job") 
    def default(self, id): 
        try:
            job = Job.by_id(id)
        except InvalidRequestError:
            flash(_(u"Invalid job id %s" % id))
            redirect(".")
    
        recipe_set_history = [RecipeSetActivity.query().with_parent(elem,"activity") for elem in job.recipesets]
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

        return dict(title   = 'Job',
                    user                 = identity.current.user,   #I think there is a TG var to use in the template so we dont need to pass this ?
                    priorities           = TaskPriority.query().all(),
                    priority_widget      = self.priority_widget, 
                    recipeset_widget     = self.recipeset_widget,
                    job_history          = recipe_set_data,
                    job_history_grid     = job_history_grid, 
                    recipe_widget        = self.recipe_widget,
                    recipe_tasks_widget  = self.recipe_tasks_widget,
                    job                  = job)

