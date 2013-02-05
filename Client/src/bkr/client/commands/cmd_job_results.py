# -*- coding: utf-8 -*-

"""
bkr job-results: Export Beaker job results as XML
=================================================

.. program:: bkr job-results

Synopsis
--------

:program:`bkr job-results` [--prettyxml] [*options*] <taskspec>...

Description
-----------

Specify one or more <taskspec> arguments to be exported. An XML dump of the 
results for each argument will be printed to stdout.

The <taskspec> arguments follow the same format as in other :program:`bkr` 
subcommands (for example, ``J:1234``). See :ref:`Specifying tasks <taskspec>` 
in :manpage:`bkr(1)`.

Options
-------

.. option:: --prettyxml

   Pretty-print the XML (with indentation and line breaks, suitable for human 
   consumption).

Common :program:`bkr` options are described in the :ref:`Options 
<common-options>` section of :manpage:`bkr(1)`.

Exit status
-----------

Non-zero on error, otherwise zero.

Examples
--------

Display results for job 12345 in human-readable form (assuming the human can 
read XML)::

    bkr job-results --prettyxml J:12345

See also
--------

:manpage:`bkr(1)`
"""


from bkr.client import BeakerCommand
from optparse import OptionValueError
from bkr.client.task_watcher import *
from xml.dom.minidom import Document, parseString

class Job_Results(BeakerCommand):
    """Get Jobs/Recipes Results"""
    enabled = True

    def options(self):
        self.parser.usage = "%%prog %s [options] <taskspec>..." % self.normalized_name
        self.parser.add_option(
            "--prettyxml",
            default=False,
            action="store_true",
            help="Pretty print the xml",
        )


    def run(self, *args, **kwargs):
        self.check_taskspec_args(args)

        prettyxml   = kwargs.pop("prettyxml", None)

        self.set_hub(**kwargs)
        for task in args:
            myxml = self.hub.taskactions.to_xml(task)
            if prettyxml:
                print parseString(myxml).toprettyxml()
            else:
                print myxml
