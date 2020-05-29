.. _beaker-import:

beaker-import: Import distros
=============================

.. program:: beaker-import

Synopsis
--------

| :program:`beaker-import` [*options*] <distro_url> ...

Description
-----------

Imports a distro from the given ``distro_url``.  A valid
``distro_url`` is nfs://, http:// or ftp://.  Multiple ``distro_url``
can be specified with the primary ``distro_url`` being either http://
or ftp://.

In order for an import to succeed, a :file:`.treeinfo` or a :file:`.composeinfo`
must be present at the supplied ``distro_url``. Alternatively, you can also do
what is called a "naked" import by specifying ``--family``,
``--version``, ``--name``, ``--arch``, ``--kernel``,
``--initrd``. Only one tree can be imported at a time when doing a
naked import.

Options
-------

.. option:: -j, --json

   Prints the tree to be imported, in JSON format

.. option:: -c <cmd>, --add-distro-cmd <cmd>

   Command to run to add a new distro. By default this is
   :program:`/var/lib/beaker/addDistro.sh`

.. option:: -n <name>, --name <name>

   Alternate name to use, otherwise we read it from :file:`.treeinfo`

.. option:: -t <tag>, --tag <tag>

   Additional tags to add to the distro.

.. option:: -r, --run

   Run automated Jobs

.. option:: -v, --debug

   Show debug messages

.. option:: --dry-run

   Do not actually add any distros to beaker

.. option:: -q, --quiet

   Less messages

.. option:: --family <family>

   Specify family

.. option:: --variant <variant>

   Specify variant. Multiple values are valid when importing a compose>=RHEL7.

.. option:: --version <version>

   Specify version

.. option:: --kopts <kernel options>

   Add kernel options to use for install

.. option:: --kopts-post <post install kernel options>

   Add kernel options to use post install

.. option:: --ks-meta <ksmeta variables>

   Add variables to use in kickstart templates

.. option:: --preserve-install-options

   Do not overwrite the *'Install Options' (Kickstart Metadata, Kernel Options,
   & Kernel Options Post)* already stored for the distro. This option can not be
   used with any of --kopts, --kopts-post, or --ks-meta

.. option:: --buildtime <buildtime>

   Specify build time

.. option:: --arch <arch>

   Specify arch. Multiple values are valid when importing a compose

.. option:: --ignore-missing-tree-compose

   If a specific tree within a compose is missing, do not print any
   errors


Naked tree options
~~~~~~~~~~~~~~~~~~

These options only apply when importing without a .treeinfo or .composeinfo.

.. option:: --kernel <kernel>

   Specify path to kernel (relative to distro_url)

.. option:: --initrd <initrd>

   Specify path to initrd (relative to distro_url)

.. option:: --lab-controller <lab_controller>

   Specify which lab controller to import to. Defaults to http://localhost:8000.


Exit status
-----------

Non-zero on error, otherwise zero.

If ``--ignore-missing-tree-compose`` is not specified, a non-zero exit
status will be returned if any of the trees cannot be imported.

Examples
--------

When ``.composeinfo`` and ``.treeinfo`` are available::

    $ beaker-import \
        http://mymirror.example.com/pub/fedora/linux/releases/17/Fedora/ \
        ftp://mymirror.example.com/pub/fedora/linux/releases/17/Fedora/  \
        nfs://mymirror.example.com:/pub/fedora/linux/releases/17/Fedora/


Naked import::

    $ beaker-import \
       http://mymirror.example.com/FedoraNew/ \
        --family FedoraNew \
        --name FedoraNew-atomic \
        --arch x86_64 \
        --version 1 \
        --initrd=images/pxeboot/initrd.img \
        --kernel=images/pxeboot/vmlinuz \

The above command will import the distro tree at the given URL with
the supplied meta-data. The locations of the "initrd" and the "kernel"
are relative to this URL.
