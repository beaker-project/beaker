#!/usr/bin/python
# -*- coding: utf-8 -*-


import os
import sys
from optparse import Option, IndentedHelpFormatter
import xmlrpclib

import kobo.conf
from kobo.cli import CommandOptionParser
from kobo.client import ClientCommandContainer


__all__ = (
    "main",
)


class BeakerCommandContainer(ClientCommandContainer):
    pass


# register default command plugins
import bkr.client.commands
BeakerCommandContainer.register_module(bkr.client.commands, prefix="cmd_")


def main():
    config_file = os.environ.get("BEAKER_CLIENT_CONF", None)
    if not config_file:
        user_conf = os.path.expanduser('~/.beaker_client/config')
        old_conf = os.path.expanduser('~/.beaker')
        if os.path.exists(user_conf):
            config_file = user_conf
        elif os.path.exists(old_conf):
            config_file = old_conf
            sys.stderr.write("%s is deprecated for config, please use %s instead\n" % (old_conf, user_conf))
        else:
            config_file = "/etc/beaker/client.conf"
            sys.stderr.write("%s not found, using %s\n" % (user_conf, config_file))

    conf = kobo.conf.PyConfigParser()
    conf.load_from_file(config_file)

    command_container = BeakerCommandContainer(conf=conf)

    option_list = [
        Option("--username", help="specify user"),
        Option("--password", help="specify password"),
    ]

    formatter = IndentedHelpFormatter(max_help_position=60, width=120)
    parser = CommandOptionParser(command_container=command_container, default_command="help", formatter=formatter)
    parser._populate_option_list(option_list, add_help=False)

    # This is parser.run(), but with more sensible error handling
    cmd, cmd_opts, cmd_args = parser.parse_args()
    try:
        cmd.run(*cmd_args, **cmd_opts.__dict__)
    except (SystemExit, KeyboardInterrupt):
        raise
    except xmlrpclib.Fault, e:
        sys.stderr.write('XML-RPC fault: %s\n' % e.faultString)
        sys.exit(1)
    except Exception, e:
        sys.stderr.write('Exception: %s\n' % e)
        sys.exit(1)


if __name__ == '__main__':
    main()
