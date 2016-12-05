
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import sys
import logging
import time
import uuid
from turbogears import config
try:
    import keystoneclient
    has_keystoneclient = True
except ImportError:
    has_keystoneclient = False
try:
    from novaclient import client as nova_client
    has_novaclient = True
except ImportError:
    has_novaclient = False
try:
    from neutronclient.v2_0 import client as neutron_client
    has_neutronclient = True
except ImportError:
    has_neutronclient = False
from bkr.server.model import ConfigItem, VirtResource, OpenStackRegion

log = logging.getLogger(__name__)

class VirtManager(object):

    def __init__(self, user):
        self.user = user
        self.auth_url = config.get('openstack.identity_api_url')
        self.beaker_os_username = config.get('openstack.username')
        self.beaker_os_password = config.get('openstack.password')
        # For now we just support a single region, in future this could be expanded.
        self.region = OpenStackRegion.query.first()
        self._do_sanity_check()
        self.lab_controller = self.region.lab_controller
        keystone_session = self._create_keystone_session()
        self.keystoneclient = keystoneclient.v3.client.Client(session=keystone_session)
        self.novaclient = nova_client.Client('2', session=keystone_session)
        self.neutronclient = neutron_client.Client(session=keystone_session)

    def _do_sanity_check(self):
        if not self.auth_url:
            raise RuntimeError('OpenStack Identity API URL '
                    'was not configured in openstack.identity_api_url setting')
        if not has_novaclient:
            raise RuntimeError('Openstack was configured, but python-novaclient '
                    'is not installed')
        if not has_neutronclient:
            raise RuntimeError('Openstack was configured, but python-neutronclient '
                    'is not installed')
        if not has_novaclient:
            raise RuntimeError('Openstack was configured, but python-novaclient '
                    'is not installed')
        if not has_keystoneclient:
            raise RuntimeError('Openstack was configured, but python-keystoneclient '
                    'is not installed')
        if not self.beaker_os_username and not self.beaker_os_password:
            raise RuntimeError('Openstack was configured, but Beaker\'s OpenStack '
                    'account was not configured')
        if not self.region:
            raise RuntimeError('No region defined in openstack_region table')

        if not self.user.openstack_trust_id:
            raise RuntimeError('No Keystone trust created by %s' % self.user)

    def _create_keystone_session(self):
        auth = keystoneclient.auth.identity.v3.Password(
                   username=self.beaker_os_username,
                   password=self.beaker_os_password,
                   user_domain_id=u'default',
                   auth_url=self.auth_url,
                   trust_id=self.user.openstack_trust_id)
        session = keystoneclient.session.Session(auth=auth)
        # ensure this session is valid by getting a token
        auth.get_token(session)
        return session

    def available_flavors(self):
        return self.novaclient.flavors.list()

    def create_vm(self, name, flavor):
        image_id = self.region.ipxe_image_id
        if not image_id:
            raise RuntimeError('iPXE image has not been uploaded')
        with VirtNetwork(self.neutronclient, name) as net:
            instance = self.novaclient.servers.create(name, image_id, flavor,
                    nics=[{'net-id': net.network_id}])
            log.info('Created %r', instance)
            try:
                self._wait_for_build(instance)
                self._assign_floating_ip(net.floating_ip.get('id'), instance)
                # would be nice if nova let us build an instance without starting it
                instance.stop()
                self._wait_for_stop(instance)
                return VirtResource(uuid.UUID(instance.id), uuid.UUID(net.network_id),
                        uuid.UUID(net.subnet_id), uuid.UUID(net.router_id),
                        net.floating_ip.get('floating_ip_address'),
                        self.lab_controller)
            except:
                exc_type, exc_value, exc_tb = sys.exc_info()
                try:
                    instance.delete()
                except Exception:
                    log.exception('Failed to clean up %r during create_vm, leaked!',
                            instance)
                    # suppress this exception so the original one is not masked
                raise exc_type, exc_value, exc_tb

    def _wait_for_build(self, instance):
        for __ in range(20):
            time.sleep(5)
            log.debug('%r still building', instance)
            instance.get()
            if instance.status != 'BUILD':
                break
        if instance.status != 'ACTIVE':
            raise RuntimeError('%r failed to build, status %s'
                    % (instance, instance.status))

    def _wait_for_stop(self, instance):
        for __ in range(20):
            time.sleep(5)
            log.debug('%r still stopping', instance)
            instance.get()
            if instance.status != 'ACTIVE':
                break
        if instance.status != 'SHUTOFF':
            raise RuntimeError('%r failed to stop, status %s'
                    % (instance, instance.status))

    def _wait_for_delete(self, instance):
        is_deleted = False
        for __ in range(20):
            time.sleep(5)
            log.debug('%r still deleting', instance)
            try:
                instance.get()
            except:
                is_deleted = True
                break
        if not is_deleted:
            raise RuntimeError('%r failed to delete, status %s'
                    % (instance, instance.status))

    def _get_instance_port(self, instance_id):
        ports = self.neutronclient.list_ports(device_id=instance_id)['ports']
        # should be only one port associated with the instance
        assert len(ports) == 1
        return ports[0]

    def _assign_floating_ip(self, floating_ip, instance):
        port = self._get_instance_port(instance.id)
        self.neutronclient.update_floatingip(floating_ip, {'floatingip': {
                'port_id': port['id']}})
        log.info('Associated floating ip %r to %r', floating_ip, instance)

    def start_vm(self, instance_id):
        self.novaclient.servers.start(instance_id)

    def destroy_vm(self, vm):
        instance = self.novaclient.servers.get(vm.instance_id)
        self.novaclient.servers.delete(instance.id)
        self._wait_for_delete(instance)
        self.neutronclient.remove_interface_router(str(vm.router_id),
                {'subnet_id': str(vm.subnet_id)})
        self.neutronclient.delete_router(str(vm.router_id))
        self.neutronclient.delete_network(str(vm.network_id))
        fips = self.neutronclient.list_floatingips(floating_ip_address=vm.floating_ip)
        for fip in fips['floatingips']:
            self.neutronclient.delete_floatingip(fip['id'])

    def get_console_output(self, instance_id, length):
        return self.novaclient.servers.get_console_output(instance_id,
                length)

    def delete_keystone_trust(self):
        self.keystoneclient.trusts.delete(self.user.openstack_trust_id)

def create_keystone_trust(username, password, project_name):
    auth_url = config.get('openstack.identity_api_url')
    trustee = keystoneclient.v3.client.Client(
            username=config.get('openstack.username'),
            password=config.get('openstack.password'),
            auth_url=auth_url)
    try:
        trustor = keystoneclient.v3.client.Client(username=username,
                password=password, project_name=project_name, auth_url=auth_url)
        trust = trustor.trusts.create(trustor_user=trustor.user_id,
                                      trustee_user=trustee.user_id,
                                      role_names=trustor.auth_ref.role_names,
                                      impersonation=True,
                                      project=trustor.project_id)
        return trust.id
    except keystoneclient.exceptions.Unauthorized as exc:
        raise ValueError(exc.message)

class VirtNetwork(object):
    """
    This is a context manager which sets up an OpenStack network(neutron).
    """
    def __init__(self, client, name):
        self.neutron = client
        self.name = name
        self.network_id = None
        self.router_id = None
        self.subnet_id = None
        self.interface_id = None
        self.floating_ip = None

    def __repr__(self):
        return '%s(name=%r, network_id=%r, router_id=%r, subnet_id=%r, \
                interface_id=%r)' % (self.__class__.__name__, self.name,
                self.network_id, self.router_id, self.subnet_id, self.interface_id)

    def _create_router(self, external_network_id):
        external_gateway_info = {'external_gateway_info': {
                 'network_id': external_network_id},
                 'name': self.name,
                 'admin_state_up': True}
        router = self.neutron.create_router({'router': external_gateway_info})
        log.info('Created router %r',router)
        return router['router']['id']

    def _create_network(self):
        network = self.neutron.create_network({'network':  {'name': self.name}})
        log.info('Created network %r', network)
        return network['network']['id']

    def _create_subnet(self, network_id):
        cidr = ConfigItem.by_name(u'guest_private_network').\
                current_value('192.168.10.0/24')
        subnet_info = {'name': self.name, 'network_id': network_id, 'cidr': cidr,
                  'ip_version': 4}
        subnet = self.neutron.create_subnet({'subnet': subnet_info})
        log.info('Created subnet %r', subnet)
        return subnet['subnet']['id']

    def _create_floating_ip(self, network_id):
        fip = self.neutron.create_floatingip({'floatingip': {
                'floating_network_id': network_id}})
        log.info('Created floating ip %r', fip)
        return fip['floatingip']

    def _add_interface_to_router(self, router_id, subnet_id):
        interface = self.neutron.add_interface_router(router_id, {
                'subnet_id': subnet_id
        })
        log.info('Added interface %r', interface)
        return interface['id']

    def _configure_network(self):
        networks = self.neutron.list_networks().get('networks')
        external_network = next((network for network in networks
                if network.get('router:external')), None)
        if not external_network:
            raise RuntimeError('No external network is available')
        self.router_id = self._create_router(external_network.get('id'))
        self.network_id = self._create_network()
        self.subnet_id = self._create_subnet(self.network_id)
        self.interface_id = self._add_interface_to_router(self.router_id,
                self.subnet_id)
        self.floating_ip = self._create_floating_ip(external_network.get('id'))

    def _cleanup(self):
        try:
            if self.interface_id:
                self.neutron.remove_interface_router(self.router_id, {'subnet_id': self.subnet_id})
            if self.router_id:
                self.neutron.delete_router(self.router_id)
            if self.network_id:
                self.neutron.delete_network(self.network_id)
            if self.floating_ip:
                self.neutron.delete_floatingip(self.floating_ip.get('id'))
        except Exception:
            log.exception('Failed to clean up network %s, leaked!', self.name)
            # suppress this exception so the original one is not masked

    def __enter__(self):
        try:
            self._configure_network()
            return self
        except:
            self._cleanup()
            raise

    def __exit__(self, exc_type, exc_value, exc_tb):
        if exc_type:
            # clean up the network resources if any exception happens
            self._cleanup()
