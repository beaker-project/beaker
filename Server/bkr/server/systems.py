
from turbogears import expose, identity, controllers
from bkr.server.bexceptions import BX
from bkr.server.model import System, SystemActivity
from bkr.server.xmlrpccontroller import RPCRoot

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
        """
        system = System.by_fqdn(fqdn, identity.current.user)
        system.unreserve(service=u'XMLRPC')
        return system.fqdn # because turbogears makes us return something

    @expose()
    @identity.require(identity.not_anonymous())
    def power(self, action, fqdn, force=False):
        """
        Controls power for the system with the given fully-qualified domain 
        name.

        Controlling power for a system is not normally permitted when the 
        system is in use by someone else, because it is likely to interfere 
        with their usage. Callers may pass True for the *force* argument to 
        override this safety check.

        This method does not return until Cobbler has reported that the power 
        control was succesful. An exception will be raised if there is an error 
        communicating with Cobbler, or if Cobbler reports a failure.

        :param action: 'on', 'off', or 'reboot'
        :type action: str
        :param force: whether to power the system even if it is in use
        :type force: bool
        """
        system = System.by_fqdn(fqdn, identity.current.user)
        if not force and system.user is not None \
                and not system.current_user(identity.current.user):
            raise BX(_(u'System is in use'))
        system.action_power(action, wait=True)
        system.activity.append(SystemActivity(user=identity.current.user,
                service='XMLRPC', action=action, field_name='Power',
                old_value=u'', new_value=u'Success'))
        return action # because turbogears makes us return something

# for sphinx
systems = SystemsController
