from turbogears.database import session
from turbogears import controllers, expose, flash, widgets, validate, error_handler, validators, redirect, paginate
from turbogears.widgets import AutoCompleteField
from turbogears import identity, redirect
from cherrypy import request, response
from tg_expanding_form_widget.tg_expanding_form_widget import ExpandingForm
from kid import Element
from medusa.xmlrpccontroller import RPCRoot
from medusa.widgets import DistroTags
from medusa.helpers import *
from medusa.needpropertyxml import *

import cherrypy

from BasicAuthTransport import BasicAuthTransport
import xmlrpclib

# from medusa import json
# import logging
# log = logging.getLogger("medusa.controllers")
#import model
from model import *
import string

# Validation Schemas

class Distros(RPCRoot):
    # For XMLRPC methods in this class.
    exposed = True

    tag_form = DistroTags(name='tags')

    @expose(template="medusa.templates.distro")
    def view(self, id=None, *args, **kw):
        try:
            distro = Distro.by_id(id)
        except InvalidRequestError:
            flash(_(u"Invalid distro id %s" % id))
            redirect(".")
        return dict(title   = 'Distro',
                    value   = distro,
                    form    = self.tag_form,
                    action  = './save_tag',
                    options = dict(tags = distro.tags))

    @expose()
    def save_tag(self, id=None, tag=None, *args, **kw):
        try:
            distro = Distro.by_id(id)
        except InvalidRequestError:
            flash(_(u"Invalid distro id %s" % id))
            redirect(".")
        if tag['text']:
            distro.tags.append(tag['text'])
        flash(_(u"Added Tag %s" % tag['text']))
        redirect("./view?id=%s" % id)

    @expose()
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
                    flash(_(u"Removed Tag %s" % tag))
        redirect("./view?id=%s" % id)

    @expose(template="medusa.templates.grid")
    @paginate('list',default_order='-date_created', limit=50,allow_limit_override=True)
    def index(self, *args, **kw):
        distros = session.query(Distro).join('breed').join('arch').join(['osversion','osmajor'])
        if 'tag' in kw:
            distros = distros.join('_tags').filter(DistroTag.c.tag==kw['tag'])
        if 'name' in kw:
            distros = distros.filter(Distro.c.install_name.like('%%%s%%' % kw['name']))
        distros_grid = widgets.PaginateDataGrid(fields=[
                                  widgets.PaginateDataGrid.Column(name='install_name', getter=lambda x: make_link(url  = 'view?id=%s' % x.id,
                                  text = x.install_name), title='Install Name', options=dict(sortable=True)),
                                  widgets.PaginateDataGrid.Column(name='name', getter=lambda x: x.name, title='Name', options=dict(sortable=True)),
                                  widgets.PaginateDataGrid.Column(name='breed.breed', getter=lambda x: x.breed, title='Breed', options=dict(sortable=True)),
                                  widgets.PaginateDataGrid.Column(name='osversion.osmajor.osmajor', getter=lambda x: x.osversion.osmajor, title='OS Major Version', options=dict(sortable=True)),
                                  widgets.PaginateDataGrid.Column(name='osversion.osminor', getter=lambda x: x.osversion.osminor, title='OS Minor Version', options=dict(sortable=True)),
                                  widgets.PaginateDataGrid.Column(name='variant', getter=lambda x: x.variant, title='Variant', options=dict(sortable=True)),
                                  widgets.PaginateDataGrid.Column(name='virt', getter=lambda x: x.virt, title='Virt', options=dict(sortable=True)),
                                  widgets.PaginateDataGrid.Column(name='arch.arch', getter=lambda x: x.arch, title='Arch', options=dict(sortable=True)),
                                  widgets.PaginateDataGrid.Column(name='method', getter=lambda x: x.method, title='Method', options=dict(sortable=True)),
                                  widgets.PaginateDataGrid.Column(name='date_created', getter=lambda x: x.date_created, title='Date Created', options=dict(sortable=True)),
                              ])
        return dict(title="Distros", grid = distros_grid,
                                         search_bar = None,
                                         list = distros)

    @cherrypy.expose
    def pick(self, machine_account, xml):
        """
        Based on XML passed in filter distro selection
        """
        #FIXME Should validate XML before proceeding.
        queries = []
        joins = []
        for child in ElementWrapper(xmltramp.parse(xml)):
            if callable(getattr(child, 'filter')):
                (join, query) = child.filter()
                queries.append(query)
                joins.extend(join)
        distros = Distro.query()
        if joins:
            distros = distros.filter(and_(*joins))
        if queries:
            distros = distros.filter(and_(*queries))
        distros = distros.add_column('tree_path').join('lab_controller_assocs')
        distros = distros.add_column('fqdn').join(['lab_controller_assocs','lab_controller'])
        try:
            distro, tree_path, fqdn = distros.order_by('-date_created').first()
        except TypeError:
            return None
        if distro:
            return dict(distro         = distro.install_name,
                        arch           = '%s' % distro.arch,
                        family         = '%s' % distro.osversion,
                        variant        = distro.variant,
                        lab_controller = fqdn,
                        tree_path      = tree_path)
        else:
            return None

    default = index
