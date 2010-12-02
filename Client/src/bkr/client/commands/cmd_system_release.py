
from bkr.client import BeakerCommand

class System_Release(BeakerCommand):
    """Release a reserved system"""
    enabled = True

    def options(self):
        self.parser.usage = "%%prog %s [options] <fqdn>" % self.normalized_name

    def run(self, *args, **kwargs):
        username = kwargs.pop("username", None)
        password = kwargs.pop("password", None)

        if len(args) != 1:
            self.parser.error('Exactly one system fqdn must be given')
        fqdn = args[0]

        self.set_hub(username, password)
        self.hub.systems.release(fqdn)
