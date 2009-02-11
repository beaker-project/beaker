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
import time
import re

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
        labcontroller.distros_md5 = '0.0'

        flash( _(u"%s saved" % labcontroller.fqdn) )
        redirect(".")

    @expose()
    def rescan(self, **kw):
        if kw.get('id'):
            now = time.time()
            valid_variants = ['AS','ES','WS','Desktop']
            valid_methods  = ['http','ftp','nfs']

            labcontroller = LabController.by_id(kw['id'])
            url = "http://%s/cobbler_api_rw/" % labcontroller.fqdn
            now = time.time()
            remote = xmlrpclib.ServerProxy(url)
            token = remote.login(labcontroller.username,labcontroller.password)
            distros = []
            release = re.compile(r'family=(\w+\d+.\d+)')
            for lc_distro in remote.get_distros():
                name = lc_distro['name'].split('_')[0]
                meta = string.join(lc_distro['name'].split('_')[1:],'_').split('-')
                variant = None
                method = None
                virt = False
                
                for curr_variant in valid_variants:
                    if curr_variant in meta:
                        variant = curr_variant
                        break
                for curr_method in valid_methods:
                    if curr_method in meta:
                        method = curr_method
                        break
                if 'xen' in meta:
                    virt = True

                if 'comment' in lc_distro:
                    if release.search(lc_distro['comment']):
                        lc_os_version = release.search(lc_distro['comment']).group(1)
                    else:
                        continue

                    try:
                        distro = Distro.by_install_name(lc_distro['name'])
                    except: #FIXME
                        distro = Distro(lc_distro['name'])
                        distro.name = name
                        try:
                            breed = Breed.by_name(lc_distro['breed'])
                        except: #FIXME
                            breed = Breed(lc_distro['breed'])
                            session.save(breed)
                            session.flush([breed])
                        distro.breed = breed
                        lc_osmajor = lc_os_version.split('.')[0]
                        try:
                            lc_osminor = lc_os_version.split('.')[1]
                        except:
                            lc_osminor = 0
                        try:
                            osmajor = OSMajor.by_name(lc_osmajor)
                        except: #FIXME
                            osmajor = OSMajor(lc_osmajor)
                            session.save(osmajor)
                            session.flush([osmajor])
                        try:
                            osversion = OSVersion.by_name(osmajor,lc_osminor)
                        except: #FIXME
                            osversion = OSVersion(osmajor,lc_osminor)
                            session.save(osversion)
                            session.flush([osversion])
                        distro.osversion = osversion
                        try:
                            arch = Arch.by_name(lc_distro['arch'])
                        except: #FIXME
                            arch = Arch(lc_distro['arch'])
                            session.save(arch)
                            session.flush([arch])
                        distro.arch = arch
                        distro.variant = variant
                        distro.method = method
                        distro.virt = virt
                        distro.date_created = datetime.fromtimestamp(float(lc_distro['tree_build_time']))
                        activity = Activity(None,'XMLRPC','Added','Distro',None, lc_distro['name'])
                    distros.append(distro)
            for i in xrange(len(labcontroller.distros)-1,-1,-1):
                distro = labcontroller.distros[i]
                if distro not in distros:
                    activity = Activity(None,'XMLRPC','Removed','Distro',distro.install_name,None)
#                    del labcontroller.distros[i]
                    
            for distro in distros:
                if distro not in labcontroller.distros:
                    #FIXME Distro Activity Add
                    labcontroller.distros.append(distro)
            labcontroller.distros_md5 = now
        else:
            flash( _(u"No Lab Controller id passed!"))
        redirect(".")

    @expose(template="medusa.templates.grid_add")
    @paginate('list')
    def index(self):
        labcontrollers = session.query(LabController)
        labcontrollers_grid = widgets.PaginateDataGrid(fields=[
                                  ('FQDN', lambda x: make_edit_link(x.fqdn,x.id)),
                                  ('Timestamp', lambda x: x.distros_md5),
                                  (' ', lambda x: make_remove_link(x.id)),
                                  (' ', lambda x: make_scan_link(x.id)),
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
