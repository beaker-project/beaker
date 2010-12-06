from turbogears.database import session
from turbogears import controllers, expose, flash, widgets, validate, error_handler, validators, redirect, paginate, url
from model import *
from turbogears import identity, redirect, config
import search_utility as su
import bkr
import bkr.server.stdvars
from bkr.server.power import PowerTypes
from bkr.server.keytypes import KeyTypes
from bkr.server.CSV_import_export import CSV
from bkr.server.group import Groups
from bkr.server.tag import Tags
from bkr.server.osversion import OSVersions
from bkr.server.distro_family import DistroFamily
from bkr.server.labcontroller import LabControllers
from bkr.server.user import Users
from bkr.server.distro import Distros
from bkr.server.activity import Activities
from bkr.server.reports import Reports
from bkr.server.job_matrix import JobMatrix
from bkr.server.reserve_workflow import ReserveWorkflow
from bkr.server.retention_tags import RetentionTag as RetentionTagController
from bkr.server.watchdog import Watchdogs
from bkr.server.systems import SystemsController
from bkr.server.widgets import myPaginateDataGrid
from bkr.server.widgets import PowerTypeForm
from bkr.server.widgets import PowerForm
from bkr.server.widgets import LabInfoForm
from bkr.server.widgets import PowerActionForm
from bkr.server.widgets import ReportProblemForm
from bkr.server.widgets import SystemDetails
from bkr.server.widgets import SystemHistory
from bkr.server.widgets import SystemExclude
from bkr.server.widgets import SystemKeys
from bkr.server.widgets import SystemNotes
from bkr.server.widgets import SystemGroups
from bkr.server.widgets import SystemInstallOptions
from bkr.server.widgets import SystemProvision
from bkr.server.widgets import SearchBar, SystemForm
from bkr.server.widgets import SystemArches
from bkr.server.widgets import TaskSearchForm
from bkr.server.authentication import Auth
from bkr.server.xmlrpccontroller import RPCRoot
from bkr.server.cobbler_utils import hash_to_string
from bkr.server.jobs import Jobs
from bkr.server.recipes import Recipes
from bkr.server.recipesets import RecipeSets
from bkr.server.tasks import Tasks
from bkr.server.task_actions import TaskActions
from bkr.server.controller_utilities import Utility, SystemSaveForm, SearchOptions, SystemTab
from bkr.server.bexceptions import *
from cherrypy import request, response
from cherrypy.lib.cptools import serve_file
from tg_expanding_form_widget.tg_expanding_form_widget import ExpandingForm
from bkr.server.needpropertyxml import *
from bkr.server.helpers import *
from bkr.server.tools.init import dummy
from bkr.server import mail
from decimal import Decimal
import bkr.server.recipes
import bkr.server.rdf
import random

from kid import Element
import cherrypy
import md5
import re
import string
import pkg_resources
import rdflib.graph

# for debugging
import sys

# from bkr.server import json
import logging
log = logging.getLogger("bkr.server.controllers")
import breadcrumbs
from datetime import datetime


class Netboot:
    # For XMLRPC methods in this class.
    exposed = True

    # path for Legacy RHTS
    @cherrypy.expose
    def system_return(self, *args):
        return Root().system_return(*args)

    @cherrypy.expose
    def commandBoot(self, commands):
        """
        NetBoot Compat layer for old RHTS Scheduler
        """
        repos = []
        bootargs = None
        kickstart = None
        packages = []
        runtest_url = None
        testrepo = None
        hostname = None
        distro_name = None
        partitions = None
        SETENV = re.compile(r'SetEnvironmentVar\s+([^\s]+)\s+"*([^"]+)')
        BOOTARGS = re.compile(r'BootArgs\s+(.*)')
        KICKSTART = re.compile(r'Kickstart\s+(.*)')
        ADDREPO = re.compile(r'AddRepo\s+([^\s]+)')
        TESTREPO = re.compile(r'TestRepo\s+([^\s]+)')
        INSTALLPACKAGE = re.compile(r'InstallPackage\s+([^\s]+)')
        KICKPART = re.compile(r'KickPart\s+([^\s]+)')

        for command in commands.split('\n'):
            if SETENV.match(command):
                if SETENV.match(command).group(1) == "RESULT_SERVER":
                    rhts_server = SETENV.match(command).group(2)
                if SETENV.match(command).group(1) == "RECIPEID":
                    recipeid = SETENV.match(command).group(2)
                if SETENV.match(command).group(1) == "RUNTEST_URL":
                    runtest_url = SETENV.match(command).group(2)
                if SETENV.match(command).group(1) == "HOSTNAME":
                    hostname = SETENV.match(command).group(2)
                if SETENV.match(command).group(1) == "INSTALL_NAME":
                    distro_name = SETENV.match(command).group(2)
            if KICKPART.match(command):
                partitions = KICKPART.match(command).group(1)
            if INSTALLPACKAGE.match(command):
                packages.append(INSTALLPACKAGE.match(command).group(1))
            if BOOTARGS.match(command):
                bootargs = BOOTARGS.match(command).group(1)
            if KICKSTART.match(command):
                kickstart = string.join(KICKSTART.match(command).group(1).split("RHTSNEWLINE"), "\n")
            if ADDREPO.match(command):
                repos.append(ADDREPO.match(command).group(1))
            if TESTREPO.match(command):
                testrepo = TESTREPO.match(command).group(1)
            
        ks_meta = "rhts_server=%s testrepo=%s recipeid=%s packages=%s" % (rhts_server, testrepo, recipeid, string.join(packages,":"))
        if config.get('test_password'):
            ks_meta = '%s password=%s' % (ks_meta, config.get('test_password'))
        if runtest_url:
            ks_meta = "%s runtest_url=%s" % (ks_meta, runtest_url)
        if repos:
            ks_meta = "%s customrepos=%s" % (ks_meta, string.join(repos,"|"))
        if partitions:
            ks_meta = "%s partitions=%s" % (ks_meta, partitions)
        if distro_name:
            distro = Distro.by_install_name(distro_name)
        else:
            raise BX(_("distro not defined"))
        if hostname:
            system = System.query().filter(System.fqdn == hostname).one()
            system.activity.append(SystemActivity(system.user, 'VIA %s' % None, 'Reserved', 'User', "", "%s" % system.user))
            system.action_auto_provision(distro, 
                                         ks_meta, 
                                         bootargs, 
                                         None, 
                                         kickstart)
            system.activity.append(SystemActivity(system.user, 'VIA %s' % None, 'Provision', 'Distro', "", "Success: %s" % distro.install_name))
        else:
            raise BX(_("hostname not defined"))
        return 0

class Arches:
    @expose(format='json')
    def by_name(self,name):
        name = name.lower()
        search = Arch.list_by_name(name)
        arches = [match.arch for match in search]
        return dict(arches=arches)

class Devices:

    @expose(template='bkr.server.templates.grid')
    @paginate('list',default_order='fqdn',limit=10,max_limit=None)
    def view(self, id):
        device = session.query(Device).get(id)
        systems = System.all(identity.current.user).join('devices').filter_by(id=id).distinct()
        device_grid = myPaginateDataGrid(fields=[
                        ('System', lambda x: make_link("/view/%s" % x.fqdn, x.fqdn)),
                        ('Description', lambda x: device.description),
                       ])
        return dict(title="", 
                    grid = device_grid, 
                    search_bar=None,
                    object_count = systems.count(),
                    list = systems)

    @expose(template='bkr.server.templates.grid')
    @paginate('list',default_order='description',limit=50,max_limit=None)
    def default(self, *args, **kw):
        args = list(args)
        if len(args) == 1:
            devices = session.query(Device).join('device_class').filter_by(device_class=args[0])
                
        if len(args) != 1:
            devices = session.query(Device).join('device_class')
        devices_grid = myPaginateDataGrid(fields=[
                        widgets.PaginateDataGrid.Column(name='description', getter=lambda x: make_link("/devices/view/%s" % x.id, x.description), title='Description', options=dict(sortable=True)),
                        widgets.PaginateDataGrid.Column(name='device_class.device_class', getter=lambda x: x.device_class, title='Type', options=dict(sortable=True)),
                        widgets.PaginateDataGrid.Column(name='bus', getter=lambda x: x.bus, title='Bus', options=dict(sortable=True)),
                        widgets.PaginateDataGrid.Column(name='driver', getter=lambda x: x.driver, title='Driver', options=dict(sortable=True)),
                        widgets.PaginateDataGrid.Column(name='vendor_id', getter=lambda x: x.vendor_id, title='Vendor ID', options=dict(sortable=True)),
                        widgets.PaginateDataGrid.Column(name='device_id', getter=lambda x: x.device_id, title='Device ID', options=dict(sortable=True)),
                        widgets.PaginateDataGrid.Column(name='subsys_vendor_id', getter=lambda x: x.subsys_vendor_id, title='Subsys Vendor ID', options=dict(sortable=True)),
                        widgets.PaginateDataGrid.Column(name='subsys_device_id', getter=lambda x: x.subsys_device_id, title='Subsys Device ID', options=dict(sortable=True)),
                       ])
        return dict(title="Devices", 
                    grid = devices_grid, 
                    search_bar=None, 
                    object_count = devices.count(),
                    list = devices)

class ReportProblemController(object):

    form_widget = ReportProblemForm()

    @expose(template='bkr.server.templates.form-post')
    @identity.require(identity.not_anonymous())
    def index(self, system_id, recipe_id=None, problem_description=None, tg_errors=None):
        """
        Allows users to report a problem with a system to the system's owner.
        """
        try:
            system = System.by_id(system_id, identity.current.user)
        except InvalidRequestError:
            flash(_(u'Unable to find system with id of %s' % system_id))
            redirect('/')
        recipe = None
        if recipe_id is not None:
            try:
                recipe = Recipe.by_id(recipe_id)
            except InvalidRequestError:
                pass
        return dict(
            title=_(u'Report a problem with %s') % system.fqdn,
            form=self.form_widget,
            method='post',
            action='submit',
            value={'system_id': system_id, 'recipe_id': recipe_id},
            options={'system': system, 'recipe': recipe}
        )

    @expose()
    @error_handler(index)
    @validate(form=form_widget)
    @identity.require(identity.not_anonymous())
    def submit(self, system_id, problem_description, recipe_id=None):
        system = System.by_id(system_id, identity.current.user)
        recipe = None
        if recipe_id is not None:
            try:
                recipe = Recipe.by_id(recipe_id)
            except InvalidRequestError:
                pass
        mail.system_problem_report(system, problem_description,
                recipe, identity.current.user)
        activity = SystemActivity(identity.current.user, u'WEBUI', u'Reported problem',
                u'Status', None, problem_description)
        system.activity.append(activity)
        flash(_(u'Your problem report has been forwarded to the system owner'))
        redirect('/view/%s' % system.fqdn)

class Root(RPCRoot): 
    powertypes = PowerTypes()
    keytypes = KeyTypes()
    devices = Devices()
    groups = Groups()
    tags = Tags()
    distrofamily = DistroFamily()
    osversions = OSVersions()
    labcontrollers = LabControllers()
    distros = Distros()
    activity = Activities()
    users = Users()
    arches = Arches()
    netboot = Netboot()
    auth = Auth()
    csv = CSV()
    jobs = Jobs()
    recipesets = RecipeSets()
    recipes = Recipes()
    tasks = Tasks()
    taskactions = TaskActions()
    reports = Reports()
    matrix = JobMatrix()
    reserveworkflow = ReserveWorkflow()
    watchdogs = Watchdogs()
    retentiontag = RetentionTagController()
    report_problem = ReportProblemController()
    systems = SystemsController()

    for entry_point in pkg_resources.iter_entry_points('bkr.controllers'):
        controller = entry_point.load()
        log.info('Attaching root extension controller %s as %s',
                controller, entry_point.name)
        locals()[entry_point.name] = controller

    id         = widgets.HiddenField(name='id')
    submit     = widgets.SubmitButton(name='submit')

    email      = widgets.TextField(name='email_address', label='Email Address') 
    autoUsers  = widgets.AutoCompleteField(name='user',
                                           search_controller=url("/users/by_name"),
                                           search_param="input",
                                           result_name="matches")
    
    prefs_form   = widgets.TableForm(
        'UserPrefs',
        fields = [email],
        action = 'save_data',
        submit_text = _(u'Change'),
    )

    loan_form     = widgets.TableForm(
        'Loan',
        fields = [id, autoUsers,],
        action = 'save_data',
        submit_text = _(u'Change'),
    )

    owner_form    = widgets.TableForm(
        'Owner',
        fields = [id, autoUsers,],
        action = 'save_data',
        submit_text = _(u'Change'),
    )  
  
    system_form = SystemForm()
    power_form = PowerForm(name='power')
    labinfo_form = LabInfoForm(name='labinfo')
    power_action_form = PowerActionForm(name='power_action')
    system_details = SystemDetails()
    system_activity = SystemHistory()
    system_exclude = SystemExclude(name='excluded_families')
    system_keys = SystemKeys(name='keys')
    system_notes = SystemNotes(name='notes')
    system_groups = SystemGroups(name='groups')
    system_installoptions = SystemInstallOptions(name='installoptions')
    system_provision = SystemProvision(name='provision')
    arches_form = SystemArches(name='arches') 
    task_form = TaskSearchForm(name='tasks')

    @expose(format='json')
    def change_system_admin(self,system_id=None,group_id=None,cmd=None,**kw):
        if system_id is None or group_id is None or cmd is None:
            log.debug('Did not call change_system_admin with correct formal args')
            return {'success' : 0}

        sys = System.by_id(system_id,identity.current.user)
        if sys.is_admin() is None:
            #Someone tried to be tricky...
            return {'success' : 0}

        group = Group.by_id(group_id)
        if cmd == 'add':
            group.admin_systems.append(System.by_id(system_id,identity.current.user)) 
            return { 'success' : 1 }
        if cmd == 'remove':
            group.admin_systems.remove(System.by_id(system_id,identity.current.user))
            return {'success' : 1 }


    @expose(format='json')
    def get_keyvalue_search_options(self,**kw):
        return_dict = {}
        return_dict['keyvals'] = [x for x in Key.get_all_keys() if x != 'MODULE']
        return return_dict

    @expose(format='json')
    def get_search_options_distros(self,table_field,**kw):
        return su.Distro.search.get_search_options(table_field, *args, **kw)

    @expose(format='json')
    def get_search_options_recipe(self,table_field, *args, **kw):
        return su.Recipe.search.get_search_options(table_field, *args, **kw)

    @expose(format='json')
    def get_search_options_job(self,table_field,**kw):
        return su.Job.search.get_search_options(table_field, *args, **kw)

    @expose(format='json')
    def get_search_options_task(self,table_field, *args, **kw):
        return su.Task.search.get_search_options(table_field, *args, **kw)

    @expose(format='json')
    def get_search_options_activity(self,table_field,**kw):
        return su.Activity.search.get_search_options(table_field, *args, **kw)

    @expose(format='json')
    def get_search_options_history(self,table_field, *args, **kw):
        return su.History.search.get_search_options(table_field, *args, **kw)

    @expose(format='json')
    def get_operators_keyvalue(self,keyvalue_field,*args,**kw):
        return su.Key.search.get_search_options(keyvalue_field, *args, **kw)

    @expose(format='json')
    def get_search_options(self,table_field,**kw):
        return_dict = {}
        search =  su.System.search.search_on(table_field)
      
        #Determine what field type we are dealing with. If it is Boolean, convert our values to 0 for False
        # and 1 for True
        col_type = su.System.search.field_type(table_field)
       
        if col_type.lower() == 'boolean':
            search['values'] = { 0:'False', 1:'True'}
            
        #Determine if we have search values. If we do, then we should only have the operators
        # 'is' and 'is not'.
        if search['values']:
            search['operators'] = filter(lambda x: x == 'is' or x == 'is not', search['operators'])         

        search['operators'].sort()
        return_dict['search_by'] = search['operators'] 
        return_dict['search_vals'] = search['values'] 
     
        return return_dict

    @expose(format='json')
    def get_fields(self, table_name):
        return dict( fields = System.get_fields(table_name))
  
    @expose(format='json')
    def get_installoptions(self, system_id=None, distro_id=None):
        try:
            system = System.by_id(system_id,identity.current.user)
        except InvalidRequestError:
            return dict(ks_meta=None)
        try:
            distro = Distro.by_id(distro_id)
        except InvalidRequestError:
            return dict(ks_meta=None)
        install_options = system.install_options(distro)
        ks_meta = hash_to_string(install_options['ks_meta'])
        kernel_options = hash_to_string(install_options['kernel_options'])
        kernel_options_post = hash_to_string(install_options['kernel_options_post'])
        return dict(ks_meta = ks_meta, kernel_options = kernel_options,
                    kernel_options_post = kernel_options_post)

    @expose(format='json')
    def change_priority_recipeset(self,priority_id,recipeset_id): 
        user = identity.current.user
        if not user:
            return {'success' : None, 'msg' : 'Must be logged in' }

        try:
            recipeset = RecipeSet.by_id(recipeset_id)
            old_priority = recipeset.priority.priority
        except:
            log.error('No rows returned for recipeset_id %s in change_priority_recipeset:%s' % (recipeset_id,e))
            return { 'success' : None, 'msg' : 'RecipeSet is not valid' }

        try: 
            priority_query = TaskPriority.by_id(priority_id)  # will throw an error here if priorty id is invalid 
        except InvalidRequestError, (e):
            log.error('No rows returned for priority_id %s in change_priority_recipeset:%s' % (priority_id,e)) 
            return { 'success' : None, 'msg' : 'Priority not found', 'current_priority' : recipeset.priority.id }
         
        allowed_priority_ids = [elem.id for elem in recipeset.allowed_priorities(user)]
       
        if long(priority_id) not in allowed_priority_ids:
            return {'success' : None, 'msg' : 'Insufficient privileges for that priority', 'current_priority' : recipeset.priority.id }
         

        activity = RecipeSetActivity(identity.current.user, 'WEBUI', 'Changed', 'Priority', recipeset.priority.id,priority_id)
        recipeset.priority = priority_query
        session.save_or_update(recipeset)        
        recipeset.activity.append(activity)
        return {'success' : True } 

    @expose(template='bkr.server.templates.grid_add')
    @expose(template='bkr.server.templates.systems_feed', format='xml', as_format='atom',
            content_type='application/atom+xml', accept_format='application/atom+xml')
    @paginate('list',default_order='fqdn',limit=20,max_limit=None)
    def index(self, *args, **kw): 
        return_dict =  self._systems(systems = System.all(identity.current.user), *args, **kw) 
        return return_dict

    @expose(template='bkr.server.templates.form')
    @identity.require(identity.not_anonymous())
    def prefs(self, *args, **kw):
        user = identity.current.user
        return dict(
            title    = 'User Prefs',
            form     = self.prefs_form,
            widgets  = {},
            action   = '/save_prefs',
            value    = user,
            options  = None)


    @expose()
    @identity.require(identity.not_anonymous())
    def save_prefs(self, *args, **kw):
        email = kw.get('email_address',None) 
        
        if email and email != identity.current.user.email_address:
            flash(_(u"Email Address Changed"))
            identity.current.user.email_address = email
        redirect('/')

    @expose(template='bkr.server.templates.grid')
    @expose(template='bkr.server.templates.systems_feed', format='xml', as_format='atom',
            content_type='application/atom+xml', accept_format='application/atom+xml')
    @identity.require(identity.not_anonymous())
    @paginate('list',default_order='fqdn',limit=20,max_limit=None)
    def available(self, *args, **kw):
        return self._systems(systems = System.available(identity.current.user), *args, **kw)

    @expose(template='bkr.server.templates.grid')
    @expose(template='bkr.server.templates.systems_feed', format='xml', as_format='atom',
            content_type='application/atom+xml', accept_format='application/atom+xml')
    @identity.require(identity.not_anonymous())
    @paginate('list',default_order='fqdn',limit=20,max_limit=None)
    def free(self, *args, **kw): 
        return self._systems(systems = System.free(identity.current.user), *args, **kw)

    @expose(template='bkr.server.templates.grid')
    @expose(template='bkr.server.templates.systems_feed', format='xml', as_format='atom',
            content_type='application/atom+xml', accept_format='application/atom+xml')
    @identity.require(identity.not_anonymous())
    @paginate('list',limit=20,max_limit=None)
    def mine(self, *args, **kw):
        return self._systems(systems = System.mine(identity.current.user), *args, **kw)

      
    @expose(template='bkr.server.templates.grid') 
    @identity.require(identity.not_anonymous())
    @paginate('list',default_order='fqdn', limit=20, max_limit=None)
    def reserve_system(self, *args,**kw):
        
        def reserve_link(x,distro):
            if x.is_free():
                return make_link("/reserveworkflow/reserve?system_id=%s&distro_id=%s" % (Utility.get_correct_system_column(x).id,distro), 'Reserve Now')
            else:
                return make_link("/reserveworkflow/reserve?system_id=%s&distro_id=%s" % (Utility.get_correct_system_column(x).id,distro), 'Queue Reservation')
        try:
            try: 
                distro_install_name = kw['distro'] #this should be the distro install_name, throw KeyError is expected and caught
                distro = Distro.query().filter(Distro.install_name == distro_install_name).one()
            except KeyError:
                try: 
                    distro_id = kw['distro_id']
                    distro = Distro.query().filter(Distro.id == distro_id).one()
                except KeyError:
                    raise
            # I don't like duplicating this code in find_systems_for_distro() but it dies on trying to jsonify a Query object... 
            systems_distro_query = distro.systems()
            avail_systems_distro_query = System.available_for_schedule(identity.current.user,systems=systems_distro_query)
            warn = None
            if avail_systems_distro_query.count() < 1: 
                warn = 'No Systems compatible with distro %s' % distro.install_name
          
            getter = lambda x: reserve_link(x,distro.id)       
            direct_column = Utility.direct_column(title='Action',getter=getter)     
            return_dict  = self._systems(systems=avail_systems_distro_query, direct_columns=[(8,direct_column)],warn_msg=warn, *args, **kw)
       
            return_dict['title'] = 'Reserve Systems'
            return_dict['warn_msg'] = warn
            return_dict['tg_template'] = "bkr.server.templates.reserve_grid"
            return_dict['action'] = '/reserve_system'
            return_dict['options']['extra_hiddens'] = {'distro' : distro.install_name} 
            return return_dict
        except KeyError, (e):
            flash(_(u'Need a  valid distro to search on')) 
            redirect(url('/reserveworkflow',**kw))              
        except InvalidRequestError,(e):
            flash(_(u'Invalid Distro given'))                 
            redirect(url('/reserveworkflow',**kw))    
          
    def _history_search(self,activity,**kw):
        history_search = su.History.search(activity)
        for search in kw['historysearch']:
            col = search['table'] 
            history_search.append_results(search['value'],col,search['operation'],**kw)
        return history_search.return_results()

    def _system_search(self,kw,sys_search,use_custom_columns = False): 
        for search in kw['systemsearch']: 
	        #clsinfo = System.get_dict()[search['table']] #Need to change this
            class_field_list = search['table'].split('/')
            cls_ref = su.System.search.translate_name(class_field_list[0])
            col = class_field_list[1]              
            #If value id False or True, let's convert them to
            if class_field_list[0] != 'Key':
               sys_search.append_results(cls_ref,search['value'],col,search['operation']) 
            else:
               sys_search.append_results(cls_ref,search['value'],col,search['operation'],keyvalue=search['keyvalue']) 

        return sys_search.return_results()
              

    def histories(self,activity,**kw):  
       
        return_dict = {}                    
        if 'simplesearch' in kw:
            simplesearch = kw['simplesearch']
            kw['historysearch'] = [{'table' : 'Field Name',   
                                    'operation' : 'contains', 
                                    'value' : kw['simplesearch']}] 
                    
        else:
            simplesearch = None
        return_dict.update({'simplesearch':simplesearch})

        if kw.get("historysearch"):
            searchvalue = kw['historysearch']  
            activities_found = self._history_search(activity,**kw)
            return_dict.update({'activities_found':activities_found})               
            return_dict.update({'searchvalue':searchvalue})
        return return_dict
 
    def _systems(self, systems, *args, **kw):
        search_bar = SearchBar(name='systemsearch',
                               label=_(u'System Search'),
                               enable_custom_columns = True,
                               extra_selects = [ { 'name': 'keyvalue',
                                                   'column':'key/value',
                                                   'display':'none',
                                                   'pos' : 2,
                                                   'callback':url('/get_operators_keyvalue') }],
                               table=su.System.search.create_search_table(\
                                   [{su.System:{'all':[]}},
                                    {su.Cpu:{'all':[]}},
                                    {su.Device:{'all':[]}},
                                    {su.Key:{'all':[]}}]),
                               complete_data = su.System.search.create_complete_search_table(\
                                   [{su.System:{'all':[]}},
                                    {su.Cpu:{'all':[]}},
                                    {su.Device:{'all':[]}},
                                    {su.Key:{'all':[]}}]),
                               search_controller=url("/get_search_options"),
                               table_search_controllers = {'key/value':url('/get_keyvalue_search_options')},)

        if 'quick_search' in kw:
            table,op,value = kw['quick_search'].split('-')
            kw['systemsearch'] = [{'table' : table,
                                'operation' : op,
                                'keyvalue': None,
                                'value' : value}]
            simplesearch = kw['simplesearch']
        elif 'simplesearch' in kw:
            simplesearch = kw['simplesearch']
            kw['systemsearch'] = [{'table' : 'System/Name',   
                                   'operation' : 'contains',
                                   'keyvalue' : None,
                                   'value' : kw['simplesearch']}]
        else:
            simplesearch = None

        # Short cut search by type
        if 'type' in kw:
            kw['systemsearch'] = [{'table' : 'System/Type',
                                   'operation' : 'is',
                                   'value' : kw['type']}]      
            #when we do a short cut type search, result column args are not passed
            #we need to recreate them here from our cookies 
            if 'column_values' in request.simple_cookie: 
                text = request.simple_cookie['column_values'].value
                vals_to_set = text.split(',')
                for elem in vals_to_set:
                    kw['systemsearch_column_%s' % elem] = elem 
       
        default_result_columns = ('System/Name', 'System/Status', 'System/Vendor',
                                  'System/Model','System/Arch', 'System/User', 'System/Type') 

        if kw.get("systemsearch"):
            searchvalue = kw['systemsearch']
            sys_search = su.System.search(systems)
            columns = []
            for elem in kw:
                if re.match('systemsearch_column_',elem):
                    columns.append(kw[elem])
           
            if columns.__len__() == 0:  #If nothing is selected, let's give them the default    
                for elem in default_result_columns:
                    key = 'systemsearch_column_',elem
                    kw[key] = elem
                    columns.append(elem)

            use_custom_columns = False
            for column in columns:
                table,col = column.split('/')
                if sys_search.translate_name(table) is not su.System:
                    use_custom_columns = True     
                    break     

            sys_search.add_columns_desc(columns) 
            systems = self._system_search(kw,sys_search)

            (system_columns_desc,extra_columns_desc) = sys_search.get_column_descriptions()  
            if use_custom_columns is True:
                my_fields = Utility.custom_systems_grid(system_columns_desc,extra_columns_desc)
            else: 
                my_fields = Utility.custom_systems_grid(system_columns_desc)

            systems = systems.reset_joinpoint().outerjoin('user')\
                    .outerjoin('status').outerjoin('arch').outerjoin('type')\
                    .distinct()
        else: 
            systems = systems.reset_joinpoint().outerjoin('user')\
                    .outerjoin('status').outerjoin('arch').outerjoin('type')\
                    .distinct()
            use_custom_columns = False
            columns = None
            searchvalue = None
            my_fields = Utility.custom_systems_grid(default_result_columns)
        
        if 'direct_columns' in kw: #Let's add our direct columns here
            for index,col in kw['direct_columns']:
                my_fields.insert(index - 1, col)
                
        display_grid = myPaginateDataGrid(fields=my_fields)
        col_data = Utility.result_columns(columns)   
        #systems_count = len(systems)     
        return dict(title="Systems", grid = display_grid,
                                     list = systems, 
                                     object_count = systems.count(),
                                     searchvalue = searchvalue,                                    
                                     options =  {'simplesearch' : simplesearch,'columns':col_data,
                                                 'result_columns' : default_result_columns,
                                                 'col_defaults' : col_data['default'],
                                                 'col_options' : col_data['options']},
                                     action = '.', 
                                     search_bar = search_bar,
                                     atom_url='?tg_format=atom&list_tgp_order=-date_modified&'
                                        + cherrypy.request.query_string,
                                     )

    @expose(format='json')
    def by_fqdn(self, input):
        input = input.lower()
        search = System.list_by_fqdn(input,identity.current.user).all()
        matches =  [match.fqdn for match in search]
        return dict(matches = matches)

    @expose()
    @identity.require(identity.not_anonymous())
    def key_remove(self, system_id=None, key_type=None, key_value_id=None):
        removed = None
        if system_id and key_value_id and key_type:
            try:
                system = System.by_id(system_id,identity.current.user)
            except:
                flash(_(u"Invalid Permision"))
                redirect("/")
        else:
            flash(_(u"system_id, key_value_id and key_type must be provided"))
            redirect("/")
        
        if system.can_admin(identity.current.user):
            if key_type == 'int':
                key_values = system.key_values_int
            else:
                key_values = system.key_values_string
            for key_value in key_values:
                if key_value.id == int(key_value_id):
                    if key_type == 'int':
                        system.key_values_int.remove(key_value)
                    else:
                        system.key_values_string.remove(key_value)
                    removed = key_value
                    activity = SystemActivity(identity.current.user, 'WEBUI', 'Removed', 'Key/Value', "%s/%s" % (removed.key.key_name, removed.key_value), "")
                    system.activity.append(activity)
        
        if removed:
            system.date_modified = datetime.utcnow()
            flash(_(u"removed %s/%s" % (removed.key.key_name,removed.key_value)))
        else:
            flash(_(u"Key_Value_Id not Found"))
        redirect("./view/%s" % system.fqdn)

    @expose()
    @identity.require(identity.not_anonymous())
    def arch_remove(self, system_id=None, arch_id=None):
        removed = None
        if system_id and arch_id:
            try:
                system = System.by_id(system_id,identity.current.user)
            except:
                flash(_(u"Invalid Permision"))
                redirect("/")
        else:
            flash(_(u"system_id and arch_id must be provided"))
            redirect("/")
        if system.can_admin(identity.current.user):
           for arch in system.arch:
               if arch.id == int(arch_id):
                   system.arch.remove(arch)
                   removed = arch
                   activity = SystemActivity(identity.current.user, 'WEBUI', 'Removed', 'Arch', arch.arch, "")
                   system.activity.append(activity)
        if removed:
            system.date_modified = datetime.utcnow()
            flash(_(u"%s Removed" % removed.arch))
        else:
            flash(_(u"Arch ID not found"))
        redirect("./view/%s" % system.fqdn)

    @expose()
    @identity.require(identity.not_anonymous())
    def group_remove(self, system_id=None, group_id=None):
        removed = None
        if system_id and group_id:
            try:
                system = System.by_id(system_id,identity.current.user)
            except:
                flash(_(u"Invalid Permision"))
                redirect("/")
        else:
            flash(_(u"system_id and group_id must be provided"))
            redirect("/")
        if not identity.in_group("admin") and \
          system.shared and len(system.groups) == 1:
            flash(_(u"You don't have permission to remove the last group if the system is shared"))
            redirect("./view/%s" % system.fqdn)
        if system.can_admin(identity.current.user):
           for group in system.groups:
               if group.group_id == int(group_id):
                   system.groups.remove(group)
                   removed = group
                   activity = SystemActivity(identity.current.user, 'WEBUI', 'Removed', 'Group', group.display_name, "")
                   gactivity = GroupActivity(identity.current.user, 'WEBUI', 'Removed', 'System', "", system.fqdn)
                   group.activity.append(gactivity)
                   system.activity.append(activity)
        if removed:
            system.date_modified = datetime.utcnow()
            flash(_(u"%s Removed" % removed.display_name))
        else:
            flash(_(u"Group ID not found"))
        redirect("./view/%s" % system.fqdn)

    @expose(template="bkr.server.templates.system")
    @identity.require(identity.not_anonymous())
    def new(self):
        options = {}
        options['readonly'] = False
        return dict(
            title    = 'New System',
            form     = self.system_form,
            widgets  = {},
            action   = '/save',
            value    = None,
            options  = options)

    @expose(template="bkr.server.templates.form")
    def test(self, fqdn=None, **kw):
        try:
            system = System.by_fqdn(fqdn,identity.current.user)
        except InvalidRequestError:
            flash( _(u"Unable to find %s" % fqdn) )
            redirect("/")

        return dict(
            title   = "test",
            system  = system,
            form    = self.system_provision,
            action  = '/save',
            value   = system,
            options = dict(readonly = False,
                     lab_controller = system.lab_controller,
                     prov_install = [(distro.id, distro.install_name) for distro in system.distros()]))

    @expose(template="bkr.server.templates.system")
    @paginate('history_data',limit=30,default_order='-created', max_limit=None)
    def _view_system_as_html(self, fqdn=None, **kw):
        if fqdn: 
            try:
                system = System.by_fqdn(fqdn,identity.current.user)
            except InvalidRequestError:
                flash( _(u"Unable to find %s" % fqdn) )
                redirect("/")

            #Let's deal with a history search here
            histories_return = self.histories(SystemActivity.query().with_parent(system,"activity"), **kw) 
            history_options = {}
            if 'searchvalue' in histories_return:
                history_options['searchvalue'] = histories_return['searchvalue']
            if 'simplesearch' in histories_return:
                history_options['simplesearch'] = histories_return['simplesearch'] 
        elif kw.get('id'):
            try:
                system = System.by_id(kw['id'],identity.current.user)
            except InvalidRequestError:
                flash( _(u"Unable to find system with id of %s" % kw['id']) )
                redirect("/")
        else:
            system = None
        options = {}
        readonly = False
        is_user = False
        title = 'New'
        if system:
            title = system.fqdn
            our_user = identity.current.user #simple optimisation
            currently_held = system.user == our_user
            if system.can_admin(user=our_user): 
                options['owner_change_text'] = ' (Change)'
            else:
                readonly = True
            if system.can_loan(our_user):
                options['loan_text'] = ' (Loan)'
            if system.current_loan(our_user):
                options['loan_text'] = ' (Return)'
             
            if system.can_share(our_user) and system.can_provision_now(our_user): #Has privs and machine is available, can take
                options['user_change_text'] = ' (Take)'

            if system.current_user(our_user):
                options['user_change_text'] = ' (Return)'
                is_user = True

            self.provision_now_rights,self.will_provision,self.provision_action = \
                SystemTab.get_provision_perms(system, our_user, currently_held)

        if 'activities_found' in histories_return: 
            historical_data = histories_return['activities_found']
        else: 
            historical_data = system.activity[:150]
            
        if readonly:
            attrs = dict(readonly = 'True')
        else:
            attrs = dict()
        options['readonly'] = readonly

        options['reprovision_distro_id'] = [(distro.id, distro.install_name) for distro in system.distros()]
        #Excluded Family options
        options['excluded_families'] = []
        for arch in system.arch:
            options['excluded_families'].append((arch.arch, [(osmajor.id, osmajor.osmajor, [(osversion.id, '%s' % osversion, attrs) for osversion in osmajor.osversion],attrs) for osmajor in OSMajor.query()]))
        try:
            can_admin = system.can_admin(user = identity.current.user)
        except AttributeError,e:
            can_admin = False
        # If you have anything in your widgets 'javascript' variable,
        # do not return the widget here, the JS will not be loaded,
        # return it as an arg in return()
        widgets = dict( 
                        labinfo   = self.labinfo_form,
                        details   = self.system_details,
                        exclude   = self.system_exclude,
                        keys      = self.system_keys,
                        notes     = self.system_notes,
                        groups    = self.system_groups,
                        install   = self.system_installoptions,
                        arches    = self.arches_form 
                      )
        if system.type != SystemType.by_name(u'Virtual'):
            widgets['provision'] = self.system_provision
            widgets['power'] = self.power_form
            widgets['power_action'] = self.power_action_form

        return dict(
            title           = title,
            readonly        = readonly,
            is_user         = is_user,
            form            = self.system_form,
            action          = '/save',
            value           = system,
            options         = options,
            history_data    = historical_data,
            task_widget     = self.task_form,
            history_widget  = self.system_activity,
            widgets         = widgets,
            widgets_action  = dict( power     = '/save_power',
                                    history   = '/view/%s' % fqdn,
                                    labinfo   = '/save_labinfo',
                                    exclude   = '/save_exclude',
                                    keys      = '/save_keys',
                                    notes     = '/save_note',
                                    groups    = '/save_group',
                                    install   = '/save_install',
                                    provision = getattr(self,'provision_action',''),
                                    power_action = '/action_power',
                                    arches    = '/save_arch',
                                    tasks     = '/tasks/do_search',
                                  ),
            widgets_options = dict(power     = options,
                                   history   = history_options or {},
                                   labinfo   = options,
                                   exclude   = options,
                                   keys      = dict(readonly = readonly,
                                                key_values_int = system.key_values_int,
                                                key_values_string = system.key_values_string),
                                   notes     = dict(readonly = readonly,
                                                notes = system.notes),
                                   groups    = dict(readonly = readonly,
                                                groups = system.groups,
                                                system_id = system.id,
                                                can_admin = can_admin),
                                   install   = dict(readonly = readonly,
                                                provisions = system.provisions,
                                                prov_arch = [(arch.id, arch.arch) for arch in system.arch]),
                                   provision = dict(is_user = is_user,
                                                    will_provision = self.will_provision,
                                                    provision_now_rights = self.provision_now_rights,
                                                    lab_controller = system.lab_controller,
                                                    prov_install = [(distro.id, distro.install_name) for distro in system.distros().order_by(distro_table.c.install_name)]),
                                   power_action = dict(is_user=is_user),
                                   arches    = dict(readonly = readonly,
                                                    arches = system.arch),
                                   tasks      = dict(system_id = system.id,
                                                     arch = [(0, 'All')] + [(arch.id, arch.arch) for arch in system.arch],
                                                     hidden = dict(system = 1)),
                                  ),
        )
    _view_system_as_html.exposed = False # exposed indirectly by view()

    def _view_system_as_rdf(self, fqdn, **kwargs):
        try:
            system = System.by_fqdn(fqdn, identity.current.user)
        except InvalidRequestError:
            raise cherrypy.NotFound(fqdn)
        graph = rdflib.graph.Graph()
        bkr.server.rdf.describe_system(system, graph)
        bkr.server.rdf.bind_namespaces(graph)
        if kwargs['tg_format'] == 'turtle':
            cherrypy.response.headers['Content-Type'] = 'application/x-turtle'
            return graph.serialize(format='turtle')
        else:
            cherrypy.response.headers['Content-Type'] = 'application/rdf+xml'
            return graph.serialize(format='pretty-xml')

    @cherrypy.expose
    def view(self, fqdn=None, **kwargs):
        # XXX content negotiation too?
        tg_format = kwargs.get('tg_format', 'html')
        if tg_format in ('rdfxml', 'turtle'):
            return self._view_system_as_rdf(fqdn, **kwargs)
        else:
            return self._view_system_as_html(fqdn, **kwargs)
         
    @expose(template='bkr.server.templates.form')
    @identity.require(identity.not_anonymous())
    def loan_change(self, id):
        try:
            system = System.by_id(id,identity.current.user)
        except InvalidRequestError:
            flash( _(u"Unable to find system with id of %s" % id) )
            redirect("/")
        if system.loaned:
            if system.current_loan(identity.current.user):
                activity = SystemActivity(identity.current.user, 'WEBUI', 'Changed', 'Loaned To', '%s' % system.loaned, 'None')
                system.activity.append(activity)
                system.loaned = None
                flash( _(u"Loan Returned for %s" % system.fqdn) )
                redirect("/view/%s" % system.fqdn)
            else:
                flash( _(u"Insufficient permissions to return loan"))
                redirect("/")
        else:
            if not system.can_loan(identity.current.user):
                flash( _(u"Insufficient permissions to loan system"))
                redirect("/")
        return dict(
            title   = "Loan system %s" % system.fqdn,
            form = self.loan_form,
            action = '/save_loan',
            options = None,
            value = {'id': system.id},
        )

    @expose(template='bkr.server.templates.form')
    @identity.require(identity.not_anonymous())
    def owner_change(self, id):
        try:
            system = System.by_id(id,identity.current.user)
        except InvalidRequestError:
            flash( _(u"Unable to find system with id of %s" % id) )
            redirect("/")
        if not system.can_admin(identity.current.user):
            flash( _(u"Insufficient permissions to change owner"))
            redirect("/")

        return dict(
            title   = "Change Owner for %s" % system.fqdn,
            form = self.owner_form,
            action = '/save_owner',
            options = None,
            value = {'id': system.id},
        )
            
    @expose()
    @identity.require(identity.not_anonymous())
    def save_loan(self, id, *args, **kw):
        try:
            system = System.by_id(id,identity.current.user)
        except InvalidRequestError:
            flash( _(u"Unable to find system with id of %s" % id) )
            redirect("/")

        if not system.can_loan(identity.current.user):
            flash( _(u"Insufficient permissions to loan system"))
            redirect("/")
        user = User.by_user_name(kw['user']['text'])
        activity = SystemActivity(identity.current.user, 'WEBUI', 'Changed', 'Loaned To', 'None' , '%s' % user)
        system.activity.append(activity)
        system.loaned = user
        flash( _(u"%s Loaned to %s" % (system.fqdn, user) ))
        redirect("/view/%s" % system.fqdn)
    
    @expose()
    @identity.require(identity.not_anonymous())
    def save_owner(self, id, *args, **kw):
        try:
            system = System.by_id(id,identity.current.user)
        except InvalidRequestError:
            flash( _(u"Unable to find system with id of %s" % id) )
            redirect("/")
        if not system.can_admin(identity.current.user):
            flash( _(u"Insufficient permissions to change owner"))
            redirect("/")
        user = User.by_user_name(kw['user']['text'])
        activity = SystemActivity(identity.current.user, 'WEBUI', 'Changed', 'Owner', '%s' % system.owner, '%s' % user)
        system.activity.append(activity)
        system.owner = user
        system.date_modified = datetime.utcnow()
        flash( _(u"OK") )
        redirect("/")

    @expose()
    @identity.require(identity.not_anonymous())
    def user_change(self, id):
        msg = ""
        status = None
        activity = None
        try:
            system = System.by_id(id,identity.current.user)
        except InvalidRequestError:
            flash( _(u"Unable to find system with id of %s" % id) )
            redirect("/")
        if system.user:
            try:
                system.unreserve(service=u'WEBUI')
                flash(_(u'Returned %s') % system.fqdn)
            except BeakerException, e:
                log.exception('Failed to return')
                flash(_(u'Failed to return %s: %s') % (system.fqdn, e))
        else:
            try:
                system.reserve(service=u'WEBUI')
                flash(_(u'Reserved %s') % system.fqdn)
            except BeakerException, e:
                log.exception('Failed to reserve')
                flash(_(u'Failed to reserve %s: %s') % (system.fqdn, e))
        redirect("/view/%s" % system.fqdn)

    system_cc_form = widgets.TableForm(
        'cc',
        fields=[
            id,
            ExpandingForm(
                name='cc',
                label=_(u'Notify CC'),
                fields=[
                    widgets.TextField(name='email_address', label=_(u'E-mail address'),
                        validator=validators.Email()),
                ],
            ),
        ],
        submit_text=_(u'Change'),
    )

    @expose(template='bkr.server.templates.form-post')
    @identity.require(identity.not_anonymous())
    def cc_change(self, system_id):
        try:
            system = System.by_id(system_id, identity.current.user)
        except InvalidRequestError:
            flash(_(u'Unable to find system with id of %s' % system_id))
            redirect('/')
        if not system.can_admin(identity.current.user):
            flash(_(u'Insufficient permissions to edit CC list'))
            redirect('/')
        return dict(
            title=_(u'Notify CC list for %s') % system.fqdn,
            form=self.system_cc_form,
            action='save_cc',
            options=None,
            value={'id': system.id, 'cc': system._system_ccs},
        )

    @error_handler(cc_change)
    @expose()
    @identity.require(identity.not_anonymous())
    @validate(form=system_cc_form)
    def save_cc(self, id, cc):
        try:
            system = System.by_id(id, identity.current.user)
        except InvalidRequestError:
            flash(_(u'Unable to find system with id of %s' % id))
            redirect('/')
        if not system.can_admin(identity.current.user):
            flash(_(u'Insufficient permissions to edit CC list'))
            redirect('/')
        orig_value = list(system.cc)
        new_value = [item['email_address']
                for item in cc if item['email_address']]
        system.cc = new_value
        system.activity.append(SystemActivity(user=identity.current.user,
                service=u'WEBUI', action=u'Changed', field_name=u'Cc',
                old_value=u'; '.join(orig_value),
                new_value=u'; '.join(new_value)))
        system.date_modified = datetime.utcnow()
        flash(_(u'Notify CC list for system %s changed') % system.fqdn)
        redirect('/view/%s' % system.fqdn)

    @error_handler(view)
    @expose()
    @identity.require(identity.not_anonymous())
    @validate(form=labinfo_form)
    def save_labinfo(self, **kw):
        try:
            system = System.by_id(kw['id'],identity.current.user)
        except InvalidRequestError:
            flash( _(u"Unable to save Lab Info for %s" % kw['id']) )
            redirect("/")
        if system.labinfo:
            labinfo = system.labinfo
        else:
            labinfo = LabInfo()

        for field in LabInfo.fields:
            if kw.get(field):
                orig_value = getattr(labinfo, field)
                # Convert to Decimal for Comparisons.
                if type(orig_value) == Decimal:
                    new_value = Decimal('%s' % kw[field])
                else:
                    new_value = kw[field]
                if new_value != orig_value:
                    activity = SystemActivity(identity.current.user, 'WEBUI', 'Changed', field, '%s' % orig_value, kw[field] )
                    setattr(labinfo, field, kw[field])
                    system.activity.append(activity) 
        system.labinfo = labinfo
        system.date_modified = datetime.utcnow()
        flash( _(u"Saved Lab Info") )
        redirect("/view/%s" % system.fqdn)

    @error_handler(view)
    @expose()
    @identity.require(identity.not_anonymous())
    def save_power(self, 
                   id,
                   power_address,
                   power_type_id,
                   release_action_id,
                   **kw):
        try:
            system = System.by_id(id,identity.current.user)
        except InvalidRequestError:
            flash( _(u"Unable to save Power for %s" % id) )
            redirect("/")

        if kw.get('reprovision_distro_id'):
            try:
                reprovision_distro = Distro.by_id(kw['reprovision_distro_id'])
            except InvalidRequestError:
                reprovision_distro = None
            if system.reprovision_distro and \
              system.reprovision_distro != reprovision_distro:
                system.activity.append(SystemActivity(identity.current.user, 'WEBUI', 'Changed', 'reprovision_distro', '%s' % system.reprovision_distro, '%s' % reprovision_distro ))
                system.reprovision_distro = reprovision_distro
            else:
                system.activity.append(SystemActivity(identity.current.user, 'WEBUI', 'Changed', 'reprovision_distro', '%s' % system.reprovision_distro, '%s' % reprovision_distro ))
                system.reprovision_distro = reprovision_distro

        try:
            release_action = ReleaseAction.by_id(release_action_id)
        except InvalidRequestError:
            release_action = None
        if system.release_action and system.release_action != release_action:
            system.activity.append(SystemActivity(identity.current.user, 'WEBUI', 'Changed', 'release_action', '%s' % system.release_action, '%s' % release_action ))
            system.release_action = release_action
        else:
            system.activity.append(SystemActivity(identity.current.user, 'WEBUI', 'Changed', 'release_action', '%s' % system.release_action, '%s' % release_action ))
            system.release_action = release_action
            
        if system.power:
            if power_address != system.power.power_address:
                #Power Address Changed
                activity = SystemActivity(identity.current.user, 'WEBUI', 'Changed', 'power_address', system.power.power_address, power_address )
                system.power.power_address = power_address
                system.activity.append(activity)
            if kw.get('power_user'):
                if kw['power_user'] != system.power.power_user:
                    #Power User Changed
                    activity = SystemActivity(identity.current.user, 'WEBUI', 'Changed', 'power_user', '********', '********' )
                    system.power.power_user = kw['power_user']
                    system.activity.append(activity)
            else:
                activity = SystemActivity(identity.current.user, 'WEBUI', 'Removed', 'power_user', '********', '********' )
                system.activity.append(activity)
                system.power.power_user = None
            if kw.get('power_passwd'):
                if kw['power_passwd'] != system.power.power_passwd:
                    #Power Passwd Changed
                    activity = SystemActivity(identity.current.user, 'WEBUI', 'Changed', 'power_passwd', '********', '********' )
                    system.power.power_passwd = kw['power_passwd']
                    system.activity.append(activity)
            else:
                activity = SystemActivity(identity.current.user, 'WEBUI', 'Removed', 'power_passwd', '********', '********' )
                system.activity.append(activity)
                system.power.power_passwd = None
            if kw.get('power_id'):
                if kw['power_id'] != system.power.power_id:
                    #Power ID Changed
                    activity = SystemActivity(identity.current.user, 'WEBUI', 'Changed', 'power_id', system.power.power_id, kw['power_id'] )
                    system.power.power_id = kw['power_id']
                    system.activity.append(activity)
            else:
                activity = SystemActivity(identity.current.user, 'WEBUI', 'Removed', 'power_id', system.power.power_id, '' )
                system.activity.append(activity)
                system.power.power_id = None
            if power_type_id != system.power.power_type_id:
                #Power Type Changed
                if int(power_type_id) == 0:
                    system.power = None
                else:
                    try:
                        power_type = PowerType.by_id(power_type_id)
                    except InvalidRequestError:
                        flash( _(u"Invalid power type %s" % power_type_id) )
                        redirect("/view/%s" % system.fqdn)
                    activity = SystemActivity(identity.current.user, 'WEBUI', 'Changed', 'power_type', system.power.power_type.name, power_type.name )
                    system.power.power_type = power_type
                    system.activity.append(activity)
            flash( _(u"Updated Power") )
        else:
            try:
                power_type = PowerType.by_id(power_type_id)
            except InvalidRequestError:
                flash( _(u"Invalid power type %s" % power_type_id) )
                redirect("/view/%s" % system.fqdn)
            power = Power(power_type=power_type, power_address=power_address)
            if kw.get('power_user'):
                power.power_user = kw['power_user']
            if kw.get('power_passwd'):
                power.power_passwd = kw['power_passwd']
            if kw.get('power_id'):
                power.power_id = kw['power_id']
            system.power = power
            flash( _(u"Saved Power") )
        system.date_modified = datetime.utcnow()
        redirect("/view/%s" % system.fqdn)

    @expose()
    @validate(form=system_form)
    @identity.require(identity.not_anonymous())
    @error_handler(new)
    def save(self, **kw):
        if kw.get('id'):
            try:
                query = System.query().filter(System.fqdn ==kw['fqdn'])
                for sys_object in query:
                    if str(sys_object.id) != str(kw['id']):
                        flash( _(u"%s already exists!" % kw['fqdn']))
                        redirect("/") 
                system = System.by_id(kw['id'],identity.current.user)
            except InvalidRequestError:
                flash( _(u"Unable to save %s" % kw['id']) )
                redirect("/")
           
        else:
            if System.query().filter(System.fqdn == kw['fqdn']).count() != 0:   
                flash( _(u"%s already exists!" % kw['fqdn']) )
                redirect("/")
            system = System(fqdn=kw['fqdn'],owner=identity.current.user)
# TODO what happens if you log changes here but there is an issue and the actual change to the system fails?
#      would be good to have the save wait until the system is updated
# TODO log  group +/-
        # Fields missing from kw have been set to NULL
        # We want to store the logged info in a somewhat verbose manner, so if the column is in fact a FK to another table, put it in a fk_log_entry obj
        status_entry = SystemSaveForm.fk_log_entry(form_field='status_id', mapper_class=SystemStatus, mapper_column_name='status', description='Status')
        lab_controller_entry = SystemSaveForm.fk_log_entry(form_field='lab_controller_id', mapper_class=LabController, mapper_column_name='fqdn', description='LabController') 
        type_entry = SystemSaveForm.fk_log_entry(form_field='type_id', mapper_class=SystemType, mapper_column_name='type',description='Type')


        log_fields = [ 'fqdn', 'vendor', 'lender', 'model', 'serial', 'location', 
                       'mac_address', 'status_reason', status_entry,lab_controller_entry,type_entry]

        for field in log_fields:
            if isinstance(field,SystemSaveForm.fk_log_entry): #check if we are a foreign key with mapper object and column name           
                fk_log_entry_obj = field
                field = fk_log_entry_obj.form_field
                mapper_class = fk_log_entry_obj.mapper_class
                col_name = fk_log_entry_obj.mapper_column_name
                description = fk_log_entry_obj.description 
                       
            try:
                current_val = getattr(system,field)
            except AttributeError:
                flash(_(u'Field %s is not a valid system property' % field)) 
                continue

            new_val = kw.get(field)
             
            if unicode(current_val) != unicode(new_val): 
                function_name = '%s_change_handler' % field
                field_change_handler = getattr(SystemSaveForm.handler,function_name,None)
                if field_change_handler is not None:
                    kw = field_change_handler(current_val,new_val,**kw)

                #The following try/except block trys to set the actual old/new values for the fields we are changing
                # It tests for current and new values that are 'None' (i.e Changing from a valid lab controller to no lab controller)
                # Except will trigger if the mapper_class has not been declared (i.e we are not a tuple), or if our mapper_column_name was invalid
                # and will log a warning msg
                try:
                    if current_val: 
                        current_sqla_obj = mapper_class.by_id(current_val)
                        current_val = getattr(current_sqla_obj,col_name)
                    if new_val: 
                        new_sqla_obj = mapper_class.by_id(new_val)
                        new_val = getattr(new_sqla_obj,col_name)

                    field = description
                except AttributeError,e:
                    log.error(e)
                    warn_msg =  "There was a problem logging the new value for %s" % (description)          
                    try:
                        unloggable_warn += "\n%s" % warn_msg
                    except UnboundLocalError,e:
                        unloggable_warn = warn_msg
                    continue
                except UnboundLocalError, e: pass # We probably weren't a fk_log_entry object
                   
                
                activity = SystemActivity(identity.current.user, 'WEBUI', 'Changed', field, current_val, new_val)
                system.activity.append(activity)
        
        try: 
            flash(unloggable_warn)
        except UnboundLocalError,e: pass
        # We only want admins to be able to share systems to everyone.
        shared = kw.get('shared',False)
        if shared != system.shared:
            if not identity.in_group("admin") and \
              shared and len(system.groups) == 0:
                flash( _(u"You don't have permission to share without the system being in a group first " ) )
                redirect("/view/%s" % system.fqdn)
            current_val = str(system.shared and True or False) #give us the text 'True' or 'False'
            new_val = str(shared and True) #give us the text 'True' or 'False'
            activity = SystemActivity(identity.current.user, 'WEBUI', 'Changed', 'shared', current_val, new_val )
            system.activity.append(activity)
            system.shared = shared
                
        log_bool_fields = [ 'private' ]
        for field in log_bool_fields:
            try:
                current_val = str(getattr(system,field) and True or False)
            except KeyError:
                current_val = ""
            new_val = str(kw.get(field) or False)
            if str(current_val) != new_val:
                activity = SystemActivity(identity.current.user, 'WEBUI', 'Changed', field, current_val, new_val )
                system.activity.append(activity)
        system.status_id=kw['status_id']
        system.location=kw['location']
        system.model=kw['model']
        system.type_id=kw['type_id']
        system.serial=kw['serial']
        system.vendor=kw['vendor']
        system.lender=kw['lender']
        system.fqdn=kw['fqdn']
        system.status_reason = kw['status_reason']
        system.date_modified = datetime.utcnow()
        if kw.get('private'):
            system.private=kw['private']
        else:
            system.private=False

        # Change Lab Controller
        if kw['lab_controller_id'] == 0:
            system.lab_controller_id = None
        else:
            system.lab_controller_id = kw['lab_controller_id']
        system.mac_address=kw['mac_address']

        # We can't compute a new checksum, so let's just clear it so that it 
        # always compares false
        if system.checksum is not None:
            system.activity.append(SystemActivity(user=identity.current.user,
                    service=u'WEBUI', action=u'Changed', field_name=u'checksum',
                    old_value=system.checksum, new_value=None))
            system.checksum = None

        session.save_or_update(system)
        redirect("/view/%s" % system.fqdn)

    @expose()
    @identity.require(identity.not_anonymous())
    def save_keys(self, id, **kw):
        try:
            system = System.by_id(id,identity.current.user)
        except InvalidRequestError:
            flash( _(u"Unable to Add Key for %s" % id) )
            redirect("/")
        # Add a Key/Value Pair
        if kw.get('key_name') and kw.get('key_value'):
            try:
                key = Key.by_name(kw['key_name'])
            except InvalidRequestError:
                #FIXME allow user to create new keys
                flash(_(u"Invalid key %s" % kw['key_name']))
                redirect("/view/%s" % system.fqdn)
            if key.numeric:
                key_value = Key_Value_Int(key,kw['key_value'])
                system.key_values_int.append(key_value)
            else:
                key_value = Key_Value_String(key,kw['key_value'])
                system.key_values_string.append(key_value)
            activity = SystemActivity(identity.current.user, 'WEBUI', 'Added', 'Key/Value', "", "%s/%s" % (kw['key_name'],kw['key_value']) )
            system.activity.append(activity)
            system.date_modified = datetime.utcnow()
        redirect("/view/%s" % system.fqdn)

    @expose()
    @identity.require(identity.not_anonymous())
    def save_arch(self, id, **kw):
        try:
            system = System.by_id(id,identity.current.user)
        except InvalidRequestError:
            flash( _(u"Unable to Add arch for %s" % id) )
            redirect("/")
        # Add an Arch
        if kw.get('arch').get('text'):
            arch = Arch.by_name(kw['arch']['text'])
            system.arch.append(arch)
            activity = SystemActivity(identity.current.user, 'WEBUI', 'Added', 'Arch', "", kw['arch']['text'])
            system.activity.append(activity)
            system.date_modified = datetime.utcnow()
        redirect("/view/%s" % system.fqdn)

    @expose()
    @identity.require(identity.not_anonymous())
    def save_group(self, id, **kw):
        try:
            system = System.by_id(id,identity.current.user)
        except InvalidRequestError:
            flash( _(u"Unable to Add Group for %s" % id) )
            redirect("/")
        # Add a Group
        if kw.get('group').get('text'):
            try:
                group = Group.by_name(kw['group']['text'])
            except InvalidRequestError:
                flash(_(u"%s is an Invalid Group" % kw['group']['text']))
                redirect("/view/%s" % system.fqdn)
            system.groups.append(group)
            activity = SystemActivity(identity.current.user, 'WEBUI', 'Added', 'Group', "", kw['group']['text'])
            gactivity = GroupActivity(identity.current.user, 'WEBUI', 'Added', 'System', "", system.fqdn)
            group.activity.append(gactivity)
            system.activity.append(activity)
            system.date_modified = datetime.utcnow()
        redirect("/view/%s" % system.fqdn)

    @expose()
    @identity.require(identity.not_anonymous())
    def action_power(self, id, action, **kw):
        try:
            system = System.by_id(id,identity.current.user)
        except InvalidRequestError:
            flash( _(u"Unable to look up system id:%s via your login" % id) )
            redirect("/")
        try:
            system.action_power(action)
        except xmlrpclib.Fault, msg:
            flash(_(u"Failed to %s %s, XMLRPC error: %s" % (action, system.fqdn, msg)))
            activity = SystemActivity(identity.current.user, 'WEBUI', action, 'Power', "", "%s" % msg)
            system.activity.append(activity)
            redirect("/view/%s" % system.fqdn)
        except BX, msg:
            flash(_(u"Failed to %s %s, error: %s" % (action, system.fqdn, msg)))
            activity = SystemActivity(identity.current.user, 'WEBUI', action, 'Power', "", "%s" % msg)
            system.activity.append(activity)
            redirect("/view/%s" % system.fqdn)

        activity = SystemActivity(identity.current.user, 'WEBUI', action, 'Power', "", "Success")
        system.activity.append(activity)
        flash(_(u"%s %s" % (system.fqdn, action)))
        redirect("/view/%s" % system.fqdn)

    @expose()
    @identity.require(identity.not_anonymous())
    def schedule_provision(self,id, prov_install=None, ks_meta=None, koptions=None, koptions_post=None, reserve_days=None, **kw):
        distro_id = prov_install
        try:
            user = identity.current.user
            system = System.by_id(id,user)
        except InvalidRequestError:
            flash( _(u"Unable to save scheduled provision for %s" % id) )
            redirect("/")
        try:
            distro = Distro.by_id(distro_id)
        except InvalidRequestError:
            flash( _(u"Unable to lookup distro for %s" % id) )
            redirect(u"/view/%s" % system.fqdn)
    
        reserve_days = int(reserve_days)
        if reserve_days is None:#This should not happen
            log.debug('reserve_days has not been set in provision page, using default')
            reserve_days = SystemProvision.DEFAULT_RESERVE_DAYS
        else: 
            if reserve_days > SystemProvision.MAX_DAYS_PROVISION: #Someone is trying to cheat
                log.debug('User has tried to set provision to %s days, which is more than the allowable %s days' % (reserve_days,SystemProvision.DEFAULT_RESERVE_DAYS))
                reserve_days = SystemProvision.DEFAULT_RESERVE_DAYS

        reserve_time =  ((reserve_days * 24) * 60) * 60    
        job_details = dict(whiteboard = 'Provision %s' % distro.name,
                            distro_id = distro_id,
                            system_id = id,
                            ks_meta = ks_meta,
                            koptions = koptions,
                            koptions_post = koptions_post,
                            reservetime = reserve_time)

        try:                               
            provision_system_job = Job.provision_system_job(**job_details)
        except BX, msg:
            flash(_(u"%s" % msg))
            redirect(u"/view/%s" % system.fqdn)

        self.jobs.success_redirect(provision_system_job.id)
    
    @expose()
    @identity.require(identity.not_anonymous())
    def action_provision(self, id, prov_install=None, ks_meta=None, 
                             koptions=None, koptions_post=None, reboot=None):

        """
        We schedule a job which will provision a system. 

        """
        distro_id = prov_install
        try:
            user = identity.current.user
            system = System.by_id(id,user)
        except InvalidRequestError:
            flash( _(u"Unable to save scheduled provision for %s" % id) )
            redirect("/")
        try:
            distro = Distro.by_id(distro_id)
        except InvalidRequestError:
            flash( _(u"Unable to lookup distro for %s" % id) )
            redirect(u"/view/%s" % system.fqdn)
         
        try:
            can_provision_now = system.can_provision_now(user) #Check perms
            if can_provision_now:
                system.action_provision(distro = distro,
                                        ks_meta = ks_meta,
                                        kernel_options = koptions,
                                        kernel_options_post = koptions_post)
            else: #This shouldn't happen, maybe someone is trying to be funny
                raise BX('User: %s has insufficent permissions to provision %s' % (user.user_name, system.fqdn))
        except BX, msg: 
            activity = SystemActivity(identity.current.user, 'WEBUI', 'Provision', 'Distro', "", "%s: %s" % (msg, distro.install_name))
            system.activity.append(activity)
            flash(_(u"%s" % msg))
            redirect("/view/%s" % system.fqdn)

        activity = SystemActivity(identity.current.user, 'WEBUI', 'Provision', 'Distro', "", "Success: %s" % distro.install_name)
        system.activity.append(activity)

        if reboot:
            try:
                system.remote.power(action="reboot")
            except BX, msg:
                activity = SystemActivity(identity.current.user, 'WEBUI', 'Reboot', 'Power', "", "%s" % msg)
                system.activity.append(activity)
                flash(_(u"%s" % msg))
                redirect("/view/%s" % system.fqdn)

        activity = SystemActivity(identity.current.user, 'WEBUI', 'Reboot', 'Power', "", "Success")
        system.activity.append(activity)
        flash(_(u"Successfully Provisioned %s with %s" % (system.fqdn,distro.install_name)))
        redirect("/view/%s" % system.fqdn)

    @expose()
    @identity.require(identity.not_anonymous())
    def save_note(self, id, **kw):
        try:
            system = System.by_id(id,identity.current.user)
        except InvalidRequestError:
            flash( _(u"Unable to save Note for %s" % id) )
            redirect("/")
        # Add a Note
        if kw.get('note'):
            note = Note(user=identity.current.user,text=kw['note'])
            system.notes.append(note)
            activity = SystemActivity(identity.current.user, 'WEBUI', 'Added', 'Note', "", kw['note'])
            system.activity.append(activity)
            system.date_modified = datetime.utcnow()
        redirect("/view/%s" % system.fqdn)

    @expose()
    @identity.require(identity.not_anonymous())
    def save_exclude(self, id, **kw):
        try:
            system = System.by_id(id,identity.current.user)
        except InvalidRequestError:
            flash( _(u"Unable to save Exclude flags for %s" % id) )
            redirect("/")
        for arch in system.arch:
        # Update Excluded Families
            if kw.get('excluded_families') and \
             kw['excluded_families'].has_key(arch.arch):
                if isinstance(kw['excluded_families'][arch.arch], list):
                    excluded_osmajor = [int(i) for i in kw['excluded_families'][arch.arch]]
                else:
                    excluded_osmajor = [int(kw['excluded_families'][arch.arch])]
                for new_families in excluded_osmajor:
                    if new_families not in [osmajor.osmajor.id for osmajor in system.excluded_osmajor_byarch(arch)]:
                        new_excluded_osmajor = ExcludeOSMajor(osmajor=OSMajor.by_id(new_families),arch=arch)
                        activity = SystemActivity(identity.current.user, 'WEBUI', 'Added', 'Excluded_families', "", "%s/%s" % (new_excluded_osmajor.osmajor, arch))
                        system.excluded_osmajor.append(new_excluded_osmajor)
                        system.activity.append(activity)
            else:
                excluded_osmajor = []
            for old_families in system.excluded_osmajor_byarch(arch):
                if old_families.osmajor.id not in excluded_osmajor:
                    activity = SystemActivity(identity.current.user, 'WEBUI', 'Removed', 'Excluded_families', "%s/%s" % (old_families.osmajor, arch), "")
                    session.delete(old_families)
                    system.activity.append(activity)
                    
            if kw.get('excluded_families_subsection') and \
             kw['excluded_families_subsection'].has_key(arch.arch):
                if isinstance(kw['excluded_families_subsection'][arch.arch], list):
                    excluded_osversion = [int(i) for i in kw['excluded_families_subsection'][arch.arch]]
                else:
                    excluded_osversion = [int(kw['excluded_families_subsection'][arch.arch])]
                for new_osversion in excluded_osversion:
                    if new_osversion not in [osversion.osversion.id for osversion in system.excluded_osversion_byarch(arch)]:
                        new_excluded_osversion = ExcludeOSVersion(osversion=OSVersion.by_id(new_osversion),arch=arch)
                        activity = SystemActivity(identity.current.user, 'WEBUI', 'Added', 'Excluded_families', "", "%s/%s" % (new_excluded_osversion.osversion, arch))
                        system.excluded_osversion.append(new_excluded_osversion)
                        system.activity.append(activity)
            else:
                excluded_osversion = []
            for old_osversion in system.excluded_osversion_byarch(arch):
                if old_osversion.osversion.id not in excluded_osversion:
                    activity = SystemActivity(identity.current.user, 'WEBUI', 'Removed', 'Excluded_families', "%s/%s" % (old_osversion.osversion, arch), "")
                    session.delete(old_osversion)
                    system.activity.append(activity)
        redirect("/view/%s" % system.fqdn)

    @expose()
    @identity.require(identity.not_anonymous())
    def remove_install(self, system_id, arch_id, **kw):
        try:
            system = System.by_id(system_id, identity.current.user)
        except InvalidRequestError:
            flash( _(u"Unable to remove Install Option for %s" % system_id) )
            redirect("/")
        try:
            arch = Arch.by_id(arch_id)
        except InvalidRequestError:
            flash( _(u"Unable to lookup arch for %s" % arch_id) )
            redirect("/")
        
        if kw.get('osversion_id'):
            # remove osversion option
            osversion = OSVersion.by_id(int(kw['osversion_id']))
            system.provisions[arch].provision_families[osversion.osmajor].provision_family_updates[osversion] = None
        elif kw.get('osmajor_id'):
            # remove osmajor option
            osmajor = OSMajor.by_id(int(kw['osmajor_id']))
            system.provisions[arch].provision_families[osmajor] = None
        else:
            # remove arch option
            system.provisions[arch] = None
        system.date_modified = datetime.utcnow()
        redirect("/view/%s" % system.fqdn)

    @expose()
    def search_history(self):
        pass

    @expose()
    @identity.require(identity.not_anonymous())
    def save_install(self, id, **kw):
        try:
            system = System.by_id(id,identity.current.user)
        except InvalidRequestError:
            flash( _(u"Unable to save Install Options for %s" % id) )
            redirect("/")
        # Add an install option
        if kw.get('prov_ksmeta') or kw.get('prov_koptions') or \
           kw.get('prov_koptionspost'):
            arch = Arch.by_id(int(kw['prov_arch']))
            if int(kw['prov_osversion']) != 0:
                osversion = OSVersion.by_id(int(kw['prov_osversion']))
                if system.provisions.has_key(arch):
                    if system.provisions[arch].provision_families.has_key(osversion.osmajor):
                        if system.provisions[arch].provision_families[osversion.osmajor].provision_family_updates.has_key(osversion):
                            provision = system.provisions[arch].provision_families[osmajor].provision_family_updates[osversion]
                            action = "Changed"
                        else:
                            provision = ProvisionFamilyUpdate()
                            action = "Added"
                        system.activity.append(SystemActivity(identity.current.user, 'WEBUI', action, 'InstallOption:ks_meta:%s/%s' % (arch, osversion), provision.ks_meta, kw['prov_ksmeta']))
                        system.activity.append(SystemActivity(identity.current.user, 'WEBUI', action, 'InstallOption:kernel_options:%s/%s' % (arch, osversion), provision.kernel_options, kw['prov_koptions']))
                        system.activity.append(SystemActivity(identity.current.user, 'WEBUI', action, 'InstallOption:kernel_options_post:%s/%s' % (arch, osversion), provision.kernel_options_post, kw['prov_koptionspost']))
                        provision.ks_meta=kw['prov_ksmeta']
                        provision.kernel_options=kw['prov_koptions']
                        provision.kernel_options_post=kw['prov_koptionspost']
                        provision.osversion = osversion
                        system.provisions[arch].provision_families[osversion.osmajor].provision_family_updates[osversion] = provision
                
            elif int(kw['prov_osmajor']) != 0:
                osmajor = OSMajor.by_id(int(kw['prov_osmajor']))
                if system.provisions.has_key(arch):
                    if system.provisions[arch].provision_families.has_key(osmajor):
                        provision = system.provisions[arch].provision_families[osmajor]
                        action = "Changed"
                    else:
                        provision = ProvisionFamily()
                        action = "Added"
                    system.activity.append(SystemActivity(identity.current.user, 'WEBUI', action, 'InstallOption:ks_meta:%s/%s' % (arch, osmajor), provision.ks_meta, kw['prov_ksmeta']))
                    system.activity.append(SystemActivity(identity.current.user, 'WEBUI', action, 'InstallOption:kernel_options:%s/%s' % (arch, osmajor), provision.kernel_options, kw['prov_koptions']))
                    system.activity.append(SystemActivity(identity.current.user, 'WEBUI', action, 'InstallOption:kernel_options_post:%s/%s' % (arch, osmajor), provision.kernel_options_post, kw['prov_koptionspost']))
                    provision.ks_meta=kw['prov_ksmeta']
                    provision.kernel_options=kw['prov_koptions']
                    provision.kernel_options_post=kw['prov_koptionspost']
                    provision.osmajor=osmajor
                    system.provisions[arch].provision_families[osmajor] = provision
            else:
                if system.provisions.has_key(arch):
                    provision = system.provisions[arch]
                    action = "Changed"
                else:
                    provision = Provision()
                    action = "Added"
                system.activity.append(SystemActivity(identity.current.user, 'WEBUI', action, 'InstallOption:ks_meta:%s' % arch, provision.ks_meta, kw['prov_ksmeta']))
                system.activity.append(SystemActivity(identity.current.user, 'WEBUI', action, 'InstallOption:kernel_options:%s' % arch, provision.kernel_options, kw['prov_koptions']))
                system.activity.append(SystemActivity(identity.current.user, 'WEBUI', action, 'InstallOption:kernel_options_post:%s' % arch, provision.kernel_options_post, kw['prov_koptionspost']))
                provision.ks_meta=kw['prov_ksmeta']
                provision.kernel_options=kw['prov_koptions']
                provision.kernel_options_post=kw['prov_koptionspost']
                provision.arch=arch
                system.provisions[arch] = provision
            system.date_modified = datetime.utcnow()
        redirect("/view/%s" % system.fqdn)

    @cherrypy.expose
    # Testing auth via xmlrpc
    #@identity.require(identity.in_group("admin"))
    def lab_controllers(self, *args):
        return [lc.fqdn for lc in LabController.query()]
    
    def pick_common(self, distro=None, user=None, xml=None):
        distro = Distro.by_install_name(distro)
        systems = distro.systems(user)
        #FIXME Should validate XML before processing.
        queries = []
        joins = []
        for child in ElementWrapper(xmltramp.parse(xml)):
            if callable(getattr(child, 'filter')):
                (join, query) = child.filter()
                queries.append(query)
                joins.extend(join)
        if joins:
            systems = systems.filter(and_(*joins))
        if queries:
            systems = systems.filter(and_(*queries))
        return systems
        
    @cherrypy.expose
    def system_pick(self, distro=None, username=None, xml=None):
        if not distro:
            return (None,"You must supply a distro")
        if not username:
            return (None,"You must supply a user name")
        if not xml:
            return (None,"No xml query provided")

        user = None
        try:
            # some systems use Bugzilla as auth.
            # This is only temporary and will go away.
            user = User.by_email_address(username)
        except InvalidRequestError:
            username = username.split('@')[0]
            user = User.by_user_name(username)
        if not user:
            return (None, -1)
        systems = self.pick_common(distro, user, xml)

        hit = False
        systems_list = systems.all()
        size = len(systems_list)
        while size:
            size = size - 1
            index = random.randint(0, size)
            system = systems_list[index]
            systems_list[index] = systems_list[size]
   
            # If the system doesn't have a current user then take it
            if session.connection(System).execute(system_table.update(
                     and_(system_table.c.id==system.id,
                          system_table.c.user_id==None)), 
                           user_id=user.user_id).rowcount == 1:
                hit = True
                break

        if hit:
            # We have a match and its available!
            return (dict(fqdn    = system.fqdn,
                         mac_address = '%s' % system.mac_address), 1)
        elif systems.count():
            # We have matches but none are available right now
            system = systems.first()
            return (dict(fqdn    = system.fqdn,
                         mac_address = '%s' % system.mac_address), 0)
        else:
            # Nothing matches what the user requested.
            return (None, -1)

    @cherrypy.expose
    def system_validate(self, distro=None, username=None, xml=None):
        if not distro:
            return (None,"You must supply a distro")
        if not username:
            return (None,"You must supply a user name")
        if not xml:
            return (None,"No xml query provided")

        user = None
        try:
            # some systems use Bugzilla as auth.
            # This is only temporary and will go away.
            user = User.by_email_address(username)
        except InvalidRequestError:
            username = username.split('@')[0]
            user = User.by_user_name(username)
        if not user:
            return (None, -1)
        systems = self.pick_common(distro, user, xml)

        if systems.count():
            # We have matches 
            system = systems.first()
            return (dict(fqdn    = system.fqdn,
                         mac_address = '%s' % system.mac_address), 0)
        else:
            # Nothing matches what the user requested.
            return (None, -1)
            
    @cherrypy.expose
    def system_return(self, fqdn=None, full_name=None, mylog=True):
        if not fqdn:
            return (0,"You must supply a system")
        if not full_name:
            return (0,"You must supply a user name")

        user = None
        try:
            # some systems use Bugzilla as auth.
            # This is only temporary and will go away.
            user = User.by_email_address(full_name)
        except InvalidRequestError:
            full_name = full_name.split('@')[0]
            user = User.by_user_name(full_name)
        try:
            system = System.by_fqdn(fqdn,user)
        except InvalidRequestError:
            return (0, "Invalid system")
        if system.user == user:
            if mylog:
                system.activity.append(SystemActivity(system.user, "VIA %s" % identity.current.user, "Returned", "User", "%s" % system.user, ''))
                try:
                    system.action_release()
                except BX, error:
                    msg = "Failed to power off system: %s" % error
                    system.activity.append(SystemActivity(system.user, "VIA %s" % identity.current.user, "Off", "Power", "", msg))
            else:
                system.user = None
        return
        

    @cherrypy.expose
    def legacypush(self, fqdn=None, inventory=None):
        if not fqdn:
            return (0,"You must supply a FQDN")
        if not inventory:
            return (0,"No inventory data provided")

        try:
            system = System.query.filter(System.fqdn == fqdn).one()
        except InvalidRequestError:
            system = System(fqdn=fqdn)
        return system.update_legacy(inventory)

    @cherrypy.expose
    def push(self, fqdn=None, inventory=None):
        if not fqdn:
            return (0,"You must supply a FQDN")
        if not inventory:
            return (0,"No inventory data provided")
        try:
            system = System.query.filter(System.fqdn == fqdn).one()
        except InvalidRequestError:
            # New system, add it.
            system = System(fqdn=fqdn)
        return system.update(inventory)

    @expose(template="bkr.server.templates.login")
    def login(self, forward_url='/', **kwargs):
        if not identity.current.anonymous \
                and identity.was_login_attempted() \
                and not identity.get_identity_errors():
            redirect(forward_url, redirect_params=kwargs)

        if identity.was_login_attempted():
            msg=_("The credentials you supplied were not correct or "
                   "did not grant access to this resource.")
        elif identity.get_identity_errors():
            msg=_("You must provide your credentials before accessing "
                   "this resource.")
        else:
            msg=_("Please log in.")
            
        response.status=403
        return dict(message=msg, action=request.path, logging_in=True,
                    original_parameters=kwargs, forward_url=forward_url)

    @expose()
    def logout(self):
        identity.current.logout()
        raise redirect("/")

    @expose()
    def robots_txt(self):
        return "User-agent: *\nDisallow: /\n"

    @expose()
    def favicon_ico(self):
        static_dir = config.get('static_filter.dir', path="/static")
        filename = join(os.path.normpath(static_dir), 'images', 'favicon.ico')
        return serve_file(filename)

#    @expose(template='bkr.server.templates.activity')
#    def activity(self, *args, **kw):
# TODO This is mainly for testing
# if it hangs around it should check for admin access
#        return dict(title="Activity", search_bar=None, activity = Activity.all())
#
