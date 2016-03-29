Subcommands are loaded from setuptools entry points
===================================================

Third-party packages can now supply their own bkr subcommands by defining 
a setuptools entry point in the ``bkr.client.commands`` group. The name of the 
entry point is used as the subcommand name, and the entry point itself must be 
a subclass of :py:class:`bkr.client.BeakerCommand`.

Previously the only way for packages to provide their own subcommand was to 
drop a module into the ``bkr.client.commands`` package, following certain 
naming conventions. This mechanism of loading subcommands is still supported 
for backwards compatibility.
