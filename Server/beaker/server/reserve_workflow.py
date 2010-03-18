from turbogears import controllers, identity, expose, url, database, validate, flash, redirect
from turbogears.database import session
from sqlalchemy.sql.expression import and_
from beaker.server.widgets import ReserveWorkflow as ReserveWorkflowWidget
from beaker.server.widgets import ReserveSystem
import beaker.server.model as model
from sqlalchemy.exceptions import InvalidRequestError
from beaker.server.cobbler_utils import hash_to_string

import logging
log = logging.getLogger(__name__)

class ReserveWorkflow:
    widget = ReserveWorkflowWidget()
    reserveform = ReserveSystem()
 
    @expose()
    def doit(self, distro_id, **kw):
        """ Create a new reserve job, if system_id is defined schedule it too """
        try:
            distro = model.Distro.by_id(distro_id)
        except InvalidRequestError:
            flash(_(u'Invalid Distro ID %s' % distro_id))
            redirect('/')
        job = model.Job(ttasks=2, owner=identity.current.user)
        if kw.get('whiteboard'):
            job.whiteboard = kw.get('whiteboard')
        recipeSet = model.RecipeSet(ttasks=2)
        recipe = model.MachineRecipe(ttasks=2)
        # Inlcude the XML definition so that cloning this job will act as expected.
        recipe.distro_requires = distro.to_xml().toxml()
        recipe.distro = distro
        if kw.get('system_id'):
            try:
                system = model.System.by_id(kw.get('system_id'), identity.current.user)
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
        recipe.append_tasks(model.RecipeTask(task = model.Task.by_name('/distribution/install')))
        # Add Reserve task
        reserveTask = model.RecipeTask(task = model.Task.by_name('/distribution/reservesys'))
        if kw.get('reservetime'):
            #FIXME add DateTimePicker to ReserveSystem Form
            reservetask.params.append(model.RecipeTaskParam( name = 'RESERVETIME', 
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
            
        flash(_(u'Successfully queued job %s' % job.id))
        redirect('/jobs/%s' % job.id)

    @expose(template='beaker.server.templates.form')
    def reserve(self, distro_id, system_id=None):
        """ Either queue or provision the system now """
        if system_id:
            try:
                system = model.System.by_id(system_id, identity.current.user)
            except InvalidRequestError:
                flash(_(u'Invalid System ID %s' % system_id))
            system_name = system.fqdn
        else:
            system_name = 'Any System'
        try:
            distro = model.Distro.by_id(distro_id)
        except InvalidRequestError:
            flash(_(u'Invalid Distro ID %s' % distro_id))
        return dict(form=self.reserveform,
                    action='./doit',
                    value = dict(
                                 system_id = system_id,
                                 distro_id = distro_id,
                                 system = system_name,
                                 distro = distro.install_name,
                                ),
                    options = None,
                    title='Reserve System %s' % system_name)

    @identity.require(identity.not_anonymous())
    @expose(template='beaker.server.templates.generic') 
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
        arches = model.Arch.query().outerjoin(['distros','osversion','osmajor']).outerjoin(['distros','_tags']). \
                                              filter(and_(model.OSMajor.osmajor == distro_family,
                                                          model.Distro.method == method,
                                                          model.DistroTag.tag == tag))
        options = [elem.arch for elem in arches]
        return {'options' : options }

    @expose(allow_json=True)
    def get_distro_options(self,arch,distro_family,method,tag):
        """
        get_distro_options() will return all the distros for a given arch,
        distro_family,method and tag
        """

        distro = model.Distro.query().join(['osversion','osmajor']).join('arch')

        if tag:
            my_and = and_(model.OSMajor.osmajor == distro_family,
                          model.Distro.method == method,
                          model.Arch.arch == arch,
                          model.DistroTag.tag == tag)
            distro = distro.join('_tags')
        else:
            my_and = and_(model.OSMajor.osmajor == distro_family,
                          model.Distro.method == method,
                          model.Arch.arch == arch)

        distro = distro.filter(my_and)

        options = [elem.install_name for elem in distro]
        return {'options': options}

      
       
      
