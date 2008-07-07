from turbogears.database import session
from turbogears import controllers, expose, flash, widgets, validate, error_handler, validators, redirect, paginate
from turbogears import identity, redirect
from cherrypy import request, response
from kid import Element
from logan.widgets import myPaginateDataGrid
from logan.xmlrpccontroller import RPCRoot

import cherrypy

# from medusa import json
# import logging
# log = logging.getLogger("medusa.controllers")
#import model
from model import *
import string

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

    @expose(template='logan.templates.form')
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
        job = Job(whiteboard='%s' % xmljob.whiteboard,
                  owner_id=userid)
        for xmlrecipeSet in xmljob.iter_recipeSets():
            recipeSet = RecipeSet()
            for xmlrecipe in xmlrecipeSet.iter_recipes():
                recipe = self.handleRecipe(xmlrecipe)
                recipeSet.recipes.append(recipe)
            job.recipesets.append(recipeSet)    
        return job

    def handleRecipe(self, xmlrecipe, guest=False):
        if not guest:
            recipe = MachineRecipe()
            for xmlguest in xmlrecipe.iter_guests():
                guestrecipe = self.handleRecipe(xmlguest, guest=True)
                recipe.guests.append(guestrecipe)
        else:
            recipe = GuestRecipe()
            recipe.guestargs = xmlrecipe.guestargs
        recipe.host_requires = xmlrecipe.hostRequires()
        recipe.distro_requires = xmlrecipe.distroRequires()
        for xmltest in xmlrecipe.iter_tests():
            recipetest = RecipeTest()
            try:
                test = Test.by_name(xmltest.name)
            except:
                raise ValueError('Invalid Test: %s' % xmltest.name)
            recipetest.test = test
            recipetest.role = xmltest.role
            for xmlparam in xmltest.iter_params():
                param = RecipeTestParam( name=xmlparam.name, 
                                        value=xmlparam.value)
                recipetest.params.append(param)
            recipe.tests.append(recipetest)
        return recipe

    @expose()
    def to_xml(self, job_id):
        jobxml = Job.by_id(job_id).to_xml().toxml()
        return dict(xml=jobxml)

    @expose(template='logan.templates.grid')
    @paginate('list',default_order='id')
    def index(self, *args, **kw):
        jobs = session.query(Job).join('status').join('owner')
        jobs_grid = myPaginateDataGrid(fields=[
		     widgets.PaginateDataGrid.Column(name='id', getter=lambda x:x.id, title='ID', options=dict(sortable=True)),
		     widgets.PaginateDataGrid.Column(name='whiteboard', getter=lambda x:x.whiteboard, title='Whiteboard', options=dict(sortable=True)),
		     widgets.PaginateDataGrid.Column(name='owner.email_address', getter=lambda x:x.owner.email_address, title='Owner', options=dict(sortable=True)),
		     widgets.PaginateDataGrid.Column(name='status.status', getter=lambda x:x.status, title='Status', options=dict(sortable=True)),
		     widgets.PaginateDataGrid.Column(name='result.result', getter=lambda x:x.result, title='Result', options=dict(sortable=True)),
                    ])
        return dict(title="Jobs", grid=jobs_grid, list=jobs, search_bar=None)
