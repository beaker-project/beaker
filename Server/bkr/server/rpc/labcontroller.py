
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import logging
from datetime import datetime, timedelta

from sqlalchemy.orm import contains_eager
from sqlalchemy.orm.exc import NoResultFound
from six.moves import urllib

from bkr.common.bexceptions import BX
from bkr.common.helpers import total_seconds
from bkr.server import config
from bkr.server import identity
from bkr.server.database import session
from bkr.server.rpc.distrotrees import DistroTrees
from bkr.server.rpc import expose, register
from bkr.server.model import (
    Arch, OSMajor, OSVersion, Distro, DistroTree, DistroTreeRepo,
    DistroTreeImage, ImageType, KernelType, Command, CommandStatus,
    System, SystemStatus)


log = logging.getLogger(__name__)


@register('labcontrollers')
class LabControllers(object):
    # For XMLRPC methods in this class.
    exposed = True

    @expose
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
            raise BX('Cannot import distro as %s: it is configured as an alias for %s'
                       % (new_distro['osmajor'], osmajor.osmajor))

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

    @expose
    @identity.require(identity.in_group("lab_controller"))
    def remove_distro_trees(self, distro_tree_ids):
        lab_controller = identity.current.user.lab_controller
        for distro_tree_id in distro_tree_ids:
            distro_tree = DistroTree.by_id(distro_tree_id)
            distro_tree.expire(lab_controller=lab_controller)
        return True

    @expose
    @identity.require(identity.in_group('lab_controller'))
    def get_running_command_ids(self):
        lab_controller = identity.current.user.lab_controller
        running_commands = Command.query \
            .join(Command.system) \
            .filter(System.lab_controller == lab_controller) \
            .filter(Command.status == CommandStatus.running) \
            .values(Command.id)
        return [id for id, in running_commands]

    @expose
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
                    'kernel_url': urllib.parse.urljoin(distro_tree_url, installation.kernel_path),
                    'initrd_url': urllib.parse.urljoin(distro_tree_url, installation.initrd_path),
                    'kernel_options': installation.kernel_options or '',
                }
                if installation.image_path:
                    d["netboot"]["image_url"] = urllib.parse.urljoin(
                        distro_tree_url, installation.image_path
                    )
                else:
                    d['netboot']['image_url'] = None
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

    @expose
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
            'kernel_url': urllib.parse.urljoin(distro_tree_url, kernel.path),
            'initrd_url': urllib.parse.urljoin(distro_tree_url, initrd.path),
            'kernel_options': installation.kernel_options or '',
            'distro_tree_urls': [lca.url for lca in distro_tree.lab_controller_assocs
                    if lca.lab_controller == system.lab_controller],
        }

    @expose
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

    @expose
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

    @expose
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

    @expose
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


    @expose
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

    @expose
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

    @expose
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
