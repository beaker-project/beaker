
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
import novaclient.client
from sqlalchemy.orm.exc import NoResultFound
from bkr.server.util import absolute_url
from bkr.server.model.types import ImageType
from bkr.server.model.distrolibrary import KernelType
from bkr.server.model.lab import LabController
from bkr.server.model.openstack import OpenStackRegion

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
        self.nova = novaclient.client.Client('2',
                user.openstack_username,
                user.openstack_password,
                user.openstack_tenant_name,
                auth_url)

    def available_flavors(self):
        return self.nova.flavors.list()

    def create_vm(self, name, flavor):
        image_id = self.region.ipxe_image_id
        if not image_id:
            raise RuntimeError('iPXE image has not been uploaded')
        instance = self.nova.servers.create(name, image_id, flavor)
        log.info('Created %r', instance)
        try:
            self._wait_for_build(instance)
            # would be nice if nova let us build an instance without starting it
            instance.stop()
            self._wait_for_stop(instance)
            return uuid.UUID(instance.id)
        except:
            exc_type, exc_value, exc_tb = sys.exc_info()
            try:
                instance.delete()
            except Exception:
                log.exception('Failed to clean up %r during create_vm, leaked!',
                        self.instance)
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
            time.sleep(1)
            log.debug('%r still stopping', instance)
            instance.get()
            if instance.status != 'ACTIVE':
                break
        if instance.status != 'SHUTOFF':
            raise RuntimeError('%r failed to stop, status %s'
                    % (instance, instance.status))

    def start_vm(self, instance_id):
        self.nova.servers.start(instance_id)

    def destroy_vm(self, instance_id):
        self.nova.servers.delete(instance_id)

    def get_console_output(self, instance_id, length):
        return self.nova.servers.get_console_output(instance_id, length)
