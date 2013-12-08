
import logging
import time
import os.path
from turbogears.config import get
import ovirtsdk.api
from bkr.server.bexceptions import VMCreationFailedException
from bkr.server.model.types import ImageType
from bkr.server.model.config import ConfigItem
from bkr.server.model.distrolibrary import KernelType

log = logging.getLogger(__name__)

class VirtManager(object):

    def __init__(self):
        self.api = None

    def __enter__(self):
        self.api = ovirtsdk.api.API(url=get('ovirt.api_url'), timeout=10,
                username=get('ovirt.username'), password=get('ovirt.password'),
                # XXX add some means to specify SSL CA cert
                insecure=True)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.api, api = None, self.api
        api.disconnect()

    def create_vm(self, name, lab_controllers, *args, **kwargs):
        if self.api is None:
            raise RuntimeError('Context manager was not entered')

        # Try to create the VM on every cluster that is in an acceptable data center
        for lab_controller in lab_controllers:
            for mapping in lab_controller.data_centers:
                cluster_query = 'datacenter.name=%s' % mapping.data_center
                clusters = self.api.clusters.list(cluster_query)
                if mapping.storage_domain:
                    storage_domains = [self.api.storagedomains.get(mapping.storage_domain)]
                else:
                    sd_query = 'datacenter=%s' % mapping.data_center
                    storage_domains = self.api.storagedomains.list(sd_query)
                for cluster in clusters:
                    log.debug('Trying to create vm %s on cluster %s', name, cluster.name)
                    vm = None
                    try:
                        self._create_vm_on_cluster(name, cluster,
                                storage_domains, *args, **kwargs)
                    except Exception:
                        log.exception("Failed to create VM %s on cluster %s",
                                name, cluster.name)
                        if vm is not None:
                            try:
                                vm.delete()
                            except Exception:
                                pass
                        continue
                    else:
                        return lab_controller
        raise VMCreationFailedException('No clusters successfully created VM %s' % name)

    def _create_vm_on_cluster(self, name, cluster, storage_domains,
            mac_address=None, virtio_possible=True):
        from ovirtsdk.xml.params import VM, Template, NIC, Network, Disk, \
                StorageDomains, MAC
        # Default of 1GB memory and 20GB disk
        memory = ConfigItem.by_name(u'default_guest_memory').current_value(1024) * 1024**2
        disk_size = ConfigItem.by_name(u'default_guest_disk_size').current_value(20) * 1024**3

        if virtio_possible:
            nic_interface = "virtio"
            disk_interface = "virtio"
        else:
            # use emulated interface
            nic_interface = "rtl8139"
            disk_interface = "ide"

        vm_definition = VM(name=name, memory=memory, cluster=cluster,
                type_='server', template=Template(name='Blank'))
        vm = self.api.vms.add(vm_definition)
        nic = NIC(name='eth0', interface=nic_interface, network=Network(name='rhevm'),
                mac=MAC(address=str(mac_address)))
        vm.nics.add(nic)
        disk = Disk(storage_domains=StorageDomains(storage_domain=storage_domains),
                size=disk_size, type_='data', interface=disk_interface, format='cow',
                bootable=True)
        vm.disks.add(disk)

        # Wait up to twenty seconds(!) for the disk image to be created.
        # Check both the vm state and disk state, image creation may not
        # lock the vms. That should be a RHEV issue, but it doesn't hurt
        # to check both of them by us.
        for _ in range(20):
            vm = self.api.vms.get(name)
            vm_state = vm.status.state
            # create disk with param 'name' doesn't work in RHEV 3.0, so just
            # find the first disk of the vm as we only attached one to it
            disk_state = vm.disks.list()[0].status.state
            if vm_state == 'down' and disk_state == "ok":
                break
            time.sleep(1)
        vm = self.api.vms.get(name)
        vm_state = vm.status.state
        disk_state = vm.disks.list()[0].status.state
        if vm_state != 'down':
            raise ValueError("VM %s's state: %s", name, vm_state)
        if disk_state != 'ok':
            raise ValueError("VM %s's disk state: %s", name, disk_state)

    def start_install(self, name, distro_tree, kernel_options, lab_controller):
        if self.api is None:
            raise RuntimeError('Context manager was not entered')
        from ovirtsdk.xml.params import OperatingSystem, Action, VM
        # RHEV can only handle a local path to kernel/initrd, so we rely on autofs for now :-(
        # XXX when this constraint is lifted, fix beakerd.virt_recipes too
        location = distro_tree.url_in_lab(lab_controller, 'nfs', required=True)
        kernel = distro_tree.image_by_type(ImageType.kernel, KernelType.by_name(u'default'))
        initrd = distro_tree.image_by_type(ImageType.initrd, KernelType.by_name(u'default'))
        local_path = location.replace('nfs://', '/net/', 1).replace(':/', '/', 1)
        kernel_path = os.path.join(local_path, kernel.path)
        initrd_path = os.path.join(local_path, initrd.path)
        log.debug(u'Starting VM %s installing %s', name, distro_tree)
        a = Action(vm=VM(os=OperatingSystem(kernel=kernel_path,
                initrd=initrd_path, cmdline=kernel_options)))
        self.api.vms.get(name).start(action=a)

    def destroy_vm(self, name):
        from ovirtsdk.infrastructure.errors import RequestError
        if self.api is None:
            raise RuntimeError('Context manager was not entered')
        vm = self.api.vms.get(name)
        if vm is not None:
            try:
                log.debug('Stopping %s on %r', name, self)
                vm.stop()
            except RequestError:
                pass # probably not running for some reason
            log.debug('Deleting %s on %r', name, self)
            vm.delete()
