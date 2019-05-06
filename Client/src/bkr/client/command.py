# -*- coding: utf-8 -*-

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import optparse
import os
import sys
from optparse import Option

import six

from bkr.common.hub import HubProxy
from bkr.common.pyconfig import PyConfigParser


def username_prompt(prompt=None, default_value=None):
    """
    Ask for a username.
    """

    if default_value is not None:
        return default_value

    prompt = prompt or "Enter your username: "
    sys.stderr.write(prompt)
    return sys.stdin.readline()


def password_prompt(prompt=None, default_value=None):
    """
    Ask for a password.
    """
    import getpass

    if default_value is not None:
        return default_value

    prompt = prompt or "Enter your password: "
    try:
        # try to use stderr stream
        result = getpass.getpass(prompt, stream=sys.stderr)
    except TypeError:
        # fall back to stdout
        result = getpass.getpass(prompt)
    return result


def yes_no_prompt(prompt, default_value=None):
    """
    Give a yes/no (y/n) question.
    """
    if default_value is not None:
        if default_value not in ("Y", "N"):
            raise ValueError("Invalid default value: %s" % default_value)
        default_value = default_value.upper()

    prompt = "%s [%s/%s]: " % (prompt, ("y", "Y")[default_value == "Y"], ("n", "N")[default_value == "N"])
    sys.stderr.write(prompt)

    while True:
        user_input = sys.stdin.readline().strip().upper()
        if user_input == "" and default_value is not None:
            user_input = default_value

        if user_input == "Y":
            return True
        if user_input == "N":
            return False


def are_you_sure_prompt(prompt=None):
    """
    Give a yes/no (y/n) question.
    """
    prompt = prompt or "Are you sure? Enter 'YES' to continue: "
    sys.stderr.write(prompt)
    user_input = sys.stdin.readline().strip()

    if user_input == "YES":
        return True

    return False


class Plugin(object):
    """A plugin base class."""

    author = None
    version = None
    enabled = False

    def __getattr__(self, name):
        """
        Get missing attribute from a container.
        This is quite hackish but it allows to define settings
        and methods per container.
        """
        return getattr(self.container, name)


class Command(Plugin):
    """
    An abstract class representing a command for CommandOptionParser.
    """

    enabled = False
    admin = False

    username_prompt = staticmethod(username_prompt)
    password_prompt = staticmethod(password_prompt)
    yes_no_prompt = staticmethod(yes_no_prompt)
    are_you_sure_prompt = staticmethod(are_you_sure_prompt)

    def __init__(self, parser):
        Plugin.__init__(self)
        self.parser = parser

    def options(self):
        """
        Add options to self.parser.
        """
        pass

    def run(self, *args, **kwargs):
        """
        Run a command. Arguments contain parsed options.
        """
        raise NotImplementedError()


class PluginContainer(object):
    """
    A plugin container.

    Usage: Inherit PluginContainer and register plugins to the new class.

    """

    def __getitem__(self, name):
        return self._get_plugin(name)

    def __iter__(self):
        return six.iterkeys(self.plugins)

    @classmethod
    def normalize_name(cls, name):
        return name

    @classmethod
    def _get_plugins(cls):
        """
        Return dictionary of registered plugins.
        """

        result = {}
        parent_plugins = cls._get_parent_plugins(cls.normalize_name)  # pylint: disable=no-member
        class_plugins = getattr(cls, "_class_plugins", {})
        d = parent_plugins.copy()
        d.update(class_plugins)
        for name, plugin_class in d.items():
            result[name] = plugin_class
        return result

    @classmethod
    def _get_parent_plugins(cls, normalize_function):
        result = {}
        for parent in cls.__bases__:
            if parent is PluginContainer:
                # don't use PluginContainer itself - plugins have to be registered to subclasses
                continue

            if not issubclass(parent, PluginContainer):
                # skip parents which are not PluginContainer subclasses
                continue

            # read inherited plugins first (conflicts are resolved recursively)
            plugins = parent._get_parent_plugins(normalize_function)  # pylint: disable=no-member

            # read class plugins, override inherited on name conflicts
            if hasattr(parent, "_class_plugins"):
                for plugin_class in parent._class_plugins.values():  # pylint: disable=no-member
                    normalized_name = normalize_function(plugin_class.__name__)
                    plugins[normalized_name] = plugin_class

            for name, value in six.iteritems(plugins):
                if result.get(name, value) != value:
                    raise RuntimeError(
                        "Cannot register plugin '%s'. "
                        "Another plugin with the same normalized name (%s) "
                        "is already in the container." % (str(value), normalized_name))

            result.update(plugins)

        return result

    @property
    def plugins(self):
        if not hasattr(self, "_plugins"):
            self._plugins = self.__class__._get_plugins()
        return self._plugins

    def _get_plugin(self, name):
        """
        Return a plugin or raise KeyError.
        """
        normalized_name = self.normalize_name(name)

        if normalized_name not in self.plugins:
            raise KeyError("Plugin not found: %s" % normalized_name)

        plugin = self.plugins[normalized_name]
        plugin.container = self
        plugin.normalized_name = normalized_name
        return plugin

    @classmethod
    def register_plugin(cls, plugin, name=None):
        """
        Register a new plugin. Return normalized plugin name.
        """

        if cls is PluginContainer:
            raise TypeError("Can't register plugin to the PluginContainer base class.")

        if "_class_plugins" not in cls.__dict__:
            cls._class_plugins = {}

        if not getattr(plugin, "enabled", False):
            return

        if not name:
            name = cls.normalize_name(plugin.__name__)
        cls._class_plugins[name] = plugin
        return name

    @classmethod
    def register_module(cls, module, prefix=None, skip_broken=False):
        """

        Register all plugins in a module's sub-modules.

        @param module: a python module that contains plugin sub-modules
        @type  module: module
        @param prefix: if specified, only modules with this prefix will be processed
        @type  prefix: str
        @param skip_broken: skip broken sub-modules and print a warning
        @type  skip_broken: bool
        """
        path = os.path.dirname(module.__file__)
        module_list = []

        for fn in os.listdir(path):
            if not fn.endswith(".py"):
                continue
            if fn.startswith("_"):
                continue
            if prefix and not fn.startswith(prefix):
                continue
            if not os.path.isfile(os.path.join(path, fn)):
                continue
            module_list.append(fn[:-3])

        if skip_broken:
            for mod in module_list[:]:
                try:
                    __import__(module.__name__, {}, {}, [mod])
                except:
                    import sys
                    sys.stderr.write("WARNING: Skipping broken plugin module: %s.%s"
                                     % (module.__name__, mod))
                    module_list.remove(mod)
        else:
            __import__(module.__name__, {}, {}, module_list)

        for mn in module_list:
            mod = getattr(module, mn)
            for pn in dir(mod):
                plugin = getattr(mod, pn)
                if type(plugin) is type and issubclass(plugin, Plugin) and plugin is not Plugin:
                    cls.register_plugin(plugin)


class BeakerClientConfigurationError(ValueError):
    """
    Raised to indicate that the Beaker client is not configured properly.
    """
    pass


class CommandContainer(PluginContainer):
    """
    Container for Command classes.
    """

    @classmethod
    def normalize_name(cls, name):
        """
        Replace some characters in command names.
        """
        return name.lower().replace('_', '-').replace(' ', '-')


class ClientCommandContainer(CommandContainer):

    def __init__(self, conf, **kwargs):
        self.conf = PyConfigParser()
        self.conf.load_from_conf(conf)
        self.conf.load_from_dict(kwargs)

    def set_hub(self, username=None, password=None, auto_login=True, proxy_user=None):
        if username:
            if password is None:
                password = password_prompt(default_value=password)
            self.conf["AUTH_METHOD"] = "password"
            self.conf["USERNAME"] = username
            self.conf["PASSWORD"] = password
        if proxy_user:
            self.conf["PROXY_USER"] = proxy_user

        cacert = self.conf.get('CA_CERT')
        if cacert and not os.path.exists(cacert):
            raise BeakerClientConfigurationError(
                'CA_CERT configuration points to non-existing file: %s' % cacert)

        self.hub = HubProxy(conf=self.conf, auto_login=auto_login)


class CommandOptionParser(optparse.OptionParser):
    """Enhanced OptionParser with plugin support."""

    def __init__(self,
                 usage=None,
                 option_list=None,
                 option_class=Option,
                 version=None,
                 conflict_handler="error",
                 description=None,
                 formatter=None,
                 add_help_option=True,
                 prog=None,
                 command_container=None,
                 default_command="help",
                 add_username_password_options=False):

        usage = usage or "%prog <command> [args] [--help]"
        self.container = command_container
        self.default_command = default_command
        self.command = None
        formatter = formatter or optparse.IndentedHelpFormatter(max_help_position=33)

        optparse.OptionParser.__init__(self, usage, option_list, option_class, version,
                                       conflict_handler, description, formatter, add_help_option,
                                       prog)

        if add_username_password_options:
            option_list = [
                optparse.Option("--username", help="specify user"),
                optparse.Option("--password", help="specify password"),
            ]
            self._populate_option_list(option_list, add_help=False)

    def print_help(self, file=None, admin=False):
        if file is None:
            file = sys.stdout
        file.write(self.format_help())
        if self.command in (None, "help", "help-admin"):
            file.write("\n")
            file.write(self.format_help_commands(admin=admin))

    def format_help_commands(self, admin=False):
        commands = []
        admin_commands = []

        for name, plugin in sorted(six.iteritems(self.container.plugins)):
            if getattr(plugin, 'hidden', False):
                continue
            is_admin = getattr(plugin, "admin", False)
            text = "  %-30s %s" % (name, plugin.__doc__.strip() if plugin.__doc__ else "")
            if is_admin:
                if admin:
                    admin_commands.append(text)
            else:
                commands.append(text)

        if commands:
            commands.insert(0, "commands:")
            commands.append("")

        if admin_commands:
            admin_commands.insert(0, "admin commands:")
            admin_commands.append("")

        return "\n".join(commands + admin_commands)

    def parse_args(self, args=None, values=None):
        """
        Return (command_instance, opts, args)
        """
        args = self._get_args(args)

        if len(args) > 0 and not args[0].startswith("-"):
            command = args[0]
            args = args[1:]
        else:
            command = self.default_command
            # keep args as is

        if not command in self.container.plugins:
            self.error("unknown command: %s" % command)

        CommandClass = self.container[command]
        cmd = CommandClass(self)
        if self.command != cmd.normalized_name:
            self.command = cmd.normalized_name
            cmd.options()
        cmd_opts, cmd_args = optparse.OptionParser.parse_args(self, args, values)
        return cmd, cmd_opts, cmd_args

    def run(self, args=None, values=None):
        """
        Parse arguments and run a command
        """
        cmd, cmd_opts, cmd_args = self.parse_args(args, values)
        cmd_kwargs = cmd_opts.__dict__
        cmd.run(*cmd_args, **cmd_kwargs)


class Help(Command):
    """
    Show this help message and exit
    """
    enabled = True

    def options(self):
        pass

    def run(self, *args, **kwargs):
        self.parser.print_help(admin=False)


class Help_Admin(Command):
    """
    Show help message about administrative commands and exit
    """
    enabled = True

    def options(self):
        # override default --help option
        opt = self.parser.get_option("--help")
        opt.action = "store_true"
        opt.dest = "help"

    def run(self, *args, **kwargs):
        self.parser.print_help(admin=True)


CommandContainer.register_plugin(Help)
CommandContainer.register_plugin(Help_Admin)
