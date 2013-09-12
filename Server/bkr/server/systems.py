
import logging
import xmlrpclib
import datetime
from sqlalchemy import and_
from turbogears import expose, controllers, flash, redirect
from bkr.server import identity
from bkr.server.bexceptions import BX
from bkr.server.model import System, SystemActivity, SystemStatus, DistroTree, \
        OSMajor, DistroTag, Arch, Distro
from bkr.server.installopts import InstallOptions
from bkr.server.kickstart import generate_kickstart
from bkr.server.xmlrpccontroller import RPCRoot
from turbogears.database import session
import cherrypy

log = logging.getLogger(__name__)

__all__ = ['SystemsController']

class SystemsController(controllers.Controller):
    # For XMLRPC methods in this class.
    exposed = True

    @expose()
    @identity.require(identity.not_anonymous())
    def return_loan(self, fqdn=None, **kw):
        return self.update_loan(fqdn=fqdn, loaned=None)

    @expose()
    @identity.require(identity.not_anonymous())
    def update_loan(self, fqdn=None, loaned=None, loan_comment=None, **kw):
        """Update system loan and loan comment.

        Returns the loanee
        """
        # The formal param 'loaned' is dictated to us by widgets.SystemForm...
        loaning_to = loaned
        system = System.by_fqdn(fqdn, identity.current.user)
        system.change_loan(loaning_to, loan_comment)
        return loaning_to if loaning_to else ''

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
        if not force and system.user is not None \
                and system.user != identity.current.user:
            raise BX(_(u'System is in use'))
        if clear_netboot:
            system.clear_netboot(service=u'XMLRPC')
        system.action_power(action, service=u'XMLRPC', delay=delay)
        return system.fqdn # because turbogears makes us return something

    @expose()
    @identity.require(identity.not_anonymous())
    def clear_netboot_form(self, fqdn):
        """Queues the clear netboot commands

        Enqueues the command to clear any netboot configuration for this
        system, and on success redirects to the system page.
        """
        system = System.by_fqdn(fqdn, identity.current.user)
        system.clear_netboot(service=u'WEBUI')
        flash(_(u'Clear netboot command enqueued'))
        redirect(u'../view/%s' % fqdn)

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
        if distro_tree.systems().filter(System.id == system.id).count() < 1:
            raise BX(_(u'Distro tree %s cannot be provisioned on %s')
                    % (distro_tree, system.fqdn))

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

# for sphinx
systems = SystemsController
