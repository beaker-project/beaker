from turbogears.database import session
from turbogears import controllers, expose, flash, widgets, validate, error_handler, validators, redirect, paginate
from turbogears.widgets import AutoCompleteField
from turbogears import identity, redirect
from cherrypy import request, response
from tg_expanding_form_widget.tg_expanding_form_widget import ExpandingForm
from kid import Element
from bkr.server.xmlrpccontroller import RPCRoot
from bkr.server.helpers import *
from bkr.server.widgets import LabControllerDataGrid, LabControllerForm
from xmlrpclib import ProtocolError

import cherrypy
import time
import datetime
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

class LabControllers(RPCRoot):
    # For XMLRPC methods in this class.
    exposed = True

    labcontroller_form = LabControllerForm()

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
            options = {'user': labcontroller.user},
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
        # labcontroller.username and password is used to login to 
        # the lab controller
        labcontroller.username = kw['username']
        labcontroller.password = kw['password']

        # labcontroller.user is used by the lab controller to login here
        try:
            # pick up an existing user if it exists.
            luser = User.query.filter_by(user_name=kw['lusername']).one()
        except InvalidRequestError:
            # Nope, create from scratch
            luser = User()
        if labcontroller.user != luser:
            labcontroller.user = luser

        # Make sure user is a member of lab_controller group
        group = Group.by_name(u'lab_controller')
        if group not in luser.groups:
            luser.groups.append(group)
        # Verify email address is unique.
        try:
            ouser = User.by_email_address(kw['email'])
        except InvalidRequestError:
            ouser = None
        if ouser and ouser != luser:
            session.rollback()
            flash( _(u"%s not saved, Duplicate email address" % labcontroller.fqdn) )
            redirect(".")
        
        luser.display_name = kw['fqdn']
        luser.email_address = kw['email']
        luser.user_name = kw['lusername']
        if kw['lpassword']:
            luser.password = kw['lpassword']
        labcontroller.disabled = kw['disabled']

        labcontroller.distros_md5 = '0.0'

        flash( _(u"%s saved" % labcontroller.fqdn) )
        redirect(".")

    @cherrypy.expose
    @identity.require(identity.in_group("lab_controller"))
    def addDistro(self, new_distro):
        distro = self._addDistro(identity.current.user.lab_controller,
                               new_distro)
        if distro:
            activity = Activity(identity.current.user,'XMLRPC','Added LabController',distro.install_name,None,identity.current.user.lab_controller.fqdn)
            return distro.install_name
        else:
            return ""

    @cherrypy.expose
    def addDistros(self, lab_controller_name, new_distros):
        """
        DEPRECATED
        XMLRPC Push method for adding distros
        """
        distros = self._addDistros(lab_controller_name, new_distros)
        return [distro.install_name for distro in distros]

    def _addDistros(self, lab_controller_name, new_distros):
        """
        DEPRECATED
        Internal Push method for adding distros
        """
        try:
            lab_controller = LabController.by_name(lab_controller_name)
        except InvalidRequestError:
            raise "Invalid Lab Controller"
        distros = []
        for new_distro in new_distros:
            distro = self._addDistro(lab_controller, new_distro)
            if distro:
                activity = Activity(identity.current.user,'XMLRPC','Added LabController',distro.install_name,None,lab_controller.fqdn)
                distros.append(distro)
        return distros

    def _addDistro(self, lab_controller, new_distro):
        arches = []

        # Try and look up the distro by the install name
        try:
            distro = Distro.by_install_name(new_distro['name'])
        except InvalidRequestError:
            distro = Distro(new_distro['name'])
            distro.name = new_distro['treename']

        # All the arches this distro's osmajor applies to
        if 'arches' in new_distro:
            for arch_name in new_distro['arches']:
                try:
                   arches.append(Arch.by_name(arch_name))
                except InvalidRequestError:
                   pass

        # osmajor is required
        if 'osmajor' in new_distro:
            try:
                osmajor = OSMajor.by_name(new_distro['osmajor'])
            except InvalidRequestError:
                osmajor = OSMajor(new_distro['osmajor'])
                session.save(osmajor)
                session.flush([osmajor])
        else:
            return

        if 'osminor' in new_distro:
            try:
                osversion = OSVersion.by_name(osmajor,new_distro['osminor'])
            except InvalidRequestError:
                osversion = OSVersion(osmajor,new_distro['osminor'],arches)
                session.save(osversion)
                session.flush([osversion])
            distro.osversion = osversion
        else:
            return

        # If variant is specified in comment then use it.
        if 'variant' in new_distro:
            distro.variant = new_distro['variant']

        if 'breed' in new_distro:
            try:
                breed = Breed.by_name(new_distro['breed'])
            except InvalidRequestError:
                breed = Breed(new_distro['breed'])
                session.save(breed)
                session.flush([breed])
            distro.breed = breed

        # Automatically tag the distro if tags exists
        if 'tags' in new_distro:
            for tag in new_distro['tags']:
                if tag not in distro.tags:
                    distro.tags.append(tag)

        try:
            arch = Arch.by_name(new_distro['arch'])
        except InvalidRequestError:
            arch = Arch(new_distro['arch'])
            session.save(arch)
            session.flush([arch])
        distro.arch = arch
        if arch not in distro.osversion.arches:
            distro.osversion.arches.append(arch)
        # XXX temporary hotfix
        distro.virt = '-xen-' in new_distro['name']
        distro.date_created = datetime.fromtimestamp(float(new_distro['tree_build_time']))
        if distro not in lab_controller.distros:
            lcd = LabControllerDistro()
            lcd.distro = distro
            if 'tree' in new_distro['ks_meta']:
                lcd.tree_path = new_distro['ks_meta']['tree']
            lab_controller._distros.append(lcd)
        return distro

    @cherrypy.expose
    @identity.require(identity.in_group("lab_controller"))
    def removeDistro(self, old_distro):
        distro = self._removeDistro(identity.current.user.lab_controller,
                                  old_distro)
        if distro:
            activity = Activity(identity.current.user,'XMLRPC','Removed LabController',distro.install_name,None,identity.current.user.lab_controller.fqdn)
            return distro.install_name
        else:
            return ""

    @cherrypy.expose
    def removeDistros(self, lab_controller_name, old_distros):
        """
        DEPRECATED
        XMLRPC Push method for adding distros
        """
        distros = self._removeDistros(lab_controller_name, old_distros)
        return [distro.install_name for distro in distros]

    def _removeDistros(self, lab_controller_name, old_distros):
        """
        DEPRECATED
        Internal Push method for adding distros
        """
        try:
            lab_controller = LabController.by_name(lab_controller_name)
        except InvalidRequestError:
            raise "Invalid Lab Controller"
        distros = []
        for old_distro in old_distros:
            distro = self._removeDistro(lab_controller, old_distro)
            if distro:
                activity = Activity(identity.current.user,'XMLRPC','Removed LabController',distro.install_name,None,lab_controller.fqdn)
                distros.append(distro)
        return distros

    def _removeDistro(self, lab_controller, old_distro):
        """
        Push method for removing distro
        """
        try:
            distro = Distro.by_install_name(old_distro)
        except InvalidRequestError:
            pass

        if lab_controller in distro.lab_controllers:
            distro.lab_controllers.remove(lab_controller)
            return distro
        else:
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

    def make_lc_remove_link(self, lc):
        if lc.removed is not None:
            return make_link(url  = 'unremove?id=%s' % lc.id,
                text = 'Re-Add (+)')
        else:
            a = Element('a', {'class': 'list'}, href='#')
            a.text = 'Remove (-)'
            a.attrib.update({'onclick' : "has_watchdog('%s')" % lc.id})
            return a

    def make_lc_scan_link(self, lc):
        if lc.removed:
            return
        return make_scan_link(lc.id)
            
            
    @identity.require(identity.in_group("admin"))
    @expose(template="bkr.server.templates.grid_add")
    @paginate('list')
    def index(self):
        labcontrollers = session.query(LabController)

        labcontrollers_grid = LabControllerDataGrid(fields=[
                                  ('FQDN', lambda x: make_edit_link(x.fqdn,x.id)),
                                  ('Disabled', lambda x: x.disabled),
                                  ('Removed', lambda x: x.removed),
                                  ('Timestamp', lambda x: x.distros_md5),
                                  (' ', lambda x: self.make_lc_remove_link(x)),
                              ])
#                                  (' ', lambda x: self.make_lc_scan_link(x)),
        return dict(title="Lab Controllers", 
                    grid = labcontrollers_grid,
                    search_bar = None,
                    object_count = labcontrollers.count(),
                    list = labcontrollers)


    @identity.require(identity.in_group("admin"))
    @expose()
    def unremove(self, id):
        labcontroller = LabController.by_id(id)
        labcontroller.removed = None
        labcontroller.disabled = False
        flash('Succesfully re-added %s' % labcontroller.fqdn)
        redirect(url('.'))

    @expose('json')
    def has_active_recipes(self, id):
        labcontroller = LabController.by_id(id)
        count = labcontroller.dyn_systems.filter(System.watchdog != None).count()
        if count:
            return {'has_active_recipes' : True}
        else:
            return {'has_active_recipes' : False}

    @identity.require(identity.in_group("admin"))
    @expose()
    def remove(self, id, *args, **kw):
        try:
            labcontroller = LabController.by_id(id)
            labcontroller.removed = datetime.utcnow()
            system_table.update().where(system_table.c.lab_controller_id == id).\
                values(lab_controller_id=None).execute()
            watchdogs = Watchdog.by_status(labcontroller=labcontroller, 
                status='active')
            for w in watchdogs:
                w.recipe.recipeset.job.cancel(msg='LabController %s has been deleted' % labcontroller.fqdn)
            labcontroller.disabled = True
            session.commit()
        finally:
            session.close()

        flash( _(u"%s Removed") % labcontroller.fqdn )
        raise redirect(".")
