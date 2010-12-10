
import sys
from bkr.client import BeakerCommand

class System_Provision(BeakerCommand):
    """Provision a system with a distro"""
    enabled = True

    def options(self):
        self.parser.usage = "%%prog %s [options] <fqdn>" % self.normalized_name
        self.parser.add_option('--distro', metavar='INSTALL_NAME',
                help='Provision with distro named INSTALL_NAME')
        self.parser.add_option('--ks-meta', metavar='OPTS',
                help='Pass OPTS as kickstart metadata')
        self.parser.add_option('--kernel-options', metavar='OPTS',
                help='Pass OPTS as kernel options during installation')
        self.parser.add_option('--kernel-options-post', metavar='OPTS',
                help='Pass OPTS as kernel options after installation')
        self.parser.add_option('--kickstart', metavar='FILENAME',
                help='Read complete kickstart from FILENAME (- for stdin)')
        self.parser.add_option('--no-reboot',
                action='store_false', dest='reboot',
                help="Set Cobbler configuration for system but don't reboot")
        self.parser.set_defaults(reboot=True)

    def run(self, *args, **kwargs):
        username = kwargs.pop("username", None)
        password = kwargs.pop("password", None)

        if len(args) != 1:
            self.parser.error('Exactly one system fqdn must be given')
        fqdn = args[0]

        if not kwargs['distro']:
            self.parser.error('Distro must be given with --distro')

        if kwargs['kickstart'] == '-':
            kickstart = sys.stdin.read()
        elif kwargs['kickstart']:
            kickstart = open(kwargs['kickstart'], 'r').read()
        else:
            kickstart = None

        self.set_hub(username, password)
        self.hub.systems.provision(fqdn, kwargs['distro'],
                kwargs['ks_meta'], kwargs['kernel_options'],
                kwargs['kernel_options_post'], kickstart, kwargs['reboot'])
