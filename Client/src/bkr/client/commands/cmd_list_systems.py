
import sys
import urllib
import urllib2
import lxml.etree
from bkr.client import BeakerCommand

class List_Systems(BeakerCommand):
    """List systems"""
    enabled = True

    def options(self):
        self.parser.usage = "%%prog %s [options]" % self.normalized_name
        self.parser.add_option('--available', action='store_const',
                const='available', dest='feed',
                help='Only include systems available to be used by this user')
        self.parser.add_option('--free', action='store_const',
                const='free', dest='feed',
                help='Only include systems available '
                     'to this user and not currently being used')
        self.parser.add_option('--mine', action='store_const',
                const='mine', dest='feed',
                help='Only include systems owned by this user')
        self.parser.add_option('--type', metavar='TYPE',
                help='Only include systems of TYPE')
        self.parser.add_option('--status', metavar='STATUS',
                help='Only include systems with STATUS')
        self.parser.add_option('--group', metavar='GROUP',
                help='Only include systems in GROUP')
        self.parser.set_defaults(feed='')

    def run(self, *args, **kwargs):
        username = kwargs.pop("username", None)
        password = kwargs.pop("password", None)

        if args:
            self.parser.error('This command does not accept any arguments')

        qs_args = [
            ('tg_format', 'atom'),
            ('list_tgp_limit', 0),
        ]
        for i, x in enumerate(['type', 'status', 'group']):
            if kwargs[x]:
                qs_args.extend([
                    ('systemsearch-%d.table' % i,     'System/%s' % x.capitalize()),
                    ('systemsearch-%d.operation' % i, 'is'),
                    ('systemsearch-%d.value' % i,     kwargs[x])
                ])
        feed_url = '/%s?%s' % (kwargs['feed'], urllib.urlencode(qs_args))

        # This will log us in using XML-RPC
        self.set_hub(username, password)

        # Now we can steal the cookie jar to make our own HTTP requests
        urlopener = urllib2.build_opener(urllib2.HTTPCookieProcessor(
                self.hub._transport.cookiejar))
        atom = lxml.etree.parse(urlopener.open(self.hub._hub_url + feed_url))
        titles = atom.xpath('/atom:feed/atom:entry/atom:title',
                namespaces={'atom': 'http://www.w3.org/2005/Atom'})
        if not titles:
            sys.stderr.write('Nothing Matches\n')
            sys.exit(1)
        for title in titles:
            print title.text.strip()
