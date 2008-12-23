#!/usr/bin/python
#
# Copyright 2008
# Bill Peck <bpeck@redhat.com>
#
# This software may be freely redistributed under the terms of the GNU
# general public license.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

from cobbler import api
import md5
import string
import pprint
import re
import socket
import cobbler

class Labcontroller:

    # Update these if need be.
    version = "0.0.1"
    api_version = "0.0.1"
    description = "Allows Medusa to control a cobbler lab controller"
    shoehorn = api.BootAPI()

    def distros_md5(self):
        """
        Return an md5sum of the distros on this lab controller
        """

        md5sum = md5.new()
        self.shoehorn.deserialize()
        for distro in self.shoehorn.distros():
            md5sum.update(distro.name)
        return md5sum.hexdigest()

    def distros_list(self):
        """
        List all distros on this lab controller
        distros['RHEL5.3-Server-20081020.nightly'] : {'arch': 'x86_64',
                                                      'method': 'nfs',
                                                      'variant': 'None',
                                                      'virt'    : True,
                                                      'os_version': 'rhel5'}
        """
        valid_arches = ['i386','x86_64','ia64','ppc','ppc64','s390','s390x']
        valid_variants = ['AS','ES','WS','Desktop']
        valid_methods  = ['http','ftp','nfs']
        distros = {}
        self.shoehorn.deserialize()
        for curr_distro in self.shoehorn.distros():
            # If we don't know our os_version then skip
            if not curr_distro.os_version:
                continue
            name = curr_distro.name.split('_')[0]
            meta = string.join(curr_distro.name.split('_')[1:],'_').split('-')
            arch = '~'
            variant = '~'
            method = '~'
            virt = False
            for curr_arch in valid_arches:
                if curr_arch in meta:
                    arch = curr_arch
                    break
            for curr_variant in valid_variants:
                if curr_variant in meta:
                    variant = curr_variant
                    break
            for curr_method in valid_methods:
                if curr_method in meta:
                    method = curr_method
                    break
            if 'xen' in meta:
                virt = True
            # Don't add rhel3 and rhel4 without a variant
            if (curr_distro.os_version.find("rhel3") != -1 \
                or curr_distro.os_version.find("rhel4") != -1) and not variant:
                continue
            #Comment contains a more accurate os_version
            if curr_distro.comment:
                release = re.compile(r'family=(\w+\d+\.\d+)')
                if release.search(curr_distro.comment):
                    os_version = release.search(curr_distro.comment).group(1)
                else:
                    continue
            distro = dict( arch=arch, variant=variant, method=method,
                           os_version=os_version, virt=virt,
                           install_name = curr_distro.name, 
                           breed=curr_distro.breed,
                           date_created=curr_distro.tree_build_time)
            if name not in distros:
                distros[name] = [distro]
            else:
                distros[name].append(distro)
        return distros

    def provision(self, data):
        if not data.has_key("systemname"):
            return (-1, "no systemname specified")
        if not data.has_key("profilename"):
            return (-2, "no profilename specified")
        self.shoehorn.deserialize()
        system = self.shoehorn.systems().find(data['systemname'])
        if not system:
            system = self.shoehorn.new_system()
            system.set_name(data['systemname'])
            ipaddress = socket.gethostbyname_ex(data['systemname'])[2][0]
            system.set_ip_address(ipaddress, 'eth0')
        profile = self.shoehorn.profiles().find(data['profilename'])
        if not profile:
            return (-3, "%s profile not found!" % data['profilename'])

        if data.has_key("ksmeta"):
            system.set_ksmeta(data['ksmeta'])
        if data.has_key("kernel_options"):
            system.set_kernel_options(data['kernel_options'])
        if data.has_key("kernel_options_post"):
            system.set_kernel_options_post(data['kernel_options_post'])
        if data.has_key("kickstart"):
            filepath = '/var/lib/cobbler/kickstarts/systems/%s.ks' % system.name
            try:
                fo = open(filepath, 'w')
                fo.write(data['kickstart'])
                fo.close()
                del fo
            except (IOError, OSError), e:
                return (-3, "failed to write out kickstart")
            profile=self.shoehorn.copy_profile(profile, system.name)
            profile.set_kickstart(filepath)
        system.set_profile(profile.name)
        system.set_netboot_enabled(True)
        try:
            self.shoehorn.add_system(system)
        except cobbler.cexceptions.CX, e:
            return (-1, e.value)
        return (0, "Success")

    def power(self, action, data):
        """
        take a system name and power on/off/cycle
        """
        if "systemname" not in data:
            return (-1, "no systemname specified")
        if "power_type" not in data:
            return (-1, "no power_type specified")
        if "power_address" not in data:
            return (-1, "no power_address specified")
        self.shoehorn.deserialize()
        system = self.shoehorn.systems().find(data['systemname'])
        if not system:
            system = self.shoehorn.new_system()
            system.set_name(data['systemname'])
            # We set the profile to the first profile we know about.
            #  It doesn't really matter since we will overwrite this
            profile = self.shoehorn.profiles().__iter__().next()
            system.set_profile(profile.name)
            ipaddress = socket.gethostbyname_ex(data['systemname'])[2][0]
            system.set_ip_address(ipaddress)
        system.set_power_type(data['power_type'])
        system.set_power_address(data['power_address'])
        if "power_user" in data:
            system.set_power_user(data['power_user'])
        if "power_passwd" in data:
            system.set_power_pass(data['power_passwd'])
        if "power_id" in data:
            system.set_power_id(data['power_id'])
        try:
            self.shoehorn.add_system(system)
        except cobbler.cexceptions.CX, e:
            return (-1, e.value)
        if action=="on":
            try:
                rc = self.shoehorn.power_on(system)
            except cobbler.cexceptions.CX, e:
                return (-1, e.value)
        elif action=="off":
            try:
                rc = self.shoehorn.power_off(system)
            except cobbler.cexceptions.CX, e:
                return (-1, e.value)
        elif action=="reboot":
            try:
                rc = self.shoehorn.reboot(system)
            except cobbler.cexceptions.CX, e:
                return (-1, e.value)
        else:
           return (-1, "Invalid power action, off,on, or reboot")
        return (rc, "Success")
 
    def console_clear(self, systemname):
        """
        Clear a systems console log
        """
        return True

    def console_get(self, systemname):
        """
        return a systems console log
        """
        return True

if __name__ == "__main__":
    pp = pprint.PrettyPrinter(indent=4)
    l = Labcontroller()
    print l.distros_md5()
    print pp.pprint(l.distros_list())
    print l.distros_list().keys()
