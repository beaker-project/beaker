from turbogears.database import session
from turbogears import controllers, expose, flash, widgets, validate, \
    error_handler, validators, redirect, paginate, url
from cherrypy import request, response
from tg_expanding_form_widget.tg_expanding_form_widget import ExpandingForm
from kid import Element
from bkr.server import identity
from bkr.server.xmlrpccontroller import RPCRoot
from bkr.server.helpers import *
from bkr.server.widgets import AlphaNavBar, myPaginateDataGrid, HorizontalForm, \
        CheckBoxList
from bkr.server.admin_page import AdminPage

import cherrypy

from BasicAuthTransport import BasicAuthTransport
import xmlrpclib

# from bkr.server import json
# import logging
# log = logging.getLogger("bkr.server.controllers")
#import model
from model import *
import string

# Validation Schemas

class OSVersions(AdminPage):
    # For XMLRPC methods in this class.
    exposed = False

    id      = widgets.HiddenField(name="id")
    alias   = widgets.TextField(name="alias")
    arches  = CheckBoxList(name="arches", label="Arches",
                                      options=lambda: [(arch.id, arch.arch) for arch in Arch.query],
                                      validator=validators.Int())

    osmajor_form = HorizontalForm(
        fields      = [id, alias],
        submit_text = _(u"Edit OSMajor"),
    )

    osversion_form = HorizontalForm(
        fields      = [id, arches],
        action      = "edit osversion",
        submit_text = _(u"Edit OSVersion"),
    )
 
    def __init__(self,*args,**kw):
        kw['search_name'] = 'osversion' 
        kw['search_url'] = url("/osversions/by_name?anywhere=1")
        super(OSVersions,self).__init__(*args,**kw) 

        self.search_col = OSMajor.osmajor
        self.join = [OSVersion.osmajor]
        self.search_mapper = OSVersion
        self.add = False
     
    @identity.require(identity.in_group("admin"))
    @expose(template="bkr.server.templates.form")
    def edit(self, id=None, *args, **kw):
        try:
            osversion = OSVersion.by_id(id)
        except InvalidRequestError:
            flash(_(u"Invalid OSVersion ID %s" % id))
            redirect(".")
        return dict(title   = unicode(osversion),
                    value   = dict(id     = osversion.id,
                                   arches = [arch.id for arch in osversion.arches]),
                    form    = self.osversion_form,
                    action  = "./save",
                    options = None)

    @identity.require(identity.in_group("admin"))
    @expose(template="bkr.server.templates.osmajor")
    def edit_osmajor(self, id=None, *args, **kw):
        try:
            osmajor = OSMajor.by_id(id)
        except InvalidRequestError:
            flash(_(u"Invalid OSMajor ID %s" % id))
            redirect(".")
        return dict(title   = "OSMajor",
                    value   = osmajor,
                    form    = self.osmajor_form,
                    action  = "./save_osmajor",
                    options = None)

    @identity.require(identity.in_group("admin"))
    @expose()
    @validate(form=osversion_form)
    def save_osmajor(self, id=None, alias=None, *args, **kw):
        try:
            osmajor = OSMajor.by_id(id)
        except InvalidRequestError:
            flash(_(u"Invalid OSMajor ID %s" % id))
            redirect(".")
        if osmajor.alias != alias:
            osmajor.alias = alias
            flash(_(u"Changes saved for %s" % osmajor))
        else:
            flash(_(u"No changes for %s" % osmajor))
        redirect(".")

    @identity.require(identity.in_group('admin'))
    @expose()
    def save_osmajor_installopts(self, osmajor_id=None, installopts=None):
        try:
            osmajor = OSMajor.by_id(osmajor_id)
        except InvalidRequestError:
            flash(_(u"Invalid OSMajor ID %s" % id))
            redirect(".")
        for arch, options in installopts.iteritems():
            # arch=None means applied to all arches
            io = OSMajorInstallOptions.lazy_create(osmajor=osmajor,
                    arch=Arch.by_name(arch) if arch else None)
            io.ks_meta = options['ks_meta']
            io.kernel_options = options['kernel_options']
            io.kernel_options_post = options['kernel_options_post']
        flash(_(u'Install options saved for %s') % osmajor)
        redirect('.')

    @identity.require(identity.in_group("admin"))
    @expose()
    @validate(form=osversion_form)
    def save(self, id=None, arches=None, *args, **kw):
        try:
            osversion = OSVersion.by_id(id)
        except InvalidRequestError:
            flash(_(u"Invalid OSVersion ID %s" % id))
            redirect(".")
        arch_objects = [Arch.by_id(arch) for arch in arches]
        if osversion.arches != arch_objects:
            osversion.arches = arch_objects
            flash(_(u"Changes Saved for %s" % osversion))
        else:
            flash(_(u"No Changes for %s" % osversion))
        redirect(".")

    
    @expose(format='json')
    def by_name(self, input,*args,**kw):
        input = input.lower()
        if 'anywhere' in kw:
            search = OSVersion.list_osmajor_by_name(input, find_anywhere=True)
        else:
            search = OSVersion.list_osmajor_by_name(input)

        osmajors =  ["%s" % (match.osmajor.osmajor) for match in search] 
        osmajors = list(set(osmajors))
        return dict(matches=osmajors)

    @expose(template="bkr.server.templates.admin_grid")
    @paginate('list',limit=50, default_order='osmajor.osmajor')
    def index(self,*args,**kw):
        osversions = self.process_search(*args,**kw) 
        list_by_letters = []
        for elem in osversions:
            osmajor_name = elem.osmajor.osmajor
            if osmajor_name:
                list_by_letters.append(osmajor_name[0].capitalize())
        alpha_nav_data = set(list_by_letters)
        template_data = self.osversions(osversions,*args, **kw)
        nav_bar = self._build_nav_bar(alpha_nav_data,self.search_name)
        template_data['alpha_nav_bar'] = nav_bar
        return template_data
         

    def osversions(self, osversions=None, *args, **kw):
        q = session.query(self.search_mapper) # This line +3 dupes the start of process_search
        if osversions is None:
            for j in self.join:
                q = q.join(j)
            osversions = q
        osversions_grid = myPaginateDataGrid(fields=[
                                  myPaginateDataGrid.Column(name='osmajor.osmajor', getter=lambda x: make_link(url = './edit_osmajor?id=%s' % x.osmajor.id, text = x.osmajor), title='OS Major', options=dict(sortable=True)),
                                  myPaginateDataGrid.Column(name='osmajor.alias', getter=lambda x: x.osmajor.alias, title='Alias', options=dict(sortable=True)),
                                  myPaginateDataGrid.Column(name='osminor', getter=lambda x: make_link(url  = './edit?id=%s' % x.id, text = x.osminor), title='OS Minor', options=dict(sortable=True)),
                                  myPaginateDataGrid.Column(name='arches', getter=lambda x: " ".join([arch.arch for arch in x.arches]), title='Arches', options=dict(sortable=True)),
                              ])
 
        return dict(title="OS Versions", 
                    grid = osversions_grid, 
                    search_widget = self.search_widget_form,
                    addable = False,              
                    object_count = osversions.count(), 
                    list = osversions)

    default = index
