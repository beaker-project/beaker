#!/usr/bin/python
# -*- coding: utf-8 -*-


import os
import sys
from optparse import Option, IndentedHelpFormatter
import xmlrpclib
import cgi

from bkr.client.command import CommandOptionParser, ClientCommandContainer, Command
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
    except xmlrpclib.Fault, e:
        sys.stderr.write('XML-RPC fault: %s\n' % e.faultString)
        return 1
    except maybe_http_error, e:
        sys.stderr.write('HTTP error: %s\n' % e)
        content_type, _ = cgi.parse_header(e.response.headers['Content-Type'])
        if content_type == 'text/plain':
            sys.stderr.write(e.response.content)
        return 1


if __name__ == '__main__':
    sys.exit(main())
