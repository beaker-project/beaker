beaker-create-kickstart: Generate Anaconda kickstarts
=====================================================

.. program:: beaker-create-kickstart

Synopsis
--------

| :program:`beaker-create-kickstart` :option:`--user` <username>
       (:option:`--recipe-id` <recipeid> | :option:`--system` <fqdn> :option:`--distro-tree-id` <distrotreeid>)
       [*options*]

Description
-----------

``beaker-create-kickstart`` is used to generate customised kickstarts. Its
main purpose is for testing alternative templates, template variables, and
kernel options.

The generated kickstart is based off of a combination of a running/completed
recipe, system, and distro tree. It can then be further modified with any of
the available options. The resulting kickstart will be printed to stdout.

This command requires read access to the Beaker server configuration. Run it as 
root or as another user with read access to the configuration file.


Options
-------

.. option:: -u <username>, --user <username>

   Used for any user related options in the kickstart (i.e root password).

.. option:: -r <recipeid>, --recipe-id <recipeid>

   Use <recipeid> as the basis of the kickstart.

.. option:: -f <fqdn>, --system <fqdn>

   This system, combined with :option:`--distro-tree-id`, form the basis of
   the kickstart. Alternatively, :option:`--recipe-id` can be used.

.. option:: -d <distrotreeid>, --distro-tree-id <distrotreeid>

   This distro tree, combined with :option:`--system`, form the basis of
   the kickstart. Alternatively, :option:`--recipe-id` can be used.

.. option:: -t <directory>, --template-dir <directory>

   Specify an additional <directory> where kickstart templates can be found.
   Templates in this directory will take precedence over templates in the standard
   template directories. The templates need to be organized in a directory
   hierarchy that Beaker understands, see :ref:`override-kickstarts`.

.. option:: -m <options>, --ks-meta <options>

   Pass <options> into the kickstart.

.. option:: -p <options>, --kernel-options-post <options>

   Pass <options> to the kernel in the %post section of the kickstart.

Exit status
-----------

Non-zero on error, otherwise zero.

Examples
--------

Say you are developing a custom template for the ``timezone`` snippet, and you 
want to test the effect it will have on Beaker's kickstarts before you put it 
live in ``/etc/beaker``. Create a new directory, for example 
``./template-work``, mirroring the structure of snippets under ``/etc/beaker``. 
Your new ``timezone`` snippet would be placed in 
``./template-work/snippets/timezone``.

This command will generate a kickstart based on an existing recipe, looking up 
templates from your custom directory:

    beaker-create-kickstart --recipe-id 150 --template-dir ./template-work

You can generate a kickstart for the same recipe but without your custom
templates, and then diff them to see what changed:

    beaker-create-kickstart --recipe-id 150

You can also use this command to test the effect that install options will have 
for a particular system, before you set them in Beaker:

    beaker-create-kickstart --user admin --system invalid.example.com \
        --distro-tree-id 120 --ks-meta "grubport=0x3f8 ignoredisk=--only-use=vda"
