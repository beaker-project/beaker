
# -*- coding: utf-8 -*-

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os
import sys
from optparse import Option, IndentedHelpFormatter, SUPPRESS_HELP
import xmlrpclib
import cgi
import krbV
from bkr.client.command import CommandOptionParser, ClientCommandContainer
from bkr.common import __version__


__all__ = (
    "main",
)


class BeakerCommandContainer(ClientCommandContainer):
    pass

class BeakerOptionParser(CommandOptionParser):
    standard_option_list = [
        Option('--hub', metavar='URL',
            help='Connect to Beaker server at URL (overrides config file)'),
        Option('--username',
            help='Use USERNAME for password authentication (overrides config file)'),
        Option('--password',
            help='Use PASSWORD for password authentication (overrides config file)'),
        Option('--proxy-user',
            help=SUPPRESS_HELP),
    ]

# register default command plugins
import bkr.client.commands
from bkr.client import conf
BeakerCommandContainer.register_module(bkr.client.commands, prefix="cmd_")


def main():
    global conf
    command_container = BeakerCommandContainer(conf=conf)
    formatter = IndentedHelpFormatter(max_help_position=60, width=120)
    parser = BeakerOptionParser(version=__version__,
            conflict_handler='resolve',
            command_container=command_container,
            default_command="help", formatter=formatter)

    # Need to deal with the possibility that requests is not importable...
    try:
        import requests
        maybe_http_error = (requests.HTTPError,)
    except ImportError:
        maybe_http_error = ()

    # This is parser.run(), but with more sensible error handling
    cmd, cmd_opts, cmd_args = parser.parse_args()
    try:
        return cmd.run(*cmd_args, **cmd_opts.__dict__)
    except krbV.Krb5Error, e:
        if e.args[0] == krbV.KRB5KRB_AP_ERR_TKT_EXPIRED:
            sys.stderr.write('Kerberos ticket expired (run kinit to obtain a new ticket)\n')
            return 1
        elif e.args[0] == krbV.KRB5_FCC_NOFILE:
            sys.stderr.write('No Kerberos credential cache found (run kinit to create one)\n')
            return 1
        else:
            raise
    except xmlrpclib.Fault, e:
        sys.stderr.write('XML-RPC fault: %s\n' % e.faultString)
        return 1
    except maybe_http_error, e:
        sys.stderr.write('HTTP error: %s\n' % e)
        content_type, _ = cgi.parse_header(e.response.headers.get('Content-Type', ''))
        if content_type == 'text/plain':
            sys.stderr.write(e.response.content.rstrip('\n') + '\n')
        return 1


if __name__ == '__main__':
    sys.exit(main())
