from turbogears.database import session
from turbogears import controllers, expose, flash, widgets, validate, error_handler, validators, redirect, paginate, url
from turbogears.widgets import AutoCompleteField, HiddenField
from turbogears import identity, redirect
from cherrypy import request, response
from tg_expanding_form_widget.tg_expanding_form_widget import ExpandingForm
from kid import Element
from bkr.server.xmlrpccontroller import RPCRoot
from bkr.server.widgets import DistroTags, SearchBar
from bkr.server.widgets import TaskSearchForm
from bkr.server.widgets import myPaginateDataGrid
from bkr.server.model import System
from bkr.server.helpers import *
from bkr.server.controller_utilities import Utility
from bkr.server import search_utility 

import cherrypy

from BasicAuthTransport import BasicAuthTransport
import xmlrpclib

# from bkr.server import json
# import logging
# log = logging.getLogger("bkr.server.controllers")
#import model
from model import *
import string

__all__ = ['Distros']

class Distros(RPCRoot):
    # For XMLRPC methods in this class.
    exposed = True

    task_form = TaskSearchForm()
    tag_form = DistroTags(name='tags')

    @expose(template="bkr.server.templates.distro")
    def view(self, id=None, *args, **kw):
        try:
            distro = Distro.by_id(id)
        except InvalidRequestError:
            flash(_(u"Invalid distro id %s" % id))
            redirect(".")
        return dict(title       = 'Distro',
                    value       = distro,
                    value_task  = dict(distro_id = distro.id),
                    form        = self.tag_form,
                    form_task   = self.task_form,
                    action      = './save_tag',
                    action_task = '/tasks/do_search',
                    options   = dict(tags = distro.tags,
                                    hidden = dict(distro  = 1,
                                                  osmajor = 1,
                                                  arch    = 1)))

    @expose()
    def get_family(self, distro):
        """ pass in a distro name and get back the osmajor is belongs to.
        """
        try:
            family = '%s' % Distro.by_name(distro).osversion.osmajor
        except AttributeError:
            raise BX(_('Invalid Distro: %s' % distro))
        return family

    @expose()
    def get_arch(self, filter):
        """ pass in a dict() with either distro or osmajor to get possible arches
        """
        if 'distro' in filter:
            # look up distro
            try:
                arches = [arch.arch for arch in Distro.by_name(filter['distro']).osversion.arches]
            except AttributeError:
                raise BX(_('Invalid Distro: %s' % filter['distro']))
        elif 'osmajor' in filter:
            # look up osmajor
            try:
                arches = [arch.arch for arch in OSMajor.by_name(filter['osmajor']).osminor[0].arches]
            except InvalidRequestError:
                raise BX(_('Invalid OSMajor: %s' % filter['osmajor']))
        return arches

    @expose()
    @identity.require(identity.not_anonymous())
    def save_tag(self, id=None, tag=None, *args, **kw):
        try:
            distro = Distro.by_id(id)
        except InvalidRequestError:
            flash(_(u"Invalid distro id %s" % id))
            redirect(".")
        if tag['text']:
            distro.tags.append(tag['text'])
            Activity(identity.current.user,'WEBUI','Tagged',distro.install_name,None,tag['text'])
        flash(_(u"Added Tag %s" % tag['text']))
        redirect("./view?id=%s" % id)

    @expose()
    @identity.require(identity.not_anonymous())
    def tag_remove(self, id=None, tag=None, *args, **kw):
        try:
            distro = Distro.by_id(id)
        except InvalidRequestError:
            flash(_(u"Invalid distro id %s" % id))
            redirect(".")
        if tag:
            for dtag in distro.tags:
                if dtag == tag:
                    distro.tags.remove(dtag)
                    Activity(identity.current.user,'WEBUI','UnTagged',distro.install_name,tag,None)
                    flash(_(u"Removed Tag %s" % tag))
        redirect("./view?id=%s" % id)

    @expose(format='json')
    def by_name(self, distro):
        distro = distro.lower()
        return dict(distros=[(distro.install_name) for distro in Distro.query().filter(Distro.install_name.like('%s%%' % distro)).order_by('-date_created')])
    
    def _distros(self,distro,**kw):
        return_dict = {} 
        if 'simplesearch' in kw:
            simplesearch = kw['simplesearch']
            kw['distrosearch'] = [{'table' : 'Name',   
                                   'operation' : 'contains', 
                                   'value' : kw['simplesearch']}]                    
        else:
            simplesearch = None

        return_dict.update({'simplesearch':simplesearch}) 
        if kw.get("distrosearch"):
            searchvalue = kw['distrosearch']  
            distros_found = self._distro_search(distro,**kw)
            return_dict.update({'distros_found':distros_found})               
            return_dict.update({'searchvalue':searchvalue})
        return return_dict

    def _distro_search(self,distro,**kw):
        distro_search = search_utility.Distro.search(distro)
        for search in kw['distrosearch']:
            col = search['table'] 
            distro_search.append_results(search['value'],col,search['operation'],**kw)
        return distro_search.return_results()

    @expose(template="bkr.server.templates.grid")
    @paginate('list',default_order='-date_created', limit=50,max_limit=None)
    def index(self,*args,**kw):
        return self.distros(distros=session.query(Distro).join('breed').join('arch').join(['osversion','osmajor']),*args,**kw)

    @expose(template="bkr.server.templates.grid")
    @paginate('list',default_order='-date_created', limit=50,max_limit=None)
    def name(self,*args,**kw):
        return self.distros(distros=session.query(Distro).join('breed').join('arch').join(['osversion','osmajor']).filter(distro_table.c.install_name.like('%s' % kw['name'])),action='./name')

    def distros(self, distros,action='.',*args, **kw):
        distros_return = self._distros(distros,**kw) 
        searchvalue = None
        hidden_fields = None
        search_options = {}
        if distros_return:
            if 'distros_found' in distros_return:
                distros = distros_return['distros_found']
            if 'searchvalue' in distros_return:
                searchvalue = distros_return['searchvalue']
            if 'simplesearch' in distros_return:
                search_options['simplesearch'] = distros_return['simplesearch']

        distros_grid =  myPaginateDataGrid(fields=[
                                  myPaginateDataGrid.Column(name='install_name', getter=lambda x: make_link(url  = '/distros/view?id=%s' % x.id,
                                  text = x.install_name), title='Install Name', options=dict(sortable=True)),
                                  myPaginateDataGrid.Column(name='name', getter=lambda x: x.name, title='Name', options=dict(sortable=True)),
                                  myPaginateDataGrid.Column(name='breed.breed', getter=lambda x: x.breed, title='Breed', options=dict(sortable=True)),
                                  myPaginateDataGrid.Column(name='osversion.osmajor.osmajor', getter=lambda x: x.osversion.osmajor, title='OS Major Version', options=dict(sortable=True)),
                                  myPaginateDataGrid.Column(name='osversion.osminor', getter=lambda x: x.osversion.osminor, title='OS Minor Version', options=dict(sortable=True)),
                                  myPaginateDataGrid.Column(name='variant', getter=lambda x: x.variant, title='Variant', options=dict(sortable=True)),
                                  myPaginateDataGrid.Column(name='virt', getter=lambda x: x.virt, title='Virt', options=dict(sortable=True)),
                                  myPaginateDataGrid.Column(name='arch.arch', getter=lambda x: x.arch, title='Arch', options=dict(sortable=True)),
                                  myPaginateDataGrid.Column(name='method', getter=lambda x: x.method, title='Method', options=dict(sortable=True)),
                                  myPaginateDataGrid.Column(name='date_created', getter=lambda x: x.date_created, title='Date Created', options=dict(sortable=True)),
                                  Utility.direct_column(title='Provision', getter=lambda x: _provision_system_link(x))
                              ])

        def _provision_system_link(x):
            div = Element('div')
            div.append(make_link("/reserve_system?distro_id=%s" % (x.id,), "Pick System"))
            div.append(Element('br'))
            div.append(make_link("/reserveworkflow/reserve?distro_id=%s" % (x.id,), "Pick Any System"))
            return div

        

        if 'tag' in kw: 
            hidden_fields = [('tag',kw['tag'])]

        search_bar = SearchBar(name='distrosearch',
                           label=_(u'Distro Search'),    
                           table=search_utility.Distro.search.create_search_table(), 
                           complete_data = search_utility.Distro.search.create_complete_search_table(),
                           search_controller=url("/get_search_options_distros"), 
                           extra_hiddens=hidden_fields
                           )

        return dict(title="Distros", 
                    grid=distros_grid,
                    search_bar=search_bar,
                    object_count = distros.count(),
                    action=action,
                    options=search_options,
                    searchvalue=searchvalue,
                    list=distros)

    #XMLRPC method for listing distros
    @cherrypy.expose
    def filter(self, filter):
        distros = session.query(Distro)
        name = filter.get('name', None)
        family = filter.get('family', None)
        tags = filter.get('tags', [])
        arch = filter.get('arch', None)
        treepath = filter.get('treepath', None)
        limit = filter.get('limit', None)
        if tags:
            sqltags = []
            distros = distros.join('_tags')
            for tag in tags:
                sqltags.append(distro_tag_table.c.tag==tag)
            distros = distros.filter(and_(*sqltags))
        if name:
            distros = distros.filter(distro_table.c.name.like('%s' % name))
        if family:
            distros = distros.join(['osversion','osmajor'])
            distros = distros.filter(osmajor_table.c.osmajor=='%s' % family)
        if arch:
            distros = distros.join('arch')
            distros = distros.filter(arch_table.c.arch=='%s' % arch)
        if treepath:
            distros = distros.filter(lab_controller_distro_map.c.tree_path.like('%s' % treepath))
        # join on lab controllers, we only want distros that are active in at least one lab controller
        distros = distros.join('lab_controller_assocs')
        distros = distros.order_by(distro_table.c.date_created.desc())
        if limit:
            distros = distros[:limit]
        return [(distro.install_name, distro.name, '%s' % distro.arch, '%s' % distro.osversion, distro.variant, distro.method, distro.virt, ['%s' % tag for tag in distro.tags], dict([(lc.lab_controller.fqdn, lc.tree_path) for lc in distro.lab_controller_assocs])) for distro in distros]

    #XMLRPC method for listing distros
    @cherrypy.expose
    def list(self, name, family, arch, tags, treepath):
        distros = session.query(Distro)
        if tags:
            sqltags = []
            distros = distros.join('_tags')
            for tag in tags:
                sqltags.append(distro_tag_table.c.tag==tag)
            distros = distros.filter(and_(*sqltags))
        if name:
            distros = distros.filter(distro_table.c.name.like('%s' % name))
        if family:
            distros = distros.join(['osversion','osmajor'])
            distros = distros.filter(osmajor_table.c.osmajor=='%s' % family)
        if arch:
            distros = distros.join('arch')
            distros = distros.filter(arch_table.c.arch=='%s' % arch)
        if treepath:
            distros = distros.join('lab_controller_assocs')
            distros = distros.filter(lab_controller_distro_map.c.tree_path.like('%s' % treepath))
        distros = distros.order_by(distro_table.c.date_created.desc())
        return [(distro.name, '%s' % distro.arch, '%s' % distro.osversion, distro.variant, distro.method, distro.virt) for distro in distros]

    @cherrypy.expose
    @identity.require(identity.not_anonymous())
    def edit_version(self, name, version):
        """ quick and dirty to allow editing the Version.
            This is the one thing that needs editing at times
        """
        distros = session.query(Distro).filter(distro_table.c.name.like('%s' % name))
        edited = []

        os_major = version.split('.')[0]

        # Try and split OSMinor
        try:
            os_minor = version.split('.')[1]
        except IndexError:
            os_minor = 0

        # Try and find OSMajor
        try:
            osmajor = OSMajor.by_name(os_major)
        except InvalidRequestError: 
            osmajor = OSMajor(os_major)

        # Try and find OSVersion
        try:
            osversion = OSVersion.by_name(osmajor,os_minor)
        except InvalidRequestError: 
            osversion = OSVersion(osmajor,os_minor)

        # Check each Distro
        for distro in distros:
            if osversion != distro.osversion:
                edited.append('%s' % distro.install_name)
                Activity(identity.current.user,'XMLRPC','OSVersion',distro.install_name,'%s' % distro.osversion,'%s' % osversion)
                distro.osversion = osversion
        return edited


    @cherrypy.expose
    @identity.require(identity.not_anonymous())
    def tag(self, name, arch, tag):
        return self._tag(name, arch, tag)

    def _tag(self, name, arch, tag):
        added = []
        distros = session.query(Distro)
        if name:
            distros = distros.filter(distro_table.c.name.like('%s' % name))
        if arch:
            distros = distros.join('arch')
            distros = distros.filter(arch_table.c.arch=='%s' % arch)
        for distro in distros:
            if tag not in distro.tags:
                added.append('%s' % distro.install_name)
                Activity(identity.current.user,'XMLRPC','Tagged',distro.install_name,None,tag)
                distro.tags.append(tag)
                session.save_or_update(distro)
                session.flush([distro])
        return added

    @cherrypy.expose
    @identity.require(identity.not_anonymous())
    def untag(self, name, arch, tag):
        removed = []
        distros = session.query(Distro)
        if name:
            distros = distros.filter(distro_table.c.name.like('%s' % name))
        if arch:
            distros = distros.join('arch')
            distros = distros.filter(arch_table.c.arch=='%s' % arch)
        for distro in distros:
            if tag in distro.tags:
                removed.append('%s' % distro.install_name)
                Activity(identity.current.user,'XMLRPC','UnTagged',distro.install_name,tag,None)
                distro.tags.remove(tag)
        return removed

    @cherrypy.expose
    def pick(self, xml):
        """
        Based on XML passed in filter distro selection
        """
        distros = Distro.by_filter(xml)
        distros = distros.add_column('tree_path').join('lab_controller_assocs')
        distros = distros.add_column('fqdn').join(['lab_controller_assocs','lab_controller'])
        try:
            distro, tree_path, fqdn = distros.first()
        except TypeError:
            return None
        if distro:
            return dict(distro         = distro.name,
                        install_name   = distro.install_name,
                        arch           = '%s' % distro.arch,
                        family         = '%s' % distro.osversion,
                        variant        = distro.variant,
                        lab_controller = fqdn,
                        tree_path      = tree_path)
        else:
            return None

    default = index

# for sphinx
distros = Distros
