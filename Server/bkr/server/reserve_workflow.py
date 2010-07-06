from turbogears import controllers, identity, expose, url, database, validate, flash, redirect
from turbogears.database import session
from sqlalchemy.sql.expression import and_, func, not_
from bkr.server.widgets import ReserveWorkflow as ReserveWorkflowWidget
from bkr.server.widgets import ReserveSystem
from bkr.server.model import (osversion_table, distro_table, osmajor_table, arch_table, distro_tag_table,
                              Distro, Job, RecipeSet, MachineRecipe, System, RecipeTask, RecipeTaskParam,
                              Task, Arch, OSMajor, DistroTag)
from sqlalchemy.exceptions import InvalidRequestError
from bkr.server.cobbler_utils import hash_to_string
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
        job = Job(ttasks=0, owner=identity.current.user)
        if kw.get('whiteboard'):
            job.whiteboard = kw.get('whiteboard') 
        if not isinstance(distro_id,list):
            distro_id = [distro_id]

        for id in distro_id: 
            try:
                distro = Distro.by_id(id)
            except InvalidRequestError:
                flash(_(u'Invalid Distro ID %s' % id))
                redirect('/')
            recipeSet = RecipeSet(ttasks=2)
            recipe = MachineRecipe(ttasks=2)
            # Inlcude the XML definition so that cloning this job will act as expected.
            recipe.distro_requires = distro.to_xml().toxml()
            recipe.distro = distro
            # Don't report panic's for reserve workflow.
            recipe.panic = 'ignore'
            if kw.get('system_id'):
                try:
                    system = System.by_id(kw.get('system_id'), identity.current.user)
                except InvalidRequestError:
                    flash(_(u'Invalid System ID %s' % system_id))
                    redirect('/')
                # Inlcude the XML definition so that cloning this job will act as expected.
                recipe.host_requires = system.to_xml().toxml()
                recipe.systems.append(system)
            if kw.get('ks_meta'):
                recipe.ks_meta = kw.get('ks_meta')
            if kw.get('koptions'):
                recipe.kernel_options = kw.get('koptions')
            if kw.get('koptions_post'):
                recipe.kernel_options_post = kw.get('koptions_post')
            # Eventually we will want the option to add more tasks.
            # Add Install task
            recipe.append_tasks(RecipeTask(task = Task.by_name(u'/distribution/install')))
            # Add Reserve task
            reserveTask = RecipeTask(task = Task.by_name(u'/distribution/reservesys'))
            if kw.get('reservetime'):
                #FIXME add DateTimePicker to ReserveSystem Form
                reservetask.params.append(RecipeTaskParam( name = 'RESERVETIME', 
                                                                value = kw.get('reservetime')
                                                            )
                                        )
            recipe.append_tasks(reserveTask)
            recipeSet.recipes.append(recipe)
            job.recipesets.append(recipeSet)
            job.ttasks += recipeSet.ttasks
            if recipe.systems:
                # We already picked the system skip New -> Processed states
                recipe.queue()
        session.save(job)
        session.flush()

        flash(_(u'Successfully queued job %s' % job.id))
        redirect('/jobs/%s' % job.id)

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
        if 'method' in kw:
            values['method'] = kw['method']
 
        return dict(widget=self.widget,widget_options={'values' : values},title='Reserve Workflow')


    @expose(allow_json=True)
    def get_arch_options(self,distro_family,method,tag):
        """
        get_arch_options() will return all arch's available for a particular distro_family,
        method and tag
        """   
        arches = Arch.query().outerjoin(['distros','osversion','osmajor']).outerjoin(['distros','_tags']). \
                                              filter(and_(OSMajor.osmajor == distro_family,
                                                          Distro.method == method,
                                                          DistroTag.tag == tag))
        options = [elem.arch for elem in arches]
        return {'options' : options }

    @expose(allow_json=True)
    def get_distro_options(self,arch,distro_family,method,tag):
        """
        get_distro_options() will return all the distros for a given arch,
        distro_family,method and tag
        """
        arch = arch.split(',')  
        if len(arch) > 1:
            results = Distro.multiple_systems_distro(method=method,arch=arch,osmajor=distro_family,tag=tag) 
            return {'options' : results }

        distro = Distro.query().join(['osversion','osmajor']).join('arch')
        my_and = [OSMajor.osmajor == distro_family]
        if tag:
                my_and.append(DistroTag.tag == tag)                       
                distro = distro.join('_tags') 
        arch = arch[0]
        distro = distro.filter(Arch.arch == arch)
        my_and.append(Distro.method == method)

        distro = distro.filter(and_(*my_and))
        options = sorted([(elem.install_name,elem.date_created) for elem in distro], key = lambda e1: e1[1],reverse=True) #so we don't have to guess the install_name later
        options = [elem[0] for elem in options]
        return {'options': options} 

    @expose(allow_json=True)
    def find_systems_for_multiple_distros(self,distro_install_name,arches=None,*args,**kw):
        all_distro_names = list()
        for arch in arches.split(','): 
            all_distro_names.append('%s-%s' % (distro_install_name,arch))

        systems_queries, distro_ids = [],[] 
        for install_name in all_distro_names:
            try:
                distro = Distro.query().filter(Distro.install_name == install_name).one()
                distro_ids.append(distro.id)
            except InvalidRequestError:
                log.error(u'Could not find distro %s, continuing with other distros' % install_name)
                continue
            
            systems_distro_query = distro.systems()
            systems_available = System.available(identity.current.user,System.by_type(type='machine',systems=systems_distro_query)) 
            systems_queries = systems_queries + systems_available.select()

        return { 'count' : len(set(systems_queries)), 'distro_id' : distro_ids }
              
    @expose(allow_json=True) 
    def find_systems_for_distro(self,distro_install_name,*args,**kw): 
        try: 
            distro = Distro.query().filter(Distro.install_name == distro_install_name).one()
        except InvalidRequestError,(e):
            return { 'count' : 0 } 
                 
        #there seems to be a bug distro.systems 
        #it seems to be auto correlateing the inner query when you pass it a user, not possible to manually correlate
        #a Query object in 0.4  
        systems_distro_query = distro.systems()
        avail_systems_distro_query = System.available(identity.current.user,System.by_type(type='machine',systems=systems_distro_query)) 
        return {'count' : avail_systems_distro_query.count(), 'distro_id' : distro.id }
