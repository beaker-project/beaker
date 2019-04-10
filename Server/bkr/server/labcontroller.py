
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from turbogears.database import session
from turbogears import config
from bkr.server import identity
from bkr.server.xmlrpccontroller import RPCRoot
from bkr.server.distrotrees import DistroTrees
from bkr.common.helpers import total_seconds
from bkr.common.bexceptions import BX
from sqlalchemy.orm import contains_eager
from sqlalchemy.orm.exc import NoResultFound
import cherrypy
from datetime import datetime, timedelta
import urlparse

from flask import request, jsonify
from bkr.server.app import app
from bkr.server.flask_util import auth_required, read_json_request, \
    BadRequest400, Forbidden403, NotFound404, request_wants_json, \
    render_tg_template, convert_internal_errors, Conflict409
from bkr.server.util import absolute_url
from bkr.server.model import \
    LabController, User, Group, OSMajor, OSVersion, \
    Arch, Distro, DistroTree, DistroTreeRepo, DistroTreeImage, \
    DistroTreeActivity, LabControllerDistroTree, ImageType, KernelType, \
    System, SystemStatus, Watchdog, Command, CommandStatus

import logging
log = logging.getLogger(__name__)


def find_labcontroller_or_raise404(fqdn):
    """Returns a lab controller object or raises a NotFound404 error if the lab
    controller does not exist in the database."""
    try:
        labcontroller = LabController.by_name(fqdn)
    except NoResultFound:
        raise NotFound404('Lab controller %s does not exist' % fqdn)
    return labcontroller

def restore_labcontroller(labcontroller):
    """
    Restores a disabled and removed lab controller.
    """
    labcontroller.removed = None
    labcontroller.disabled = False

    labcontroller.record_activity(
        user=identity.current.user, service=u'HTTP',
        field=u'Disabled', action=u'Changed', old=unicode(True), new=unicode(False))
    labcontroller.record_activity(
        user=identity.current.user, service=u'HTTP',
        field=u'Removed', action=u'Changed', old=unicode(True), new=unicode(False))

def remove_labcontroller(labcontroller):
    """
    Disables and marks a lab controller as removed.
    """
    labcontroller.removed = datetime.utcnow()
    systems = System.query.filter(System.lab_controller == labcontroller)

    # Record systems set to status=broken. Trigger any event listener listening
    # for status changes.
    for sys in systems:
        sys.mark_broken('Lab controller de-associated')
        sys.abort_queued_commands("System disassociated from lab controller")
    # de-associate systems
    System.record_bulk_activity(systems, user=identity.current.user,
                                service=u'HTTP', action=u'Changed', field=u'Lab Controller',
                                old=labcontroller.fqdn, new=None)
    systems.update({'lab_controller_id': None},
                   synchronize_session=False)

    # cancel running recipes
    watchdogs = Watchdog.by_status(labcontroller=labcontroller,
                                   status='active')
    for w in watchdogs:
        w.recipe.recipeset.job.cancel(msg='Lab controller %s has been deleted' % labcontroller.fqdn)

    # remove distro trees
    distro_tree_assocs = LabControllerDistroTree.query\
        .filter(LabControllerDistroTree.lab_controller == labcontroller)
    DistroTree.record_bulk_activity(
        distro_tree_assocs.join(LabControllerDistroTree.distro_tree),
        user=identity.current.user, service=u'HTTP',
        action=u'Removed', field=u'lab_controller_assocs',
        old=labcontroller.fqdn, new=None)
    distro_tree_assocs.delete(synchronize_session=False)
    labcontroller.disabled = True
    labcontroller.record_activity(
        user=identity.current.user, service=u'HTTP',
        field=u'Disabled', action=u'Changed', old=unicode(False), new=unicode(True))
    labcontroller.record_activity(
        user=identity.current.user, service=u'HTTP',
        field=u'Removed', action=u'Changed', old=unicode(False), new=unicode(True))

def find_user_or_create(user_name):
    user = User.by_user_name(user_name)
    if user is None:
        user = User(user_name=user_name)
        user.user_name = user_name
        session.add(user)
    return user

def update_user(user, display_name=None, email_address=None, password=''):
    if user.lab_controller:
        raise BadRequest400(
            'User %s is already associated with lab controller %s' % (
                user, user.lab_controller))
    user.display_name = display_name
    user.email_address = email_address
    if password:
        user.password = password

    group = Group.by_name(u'lab_controller')
    if group not in user.groups:
        group.add_member(user, agent=identity.current.user)
    return user

@app.route('/labcontrollers/<fqdn>', methods=['PATCH'])
@auth_required
def update_labcontroller(fqdn):
    """
    Updates attributes of the lab controller identified by it's FQDN. The
    request body must be a json object or only the FQDN if
    that is the only value to be updated.

    :param string fqdn: Lab controller's new fully-qualified domain name.
    :jsonparam string user_name: User name associated with the lab controller.
    :jsonparam string email_address: Email of the user account associated with the lab controller.
    :jsonparam string password: Optional password for the user account used to login.
    :jsonparam string removed: If True, detaches all systems, cancels all
        running recipes and removes associated distro trees. If False, restores
        the lab controller.
    :jsonparam bool disabled: Whether the lab controller should be disabled. New
        recipes are not scheduled on a lab controller while it is disabled.
    :status 200: LabController updated.
    :status 400: Invalid data was given.
    """
    labcontroller = find_labcontroller_or_raise404(fqdn)
    if not labcontroller.can_edit(identity.current.user):
        raise Forbidden403('Cannot edit lab controller')
    data = read_json_request(request)
    with convert_internal_errors():
        # should the lab controller be removed?
        if data.get('removed', False) and not labcontroller.removed:
            remove_labcontroller(labcontroller)

        # should the controller be restored?
        if data.get('removed') is False and labcontroller.removed:
            restore_labcontroller(labcontroller)
        fqdn_changed = False
        new_fqdn = data.get('fqdn', fqdn)
        if labcontroller.fqdn != new_fqdn:
            lc = None
            try:
                lc = LabController.by_name(new_fqdn)
            except NoResultFound:
                pass
            if lc is not None:
                raise BadRequest400('FQDN %s already in use' % new_fqdn)

            labcontroller.record_activity(
                user=identity.current.user, service=u'HTTP',
                field=u'fqdn', action=u'Changed', old=labcontroller.fqdn, new=new_fqdn)
            labcontroller.fqdn = new_fqdn
            labcontroller.user.display_name = new_fqdn
            fqdn_changed = True
        if 'user_name' in data:
            user = find_user_or_create(data['user_name'])
            if labcontroller.user != user:
                user = update_user(
                    user,
                    display_name=new_fqdn,
                    email_address=data.get('email_address', user.email_address),
                    password=data.get('password', user.password)
                )
                labcontroller.record_activity(
                    user=identity.current.user, service=u'HTTP',
                    field=u'User', action=u'Changed',
                    old=labcontroller.user.user_name, new=user.user_name)
                labcontroller.user = user
        if 'email_address' in data:
            new_email_address = data.get('email_address')
            if labcontroller.user.email_address != new_email_address:
                labcontroller.user.email_address = new_email_address
        if data.get('password') is not None:
            labcontroller.user.password = data.get('password')
        if labcontroller.disabled != data.get('disabled', labcontroller.disabled):
            labcontroller.record_activity(
                user=identity.current.user, service=u'HTTP',
                field=u'disabled', action=u'Changed',
                old=unicode(labcontroller.disabled), new=data['disabled'])
            labcontroller.disabled = data['disabled']

    response = jsonify(labcontroller.__json__())
    if fqdn_changed:
        response.headers.add('Location', absolute_url(labcontroller.href))
    return response

@app.route('/labcontrollers/<fqdn>', methods=['GET'])
def get_labcontroller(fqdn):
    """Returns detailed information about a lab controller in JSON.

    :param fqdn: The lab controllers FQDN
    """
    labcontroller = find_labcontroller_or_raise404(fqdn)
    return jsonify(labcontroller.__json__())

@app.route('/labcontrollers/', methods=['GET'])
def get_labcontrollers():
    """Returns a JSON collection of all labcontrollers defined in Beaker."""
    labcontrollers = LabController.query.order_by(LabController.fqdn).all()
    if request_wants_json():
        return jsonify(entries=labcontrollers)
    can_edit = identity.current.user is not None and identity.current.user.is_admin()
    return render_tg_template('bkr.server.templates.labcontrollers', {
        'title': 'Lab Controllers',
        'labcontrollers': labcontrollers,
        'labcontrollers_url': absolute_url('/labcontrollers/'),
        'can_edit': can_edit,
    })

@app.route('/labcontrollers/', methods=['POST'])
@auth_required
def create_labcontroller():
    """
    Creates a new lab controller. The request must be :mimetype:`application/json`.

    :jsonparam string fqdn: Lab controller's new fully-qualified domain name.
    :jsonparam string user_name: User name associated with the lab controller.
    :jsonparam string email_address: Email of the user account associated with the lab controller.
    :jsonparam string password: Optional password for the user account used to login.
    :status 201: The lab controller was successfully created.
    :status 400: Invalid data was given.
    """
    data = read_json_request(request)
    return _create_labcontroller_helper(data)

def _create_labcontroller_helper(data):
    with convert_internal_errors():
        if LabController.query.filter_by(fqdn=data['fqdn']).count():
            raise Conflict409('Lab Controller %s already exists' % data['fqdn'])

        user = find_user_or_create(data['user_name'])
        user = update_user(
            user=user,
            display_name=data['fqdn'],
            email_address=data.get('email_address', user.email_address),
            password=data.get('password', user.password)
        )
        labcontroller = LabController(fqdn=data['fqdn'], disabled=False)
        labcontroller.record_activity(
            user=identity.current.user, service=u'HTTP',
            action=u'Changed', field=u'FQDN', old=u'', new=data['fqdn'])

        labcontroller.user = user
        labcontroller.record_activity(
            user=identity.current.user, service=u'HTTP',
            action=u'Changed', field=u'User', old=u'', new=user.user_name)

        # For backwards compatibility
        labcontroller.record_activity(
            user=identity.current.user, service=u'HTTP',
            action=u'Changed', field=u'Disabled', old=u'', new=unicode(labcontroller.disabled))

        session.add(labcontroller)
        # flush it so we return an id, otherwise we'll end up back in here from
        # the edit form
        session.flush()

    response = jsonify(labcontroller.__json__())
    response.status_code = 201
    return response

# backwards compatibility
# Remove me once https://bugzilla.redhat.com/show_bug.cgi?id=1211119 is fixed
@app.route('/labcontrollers/save', methods=['POST'])
@auth_required
def save_labcontroller():
    data = request.form
    return _create_labcontroller_helper(dict(user_name=data['lusername'],
                                             email_address=data['email'],
                                             password=data['lpassword'],
                                             fqdn=data['fqdn']))


class LabControllers(RPCRoot):
    # For XMLRPC methods in this class.
    exposed = True

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
                except ValueError:
                    continue # ignore
                dti = DistroTreeImage.lazy_create(distro_tree=distro_tree,
                        image_type=image_type, kernel_type=kernel_type,
                        path=image['path'])

        DistroTrees.add_distro_urls(distro_tree, lab_controller, new_distro['urls'])

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
    def get_running_command_ids(self):
        lab_controller = identity.current.user.lab_controller
        running_commands = Command.query \
            .join(Command.system) \
            .filter(System.lab_controller == lab_controller) \
            .filter(Command.status == CommandStatus.running) \
            .values(Command.id)
        return [id for id, in running_commands]

    @cherrypy.expose
    @identity.require(identity.in_group('lab_controller'))
    def get_queued_command_details(self):
        lab_controller = identity.current.user.lab_controller
        max_running_commands = config.get('beaker.max_running_commands')
        if max_running_commands:
            running_commands = Command.query\
                    .join(Command.system)\
                    .filter(System.lab_controller == lab_controller)\
                    .filter(Command.status == CommandStatus.running)\
                    .count()
            if running_commands >= max_running_commands:
                return []
        query = Command.query\
                .join(Command.system)\
                .options(contains_eager(Command.system))\
                .filter(System.lab_controller == lab_controller)\
                .filter(Command.status == CommandStatus.queued)\
                .order_by(Command.id)
        if max_running_commands:
            query = query.limit(max_running_commands - running_commands)
        result = []
        for cmd in query:
            d = {
                'id': cmd.id,
                'action': cmd.action,
                'fqdn': cmd.system.fqdn,
                'delay': 0,
                'quiescent_period': cmd.quiescent_period
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
                installation = cmd.installation
                distro_tree = cmd.installation.distro_tree
                if distro_tree:
                    schemes = ['http', 'ftp']
                    if distro_tree.arch.arch == 's390' or distro_tree.arch.arch == 's390x':
                        # zPXE needs FTP URLs for the images, it has no HTTP client.
                        # It would be nicer if we could leave this decision up to
                        # beaker-provision, but the API doesn't work like that...
                        schemes = ['ftp']
                    distro_tree_url = distro_tree.url_in_lab(lab_controller, scheme=schemes)
                else:
                    distro_tree_url = installation.tree_url
                if not distro_tree_url:
                    cmd.abort(u'No usable URL found for distro tree %s in lab %s'
                            % (distro_tree.id, lab_controller.fqdn))
                    continue

                d['netboot'] = {
                    'kernel_url': urlparse.urljoin(distro_tree_url, installation.kernel_path),
                    'initrd_url': urlparse.urljoin(distro_tree_url, installation.initrd_path),
                    'kernel_options': installation.kernel_options or '',
                }
                if distro_tree:
                    d['netboot']['distro_tree_id'] = distro_tree.id
                else:
                    d['netboot']['distro_tree_id'] = None
                if installation.arch:
                    d['netboot']['arch'] = installation.arch.arch
                else:
                    # It must be a queued command left over after migrating from Beaker < 25.
                    d['netboot']['arch'] = distro_tree.arch.arch
            result.append(d)
        return result

    @cherrypy.expose
    def get_installation_for_system(self, fqdn):
        system = System.by_fqdn(fqdn, identity.current.user)
        if not system.installations:
            raise ValueError('System %s has never been provisioned' % fqdn)
        installation = system.installations[0]
        distro_tree = installation.distro_tree
        distro_tree_url = distro_tree.url_in_lab(system.lab_controller, 'http')
        if not distro_tree_url:
            raise ValueError('No usable URL found for distro tree %s in lab %s'
                    % (distro_tree.id, system.lab_controller.fqdn))

        if system.kernel_type.uboot:
            by_kernel = ImageType.uimage
            by_initrd = ImageType.uinitrd
        else:
            by_kernel = ImageType.kernel
            by_initrd = ImageType.initrd

        kernel = distro_tree.image_by_type(by_kernel, system.kernel_type)
        if not kernel:
            raise ValueError('Kernel image not found for distro tree %s' % distro_tree.id)
        initrd = distro_tree.image_by_type(by_initrd, system.kernel_type)
        if not initrd:
            raise ValueError('Initrd image not found for distro tree %s' % distro_tree.id)
        return {
            'kernel_url': urlparse.urljoin(distro_tree_url, kernel.path),
            'initrd_url': urlparse.urljoin(distro_tree_url, initrd.path),
            'kernel_options': installation.kernel_options or '',
            'distro_tree_urls': [lca.url for lca in distro_tree.lab_controller_assocs
                    if lca.lab_controller == system.lab_controller],
        }

    @cherrypy.expose
    @identity.require(identity.in_group('lab_controller'))
    def mark_command_running(self, command_id):
        lab_controller = identity.current.user.lab_controller
        cmd = Command.query.get(command_id)
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
        cmd = Command.query.get(command_id)
        if cmd.system.lab_controller != lab_controller:
            raise ValueError('%s cannot update command for %s in wrong lab'
                    % (lab_controller, cmd.system))
        if cmd.status != CommandStatus.running:
            raise ValueError('Command %s not running' % command_id)
        cmd.change_status(CommandStatus.completed)
        if cmd.action == u'on' and cmd.installation:
            cmd.installation.rebooted = datetime.utcnow()
            recipe = cmd.installation.recipe
            if recipe:
                recipe.initial_watchdog()
        cmd.log_to_system_history()
        return True

    @cherrypy.expose
    @identity.require(identity.in_group('lab_controller'))
    def add_completed_command(self, fqdn, action):
        # Reports completion of a command that was executed
        # synchronously by the lab controller
        user = identity.current.user
        system = System.by_fqdn(fqdn, user)
        cmd = Command(user=user, service=u"XMLRPC", action=action,
                status=CommandStatus.completed)
        cmd.start_time = cmd.finish_time = datetime.utcnow()
        system.command_queue.append(cmd)
        session.flush() # Populates cmd.system (needed for next call)
        cmd.log_to_system_history()
        return True

    @cherrypy.expose
    @identity.require(identity.in_group('lab_controller'))
    def mark_command_aborted(self, command_id, message=None):
        lab_controller = identity.current.user.lab_controller
        cmd = Command.query.get(command_id)
        if cmd.system.lab_controller != lab_controller:
            raise ValueError('%s cannot update command for %s in wrong lab'
                    % (lab_controller, cmd.system))
        if cmd.status != CommandStatus.running:
            raise ValueError('Command %s not running' % command_id)
        cmd.change_status(CommandStatus.aborted)
        cmd.error_message = message
        if cmd.installation and cmd.installation.recipe:
            cmd.installation.recipe.abort('Command %s aborted' % cmd.id)
        cmd.log_to_system_history()
        return True


    @cherrypy.expose
    @identity.require(identity.in_group('lab_controller'))
    def mark_command_failed(self, command_id, message=None, system_broken=True):
        lab_controller = identity.current.user.lab_controller
        cmd = Command.query.get(command_id)
        if cmd.system.lab_controller != lab_controller:
            raise ValueError('%s cannot update command for %s in wrong lab'
                    % (lab_controller, cmd.system))
        if cmd.status != CommandStatus.running:
            raise ValueError('Command %s not running' % command_id)
        cmd.change_status(CommandStatus.failed)
        cmd.error_message = message
        # Ignore failures for 'interrupt' commands because most power types
        # don't support it and will report a "failure" in that case.
        if system_broken and cmd.action != 'interrupt' and cmd.system.status == SystemStatus.automated:
            cmd.system.mark_broken(reason=u'Power command failed: %s' % message)
        if cmd.installation:
            if cmd.installation.recipe:
                cmd.installation.recipe.abort('Command %s failed' % cmd.id)
            queued_commands = [c for c in cmd.installation.commands if c.status == CommandStatus.queued]
            for q in queued_commands:
                q.abort('Command %s failed' % cmd.id)

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
        # See https://bugzilla.redhat.com/show_bug.cgi?id=974319 and
        # https://bugzilla.redhat.com/show_bug.cgi?id=974352 for more
        # details.
        lab_controller = identity.current.user.lab_controller
        purged = (
            Command.__table__.update()
            .where(Command.status == CommandStatus.running)
            .where(Command.queue_time <
                       datetime.utcnow() - timedelta(days=1))
            .values(status=CommandStatus.aborted)
            .execute()
        )
        if purged.rowcount:
            msg = ("Aborted %d stale commands before aborting "
                   "recent running commands for %s")
            log.warn(msg, purged.rowcount, lab_controller.fqdn)
        running_commands = Command.query\
                .join(Command.system)\
                .filter(System.lab_controller == lab_controller)\
                .filter(Command.status == CommandStatus.running)
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
