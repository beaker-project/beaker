from turbogears.database import session
from turbogears import controllers, expose, flash, widgets, validate, error_handler, validators, redirect, paginate
from turbogears.widgets import AutoCompleteField
from turbogears import identity, redirect, config
from cherrypy import request, response
from tg_expanding_form_widget.tg_expanding_form_widget import ExpandingForm
from kid import Element
from bkr.server.xmlrpccontroller import RPCRoot
from bkr.server.helpers import *
from bkr.server.util import total_seconds
from bkr.server.widgets import LabControllerDataGrid, LabControllerForm
from bkr.server.distrotrees import DistroTrees
from xmlrpclib import ProtocolError
from sqlalchemy.orm import contains_eager, joinedload
import itertools
import cherrypy
import time
from datetime import datetime
import re
import urlparse

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
    @expose(template='bkr.server.templates.form-post')
    def new(self, **kw):
        return dict(
            form = self.labcontroller_form,
            action = './save',
            options = {},
            value = kw,
        )

    @identity.require(identity.in_group("admin"))
    @expose(template='bkr.server.templates.form-post')
    def edit(self, id, **kw):
        options = {}
        if id:
            labcontroller = LabController.by_id(id)
            options.update({'user' : labcontroller.user})
        else:
            labcontroller=None

        return dict(
            form = self.labcontroller_form,
            action = './save',
            options = options,
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
        if labcontroller.fqdn != kw['fqdn']:
            activity = LabControllerActivity(identity.current.user,
                'WEBUI', 'Changed', 'FQDN', labcontroller.fqdn, kw['fqdn'])
            labcontroller.fqdn = kw['fqdn']
            labcontroller.write_activity.append(activity)

        # labcontroller.user is used by the lab controller to login here
        try:
            # pick up an existing user if it exists.
            luser = User.query.filter_by(user_name=kw['lusername']).one()
        except InvalidRequestError:
            # Nope, create from scratch
            luser = User()
        if labcontroller.user != luser:
            if labcontroller.user is None:
                old_user_name = None
            else:
                old_user_name = labcontroller.user.user_name
            activity = LabControllerActivity(identity.current.user, 'WEBUI',
                'Changed', 'User', old_user_name, unicode(kw['lusername']))
            labcontroller.user = luser
            labcontroller.write_activity.append(activity)

        # Make sure user is a member of lab_controller group
        group = Group.by_name(u'lab_controller')
        if group not in luser.groups:
            luser.groups.append(group)
        luser.display_name = kw['fqdn']
        luser.email_address = kw['email']
        luser.user_name = kw['lusername']

        if kw['lpassword']:
            luser.password = kw['lpassword']
        if labcontroller.disabled != kw['disabled']:
            activity = LabControllerActivity(identity.current.user, 'WEBUI',
                'Changed', 'Disabled', unicode(labcontroller.disabled), 
                unicode(kw['disabled']))
            labcontroller.disabled = kw['disabled']
            labcontroller.write_activity.append(activity)

        flash( _(u"%s saved" % labcontroller.fqdn) )
        redirect(".")

    @cherrypy.expose
    @identity.require(identity.in_group("lab_controller"))
    def add_distro_tree(self, new_distro):
        lab_controller = identity.current.user.lab_controller

        # osmajor is required
        if 'osmajor' in new_distro:
            osmajor = OSMajor.lazy_create(osmajor=new_distro['osmajor'])
        else:
            return ''

        if 'osminor' in new_distro:
            osversion = OSVersion.lazy_create(osmajor=osmajor, osminor=new_distro['osminor'])
        else:
            return ''

        if 'arches' in new_distro:
            for arch_name in new_distro['arches']:
                try:
                   arch = Arch.by_name(arch_name)
                   if arch not in osversion.arches:
                       osversion.arches.append(arch)
                except NoResultFound:
                   pass

        distro = Distro.lazy_create(name=new_distro['name'], osversion=osversion)
        arch = Arch.lazy_create(arch=new_distro['arch'])
        variant = new_distro.get('variant')
        distro_tree = DistroTree.lazy_create(distro=distro,
                variant=variant, arch=arch)

        # Automatically tag the distro if tags exists
        if 'tags' in new_distro:
            for tag in new_distro['tags']:
                if tag not in distro.tags:
                    distro.tags.append(tag)

        if arch not in distro.osversion.arches:
            distro.osversion.arches.append(arch)
        distro_tree.date_created = datetime.utcfromtimestamp(float(new_distro['tree_build_time']))
        distro.date_created = datetime.utcfromtimestamp(float(new_distro['tree_build_time']))

        if 'repos' in new_distro:
            for repo in new_distro['repos']:
                dtr = distro_tree.repo_by_id(repo['repoid'])
                if dtr is None:
                    dtr = DistroTreeRepo(repo_id=repo['repoid'])
                    distro_tree.repos.append(dtr)
                dtr.repo_type = repo['type']
                dtr.path = repo['path']

        if 'kernel_options' in new_distro:
            distro_tree.kernel_options = new_distro['kernel_options']

        if 'kernel_options_post' in new_distro:
            distro_tree.kernel_options_post = new_distro['kernel_options_post']

        if 'ks_meta' in new_distro:
            distro_tree.ks_meta = new_distro['ks_meta']

        if 'images' in new_distro:
            for image in new_distro['images']:
                try:
                    image_type = ImageType.from_string(image['type'])
                except ValueError:
                    continue # ignore
                if 'kernel_type' not in image:
                    image['kernel_type'] = 'default'
                try:
                    kernel_type = KernelType.by_name(image['kernel_type'])
                except NoResultFound:
                    continue # ignore
                dti = distro_tree.image_by_type(image_type, kernel_type)
                if dti is None:
                    dti = DistroTreeImage(image_type=image_type,
                                          kernel_type=kernel_type)
                    distro_tree.images.append(dti)
                dti.path = image['path']

        new_urls_by_scheme = dict((urlparse.urlparse(url).scheme, url)
                for url in new_distro['urls'])
        if None in new_urls_by_scheme:
            raise ValueError('URL %r is not absolute' % new_urls_by_scheme[None])
        for lca in distro_tree.lab_controller_assocs:
            if lca.lab_controller == lab_controller:
                scheme = urlparse.urlparse(lca.url).scheme
                new_url = new_urls_by_scheme.pop(scheme, None)
                if new_url != None and lca.url != new_url:
                    distro_tree.activity.append(DistroTreeActivity(
                            user=identity.current.user, service=u'XMLRPC',
                            action=u'Changed', field_name=u'lab_controller_assocs',
                            old_value=u'%s %s' % (lca.lab_controller, lca.url),
                            new_value=u'%s %s' % (lca.lab_controller, new_url)))
                    lca.url = new_url
        for url in new_urls_by_scheme.values():
            distro_tree.lab_controller_assocs.append(LabControllerDistroTree(
                    lab_controller=lab_controller, url=url))
            distro_tree.activity.append(DistroTreeActivity(
                    user=identity.current.user, service=u'XMLRPC',
                    action=u'Added', field_name=u'lab_controller_assocs',
                    old_value=None, new_value=u'%s %s' % (lab_controller, url)))

        return distro_tree.id

    @cherrypy.expose
    @identity.require(identity.in_group("lab_controller"))
    def remove_distro_trees(self, distro_tree_ids):
        lab_controller = identity.current.user.lab_controller
        for distro_tree_id in distro_tree_ids:
            distro_tree = DistroTree.by_id(distro_tree_id)
            for lca in list(distro_tree.lab_controller_assocs):
                if lca.lab_controller == lab_controller:
                    distro_tree.lab_controller_assocs.remove(lca)
                    distro_tree.activity.append(DistroTreeActivity(
                            user=identity.current.user, service=u'XMLRPC',
                            action=u'Removed', field_name=u'lab_controller_assocs',
                            old_value=u'%s %s' % (lca.lab_controller, lca.url),
                            new_value=None))
        return True

    @cherrypy.expose
    @identity.require(identity.in_group('lab_controller'))
    def get_queued_command_details(self):
        lab_controller = identity.current.user.lab_controller
        max_running_commands = config.get('beaker.max_running_commands')
        if max_running_commands:
            running_commands = CommandActivity.query\
                    .join(CommandActivity.system)\
                    .filter(System.lab_controller == lab_controller)\
                    .filter(CommandActivity.status == CommandStatus.running)\
                    .count()
            if running_commands >= max_running_commands:
                return []
        query = CommandActivity.query\
                .join(CommandActivity.system)\
                .options(contains_eager(CommandActivity.system))\
                .filter(System.lab_controller == lab_controller)\
                .filter(CommandActivity.status == CommandStatus.queued)\
                .order_by(CommandActivity.id)
        if max_running_commands:
            query = query.limit(max_running_commands - running_commands)
        result = []
        for cmd in query:
            d = {
                'id': cmd.id,
                'action': cmd.action,
                'fqdn': cmd.system.fqdn,
                'arch': [arch.arch for arch in cmd.system.arch],
                'delay': 0,
            }
            if cmd.delay_until:
                d['delay'] = max(0, total_seconds(cmd.delay_until - datetime.utcnow()))
            # Fill in details specific to the type of command
            if cmd.action in (u'on', u'off', u'reboot', u'interrupt'):
                if not cmd.system.power:
                    cmd.abort(u'Power control unavailable for %s' % cmd.system)
                    continue
                d['power'] = {
                    'type': cmd.system.power.power_type.name,
                    'address': cmd.system.power.power_address,
                    'id': cmd.system.power.power_id,
                    'user': cmd.system.power.power_user,
                    'passwd': cmd.system.power.power_passwd,
                }
            elif cmd.action == u'configure_netboot':
                distro_tree_url = cmd.distro_tree.url_in_lab(lab_controller,
                        scheme=['http', 'ftp'])
                if not distro_tree_url:
                    cmd.abort(u'No usable URL found for distro tree %s in lab %s'
                            % (cmd.distro_tree.id, lab_controller.fqdn))
                    continue

                if cmd.system.kernel_type.uboot:
                    by_kernel = ImageType.uimage
                    by_initrd = ImageType.uinitrd
                else:
                    by_kernel = ImageType.kernel
                    by_initrd = ImageType.initrd

                kernel = cmd.distro_tree.image_by_type(by_kernel,
                                                       cmd.system.kernel_type)
                if not kernel:
                    cmd.abort(u'Kernel image not found for distro tree %s' % cmd.distro_tree.id)
                    continue
                initrd = cmd.distro_tree.image_by_type(by_initrd,
                                                       cmd.system.kernel_type)
                if not initrd:
                    cmd.abort(u'Initrd image not found for distro tree %s' % cmd.distro_tree.id)
                    continue
                d['netboot'] = {
                    'distro_tree_id': cmd.distro_tree.id,
                    'kernel_url': urlparse.urljoin(distro_tree_url, kernel.path),
                    'initrd_url': urlparse.urljoin(distro_tree_url, initrd.path),
                    'kernel_options': cmd.kernel_options or '',
                }
            result.append(d)
        return result

    @cherrypy.expose
    def get_last_netboot_for_system(self, fqdn):
        """
        This is only a temporary API for bz828927 until installation tracking 
        is properly fleshed out. At that point beaker-proxy should be updated 
        to use the new API.
        """
        cmd = CommandActivity.query\
                .join(CommandActivity.system)\
                .options(contains_eager(CommandActivity.system))\
                .filter(System.fqdn == fqdn)\
                .filter(CommandActivity.action == u'configure_netboot')\
                .filter(CommandActivity.status == CommandStatus.completed)\
                .order_by(CommandActivity.id.desc())\
                .first()
        if not cmd:
            raise ValueError('System %s has never been provisioned' % fqdn)
        distro_tree_url = cmd.distro_tree.url_in_lab(cmd.system.lab_controller, 'http')
        if not distro_tree_url:
            raise ValueError('No usable URL found for distro tree %s in lab %s'
                    % (cmd.distro_tree.id, lab_controller.fqdn))

        if cmd.system.kernel_type.uboot:
            by_kernel = ImageType.uimage
            by_initrd = ImageType.uinitrd
        else:
            by_kernel = ImageType.kernel
            by_initrd = ImageType.initrd

        kernel = cmd.distro_tree.image_by_type(by_kernel,
                                               cmd.system.kernel_type)
        if not kernel:
            raise ValueError('Kernel image not found for distro tree %s' % cmd.distro_tree.id)
        initrd = cmd.distro_tree.image_by_type(by_initrd,
                                               cmd.system.kernel_type)
        if not initrd:
            raise ValueError('Initrd image not found for distro tree %s' % cmd.distro_tree.id)
        return {
            'kernel_url': urlparse.urljoin(distro_tree_url, kernel.path),
            'initrd_url': urlparse.urljoin(distro_tree_url, initrd.path),
            'kernel_options': cmd.kernel_options or '',
            'distro_tree_urls': [lca.url for lca in cmd.distro_tree.lab_controller_assocs
                    if lca.lab_controller == cmd.system.lab_controller],
        }

    @cherrypy.expose
    @identity.require(identity.in_group('lab_controller'))
    def mark_command_running(self, command_id):
        lab_controller = identity.current.user.lab_controller
        cmd = CommandActivity.query.get(command_id)
        if cmd.system.lab_controller != lab_controller:
            raise ValueError('%s cannot update command for %s in wrong lab'
                    % (lab_controller, cmd.system))
        cmd.status = CommandStatus.running
        return True

    @cherrypy.expose
    @identity.require(identity.in_group('lab_controller'))
    def mark_command_completed(self, command_id):
        lab_controller = identity.current.user.lab_controller
        cmd = CommandActivity.query.get(command_id)
        if cmd.system.lab_controller != lab_controller:
            raise ValueError('%s cannot update command for %s in wrong lab'
                    % (lab_controller, cmd.system))
        cmd.status = CommandStatus.completed
        cmd.log_to_system_history()
        return True

    @cherrypy.expose
    @identity.require(identity.in_group('lab_controller'))
    def mark_command_failed(self, command_id, message=None):
        lab_controller = identity.current.user.lab_controller
        cmd = CommandActivity.query.get(command_id)
        if cmd.system.lab_controller != lab_controller:
            raise ValueError('%s cannot update command for %s in wrong lab'
                    % (lab_controller, cmd.system))
        cmd.status = CommandStatus.failed
        cmd.new_value = message
        if cmd.system.status == SystemStatus.automated:
            cmd.system.mark_broken(reason=u'Power command failed: %s' % message)
        cmd.log_to_system_history()
        return True

    @cherrypy.expose
    @identity.require(identity.in_group('lab_controller'))
    def clear_running_commands(self, message=None):
        """
        Called by beaker-provision on startup. Any commands which are Running
        at this point must be left over from an earlier crash.
        """
        lab_controller = identity.current.user.lab_controller
        running_commands = CommandActivity.query\
                .join(CommandActivity.system)\
                .filter(System.lab_controller == lab_controller)\
                .filter(CommandActivity.status == CommandStatus.running)
        for cmd in running_commands:
            cmd.status = CommandStatus.failed
            cmd.new_value = message
            cmd.log_to_system_history()
        return True

    @cherrypy.expose
    @identity.require(identity.in_group('lab_controller'))
    def get_distro_trees(self, filter=None):
        """
        Called by beaker-proxy. returns all active distro_trees
        for the lab controller that made the call.
        We have the lab controller do this because it may have access to 
        distros that the scheduler can't reach.
        """
        lab_controller = identity.current.user.lab_controller
        if filter is None:
            filter = {}
        if 'labcontroller' in filter and filter['labcontroller'] != lab_controller.fqdn:
            raise ValueError('Cannot filter on lab controller other than the currnet one')
        filter['labcontroller'] = lab_controller.fqdn
        distro_trees = DistroTrees().filter(filter)
        for dt in distro_trees:
            dt['available'] = [(lc, url) for lc, url in dt['available']
                    if lc == lab_controller.fqdn]
        return distro_trees

    def make_lc_remove_link(self, lc):
        if lc.removed is not None:
            return make_link(url  = 'unremove?id=%s' % lc.id,
                text = 'Re-Add (+)')
        else:
            a = Element('a', {'class': 'list'}, href='#')
            a.text = 'Remove (-)'
            a.attrib.update({'onclick' : "has_watchdog('%s')" % lc.id})
            return a

    @identity.require(identity.in_group("admin"))
    @expose(template="bkr.server.templates.grid_add")
    @paginate('list', limit=None)
    def index(self):
        labcontrollers = session.query(LabController)

        labcontrollers_grid = LabControllerDataGrid(fields=[
                                  ('FQDN', lambda x: make_edit_link(x.fqdn,x.id)),
                                  ('Disabled', lambda x: x.disabled),
                                  ('Removed', lambda x: x.removed),
                                  (' ', lambda x: self.make_lc_remove_link(x)),
                              ])
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

        LabControllerActivity(identity.current.user, 'WEBUI', 
            'Changed', 'Disabled', unicode(True), unicode(False),
            lab_controller_id = id)
        LabControllerActivity(identity.current.user, 'WEBUI', 
            'Changed', 'Removed', unicode(True), unicode(False), 
            lab_controller_id=id)
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
            systems = System.query.filter_by(lab_controller_id=id).values(System.id)
            for system_id in systems:
                sys_activity = SystemActivity(identity.current.user, 'WEBUI', \
                    'Changed', 'lab_controller', labcontroller.fqdn,
                    None, system_id=system_id[0])
            system_table.update().where(system_table.c.lab_controller_id == id).\
                values(lab_controller_id=None).execute()
            watchdogs = Watchdog.by_status(labcontroller=labcontroller, 
                status='active')
            for w in watchdogs:
                w.recipe.recipeset.job.cancel(msg='LabController %s has been deleted' % labcontroller.fqdn)
            for lca in labcontroller._distro_trees:
                lca.distro_tree.activity.append(DistroTreeActivity(
                        user=identity.current.user, service=u'WEBUI',
                        action=u'Removed', field_name=u'lab_controller_assocs',
                        old_value=u'%s %s' % (lca.lab_controller, lca.url),
                        new_value=None))
                session.delete(lca)
            labcontroller.disabled = True
            LabControllerActivity(identity.current.user, 'WEBUI', 
                'Changed', 'Disabled', unicode(False), unicode(True), 
                lab_controller_id=id)
            LabControllerActivity(identity.current.user, 'WEBUI', 
                'Changed', 'Removed', unicode(False), unicode(True), 
                lab_controller_id=id)
            session.commit()
        finally:
            session.close()

        flash( _(u"%s removed") % labcontroller.fqdn )
        raise redirect(".")
