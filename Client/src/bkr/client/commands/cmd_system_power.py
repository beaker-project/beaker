
from bkr.client import BeakerCommand

class System_Power(BeakerCommand):
    """Control power for a system"""
    enabled = True

    valid_actions = ('on', 'off', 'reboot')

    def options(self):
        self.parser.usage = "%%prog %s [options] <fqdn>" % self.normalized_name
        self.parser.add_option('--action', metavar='ACTION',
                help='Perform ACTION (on, off, or reboot) [default: %default]')
        self.parser.add_option('--clear-netboot', action='store_true',
                help="Clear system's netboot configuration "
                     "before performing action")
        self.parser.add_option('--force', action='store_true',
                help='Perform action even if system is '
                     'currently in use by another user')
        self.parser.set_defaults(action='reboot', force=False)

    def run(self, *args, **kwargs):
        username = kwargs.pop("username", None)
        password = kwargs.pop("password", None)

        if len(args) != 1:
            self.parser.error('Exactly one system fqdn must be given')
        fqdn = args[0]

        if kwargs['action'] not in self.valid_actions:
            self.parser.error('Power action must be one of: %r'
                    % (self.valid_actions,))

        self.set_hub(username, password)
        self.hub.systems.power(kwargs['action'], fqdn,
                kwargs['clear_netboot'], kwargs['force'])
