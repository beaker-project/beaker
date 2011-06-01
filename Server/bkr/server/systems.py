
import logging
import xmlrpclib
import datetime
from sqlalchemy import and_
from turbogears import expose, identity, controllers
from bkr.server.bexceptions import BX
from bkr.server.model import System, SystemActivity, SystemStatus, Distro
from bkr.server.xmlrpccontroller import RPCRoot
from bkr.server.util import parse_xmlrpc_datetime
from bkr.server.cobbler_utils import hash_to_string

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
        if system.status != SystemStatus.by_name(u'Manual'):
            raise BX(_(u'Cannot reserve system with status %s') % system.status)
        system.reserve(service=u'XMLRPC', reservation_type=u'manual')
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
        system.unreserve(service=u'XMLRPC')
        return system.fqdn # because turbogears makes us return something

    @expose()
    @identity.require(identity.not_anonymous())
    def power(self, action, fqdn, clear_netboot=False, force=False):
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

        .. versionadded:: 0.6
        .. versionchanged:: 0.6.14
           No longer waits for completion of Cobbler power task.
        """
        system = System.by_fqdn(fqdn, identity.current.user)
        if not force and system.user is not None \
                and system.user != identity.current.user:
            raise BX(_(u'System is in use'))
        if clear_netboot:
            system.remote.clear_netboot(service=u'XMLRPC')
        system.action_power(action, service=u'XMLRPC')
        return system.fqdn # because turbogears makes us return something

    @expose()
    @identity.require(identity.not_anonymous())
    def provision(self, fqdn, distro_install_name, ks_meta=None,
            kernel_options=None, kernel_options_post=None, kickstart=None,
            reboot=True):
        """
        Provisions a system with the given distro and options.

        The *ks_meta*, *kernel_options*, and *kernel_options_post* arguments 
        override the default values configured for the system. For example, if 
        the default kernel options for the system/distro are
        'console=ttyS0 ksdevice=eth0', and the caller passes 'ksdevice=eth1' 
        for *kernel_options*, the kernel options used will be
        'console=ttyS0 ksdevice=eth1'.

        :param distro_install_name: install name of distro to be provisioned
        :type distro_install_name: str
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
        """
        system = System.by_fqdn(fqdn, identity.current.user)
        if not system.can_provision_now(identity.current.user):
            raise BX(_(u'User %s has insufficient permissions to provision %s')
                    % (identity.current.user.user_name, system.fqdn))
        if not system.user == identity.current.user:
            raise BX(_(u'Reserve a system before provisioning'))
        distro = Distro.by_install_name(distro_install_name)

        # sanity check: does the distro apply to this system?
        if distro.systems().filter(System.id == system.id).count() < 1:
            raise BX(_(u'Distro %s cannot be provisioned on %s')
                    % (distro.install_name, system.fqdn))

        # ensure system-specific defaults are used
        # (overriden by this method's arguments)
        options = system.install_options(distro,
                ks_meta=ks_meta or '',
                kernel_options=kernel_options or '',
                kernel_options_post=kernel_options_post or '')
        try:
            system.action_provision(distro=distro,
                    kickstart=kickstart, **options)
        except Exception, e:
            log.exception('Failed to provision')
            system.activity.append(SystemActivity(user=identity.current.user,
                    service=u'XMLRPC', action=u'Provision',
                    field_name=u'Distro', old_value=u'',
                    new_value=u'%s: %s' % (e, distro.install_name)))
            raise
        system.activity.append(SystemActivity(user=identity.current.user,
                service=u'XMLRPC', action=u'Provision',
                field_name=u'Distro', old_value=u'',
                new_value=u'Success: %s' % distro.install_name))

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
        else: # should be an instance of xmlrpclib.DateTime
            since = parse_xmlrpc_datetime(since.value)
        system = System.by_fqdn(fqdn, identity.current.user)
        activities = SystemActivity.query.filter(and_(
                SystemActivity.object == system,
                SystemActivity.created >= since))
        return [dict(created=xmlrpclib.DateTime(a.created.timetuple()),
                     user=a.user.user_name, service=a.service, action=a.action,
                     field_name=a.field_name, old_value=a.old_value,
                     new_value=a.new_value)
                for a in activities]

# for sphinx
systems = SystemsController
