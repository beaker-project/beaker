from turbogears.database import session
from turbogears import url, expose, flash, validate, error_handler, \
                       redirect, paginate, config
from kid import XML
from bkr.server import identity
from bkr.server.xmlrpccontroller import RPCRoot
from bkr.server.helpers import make_edit_link
from bkr.server.util import total_seconds
from bkr.server.widgets import LabControllerDataGrid, LabControllerForm
from bkr.server.distrotrees import DistroTrees
from bkr.common.bexceptions import BX
from sqlalchemy.orm import contains_eager
import cherrypy
from datetime import datetime, timedelta
import urlparse

from bkr.server.model import \
    LabController, LabControllerActivity, User, Group, OSMajor, OSVersion, \
    Arch, Distro, DistroTree, DistroTreeRepo, DistroTreeImage, \
    DistroTreeActivity, LabControllerDistroTree, ImageType, KernelType, \
    System, SystemStatus, SystemActivity, system_table, \
    Watchdog, CommandActivity, CommandStatus, command_queue_table, \
    NoResultFound, InvalidRequestError

import logging
log = logging.getLogger(__name__)

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
            title='New Lab Controller'
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
            title='Edit Lab Controller'
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

        variant = new_distro.get('variant')
        arch = Arch.lazy_create(arch=new_distro['arch'])

        osmajor = OSMajor.lazy_create(osmajor=new_distro['osmajor'])
        try:
            osmajor = OSMajor.by_alias(new_distro['osmajor'])
        except NoResultFound:
            pass
        else:
            raise BX(_('Cannot import distro as %s: it is configured as an alias for %s' 
                       % (new_distro['osmajor'], osmajor.osmajor)))

        osversion = OSVersion.lazy_create(osmajor=osmajor, osminor=new_distro['osminor'])
        if 'arches' in new_distro:
            for arch_name in new_distro['arches']:
                osversion.add_arch(Arch.lazy_create(arch=arch_name))
        osversion.add_arch(arch)

        distro = Distro.lazy_create(name=new_distro['name'], osversion=osversion)
        # Automatically tag the distro if tags exists
        if 'tags' in new_distro:
            for tag in new_distro['tags']:
                distro.add_tag(tag)
        distro.date_created = datetime.utcfromtimestamp(float(new_distro['tree_build_time']))

        distro_tree = DistroTree.lazy_create(distro=distro,
                variant=variant, arch=arch)
        distro_tree.date_created = datetime.utcfromtimestamp(float(new_distro['tree_build_time']))

        if 'repos' in new_distro:
            for repo in new_distro['repos']:
                dtr = DistroTreeRepo.lazy_create(distro_tree=distro_tree,
                        repo_id=repo['repoid'], repo_type=repo['type'],
                        path=repo['path'])

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
                dti = DistroTreeImage.lazy_create(distro_tree=distro_tree,
                        image_type=image_type, kernel_type=kernel_type,
                        path=image['path'])

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
            distro_tree.expire(lab_controller=lab_controller)
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
                    % (cmd.distro_tree.id, cmd.system.lab_controller.fqdn))

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
        if cmd.status != CommandStatus.queued:
            raise ValueError('Command %s already run' % command_id)
        cmd.change_status(CommandStatus.running)
        return True

    @cherrypy.expose
    @identity.require(identity.in_group('lab_controller'))
    def mark_command_completed(self, command_id):
        lab_controller = identity.current.user.lab_controller
        cmd = CommandActivity.query.get(command_id)
        if cmd.system.lab_controller != lab_controller:
            raise ValueError('%s cannot update command for %s in wrong lab'
                    % (lab_controller, cmd.system))
        if cmd.status != CommandStatus.running:
            raise ValueError('Command %s not running' % command_id)
        cmd.change_status(CommandStatus.completed)
        cmd.log_to_system_history()
        return True

    @cherrypy.expose
    @identity.require(identity.in_group('lab_controller'))
    def add_completed_command(self, fqdn, action):
        # Reports completion of a command that was executed
        # synchronously by the lab controller
        user = identity.current.user
        system = System.by_fqdn(fqdn, user)
        cmd = CommandActivity(user=user,
                              service=u"XMLRPC",
                              action=action,
                              status=CommandStatus.completed)
        system.command_queue.append(cmd)
        session.flush() # Populates cmd.system (needed for next call)
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
        if cmd.status != CommandStatus.running:
            raise ValueError('Command %s not running' % command_id)
        cmd.change_status(CommandStatus.failed)
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
        # If the connection between the LCs and the main server is unreliable
        # commands may end up stuck in "running" state. We mitigate the
        # effects of this by purging all stale commands (those more than a
        # day old) whenever a lab controller restarts and tries to clear the
        # possibly interrupted commands for that lab.
        # We deliberately bypass the callbacks on these old commands, since
        # the affected systems may now be running unrelated recipes. Longer
        # term, we'll likely update the command system to remember the
        # associated recipe, not just the associated system
        # See https://bugzilla.redhat.com/show_bug.cgi?id=974319 and
        # https://bugzilla.redhat.com/show_bug.cgi?id=974352 for more
        # details.
        lab_controller = identity.current.user.lab_controller
        purged = (
            command_queue_table.update()
            .where(command_queue_table.c.status == CommandStatus.running)
            .where(command_queue_table.c.updated <
                       datetime.utcnow() - timedelta(days=1))
            .values(status=CommandStatus.aborted)
            .execute()
        )
        if purged.rowcount:
            msg = ("Aborted %d stale commands before aborting "
                   "recent running commands for %s")
            log.warn(msg, purged.rowcount, lab_controller.fqdn)
        running_commands = CommandActivity.query\
                .join(CommandActivity.system)\
                .filter(System.lab_controller == lab_controller)\
                .filter(CommandActivity.status == CommandStatus.running)
        for cmd in running_commands:
            cmd.abort(message)
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
            return XML('<a class="btn" href="unremove?id=%s">'
                    '<i class="icon-plus"/> Re-Add</a>' % lc.id)
        else:
            return XML('<a class="btn" href="#" onclick="has_watchdog(\'%s\')">'
                    '<i class="icon-remove"/> Remove</a>' % lc.id)

    @identity.require(identity.in_group("admin"))
    @expose(template="bkr.server.templates.grid")
    @paginate('list', limit=None)
    def index(self):
        labcontrollers = session.query(LabController)

        labcontrollers_grid = LabControllerDataGrid(fields=[
                                  ('FQDN', lambda x: make_edit_link(x.fqdn,x.id)),
                                  ('Disabled', lambda x: x.disabled),
                                  ('Removed', lambda x: x.removed),
                                  (' ', lambda x: self.make_lc_remove_link(x)),
                              ],
                              add_action='./new')
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
        count = Watchdog.by_status(labcontroller=labcontroller, status='active').count()
        if count:
            return {'has_active_recipes' : True}
        else:
            return {'has_active_recipes' : False}

    @identity.require(identity.in_group("admin"))
    @expose()
    def remove(self, id, *args, **kw):
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

        flash( _(u"%s removed") % labcontroller.fqdn )
        raise redirect(".")
