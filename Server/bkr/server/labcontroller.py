from turbogears.database import session
from turbogears import controllers, expose, flash, widgets, validate, error_handler, validators, redirect, paginate
from turbogears.widgets import AutoCompleteField
from turbogears import identity, redirect
from cherrypy import request, response
from tg_expanding_form_widget.tg_expanding_form_widget import ExpandingForm
from kid import Element
from bkr.server.xmlrpccontroller import RPCRoot
from bkr.server.helpers import *
from bkr.server.widgets import myPaginateDataGrid
from xmlrpclib import ProtocolError

import cherrypy
import time
import re

from BasicAuthTransport import BasicAuthTransport
import xmlrpclib
import bkr.timeout_xmlrpclib

# from bkr.server import json
# import logging
# log = logging.getLogger("bkr.server.controllers")
#import model
from model import *
import string

# Validation Schemas

class LabControllerFormSchema(validators.Schema):
    fqdn = validators.UnicodeString(not_empty=True, max=256, strip=True)

class LabControllers(RPCRoot):
    # For XMLRPC methods in this class.
    exposed = True

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

    @identity.require(identity.in_group("admin"))
    @expose(template='bkr.server.templates.form')
    def new(self, **kw):
        return dict(
            form = self.labcontroller_form,
            action = './save',
            options = {},
            value = kw,
        )

    @identity.require(identity.in_group("admin"))
    @expose(template='bkr.server.templates.form')
    def edit(self, id, **kw):
        labcontroller = LabController.by_id(id)
        return dict(
            form = self.labcontroller_form,
            action = './save',
            options = {},
            value = labcontroller,
        )

    @identity.require(identity.in_group("admin"))
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

    @cherrypy.expose
    def addDistros(self, lc_name, lc_distros):
        """
        XMLRPC Push method for adding distros
        """
        distros = self._addDistros(lc_name, lc_distros)
        return [distro.install_name for distro in distros]

    def _addDistros(self, lc_name, lc_distros):
        """
        Internal Push method for adding distros
        """
        try:
            labcontroller = LabController.by_name(lc_name)
        except InvalidRequestError:
            raise "Invalid Lab Controller"
        distros = []
        valid_variants = ['AS','ES','WS','Desktop']
        valid_methods  = ['http','ftp','nfs']
        release = re.compile(r'family=([^\s]+)')
        arches_search = re.compile(r'arches=([^\s]+)')
        variant_search = re.compile(r'variant=([^\s]+)')
        for lc_distro in lc_distros:
            name = lc_distro['name'].split('_')[0]
            meta = string.join(lc_distro['name'].split('_')[1:],'_').split('-')
            variant = None
            method = None
            virt = False
            arches = []
            
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

                if arches_search.search(lc_distro['comment']):
                    arch_names = arches_search.search(lc_distro['comment']).group(1).split(',')
                    for arch_name in arch_names:
                        try:
                           arches.append(Arch.by_name(arch_name))
                        except InvalidRequestError:
                           pass

                # If variant is specified in comment then use it.
                if variant_search.search(lc_distro['comment']):
                    variant = variant_search.search(lc_distro['comment']).group(1)

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
                        osversion = OSVersion(osmajor,lc_osminor,arches)
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
                    if arch not in distro.osversion.arches:
                        distro.osversion.arches.append(arch)
                    distro.variant = variant
                    distro.method = method
                    distro.virt = virt
                    distro.date_created = datetime.fromtimestamp(float(lc_distro['tree_build_time']))
                    activity = Activity(None,'XMLRPC','Added','Distro',None, lc_distro['name'])
                if distro not in labcontroller.distros:
                    #FIXME Distro Activity Add
                    lcd = LabControllerDistro()
                    lcd.distro = distro
                    if 'tree' in lc_distro['ks_meta']:
                        lcd.tree_path = lc_distro['ks_meta']['tree']
                    labcontroller._distros.append(lcd)
                distros.append(distro)
        return distros

    @cherrypy.expose
    def removeDistros(self, lc_name, distro_names):
        """
        Push method for removing distros
        """
        distros = []
        deleteddistros = []
        try:
            labcontroller = LabController.by_name(lc_name)
        except InvalidRequestError:
            raise "Invalid Lab Controller"
        for distro_name in distro_names:
            try:
                distro = Distro.by_install_name(distro_name)
            except InvalidRequestError:
                continue
            distros.append(distro)

        for i in xrange(len(labcontroller._distros)-1,-1,-1):
            distro = labcontroller._distros[i].distro
            if distro in distros:
                deleteddistros.append(distro.install_name)
                activity = Activity(None,'XMLRPC','Removed','Distro',distro.install_name,None)
                session.delete(labcontroller._distros[i])
        return None

    @identity.require(identity.in_group("admin"))
    @expose()
    def rescan(self, **kw):
        if kw.get('id'):
            labcontroller = LabController.by_id(kw['id'])
            now = time.time()
            url = "http://%s/cobbler_api" % labcontroller.fqdn
            remote = bkr.timeout_xmlrpclib.ServerProxy(url)
            try:
                token = remote.login(labcontroller.username,
                                 labcontroller.password)
            except xmlrpclib.Fault, msg:
                flash( _(u"Failed to login: %s" % msg))
                
            lc_distros = remote.get_distros()

            distros = self._addDistros(labcontroller.fqdn, lc_distros)

            for i in xrange(len(labcontroller._distros)-1,-1,-1):
                distro = labcontroller._distros[i].distro
                if distro not in distros:
                    activity = Activity(None,'XMLRPC','Removed','Distro',distro.install_name,None)
                    session.delete(labcontroller._distros[i])
                    
            labcontroller.distros_md5 = now
        else:
            flash( _(u"No Lab Controller id passed!"))
        redirect(".")

    @identity.require(identity.in_group("admin"))
    @expose(template="bkr.server.templates.grid_add")
    @paginate('list')
    def index(self):
        labcontrollers = session.query(LabController)
        labcontrollers_grid = myPaginateDataGrid(fields=[
                                  ('FQDN', lambda x: make_edit_link(x.fqdn,x.id)),
                                  ('Timestamp', lambda x: x.distros_md5),
                                  (' ', lambda x: make_remove_link(x.id)),
                                  (' ', lambda x: make_scan_link(x.id)),
                              ])
        return dict(title="Lab Controllers", 
                    grid = labcontrollers_grid,
                    search_bar = None,
                    object_count = labcontrollers.count(),
                    list = labcontrollers)

    @identity.require(identity.in_group("admin"))
    @expose()
    def remove(self, **kw):
        labcontroller = LabController.by_id(kw['id'])
        session.delete(labcontroller)
        flash( _(u"%s Deleted") % labcontroller.fqdn )
        raise redirect(".")
