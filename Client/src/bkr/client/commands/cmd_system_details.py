
import sys
import urllib
import urllib2
from bkr.client import BeakerCommand

class System_Details(BeakerCommand):
    """Export RDF/XML description of a system"""
    enabled = True

    def options(self):
        self.parser.usage = "%%prog %s [options] <fqdn>" % self.normalized_name

    def run(self, *args, **kwargs):
        username = kwargs.pop("username", None)
        password = kwargs.pop("password", None)

        if len(args) != 1:
            self.parser.error('Exactly one system fqdn must be given')
        fqdn = args[0]

        system_url = '/view/%s?tg_format=rdfxml' % urllib.quote(fqdn, '')

        # This will log us in using XML-RPC
        self.set_hub(username, password)

        # Now we can steal the cookie jar to make our own HTTP requests
        urlopener = urllib2.build_opener(urllib2.HTTPCookieProcessor(
                self.hub._transport.cookiejar))
        print urlopener.open(self.hub._hub_url + system_url).read()
