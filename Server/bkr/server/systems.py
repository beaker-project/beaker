
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import logging
import xmlrpclib
import datetime
import urlparse
from sqlalchemy import and_
from sqlalchemy.orm import contains_eager
from sqlalchemy.orm.exc import NoResultFound
from flask import request, jsonify, redirect as flask_redirect
from turbogears import expose, controllers, flash, redirect, url
from bkr.server import identity, mail
from bkr.server.bexceptions import BX, InsufficientSystemPermissions
from bkr.server.model import System, SystemActivity, SystemStatus, DistroTree, \
        OSMajor, DistroTag, Arch, Distro, User, Group, SystemAccessPolicy, \
        SystemPermission, SystemAccessPolicyRule, ImageType, KernelType, \
        VirtResource, Hypervisor, Numa, LabController, SystemType, \
        CommandActivity, Power, PowerType, ReleaseAction
from bkr.server.installopts import InstallOptions
from bkr.server.kickstart import generate_kickstart
from bkr.server.app import app
from bkr.server.flask_util import BadRequest400, Unauthorised401, \
        Forbidden403, NotFound404, MethodNotAllowed405, \
        Conflict409, UnsupportedMediaType415, ServiceUnavailable503, \
        convert_internal_errors, auth_required, read_json_request, \
        json_collection
from turbogears.database import session
import cherrypy
from bkr.server.cherrypy_util import PlainTextHTTPException

log = logging.getLogger(__name__)

__all__ = ['SystemsController']

class SystemsController(controllers.Controller):
    # For XMLRPC methods in this class.
    exposed = True

    @expose()
    @identity.require(identity.not_anonymous())
    def reserve(self, fqdn):
        """
        "Reserves" (a.k.a. "takes") the system with the given fully-qualified domain 
        name. The caller then becomes the user of the system, and can 
        provision it at will.

        A system may only be reserved when: its condition is 'Manual', it is not 
        currently in use, and the caller has permission to use the system.

        .. versionadded:: 0.6
        """
        system = System.by_fqdn(fqdn, identity.current.user)
        system.reserve_manually(service=u'XMLRPC')
        return system.fqdn # because turbogears makes us return something

    @expose()
    @identity.require(identity.not_anonymous())
    def release(self, fqdn):
        """
        Releases a reservation on the system with the given fully-qualified 
        domain name.

        The caller must be the current user of a system (i.e. must have 
        successfully reserved it previously).

        .. versionadded:: 0.6
        """
        system = System.by_fqdn(fqdn, identity.current.user)
        system.unreserve_manually_reserved(service=u'XMLRPC')
        return system.fqdn # because turbogears makes us return something

    @expose()
    @identity.require(identity.not_anonymous())
    def delete(self, fqdn):
        """
        Delete a system with the given fully-qualified domain name.

        The caller must be the owner of the system or an admin.

        :param fqdn: fully-qualified domain name of the system to be deleted
        :type fqdn: string

        .. versionadded:: 0.8.2
        """
        system = System.by_fqdn(fqdn, identity.current.user)
        if system.reservations:
            raise ValueError("Can't delete system %s with reservations" % fqdn)
        if system.owner != identity.current.user and \
           not identity.current.user.is_admin():
            raise ValueError("Can't delete system %s you don't own" % fqdn)
        session.delete(system)
        return 'Deleted %s' % fqdn

    @expose()
    @identity.require(identity.not_anonymous())
    def power(self, action, fqdn, clear_netboot=False, force=False, delay=0):
        """
        Controls power for the system with the given fully-qualified domain 
        name.

        If the *clear_netboot* argument is True, the Cobbler netboot 
        configuration for the system will be cleared before power controlling.

        Controlling power for a system is not normally permitted when the 
        system is in use by someone else, because it is likely to interfere 
        with their usage. Callers may pass True for the *force* argument to 
        override this safety check.

        This method does not wait for Cobbler to report whether the power 
        control was succesful.

        :param action: 'on', 'off', or 'reboot'
        :type action: string
        :param fqdn: fully-qualified domain name of the system to be power controlled
        :type fqdn: string
        :param clear_netboot: whether to clear netboot configuration before powering
        :type clear_netboot: boolean
        :param force: whether to power the system even if it is in use
        :type force: boolean
        :param delay: number of seconds to delay before performing the action (default none)
        :type delay: int or float

        .. versionadded:: 0.6
        .. versionchanged:: 0.6.14
           No longer waits for completion of Cobbler power task.
        """
        system = System.by_fqdn(fqdn, identity.current.user)
        if not system.can_power(identity.current.user):
            raise InsufficientSystemPermissions(
                    _(u'User %s does not have permission to power system %s')
                    % (identity.current.user, system))
        if not force and system.user is not None \
                and system.user != identity.current.user:
            raise BX(_(u'System is in use'))
        if clear_netboot:
            system.clear_netboot(service=u'XMLRPC')
        system.action_power(action, service=u'XMLRPC', delay=delay)
        return system.fqdn # because turbogears makes us return something

    @expose()
    @identity.require(identity.not_anonymous())
    def clear_netboot(self, fqdn):
        """
        Clears any netboot configuration in effect for the system with the
        given fully-qualified domain name.

        .. verisonadded:: 0.9
        """
        system = System.by_fqdn(fqdn, identity.current.user)
        system.clear_netboot(service=u'XMLRPC')
        return system.fqdn # because turbogears makes us return something

    @expose()
    @identity.require(identity.not_anonymous())
    def provision(self, fqdn, distro_tree_id, ks_meta=None,
            kernel_options=None, kernel_options_post=None, kickstart=None,
            reboot=True):
        """
        Provisions a system with the given distro tree and options.

        The *ks_meta*, *kernel_options*, and *kernel_options_post* arguments 
        override the default values configured for the system. For example, if 
        the default kernel options for the system/distro are
        'console=ttyS0 ksdevice=eth0', and the caller passes 'ksdevice=eth1' 
        for *kernel_options*, the kernel options used will be
        'console=ttyS0 ksdevice=eth1'.

        :param distro_tree_id: numeric id of distro tree to be provisioned
        :type distro_tree_id: int
        :param ks_meta: kickstart options
        :type ks_meta: str
        :param kernel_options: kernel options for installation
        :type kernel_options: str
        :param kernel_options_post: kernel options for after installation
        :type kernel_options_post: str
        :param kickstart: complete kickstart
        :type kickstart: str
        :param reboot: whether to reboot the system after applying Cobbler changes
        :type reboot: bool

        .. versionadded:: 0.6

        .. versionchanged:: 0.6.10
           System-specific kickstart/kernel options are now obeyed.

        .. versionchanged:: 0.9
           *distro_install_name* parameter is replaced with *distro_tree_id*. 
           See :meth:`distrotrees.filter`.
        """
        system = System.by_fqdn(fqdn, identity.current.user)
        if not system.user == identity.current.user:
            raise BX(_(u'Reserve a system before provisioning'))
        distro_tree = DistroTree.by_id(distro_tree_id)

        # sanity check: does the distro tree apply to this system?
        if not system.compatible_with_distro_tree(distro_tree):
            raise BX(_(u'Distro tree %s cannot be provisioned on %s')
                    % (distro_tree, system.fqdn))
        if not system.lab_controller:
            raise BX(_(u'System is not attached to a lab controller'))
        if not distro_tree.url_in_lab(system.lab_controller):
            raise BX(_(u'Distro tree %s is not available in lab %s')
                    % (distro_tree, system.lab_controller))

        if identity.current.user.rootpw_expired:
            raise BX(_('Your root password has expired, please change or clear it in order to submit jobs.'))

        # ensure system-specific defaults are used
        # (overriden by this method's arguments)
        options = system.install_options(distro_tree).combined_with(
                InstallOptions.from_strings(ks_meta or '',
                    kernel_options or '',
                    kernel_options_post or ''))
        if 'ks' not in options.kernel_options:
            rendered_kickstart = generate_kickstart(options,
                    distro_tree=distro_tree,
                    system=system, user=identity.current.user, kickstart=kickstart)
            options.kernel_options['ks'] = rendered_kickstart.link
        system.configure_netboot(distro_tree, options.kernel_options_str,
                service=u'XMLRPC')
        system.activity.append(SystemActivity(user=identity.current.user,
                service=u'XMLRPC', action=u'Provision',
                field_name=u'Distro Tree', old_value=u'',
                new_value=u'Success: %s' % distro_tree))

        if reboot:
            system.action_power(action='reboot', service=u'XMLRPC')

        return system.fqdn # because turbogears makes us return something

    @expose()
    def history(self, fqdn, since=None):
        """
        Returns the history for the given system.
        If the *since* argument is given, all history entries between that 
        timestamp and the present are returned. By default, history entries 
        from the past 24 hours are returned.

        History entries are returned as a list of structures (dicts), each of 
        which has the following keys:

            'created'
                Timestamp of the activity
            'user'
                Username of the user who performed the action
            'service'
                Service by which the action was performed (e.g. 'XMLRPC')
            'action'
                Action which was performed (e.g. 'Changed')
            'field_name'
                Name of the field which was acted upon
            'old_value'
                Value of the field before the action (if any)
            'new_value'
                Value of the field after the action (if any)

        Note that field names and actions are recorded in human-readable form, 
        which might not be ideal for machine parsing.

        All timestamps are expressed in UTC.

        .. versionadded:: 0.6.6
        """
        if since is None:
            since = datetime.datetime.utcnow() - datetime.timedelta(days=1)
        else:
            if not isinstance(since, datetime.datetime):
                raise TypeError("'since' must be an XML-RPC datetime")
        system = System.by_fqdn(fqdn, identity.current.user)
        activities = SystemActivity.query.filter(and_(
                SystemActivity.object == system,
                SystemActivity.created >= since))
        return [dict(created=a.created,
                     user=a.user.user_name, service=a.service, action=a.action,
                     field_name=a.field_name, old_value=a.old_value,
                     new_value=a.new_value)
                for a in activities]

    @cherrypy.expose()
    @identity.require(identity.not_anonymous())
    def get_osmajor_arches(self, fqdn, tags=None):
        """
        Returns a dict of all distro families with a list of arches that apply for system.
        If *tags* is given, limits to distros with at least one of the given tags.

        {"RedHatEnterpriseLinux3": ["i386", "x86_64"],}

        .. versionadded:: 0.11.0
        """
        system = System.by_fqdn(fqdn, identity.current.user)
        query = system.distro_trees(only_in_lab=False)
        if tags:
            query = query.filter(Distro._tags.any(DistroTag.tag.in_(tags)))
        query = query.join(DistroTree.arch).distinct()
        result = {}
        for osmajor, arch in query.values(OSMajor.osmajor, Arch.arch):
            result.setdefault(osmajor, []).append(arch)
        return result


def _get_system_by_FQDN(fqdn):
    """Get system by FQDN, reporting HTTP 404 if the system is not found"""
    try:
        return System.by_fqdn(fqdn, identity.current.user)
    except NoResultFound:
        raise NotFound404('System not found')

@app.route('/systems/', methods=['POST'])
@auth_required
def add_system():
    # We accept JSON or form-encoded for convenience
    if request.json:
        if 'fqdn' not in request.json:
            raise BadRequest400('Missing fqdn key')
        new_fqdn = request.json['fqdn']
    elif request.form:
        if 'fqdn' not in request.form:
            raise BadRequest400('Missing fqdn parameter')
        new_fqdn = request.form['fqdn']
    else:
        raise UnsupportedMediaType415
    with convert_internal_errors():
        if System.query.filter(System.fqdn == new_fqdn).count() != 0:
            raise Conflict409('System with fqdn %r already exists' % new_fqdn)
        system = System(fqdn=new_fqdn, owner=identity.current.user)
        session.add(system)
        # new systems are visible to everybody by default
        system.custom_access_policy = SystemAccessPolicy()
        system.custom_access_policy.add_rule(SystemPermission.view,
                everybody=True)
    # XXX this should be 201 with Location: /systems/FQDN/ but 302 is more 
    # convenient because it lets us use a traditional browser form without AJAX 
    # handling, and for now we're redirecting to /view/FQDN until that is moved 
    # to /systems/FQDN/
    return flask_redirect(url(u'/view/%s#essentials' % system.fqdn))

# XXX need to move /view/FQDN to /systems/FQDN/
@app.route('/systems/<fqdn>/', methods=['GET'])
def get_system(fqdn):
    system = _get_system_by_FQDN(fqdn)
    return jsonify(system.__json__())

@app.route('/systems/<fqdn>/', methods=['PATCH', 'POST'])
@auth_required
def update_system(fqdn):
    system = _get_system_by_FQDN(fqdn)
    if not system.can_edit(identity.current.user):
        raise Forbidden403('Cannot edit system')
    data = read_json_request(request)
    # helper for recording activity below
    def record_activity(field, old, new, action=u'Changed'):
        system.record_activity(user=identity.current.user, service=u'HTTP',
                action=action, field=field, old=old, new=new)
    with convert_internal_errors():
        # XXX what a nightmare... need to use a validation/conversion library, 
        # and maybe simplify/relocate the activity recording stuff somehow
        changed = False
        renamed = False
        if 'fqdn' in data:
            new_fqdn = data['fqdn'].lower()
            if new_fqdn != system.fqdn:
                if System.query.filter(System.fqdn == new_fqdn).count():
                    raise Conflict409('System %s already exists' % new_fqdn)
                record_activity(u'FQDN', system.fqdn, new_fqdn)
                system.fqdn = new_fqdn
                changed = True
                renamed = True
        if 'owner' in data and data['owner'].get('user_name') != system.owner.user_name:
            if not system.can_change_owner(identity.current.user):
                raise Forbidden403('Cannot change owner')
            new_owner = User.by_user_name(data['owner'].get('user_name'))
            if new_owner is None:
                raise BadRequest400('No such user %s' % data['owner'].get('user_name'))
            record_activity(u'Owner', system.owner, new_owner)
            system.owner = new_owner
            changed = True
        if 'status' in data:
            new_status = SystemStatus.from_string(data['status'])
            if new_status != system.status:
                record_activity(u'Status', system.status, new_status)
                system.status = new_status
                if not new_status.bad and system.status_reason:
                    # clear the status reason for "good" statuses
                    record_activity(u'Status Reason', system.status_reason, None)
                    system.status_reason = None
                changed = True
        if 'status_reason' in data:
            new_reason = data['status_reason'] or None
            if new_reason and not system.status.bad:
                raise ValueError('Cannot set status reason when status is %s'
                        % system.status)
            if new_reason != system.status_reason:
                record_activity(u'Status Reason', system.status_reason, new_reason)
                system.status_reason = new_reason
                changed = True
        if 'type' in data:
            new_type = SystemType.from_string(data['type'])
            if new_type != system.type:
                record_activity(u'Type', system.type, new_type)
                system.type = new_type
                changed = True
        if 'arches' in data:
            new_arches = [Arch.by_name(a) for a in (data['arches'] or [])]
            added_arches = set(new_arches).difference(system.arch)
            removed_arches = set(system.arch).difference(new_arches)
            if added_arches or removed_arches:
                for added_arch in added_arches:
                    record_activity(u'Arch', None, added_arch, u'Added')
                for removed_arch in removed_arches:
                    record_activity(u'Arch', removed_arch, None, u'Removed')
                system.arch[:] = new_arches
                changed = True
        if 'lab_controller_id' in data:
            if data['lab_controller_id']:
                new_lc = LabController.by_id(data['lab_controller_id'])
            else:
                new_lc = None
            if new_lc != system.lab_controller:
                if system.open_reservation is not None:
                    raise Conflict409('Unable to change lab controller while system '
                            'is in use (return the system first)')
                record_activity(u'Lab Controller', system.lab_controller, new_lc)
                system.lab_controller = new_lc
                changed = True
        # If we're given any power-related keys, need to ensure system.power exists
        if not system.power and set(['power_type', 'power_address', 'power_user',
                'power_password', 'power_id', 'power_quiescent_period'])\
                .intersection(data.keys()):
            system.power = Power()
        if 'power_type' in data:
            new_power_type = PowerType.by_name(data['power_type'])
            if new_power_type != system.power.power_type:
                record_activity(u'power_type', system.power.power_type.name,
                        new_power_type.name)
                system.power.power_type = new_power_type
                changed = True
        if 'power_address' in data:
            new_power_address = data['power_address'] or u''
            if new_power_address != system.power.power_address:
                record_activity(u'power_address', system.power.power_address,
                        data['power_address'])
                system.power.power_address = data['power_address']
                changed = True
        if 'power_user' in data and data['power_user'] != system.power.power_user:
            record_activity(u'power_user', u'********', u'********')
            system.power.power_user = data['power_user']
            changed = True
        if 'power_password' in data and data['power_password'] != system.power.power_passwd:
            record_activity(u'power_passwd', u'********', u'********')
            system.power.power_passwd = data['power_password']
            changed = True
        if 'power_id' in data and data['power_id'] != system.power.power_id:
            record_activity(u'power_id', system.power.power_id, data['power_id'])
            system.power.power_id = data['power_id']
            changed = True
        if 'power_quiescent_period' in data:
            new_qp = int(data['power_quiescent_period'])
            if new_qp != system.power.power_quiescent_period:
                record_activity(u'power_quiescent_period',
                        system.power.power_quiescent_period, new_qp)
                system.power.power_quiescent_period = new_qp
                changed = True
        if 'release_action' in data:
            new_release_action = ReleaseAction.from_string(data['release_action'])
            if new_release_action != (system.release_action or ReleaseAction.power_off):
                record_activity(u'release_action',
                        (system.release_action or ReleaseAction.power_off),
                        new_release_action)
                system.release_action = new_release_action
                changed = True
        if 'reprovision_distro_tree' in data:
            if (not data['reprovision_distro_tree'] or
                    'id' not in data['reprovision_distro_tree']):
                new_rpdt = None
            else:
                new_rpdt = DistroTree.by_id(data['reprovision_distro_tree']['id'])
            if new_rpdt != system.reprovision_distro_tree:
                record_activity(u'reprovision_distro_tree',
                        unicode(system.reprovision_distro_tree),
                        unicode(new_rpdt))
                system.reprovision_distro_tree = new_rpdt
                changed = True
        if 'location' in data:
            new_location = data['location'] or None
            if new_location != system.location:
                record_activity(u'Location', system.location, new_location)
                system.location = new_location
                changed = True
        if 'lender' in data:
            new_lender = data['lender'] or None
            if new_lender != system.lender:
                record_activity(u'Lender', system.lender, new_lender)
                system.lender = new_lender
                changed = True
        if 'kernel_type' in data:
            new_kernel_type = KernelType.by_name(data['kernel_type'])
            if new_kernel_type != system.kernel_type:
                record_activity(u'Kernel Type', system.kernel_type, new_kernel_type)
                system.kernel_type = new_kernel_type
                changed = True
        if 'hypervisor' in data:
            if data['hypervisor']:
                new_hypervisor = Hypervisor.by_name(data['hypervisor'])
            else:
                new_hypervisor = None
            if new_hypervisor != system.hypervisor:
                record_activity(u'Hypervisor', system.hypervisor, new_hypervisor)
                system.hypervisor = new_hypervisor
                changed = True
        if 'vendor' in data:
            new_vendor = data['vendor'] or None
            if new_vendor != system.vendor:
                record_activity(u'Vendor', system.vendor, new_vendor)
                system.vendor = new_vendor
                changed = True
        if 'model' in data:
            new_model = data['model'] or None
            if new_model != system.model:
                record_activity(u'Model', system.model, new_model)
                system.model = new_model
                changed = True
        if 'serial_number' in data:
            new_serial_number = data['serial_number'] or None
            if new_serial_number != system.serial:
                record_activity(u'Serial Number', system.serial, new_serial_number)
                system.serial = new_serial_number
                changed = True
        if 'mac_address' in data:
            new_mac_address = data['mac_address'] or None
            if new_mac_address != system.mac_address:
                record_activity(u'MAC Address', system.mac_address, new_mac_address)
                system.mac_address = new_mac_address
                changed = True
        if 'memory' in data:
            new_memory = int(data['memory']) if data['memory'] else None
            if new_memory != system.memory:
                record_activity(u'Memory', system.memory, new_memory)
                system.memory = new_memory
                changed = True
        if 'numa_nodes' in data:
            new_numa_nodes = int(data['numa_nodes']) if data['numa_nodes'] else None
            if not system.numa:
                system.numa = Numa()
            if new_numa_nodes != system.numa.nodes:
                record_activity(u'NUMA/Nodes', system.numa.nodes, new_numa_nodes)
                system.numa.nodes = new_numa_nodes
                changed = True
        if changed:
            # XXX clear checksum!?
            system.date_modified = datetime.datetime.utcnow()
    response = jsonify(system.__json__())
    if renamed:
        response.headers.add('Location', url('/view/%s' % system.fqdn))
    return response

# Not sure if this is a sane API...
@app.route('/systems/<fqdn>/cc/<email>', methods=['PUT'])
@auth_required
def add_cc(fqdn, email):
    system = _get_system_by_FQDN(fqdn)
    if not system.can_edit(identity.current.user):
        raise Forbidden403('Cannot change notify cc')
    if email not in system.cc:
        system.cc.append(email)
        system.record_activity(user=identity.current.user, service=u'HTTP',
                action=u'Added', field=u'Cc', old=None, new=email)
        system.date_modified = datetime.datetime.utcnow()
    return jsonify({'notify_cc': list(system.cc)})

@app.route('/systems/<fqdn>/cc/<email>', methods=['DELETE'])
@auth_required
def remove_cc(fqdn, email):
    system = _get_system_by_FQDN(fqdn)
    if not system.can_edit(identity.current.user):
        raise Forbidden403('Cannot change notify cc')
    if email in system.cc:
        system.cc.remove(email)
        system.record_activity(user=identity.current.user, service=u'HTTP',
                action=u'Removed', field=u'Cc', old=email, new=None)
        system.date_modified = datetime.datetime.utcnow()
    return jsonify({'notify_cc': list(system.cc)})

@app.route('/systems/<fqdn>/problem-reports/', methods=['POST'])
@auth_required
def report_problem(fqdn):
    system = _get_system_by_FQDN(fqdn)
    data = read_json_request(request)
    message = (data.get('message') or u'').strip()
    requester = identity.current.user
    mail.system_problem_report(system, message, reporter=requester)
    system.record_activity(user=requester, service=u'HTTP',
            action=u'Reported problem', field=u'Status', new=message)
    # if we tracked problem reports we could return the details here
    return 'Reported', 201

@app.route('/systems/<fqdn>/reservations/', methods=['POST'])
@auth_required
def reserve(fqdn):
    """
    Reserves the system "manually".
    """
    system = _get_system_by_FQDN(fqdn)
    with convert_internal_errors():
        reservation = system.reserve_manually(service=u'HTTP',
                user=identity.current.user)
    return jsonify(reservation.__json__())

@app.route('/systems/<fqdn>/reservations/+current', methods=['PATCH', 'PUT'])
@auth_required
def update_reservation(fqdn):
    """
    Updates the system's current reservation. The only permitted update is to 
    end the reservation (returning the system), and this is only permitted when 
    the reservation was "manual" (not made by the scheduler).
    """
    system = _get_system_by_FQDN(fqdn)
    data = read_json_request(request)
    # This interprets both PATCH and PUT as PATCH
    finish_time = data.get('finish_time')
    with convert_internal_errors():
        if finish_time == "now":
            reservation = system.unreserve_manually_reserved(service=u'HTTP',
                    user=identity.current.user)
        else:
            raise ValueError('Reservation durations are not configurable')
    return jsonify(reservation.__json__())

@app.route('/systems/<fqdn>/loan-requests/', methods=['POST'])
@auth_required
def request_loan(fqdn):
    system = _get_system_by_FQDN(fqdn)
    data = read_json_request(request)
    message = (data.get('message') or u'').strip()
    requester = identity.current.user
    to = system.owner.email_address
    mail.system_loan_request(system, message, requester, to)
    # if we tracked loan requests we could return the details here
    return 'Requested', 201

@app.route('/systems/<fqdn>/loans/', methods=['POST'])
@auth_required
def grant_loan(fqdn):
    """
    Lends the system to the specified user (or borrows the system for
    the current user if no other user is specified)

    """
    system = _get_system_by_FQDN(fqdn)
    data = read_json_request(request)
    recipient = data.get("recipient")
    if recipient is None:
        user_name = identity.current.user.user_name
    elif isinstance(recipient, basestring):
        user_name = recipient
    else:
        user_name = recipient.get('user_name')
    comment = data.get("comment")
    with convert_internal_errors():
        system.grant_loan(user_name, comment, service=u'HTTP')
    return jsonify(system.get_loan_details())

@app.route('/systems/<fqdn>/loans/+current', methods=['PATCH', 'PUT'])
@auth_required
def update_loan(fqdn):
    """
    Updates a loan on the system with the given fully-qualified
    domain name.

    Currently, the only permitted update is to return it.
    """
    system = _get_system_by_FQDN(fqdn)
    data = read_json_request(request)
    # This interprets both PATCH and PUT as PATCH
    finish = data.get("finish")
    with convert_internal_errors():
        if finish == "now":
            system.return_loan(service=u'HTTP')
        else:
            raise ValueError("Loan durations are not yet configurable")
    return jsonify(system.get_loan_details())

@app.route('/systems/<fqdn>/access-policy', methods=['GET'])
def get_system_access_policy(fqdn):
    # XXX need to consolidate this with SystemAccessPolicy.__json__
    # (maybe get rid of filtering here and implement it client side instead)
    system = _get_system_by_FQDN(fqdn)

    policy = system.custom_access_policy
    # For now, we don't distinguish between an empty policy and an absent one.
    if not policy:
        return jsonify(SystemAccessPolicy.empty_json())

    # filtering, if any
    if len(request.args.keys()) > 1:
        raise BadRequest400('Only one filtering criteria allowd')

    query = SystemAccessPolicyRule.query.\
        filter(SystemAccessPolicyRule.policy == policy)

    if request.args.get('mine'):
        if not identity.current.user:
            raise Unauthorised401("The 'mine' access policy filter requires authentication")
        query = query.join(SystemAccessPolicyRule.user)\
            .filter(User.user_name.in_([identity.current.user.user_name]))
    elif request.args.get('user', None):
        query = query.join(SystemAccessPolicyRule.user)\
            .filter(User.user_name.in_(request.args.getlist('user')))
    elif request.args.get('group', None):
        query = query.join(SystemAccessPolicyRule.group)\
            .filter(Group.group_name.in_(request.args.getlist('group')))

    return jsonify({
        'id': policy.id,
        'rules': [
            {'id': rule.id,
             'user': rule.user.user_name if rule.user else None,
             'group': rule.group.group_name if rule.group else None,
             'everybody': rule.everybody,
             'permission': unicode(rule.permission)}
            for rule in query],
        'possible_permissions': [
            {'value': unicode(permission),
             'label': unicode(permission.label)}
            for permission in SystemPermission],
    })

@app.route('/systems/<fqdn>/access-policy', methods=['POST', 'PUT'])
@auth_required
def save_system_access_policy(fqdn):
    system = _get_system_by_FQDN(fqdn)
    if not system.can_edit_policy(identity.current.user):
        raise Forbidden403('Cannot edit system policy')
    if system.custom_access_policy:
        policy = system.custom_access_policy
    else:
        policy = system.custom_access_policy = SystemAccessPolicy()
    data = read_json_request(request)
    # Figure out what is added, what is removed.
    # Rules are immutable, so if it has an id it is unchanged, 
    # if it has no id it is new.
    kept_rule_ids = frozenset(r['id'] for r in data['rules'] if 'id' in r)
    removed = []
    for old_rule in policy.rules:
        if old_rule.id not in kept_rule_ids:
            removed.append(old_rule)
    for old_rule in removed:
        system.record_activity(user=identity.current.user, service=u'HTTP',
                field=u'Access Policy Rule', action=u'Removed',
                old=repr(old_rule))
        policy.rules.remove(old_rule)
    for rule in data['rules']:
        if 'id' not in rule:
            if rule['user']:
                user = User.by_user_name(rule['user'])
                if user is None:
                    raise BadRequest400('No such user %r' % rule['user'])
            else:
                user = None
            try:
                group = Group.by_name(rule['group']) if rule['group'] else None
            except NoResultFound:
                raise BadRequest400('No such group %r' % rule['group'])
            permission = SystemPermission.from_string(rule['permission'])
            new_rule = policy.add_rule(user=user, group=group,
                    everybody=rule['everybody'], permission=permission)
            system.record_activity(user=identity.current.user, service=u'HTTP',
                    field=u'Access Policy Rule', action=u'Added',
                    new=repr(new_rule))
    return jsonify(policy.__json__())

@app.route('/systems/<fqdn>/access-policy/rules/', methods=['POST'])
@auth_required
def add_system_access_policy_rule(fqdn):
    system = _get_system_by_FQDN(fqdn)
    if not system.can_edit_policy(identity.current.user):
        raise Forbidden403('Cannot edit system policy')
    if system.custom_access_policy:
        policy = system.custom_access_policy
    else:
        policy = system.custom_access_policy = SystemAccessPolicy()
    rule = read_json_request(request)

    if rule['user']:
        user = User.by_user_name(rule['user'])
        if not user:
            raise BadRequest400("User '%s' does not exist" % rule['user'])
    else:
        user = None

    if rule['group']:
        try:
            group = Group.by_name(rule['group'])
        except NoResultFound:
            raise BadRequest400("Group '%s' does not exist" % rule['group'])
    else:
        group = None

    try:
        permission = SystemPermission.from_string(rule['permission'])
    except ValueError:
        raise BadRequest400
    new_rule = policy.add_rule(user=user, group=group,
            everybody=rule['everybody'], permission=permission)
    system.record_activity(user=identity.current.user, service=u'HTTP',
            field=u'Access Policy Rule', action=u'Added',
            new=repr(new_rule))
    return '', 204

@app.route('/systems/<fqdn>/status', methods=['GET'])
def get_system_status(fqdn):
    system = _get_system_by_FQDN(fqdn)
    system_status = {'condition': '%s' % system.status, 'current_loan': None,
        'current_reservation': None,}
    if system.loaned:
        system_status['current_loan'] = system.get_loan_details()
    if system.user:
        current_reservation = {
            'user': system.user,
            'user_name': system.user.user_name, # for compat only
        }
        open_reservation = system.open_reservation
        if open_reservation and \
            open_reservation.type == 'recipe':
            system_recipe = open_reservation.recipe
            current_reservation['recipe_id'] = '%s' % system_recipe.id
            current_reservation['start_time'] = '%s UTC' % system_recipe.start_time
        system_status['current_reservation'] = current_reservation
    return jsonify(system_status)

@app.route('/systems/<fqdn>/access-policy/rules/', methods=['DELETE'])
@auth_required
def delete_system_access_policy_rules(fqdn):
    system = _get_system_by_FQDN(fqdn)
    if not system.can_edit_policy(identity.current.user):
        raise Forbidden403('Cannot edit system policy')
    if system.custom_access_policy:
        policy = system.custom_access_policy
    else:
        policy = system.custom_access_policy = SystemAccessPolicy()
    # We expect some query string args specifying which rules should be 
    # deleted. If those are not present, it's "Method Not Allowed".
    query = SystemAccessPolicyRule.query.filter(SystemAccessPolicyRule.policy == policy)
    if 'permission' in request.args:
        query = query.filter(SystemAccessPolicyRule.permission.in_(
                request.args.getlist('permission', type=SystemPermission.from_string)))
    else:
        raise MethodNotAllowed405
    if 'user' in request.args:
        query = query.join(SystemAccessPolicyRule.user)\
                .filter(User.user_name.in_(request.args.getlist('user')))
    elif 'group' in request.args:
        query = query.join(SystemAccessPolicyRule.group)\
                .filter(Group.group_name.in_(request.args.getlist('group')))
    elif 'everybody' in request.args:
        query = query.filter(SystemAccessPolicyRule.everybody)
    else:
        raise MethodNotAllowed405
    for rule in query:
        rule.record_deletion(service=u'HTTP')
        session.delete(rule)
    return '', 204

@app.route('/systems/<fqdn>/installations/', methods=['POST'])
def provision_system(fqdn):
    system = _get_system_by_FQDN(fqdn)
    if not system.can_power(identity.current.user):
        raise Forbidden403('Cannot provision system')
    data = read_json_request(request)
    with convert_internal_errors():
        if not data['distro_tree'] or 'id' not in data['distro_tree']:
            raise ValueError('No distro tree specified')
        distro_tree = DistroTree.by_id(data['distro_tree']['id'])
        user = identity.current.user
        if user.rootpw_expired:
            raise ValueError('Your root password has expired, you must '
                    'change or clear it in order to provision.')
            redirect(u"/view/%s" % system.fqdn)
        install_options = system.install_options(distro_tree).combined_with(
                InstallOptions.from_strings(data.get('ks_meta'),
                    data.get('koptions'), data.get('koptions_post')))
        if 'ks' not in install_options.kernel_options:
            kickstart = generate_kickstart(install_options,
                    distro_tree=distro_tree, system=system, user=user)
            install_options.kernel_options['ks'] = kickstart.link
        system.configure_netboot(distro_tree,
                install_options.kernel_options_str, service=u'HTTP')
        system.record_activity(user=identity.current.user, service=u'HTTP',
                action=u'Provision', field=u'Distro Tree',
                new=unicode(distro_tree))
        if data.get('reboot'):
            system.action_power(action=u'reboot', service=u'HTTP')
    # in future "installations" will be a real thing in our model,
    # but for now we have nothing to return
    return 'Provisioned', 201

@app.route('/systems/<fqdn>/commands/', methods=['GET'])
@json_collection(columns={
    'user': User.user_name,
    'user.user_name': User.user_name,
    'user.email_address': User.email_address,
    'user.display_name': User.display_name,
    'service': CommandActivity.service,
    'submitted': CommandActivity.created,
    'action': CommandActivity.action,
    'message': CommandActivity.new_value,
    'status': CommandActivity.status,
})
def get_system_command_queue(fqdn):
    system = _get_system_by_FQDN(fqdn)
    query = system.dyn_command_queue
    # outerjoin user for sorting/filtering and also for eager loading
    query = query.outerjoin(CommandActivity.user)\
            .options(contains_eager(CommandActivity.user))
    return query

@app.route('/systems/<fqdn>/commands/', methods=['POST'])
@auth_required
def system_command(fqdn):
    system = _get_system_by_FQDN(fqdn)
    if not system.lab_controller:
        raise BadRequest400('System is not attached to a lab controller')
    if not system.can_power(identity.current.user):
        raise Forbidden403('You do not have permission to control this system')
    # We accept JSON or form-encoded for convenience
    if request.json:
        if 'action' not in request.json:
            raise BadRequest400('Missing action key')
        action = request.json['action']
    elif request.form:
        if 'action' not in request.form:
            raise BadRequest400('Missing action parameter')
        action = request.form['action']
    else:
        raise UnsupportedMediaType415
    if action == 'reboot':
        raise BadRequest400('"reboot" is not a valid power command, '
                'send "off" followed by "on" instead')
    elif action in ['on', 'off', 'interrupt']:
        if not system.power:
            raise BadRequest400('System is not configured for power support')
        command = system.action_power(service=u'HTTP', action=action)
    elif action == 'clear_netboot':
        command = system.clear_netboot(service=u'HTTP')
    else:
        raise BadRequest400('Unknown action %r' % action)
    session.flush() # for created attribute
    return jsonify(command.__json__())

@app.route('/systems/<fqdn>/activity/', methods=['GET'])
@json_collection(columns={
    'user': User.user_name,
    'user.user_name': User.user_name,
    'user.email_address': User.email_address,
    'user.display_name': User.display_name,
    'service': SystemActivity.service,
    'created': SystemActivity.created,
    'field_name': SystemActivity.field_name,
    'action': SystemActivity.action,
    'old_value': SystemActivity.old_value,
    'new_value': SystemActivity.new_value,
})
def get_system_activity(fqdn):
    system = _get_system_by_FQDN(fqdn)
    query = system.dyn_activity
    # outerjoin user for sorting/filtering and also for eager loading
    query = query.outerjoin(SystemActivity.user)\
            .options(contains_eager(SystemActivity.user))
    return query

# This is part of the iPXE-based installation support for OpenStack instances.
@app.route('/systems/by-uuid/<uuid>/ipxe-script')
def ipxe_script(uuid):
    try:
        resource = VirtResource.by_instance_id(uuid)
    except (NoResultFound, ValueError):
        raise NotFound404('Instance is not known to Beaker')
    if resource.kernel_options is None:
        # recipe.provision() hasn't been called yet
        # We need to handle this case because the VM is created and boots up 
        # *before* we generate the kickstart etc
        raise ServiceUnavailable503('Recipe has not been provisioned yet')
    distro_tree = resource.recipe.distro_tree
    distro_tree_url = distro_tree.url_in_lab(resource.lab_controller,
            scheme=['http', 'ftp'])
    kernel = distro_tree.image_by_type(ImageType.kernel,
            KernelType.by_name(u'default'))
    if not kernel:
        raise BadRequest400('Kernel image not found for distro tree %s'
                % distro_tree.id)
    initrd = resource.recipe.distro_tree.image_by_type(ImageType.initrd,
            KernelType.by_name(u'default'))
    if not initrd:
        raise BadRequest400('Initrd image not found for distro tree %s'
                % distro_tree.id)
    kernel_url = urlparse.urljoin(distro_tree_url, kernel.path)
    initrd_url = urlparse.urljoin(distro_tree_url, initrd.path)
    kernel_options = resource.kernel_options + ' netboot_method=ipxe'
    return ('#!ipxe\nkernel %s %s\ninitrd %s\nboot\n'
            % (kernel_url, kernel_options, initrd_url),
            200, [('Content-Type', 'text/plain')])

# for sphinx
systems = SystemsController
