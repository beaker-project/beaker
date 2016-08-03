
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import sys
import logging
import time
import os.path
import uuid
import tempfile
import subprocess
from turbogears import config
try:
    import novaclient.client
    has_novaclient = True
except ImportError:
    has_novaclient = False
try:
    from neutronclient.v2_0 import client as neutron_client
    has_neutronclient = True
except ImportError:
    has_neutronclient = False
from sqlalchemy.orm.exc import NoResultFound
from bkr.server.util import absolute_url
from bkr.server.model.types import ImageType
from bkr.server.model.distrolibrary import KernelType
from bkr.server.model.lab import LabController
from bkr.server.model.openstack import OpenStackRegion
from bkr.server.model import ConfigItem, VirtResource


log = logging.getLogger(__name__)

class VirtManager(object):

    def __init__(self, user):
        auth_url = config.get('openstack.identity_api_url')
        if not auth_url:
            raise RuntimeError('OpenStack Identity API URL '
                    'was not configured in openstack.identity_api_url setting')
        # For now we just support a single region, in future this could be expanded.
        self.region = OpenStackRegion.query.first()
        if not self.region:
            raise RuntimeError('No region defined in openstack_region table')
        self.lab_controller = self.region.lab_controller
        if not has_novaclient:
            raise RuntimeError('Openstack was configured, but python-novaclient '
                    'is not installed')
        self.nova = novaclient.client.Client('2',
                user.openstack_username,
                user.openstack_password,
                user.openstack_tenant_name,
                auth_url)
        if not has_neutronclient:
            raise RuntimeError('Openstack was configured, but python-neutronclient '
                    'is not installed')
        self.neutron = neutron_client.Client(
                username=user.openstack_username,
                password=user.openstack_password,
                tenant_name=user.openstack_tenant_name,
                auth_url=auth_url)

    def available_flavors(self):
        return self.nova.flavors.list()

    def create_vm(self, name, flavor):
        image_id = self.region.ipxe_image_id
        if not image_id:
            raise RuntimeError('iPXE image has not been uploaded')
        with VirtNetwork(self.neutron, name) as net:
            instance = self.nova.servers.create(name, image_id, flavor,
                    nics=[{'net-id': net.network_id}])
            log.info('Created %r', instance)
            try:
                self._wait_for_build(instance)
                # would be nice if nova let us build an instance without starting it
                instance.stop()
                self._wait_for_stop(instance)
                return VirtResource(uuid.UUID(instance.id), uuid.UUID(net.network_id),
                        uuid.UUID(net.subnet_id), uuid.UUID(net.router_id),
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

    def start_vm(self, instance_id):
        self.nova.servers.start(instance_id)

    def destroy_vm(self, vm):
        self.nova.servers.delete(vm.instance_id)
        self.neutron.remove_interface_router(str(vm.router_id),
                {'subnet_id': str(vm.subnet_id)})
        self.neutron.delete_router(str(vm.router_id))
        self.neutron.delete_network(str(vm.network_id))

    def get_console_output(self, instance_id, length):
        return self.nova.servers.get_console_output(instance_id, length)


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
        log.info('Created subnet %r',subnet)
        return subnet['subnet']['id']

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

    def _cleanup(self):
        try:
            if self.interface_id:
                self.neutron.remove_interface_router(self.router_id, {'subnet_id': self.subnet_id})
            if self.router_id:
                self.neutron.delete_router(self.router_id)
            if self.network_id:
                self.neutron.delete_network(self.network_id)
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
