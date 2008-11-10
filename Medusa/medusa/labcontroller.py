from turbogears.database import session
from turbogears import controllers, expose, flash, widgets, validate, error_handler, validators, redirect, paginate
from turbogears.widgets import AutoCompleteField
from turbogears import identity, redirect
from cherrypy import request, response
from tg_expanding_form_widget.tg_expanding_form_widget import ExpandingForm
from kid import Element
from medusa.xmlrpccontroller import RPCRoot
from medusa.helpers import *

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

class LabControllerFormSchema(validators.Schema):
    fqdn = validators.UnicodeString(not_empty=True, max=256, strip=True)

class LabControllers(RPCRoot):
    # For XMLRPC methods in this class.
    exposed = False

    id     = widgets.HiddenField(name='id')
    fqdn   = widgets.TextField(name='fqdn', label=_(u'FQDN'))
    username   = widgets.TextField(name='username', label=_(u'Username'))
    password   = widgets.PasswordField(name='password', label=_(u'Password'))

    labcontroller_form = widgets.TableForm(
        'LabController',
        fields = [id, fqdn, username, password],
        action = 'save_data',
        submit_text = _(u'Save'),
        validator = LabControllerFormSchema()
    )

    @expose(template='medusa.templates.form')
    def new(self, **kw):
        return dict(
            form = self.labcontroller_form,
            action = './save',
            options = {},
            value = kw,
        )

    @expose(template='medusa.templates.form')
    def edit(self, id, **kw):
        labcontroller = LabController.by_id(id)
        return dict(
            form = self.labcontroller_form,
            action = './save',
            options = {},
            value = labcontroller,
        )

    @expose()
    @validate(form=labcontroller_form)
    @error_handler(edit)
    def save(self, **kw):
        if kw.get('id'):
            labcontroller = LabController.by_id(kw['id'])
        else:
            labcontroller =  LabController()
        labcontroller.fqdn = kw['fqdn']
        labcontroller.username = kw['username']
        labcontroller.password = kw['password']

        flash( _(u"%s saved" % labcontroller.fqdn) )
        redirect(".")

    @expose()
    def update(self, **kw):
        if kw.get('id'):
            labcontroller = LabController.by_id(kw['id'])
            url = "http://%s/labcontroller/" % labcontroller.fqdn
            lc_xmlrpc = xmlrpclib.ServerProxy(url, BasicAuthTransport(labcontroller.username,labcontroller.password))
            lc_distros_md5 = lc_xmlrpc.distros_md5()
            if lc_distros_md5 != labcontroller.distros_md5:
                labcontroller.distros = []
                lc_distros = lc_xmlrpc.distros_list()
                for lc_distroname in lc_distros:
                    for lc_distro in lc_distros[lc_distroname]:
                        try:
                            distro = Distro.by_install_name(lc_distro['install_name'])
                        except:
                            distro = Distro(lc_distro['install_name'])
                            distro.name = lc_distroname
                            session.save(distro)
                            session.flush([distro])
                            try:
                                breed = Breed.by_name(lc_distro['breed'])
                            except:
                                breed = Breed(lc_distro['breed'])
                                session.save(breed)
                                session.flush([breed])
                            distro.breed = breed
                            try:
                                osversion = OSVersion.by_name(lc_distro['os_version'])
                            except:
                                osversion = OSVersion(lc_distro['os_version'])
                                session.save(osversion)
                                session.flush([osversion])
                            distro.osversion = osversion
                            try:
                                arch = Arch.by_name(lc_distro['arch'])
                            except:
                                arch = Arch(lc_distro['arch'])
                                session.save(arch)
                                session.flush([arch])
                            distro.arch = arch
                            distro.variant = lc_distro['variant']
                            distro.method = lc_distro['method']
                            distro.virt = lc_distro['virt']
                            distro.date_created = datetime.fromtimestamp(float(lc_distro['date_created']))
                        labcontroller.distros.append(distro)
                labcontroller.distros_md5 = lc_distros_md5
                flash( _(u"%s md5 updated" % labcontroller.fqdn) )
            else:
                flash( _(u"md5 has not changed"))
        else:
            flash( _(u"No Lab Controller id passed!"))
        redirect(".")

    @expose(template="medusa.templates.grid")
    @paginate('list')
    def index(self):
        labcontrollers = session.query(LabController)
        labcontrollers_grid = widgets.PaginateDataGrid(fields=[
                                  ('FQDN', lambda x: make_edit_link(x.fqdn,x.id)),
                                  ('distro_md5', lambda x: x.distros_md5),
                                  (' ', lambda x: make_remove_link(x.id)),
                              ])
        return dict(title="Lab Controllers", grid = labcontrollers_grid,
                                         search_bar = None,
                                         list = labcontrollers)

    @expose()
    def remove(self, **kw):
        labcontroller = LabController.by_id(kw['id'])
        session.delete(labcontroller)
        flash( _(u"%s Deleted") % labcontroller.fqdn )
        raise redirect(".")
