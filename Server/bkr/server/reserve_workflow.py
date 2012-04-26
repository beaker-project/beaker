from turbogears import controllers, identity, expose, url, database, validate, flash, redirect
from turbogears.database import session
from sqlalchemy.sql.expression import and_, func, not_
from sqlalchemy.exceptions import InvalidRequestError
from bkr.server.widgets import ReserveWorkflow as ReserveWorkflowWidget
from bkr.server.widgets import ReserveSystem
from bkr.server.model import (osversion_table, distro_table, osmajor_table, arch_table, distro_tag_table,
                              Distro, Job, RecipeSet, MachineRecipe, System, RecipeTask, RecipeTaskParam,
                              Task, Arch, OSMajor, DistroTag, SystemType)
from bkr.server.model import Job
from bkr.server.jobs import Jobs as JobController
from bkr.server.cobbler_utils import hash_to_string
from bexceptions import *
import re
import logging
log = logging.getLogger(__name__)

class ReserveWorkflow:
    widget = ReserveWorkflowWidget()
    reserveform = ReserveSystem()
  
    @expose()
    @identity.require(identity.not_anonymous())
    def doit(self, distro_id, **kw):
        """ Create a new reserve job, if system_id is defined schedule it too """
        if 'system_id' in kw:
            kw['id'] = kw['system_id']
         
        try:
            provision_system_job = Job.provision_system_job(distro_id, **kw)
        except BX, msg:
            flash(_(u"%s" % msg))
            redirect(u".")
        JobController.success_redirect(provision_system_job.id)

    @expose(template='bkr.server.templates.form')
    @identity.require(identity.not_anonymous())
    def reserve(self, distro_id, system_id=None):
        """ Either queue or provision the system now """
        if system_id:
            try:
                system = System.by_id(system_id, identity.current.user)
            except InvalidRequestError:
                flash(_(u'Invalid System ID %s' % system_id))
            system_name = system.fqdn
        else:
            system_name = 'Any System'
        distro_names = [] 

        return_value = dict(
                            system_id = system_id, 
                            system = system_name,
                            distro = '',
                            distro_ids = [],
                            )
        if not isinstance(distro_id,list):
            distro_id = [distro_id]
        for id in distro_id:
            try:
                distro = Distro.by_id(id)
                distro_names.append(distro.install_name)
                return_value['distro_ids'].append(id)
            except InvalidRequestError:
                flash(_(u'Invalid Distro ID %s' % id)) 
        distro = ", ".join(distro_names)
        return_value['distro'] = distro
        
        return dict(form=self.reserveform,
                    action='./doit',
                    value = return_value,
                    options = None,
                    title='Reserve System %s' % system_name)

    @identity.require(identity.not_anonymous())
    @expose(template='bkr.server.templates.generic') 
    def index(self,*args,**kw):
        values = {}
        if 'arch' in kw:
            values['arch'] = kw['arch']
        if 'distro_family' in kw:
            values['distro_family'] = kw['distro_family']
        if 'tag' in kw:
            values['tag'] = kw['tag']
 
        return dict(widget=self.widget,widget_options={'values' : values},title='Reserve Workflow')


    @expose(allow_json=True)
    def get_distro_options(self,arch=None,distro_family=None,tag=None):
        """
        get_distro_options() will return all the distros for a given arch,
        distro_family and tag. If there are multiple archs supplied, it will
        return a list of distro names, otherwise distro install names
        """
        if arch is None or distro_family is None:
            return {'options' : [] }
        distros = Distro.distros_for_provision(arch=arch, osmajor=distro_family, tag=tag)
        if not distros:
            return {'options' : [] }
        if isinstance(arch, list) and len(arch) > 1: #Multiple arch search
            #Get a mangled version of the install_name (i.e without the arch on the end)
            names = [re.sub(r'^(.+)\-(?:.+?)$',r'\1',d.install_name) for d in distros]
        else:
            #Only get install names
            names = [d.install_name for d in distros]
        return {'options' : names }

    @expose(allow_json=True)
    def find_systems_for_multiple_distros(self, distro_name, arches=None,*args,**kw):
        if arches is None:
            arches = []
        distro_ids = []
        for arch in arches:
            distro_install_name = '%s-%s' % (distro_name,arch)
            try:
                distro = Distro.query.join(Distro.arch).filter(Distro.install_name == distro_install_name).one()
                distro_ids.append(distro.id)
            except InvalidRequestError:
                log.error('Could not find distro %s' % distro_install_name)
                return {'enough_systems' : 0, 'error' : 'There was an error retrieving distro %s, \
                    please see your administrator.' % distro_install_name}
            systems_distro_query = distro.systems()
            systems_available = System.available_for_schedule(identity.current.user,
                System.by_type(type=SystemType.machine, systems=systems_distro_query))
            if systems_available.count() < 1:
                # Not enough systems
                return {'enough_systems' : 0, 'distro_id':None}

        return {'enough_systems':1, 'distro_id' : distro_ids}

    @expose(allow_json=True)
    def find_systems_for_distro(self, distro_install_name, *args,**kw):
        try:
            distro = Distro.query.filter(Distro.install_name == distro_install_name).one()
        except InvalidRequestError,(e):
            return { 'enough_systems' : 0, 'error' : 'There was an error retrieving distro %s, \
                please see your administrator' % distro_install_name}

        systems_distro_query = distro.systems()
        avail_systems_distro_query = System.available_for_schedule(identity.current.user,
                System.by_type(type=SystemType.machine, systems=systems_distro_query))
        enough_systems = 0
        if avail_systems_distro_query.count() > 0:
            enough_systems = 1
        return {'enough_systems' : enough_systems, 'distro_id' : distro.id }
