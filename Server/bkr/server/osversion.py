
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from turbogears.database import session
from turbogears import expose, flash, widgets, validate, \
    validators, redirect, paginate, url
from sqlalchemy.exc import InvalidRequestError
from sqlalchemy.orm.exc import NoResultFound
from bkr.server import identity
from bkr.server.helpers import make_link
from bkr.server.widgets import myPaginateDataGrid, HorizontalForm, \
        CheckBoxList
from bkr.server.admin_page import AdminPage

from bkr.server.model import Arch, OSMajor, OSVersion, OSMajorInstallOptions

# Validation Schemas

class OSVersions(AdminPage):
    # For XMLRPC methods in this class.
    exposed = False

    id      = widgets.HiddenField(name="id")
    alias   = widgets.TextField(name="alias",
                                validator=validators.UnicodeString(if_empty=None))
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
    @validate(form=osmajor_form)
    def save_osmajor(self, id=None, alias=None, *args, **kw):
        try:
            osmajor = OSMajor.by_id(id)
        except InvalidRequestError:
            flash(_(u"Invalid OSMajor ID %s" % id))
            redirect(".")
        if osmajor.alias != alias:
            if alias:
                try:
                    existing = OSMajor.by_name_alias(alias)
                except NoResultFound:
                    pass
                else:
                    flash(_(u'Cannot save alias %s, it is already used by %s')
                            % (alias, existing))
                    redirect('.')
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
            io = OSMajorInstallOptions.lazy_create(osmajor_id=osmajor.id,
                    arch_id=Arch.by_name(arch).id if arch else None)
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
        template_data['search_widget'] = self.search_widget_form
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
                    addable = False,              
                    list = osversions)

    default = index
