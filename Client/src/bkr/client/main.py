
# -*- coding: utf-8 -*-

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os
import sys
import pkg_resources
import logging
from optparse import Option, IndentedHelpFormatter, SUPPRESS_HELP
import xmlrpclib
import cgi
import krbV
from bkr.client.command import CommandOptionParser, ClientCommandContainer, BeakerClientConfigurationError
from bkr.common import __version__
from bkr.log import log_to_stream


__all__ = (
    "main",
)


class BeakerCommandContainer(ClientCommandContainer):

    @classmethod
    def register_all(cls):
        # Load all modules in the bkr.client.commands package as commands, for 
        # backwards compatibility with older packages that just drop their files 
        # into the bkr.client.commands package.
        import bkr.client.commands
        cls.register_module(bkr.client.commands, prefix='cmd_')
        # Load subcommands from setuptools entry points in the bkr.client.commands 
        # group. This is the new, preferred way for other packages to provide their 
        # own bkr subcommands.
        for entrypoint in pkg_resources.iter_entry_points('bkr.client.commands'):
            cls.register_plugin(entrypoint.load(), name=entrypoint.name)

class BeakerOptionParser(CommandOptionParser):
    standard_option_list = [
        Option('--hub', metavar='URL',
            help='Connect to Beaker server at URL (overrides config file)'),
        Option('--username',
            help='Use USERNAME for password authentication (overrides config file)'),
        Option('--password',
            help='Use PASSWORD for password authentication (overrides config file)'),
        Option('--insecure', action='store_true',
            help='Skip SSL certificate validity checks'),
        Option('--proxy-user',
            help=SUPPRESS_HELP),
    ]

BeakerCommandContainer.register_all()
from bkr.client import conf, BeakerJobTemplateError

def warn_on_version_mismatch(response):
    if 'X-Beaker-Version' not in response.headers:
        sys.stderr.write('WARNING: client version is %s '
                'but server version is < 24.0\n'
                % __version__)
    else:
        server_version = response.headers['X-Beaker-Version']
        server_major = server_version.split('.', 1)[0]
        client_major = __version__.split('.', 1)[0]
        if server_major != client_major:
            sys.stderr.write('WARNING: client version is %s '
                    'but server version is %s\n'
                    % (__version__, server_version))

def main():
    log_to_stream(sys.stderr, level=logging.WARNING)

    global conf
    command_container = BeakerCommandContainer(conf=conf)
    formatter = IndentedHelpFormatter(max_help_position=60, width=120)
    parser = BeakerOptionParser(version=__version__,
            conflict_handler='resolve',
            command_container=command_container,
            default_command="help", formatter=formatter)

    # This is parser.run(), but with more sensible error handling
    cmd, cmd_opts, cmd_args = parser.parse_args()

    if not cmd_opts.hub and not conf:
        sys.stderr.write("Configuration file not found. Please create an /etc/beaker/client.conf "
                 "or ~/.beaker_client/config configuration file.\n")
        return 1


    # Need to deal with the possibility that requests is not importable...
    try:
        import requests
        maybe_http_error = (requests.HTTPError,)
    except ImportError:
        maybe_http_error = ()

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
        warn_on_version_mismatch(e.response)
        sys.stderr.write('HTTP error: %s\n' % e)
        content_type, _ = cgi.parse_header(e.response.headers.get('Content-Type', ''))
        if content_type == 'text/plain':
            sys.stderr.write(e.response.content.rstrip('\n') + '\n')
        return 1
    except BeakerJobTemplateError, e:
        sys.stderr.write('%s\n' % e)
        return 1
    except BeakerClientConfigurationError, e:
        sys.stderr.write('%s\n' % e)
        return 1


if __name__ == '__main__':
    sys.exit(main())
