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
        jobs = []
        for id in distro_id.split(","):
            """ Create a new reserve job, if system_id is defined schedule it too """
            try:
                distro = Distro.by_id(id)
            except InvalidRequestError:
                flash(_(u'Invalid Distro ID %s' % id))
                redirect('/')
            job = Job(ttasks=2, owner=identity.current.user)
            jobs.append(job)
            if kw.get('whiteboard'):
                job.whiteboard = kw.get('whiteboard')
            recipeSet = RecipeSet(ttasks=2)
            recipe = MachineRecipe(ttasks=2)
            # Inlcude the XML definition so that cloning this job will act as expected.
            recipe.distro_requires = distro.to_xml().toxml()
            recipe.distro = distro
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
            if recipe.systems:
                # We already picked the system skip New -> Processed states
                recipe.queue()
            session.save(job)
           
        session.flush()
        if len(jobs) > 1:
            success_msg =  u'Successfully queued jobs %s' % ",".join([str(j.id) for j in jobs])
            redirect_msg = '/jobs/mine' # Seems like a reasonable place to redirect them to
        else:
            success_msg = u'Successfully queued job %s' % job.id
            redirect_msg = '/jobs/%s' % jobs[0].id

        flash(_(success_msg))
        redirect(redirect_msg)

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
        for id in distro_id.split(","):
            try:
                distro = Distro.by_id(id)
                distro_names.append(distro.install_name)
            except InvalidRequestError:
                flash(_(u'Invalid Distro ID %s' % distro_id)) 
        distro = ", ".join(distro_names)
        return dict(form=self.reserveform,
                    action='./doit',
                    value = dict(
                                system_id = system_id,
                                distro_id = distro_id,
                                system = system_name,
                                distro = distro,
                                ),
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
