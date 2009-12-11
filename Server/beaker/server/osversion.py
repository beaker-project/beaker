from turbogears.database import session
from turbogears import controllers, expose, flash, widgets, validate, error_handler, validators, redirect, paginate
from turbogears.widgets import AutoCompleteField
from turbogears import identity, redirect
from cherrypy import request, response
from tg_expanding_form_widget.tg_expanding_form_widget import ExpandingForm
from kid import Element
from beaker.server.xmlrpccontroller import RPCRoot
from beaker.server.helpers import *

import cherrypy

from BasicAuthTransport import BasicAuthTransport
import xmlrpclib

# from beaker.server import json
# import logging
# log = logging.getLogger("beaker.server.controllers")
#import model
from model import *
import string

# Validation Schemas

class OSVersions(RPCRoot):
    # For XMLRPC methods in this class.
    exposed = False

    id      = widgets.HiddenField(name="id")
    arches  = widgets.CheckBoxList(name="arches", label="Arches",
                                      options=[(arch.id, arch.arch) for arch in Arch.query()],
                                      validator=validators.Int())

    osversion_form = widgets.TableForm(
        fields      = [id, arches],
        action      = "edit osversion",
        submit_text = _(u"Edit OSVersion"),
    )

    @expose(template="beaker.server.templates.form")
    def edit(self, id=None, *args, **kw):
        try:
            osversion = OSVersion.by_id(id)
        except InvalidRequestError:
            flash(_(u"Invalid OSVersion ID %s" % id))
            redirect(".")
        return dict(title   = "OSVersion",
                    value   = dict(id     = osversion.id,
                                   arches = [arch.id for arch in osversion.arches]),
                    form    = self.osversion_form,
                    action  = "./save",
                    options = None)

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

    @expose(template="beaker.server.templates.grid")
    @paginate('list',limit=50,allow_limit_override=True)
    def index(self):
        osversions = session.query(OSVersion)
        osversions_grid = widgets.PaginateDataGrid(fields=[
                                  widgets.PaginateDataGrid.Column(name='osversion', getter=lambda x: make_link(url  = './edit?id=%s' % x.id, text = x), title='OS Version', options=dict(sortable=True)),
                                  widgets.PaginateDataGrid.Column(name='arches', getter=lambda x: " ".join([arch.arch for arch in x.arches]), title='Arches', options=dict(sortable=True)),
                                  #(' ', lambda x: make_remove_link(x.id)),
                              ])
        return dict(title="Tags", grid = osversions_grid,
                                         search_bar = None,
                                         list = osversions)

    default = index
