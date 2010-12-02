
import logging
from turbogears import expose, identity, controllers
from bkr.server.bexceptions import BX
from bkr.server.model import System, SystemActivity, Distro
from bkr.server.xmlrpccontroller import RPCRoot

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
        system.reserve(service=u'XMLRPC')
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

        This method does not return until Cobbler has reported that the power 
        control was succesful. An exception will be raised if there is an error 
        communicating with Cobbler, or if Cobbler reports a failure.

        :param action: 'on', 'off', or 'reboot'
        :type action: string
        :param fqdn: fully-qualified domain name of the system to be power controlled
        :type fqdn: string
        :param clear_netboot: whether to clear netboot configuration before powering
        :type clear_netboot: boolean
        :param force: whether to power the system even if it is in use
        :type force: boolean

        .. versionadded:: 0.6
        """
        system = System.by_fqdn(fqdn, identity.current.user)
        if not force and system.user is not None \
                and system.user != identity.current.user:
            raise BX(_(u'System is in use'))
        system.action_power(action, wait=True, clear_netboot=clear_netboot)
        system.activity.append(SystemActivity(user=identity.current.user,
                service=u'XMLRPC', action=action, field_name=u'Power',
                old_value=u'', new_value=u'Success'))
        return action # because turbogears makes us return something

    @expose()
    @identity.require(identity.not_anonymous())
    def provision(self, fqdn, distro_install_name, ks_meta=None,
            kernel_options=None, kernel_options_post=None, kickstart=None,
            reboot=True):
        """
        Provisions a system with the given distro and options.

        :param distro_install_name: install name of distro to be provisioned
        :type distro_install_name: str
        :param ks_meta: kickstart options
        :type ks_meta: dict
        :param kernel_options: kernel options for installation
        :type kernel_options: str
        :param kernel_options_post: kernel options for after installation
        :type kernel_options_post: str
        :param kickstart: complete kickstart template
        :type kickstart: str
        :param reboot: whether to reboot the system after applying Cobbler changes
        :type reboot: bool

        .. versionadded:: 0.6
        """
        system = System.by_fqdn(fqdn, identity.current.user)
        if not system.can_provision_now(identity.current.user):
            raise BX(_(u'User %s has insufficient permissions to provision %s')
                    % (identity.current.user.user_name, system.fqdn))
        if not system.user == identity.current.user:
            raise BX(_(u'Reserve a system before provisioning'))
        distro = Distro.by_install_name(distro_install_name)
        try:
            system.action_provision(distro=distro, ks_meta=ks_meta,
                    kernel_options=kernel_options,
                    kernel_options_post=kernel_options_post,
                    kickstart=kickstart)
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
            try:
                system.remote.power(action='reboot')
            except Exception, e:
                log.exception('Failed to reboot')
                system.activity.append(SystemActivity(user=identity.current.user,
                        service=u'XMLRPC', action=u'Reboot',
                        field_name=u'Power', old_value=u'',
                        new_value=unicode(e)))
                raise
            system.activity.append(SystemActivity(user=identity.current.user,
                    service=u'XMLRPC', action=u'Reboot',
                    field_name=u'Power', old_value=u'', new_value=u'Success'))
        return system.fqdn # because turbogears makes us return something

# for sphinx
systems = SystemsController
