#!/usr/bin/python
# -*- coding: utf-8 -*-


import os
import sys
from optparse import Option, IndentedHelpFormatter
import xmlrpclib

from kobo.cli import CommandOptionParser
from kobo.client import ClientCommandContainer


__all__ = (
    "main",
)


class BeakerCommandContainer(ClientCommandContainer):
    pass


# register default command plugins
import bkr.client.commands
from bkr.client import conf
BeakerCommandContainer.register_module(bkr.client.commands, prefix="cmd_")


def main():
    global conf
    command_container = BeakerCommandContainer(conf=conf)

    option_list = [
        Option('--hub', metavar='URL',
            help='Connect to Beaker server at URL (overrides config file)'),
        Option('--username',
            help='Use USERNAME for password authentication (overrides config file)'),
        Option('--password',
            help='Use PASSWORD for password authentication (overrides config file)'),
    ]

    formatter = IndentedHelpFormatter(max_help_position=60, width=120)
    parser = CommandOptionParser(command_container=command_container, default_command="help", formatter=formatter)
    parser._populate_option_list(option_list, add_help=False)

    # This is parser.run(), but with more sensible error handling
    cmd, cmd_opts, cmd_args = parser.parse_args()
    try:
        return cmd.run(*cmd_args, **cmd_opts.__dict__)
    except xmlrpclib.Fault, e:
        sys.stderr.write('XML-RPC fault: %s\n' % e.faultString)
        return 1


if __name__ == '__main__':
    sys.exit(main())
