from turbogears import controllers, identity, expose, url, database, validate, flash, redirect
from sqlalchemy.sql.expression import and_
from beaker.server.widgets import ReserveWorkflow as ReserveWorkflowWidget
import beaker.server.model as model

import logging
log = logging.getLogger(__name__)

class ReserveWorkflow:
    widget = ReserveWorkflowWidget()
 
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

        if tag:
            my_and = and_(model.OSMajor.osmajor == distro_family,
                          model.Distro.method == method,
                          model.Arch.arch == arch, 
                          model.DistroTag.tag == tag)
        else: 
            my_and = and_(model.OSMajor.osmajor == distro_family,
                          model.Distro.method == method,
                          model.Arch.arch == arch) 
 
        distro = model.Distro.query().join(['osversion','osmajor']).join('arch').join('_tags'). \
                                      filter(my_and)
                                            
                                           
                                          
        options = [elem.install_name for elem in distro]
        return {'options': options}

      
       
      
