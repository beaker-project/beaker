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
from beaker.server.xmlrpccontroller import RPCRoot
from beaker.server.helpers import *
import datetime

import cherrypy

from model import *
import string

from bexceptions import *

class Jobs(RPCRoot):
    # For XMLRPC methods in this class.
    exposed = True

    upload = widgets.FileField(name='job_xml', label='Job XML')
    form = widgets.TableForm(
        'jobs',
        fields = [upload],
        action = 'save_data',
        submit_text = _(u'Submit Data')
    )

    @expose(template='beaker.server.templates.form-post')
    @identity.require(identity.not_anonymous())
    def new(self, **kw):
        return dict(
            title = 'New Job',
            form = self.form,
            action = './save',
            options = {},
            value = kw,
        )

    @cherrypy.expose
    def upload(self, job_xml):
        """
        XMLRPC method to upload job
        """
        return (1,'Success')

    @expose()
    @identity.require(identity.not_anonymous())
    def save(self, job_xml, *args, **kw):
        """
        TurboGears method to upload job xml
        """
        import xmltramp
        from jobxml import *
        xml = xmltramp.parse(job_xml.file.read())
        xmljob = XmlJob(xml)
        try:
            job = self.process_xmljob(xmljob,identity.current.user_id)
        except BeakerException, err:
            session.rollback()
            flash(_(u'Failed to import job because of %s' % err ))
            redirect(".")
        except ValueError, err:
            session.rollback()
            flash(_(u'Failed to import job because of %s' % err ))
            redirect(".")

        session.save_or_update(job)
        session.flush()
        flash(_(u'Success!'))
        redirect(".")

    def process_xmljob(self, xmljob, userid):
        print xmljob.workflow
        print xmljob.whiteboard
        job = Job(whiteboard='%s' % xmljob.whiteboard, ttasks=0,
                  owner_id=userid)
        for xmlrecipeSet in xmljob.iter_recipeSets():
            recipeSet = RecipeSet(ttasks=0)
            for xmlrecipe in xmlrecipeSet.iter_recipes():
                recipe = self.handleRecipe(xmlrecipe)
                try:
                    recipe.distro = Distro.by_filter("%s" % 
                                                   recipe.distro_requires)[0]
                except IndexError:
                    raise BX(_('No Distro matches Machine Recipe: %s' % recipe.distro_requires))
                recipe.ttasks = len(recipe.tasks)
                recipeSet.ttasks += recipe.ttasks
                recipeSet.recipes.append(recipe)
                # We want the guests to be part of the same recipeSet
                for guest in recipe.guests:
                    recipeSet.recipes.append(guest)
                    try:
                        guest.distro = Distro.by_filter("%s" % 
                                                   guest.distro_requires)[0]
                    except IndexError:
                        raise BX(_('No Distro matches Guest Recipe: %s' % guest.distro_requires))
                    guest.ttasks = len(guest.tasks)
                    recipeSet.ttasks += guest.ttasks
            job.recipesets.append(recipeSet)    
            job.ttasks += recipeSet.ttasks
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
            recipe.tasks.append(recipetask)
        return recipe

    @expose(format='json')
    def to_xml(self, id):
        jobxml = Job.by_id(id).to_xml().toxml()
        return dict(xml=jobxml)

    @expose(template='beaker.server.templates.grid')
    @paginate('list',default_order='-id')
    def index(self, *args, **kw):
        jobs = session.query(Job).join('status').join('owner').outerjoin('result')
        jobs_grid = myPaginateDataGrid(fields=[
		     widgets.PaginateDataGrid.Column(name='id', getter=lambda x:x.id, title='ID', options=dict(sortable=True)),
		     widgets.PaginateDataGrid.Column(name='whiteboard', getter=lambda x:x.whiteboard, title='Whiteboard', options=dict(sortable=True)),
		     widgets.PaginateDataGrid.Column(name='owner.email_address', getter=lambda x:x.owner.email_address, title='Owner', options=dict(sortable=True)),
                     widgets.PaginateDataGrid.Column(name='progress', getter=lambda x: make_progress_bar(x), title='Progress', options=dict(sortable=False)),
		     widgets.PaginateDataGrid.Column(name='status.status', getter=lambda x:x.status, title='Status', options=dict(sortable=True)),
		     widgets.PaginateDataGrid.Column(name='result.result', getter=lambda x:x.result, title='Result', options=dict(sortable=True)),
                    ])
        return dict(title="Jobs", grid=jobs_grid, list=jobs, search_bar=None)

