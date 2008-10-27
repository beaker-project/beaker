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
        shoehorn = api.BootAPI()
        #for distro in self.shoehorn.distros():
        for distro in shoehorn.distros():
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
            os_version = curr_distro.os_version
            date_created = 0.0
            #Comment contains a more accurate os_version and the datestamp
            # of when the tree was composed.
            if curr_distro.comment:
                if curr_distro.comment.find(":") != -1:
                    (os_version,date_created) = curr_distro.comment.split(':')
            distro = dict( arch=arch, variant=variant, method=method,
                           os_version=os_version, virt=virt,
                           install_name = curr_distro.name, 
                           breed=curr_distro.breed,
                           date_created=date_created)
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
        system = self.shoehorn.systems().find(data['systemname'])
        profile = self.shoehorn.profiles().find(data['profilename'])

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
        return self.shoehorn.add_system(system)

    def power(self, systemname, action):
        """
        take a system name and power cycle/off
        """
        return True

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
