# -*- coding: utf-8 -*-

"""
.. _bkr-workflow-installer-test:

bkr workflow-installer-test: DEPRECATED workflow to generate a kickstart for testing Anaconda
=============================================================================================

.. program:: bkr workflow-installer-test

Synopsis
--------

:program:`bkr workflow-installer-test` [*workflow options*] [*options*]
|    [:option:`--template` <kickstart_template>]

Description
-----------

Generates an Anaconda kickstart for the purpose of testing. Uses
`Jinja2 <http://jinja.pocoo.org/docs/>`_ to render the templates.
This workflow is deprecated, use :option:`--kickstart <bkr --kickstart>` with
:program:`bkr workflow-simple` or any other workflow command.


Options
-------

.. option:: --template <kickstart_template>

    The template that the kickstart will be generated from.

Common workflow options are described in the :ref:`Workflow options
<workflow-options>` section of :manpage:`bkr(1)`.

Common :program:`bkr` options are described in the :ref:`Options
<common-options>` section of :manpage:`bkr(1)`.

Exit status
-----------

Non-zero on error, otherwise zero.

Examples
--------

Generate a kickstart based on the :file:`/tmp/my_template.cfg` template, with
the 'i386' arch and 'RedHatEnterpriseLinux6' family::

    bkr workflow-installer-test --arch i386 --family RedHatEnterpriseLinux6 \\
        --template /tmp/my_template.cfg

The templates understand the following variables::

* OS_MAJOR
* OS_MINOR
* FAMILY
* DISTRO
* VARIANT
* ARCH

See also
--------

:manpage:`bkr(1)`
"""

from __future__ import print_function

import os
import string
import sys
import xml.dom.minidom

from jinja2 import Environment
from jinja2 import FileSystemLoader
from jinja2.ext import Extension

from bkr.client import BeakerJob
from bkr.client import BeakerRecipe
from bkr.client import BeakerRecipeSet
from bkr.client import BeakerWorkflow


class SkipBlockExtension(Extension):
    """
    Jinja2 extension to skip template blocks.
    To use add it to Environment and set
    env.skip_blocks to a list of block names to skip.
    """

    def __init__(self, environment):
        super(SkipBlockExtension, self).__init__(environment)
        environment.extend(skip_blocks=[])

    def filter_stream(self, stream):
        block_level = 0
        skip_level = 0
        in_endblock = False

        for token in stream:
            if token.type == 'block_begin':
                if stream.current.value == 'block':
                    block_level += 1
                    if stream.look().value in self.environment.skip_blocks:
                        skip_level = block_level

            if token.value == 'endblock':
                in_endblock = True

            if skip_level == 0:
                yield token

            if token.type == 'block_end':
                if in_endblock:
                    in_endblock = False
                    block_level -= 1

                    if skip_level == block_level + 1:
                        skip_level = 0


def generateKickstart(template_file, args):
    """
        Generate ks.cfg from template while skipping
        blocks named 'kernel_options'.
    """

    abs_path = os.path.abspath(template_file)
    dir_name = os.path.dirname(abs_path)
    base_name = os.path.basename(abs_path)

    env = Environment(
        loader=FileSystemLoader(dir_name),
        extensions=[SkipBlockExtension],
        cache_size=0,
        line_comment_prefix='##',
    )
    env.skip_blocks.append('kernel_options')  # pylint: disable=no-member

    template = env.get_template(base_name)
    return "\n" + template.render(args)


def generateKernelOptions(template_file, args):
    """
        From the template render  the value of the
        'kernel_options' block if it exists.
    """

    abs_path = os.path.abspath(template_file)
    dir_name = os.path.dirname(abs_path)
    base_name = os.path.basename(abs_path)

    env = Environment(
        loader=FileSystemLoader(dir_name),
        cache_size=0,
        line_comment_prefix='##',
    )
    template = env.get_template(base_name)

    lines = []
    if 'kernel_options' in template.blocks:
        # there is a {% block kernel_options %} defined
        for line in template.blocks['kernel_options'](template.new_context(args)):
            lines.append(line.strip())
    else:
        # look for ## kernel_options: line
        # NB: this syntax doesn't support variable context
        # b/c Jinja strips down all comments before processing the template
        # thus there's no way (nor API) to render them like template.blocks
        kernel_options_line_prefix = '## kernel_options:'
        for line in open(abs_path, 'r').read().split("\n"):
            if line.startswith(kernel_options_line_prefix):
                line = line.split(kernel_options_line_prefix)[-1]
                lines.append(line.strip())
                break

    return " ".join(lines)


class Workflow_Installer_Test(BeakerWorkflow):
    """
    Workflow which generates kickstart configuration based on Jinja2 templates
    """
    enabled = True
    doc = xml.dom.minidom.Document()

    def options(self):
        super(Workflow_Installer_Test, self).options()

        self.parser.add_option(
            "--template",
            default="",
            help="Kickstart template to use for installation"
        )
        self.parser.usage = "%%prog %s [options]" % self.normalized_name

    def _get_os_major_version(self, os_major):
        for character in os_major:
            if character in string.ascii_letters:
                os_major = os_major.replace(character, "")
        return os_major

    def run(self, *args, **kwargs):
        sys.stderr.write('workflow-installer-test is deprecated, use '
                         '--kickstart with workflow-simple or any other workflow command')

        debug = kwargs.get("debug", False)
        dryrun = kwargs.get("dryrun", False)
        family = kwargs.get("family", None)
        distro = kwargs.get("distro", None)
        arches = kwargs.get("arches", [])
        taskParams = kwargs.get("taskparam", [])
        ksTemplate = kwargs.get("template", None)

        # todo: fetch family mapping based on distro from the server
        if not family and not distro:
            sys.stderr.write("No Family or Distro specified\n")
            sys.exit(1)

        if not arches:
            sys.stderr.write("No arches specified, you must specify at least one\n")
            sys.exit(1)

        if not ksTemplate:
            sys.stderr.write("You must specify kickstart template to run this workflow\n")
            sys.exit(1)

        if family:
            kwargs['os_major'] = int(self._get_os_major_version(family))
        else:  # get family data based on distro
            if not hasattr(self, 'hub'):
                self.set_hub(**kwargs)

            # this will return info about all arches and variants
            # but the family string is the same so break after the first iteration
            for distro in self.hub.distrotrees.filter({'name': distro, 'family': family}):
                family = distro["distro_osmajor"]  # e.g. RedHatEnterpriseLinux6
                os_version = distro["distro_osversion"]  # e.g. RedHatEnterpriseLinux6.3
                kwargs["os_major"] = int(self._get_os_major_version(family))
                kwargs["family"] = family
                kwargs["os_minor"] = int(os_version.replace(family, "").replace(".", ""))
                break

        # Add kickstart and kernel options
        ks_args = {}

        # make ksmeta from command line options and taskParams
        for parameter in ["distro", "family", "variant", "os_major", "os_minor"]:
            if kwargs.get(parameter, None):
                ks_args[parameter.upper()] = kwargs.get(parameter)

        # allow taskParams to override existing values
        try:
            for param in taskParams:
                (name, value) = param.split('=', 1)
                # use both upper case and regular case variable names
                ks_args[name.upper()] = value
                ks_args[name] = value
        except:
            sys.stderr.write("Every task param has to have a value.")
            sys.exit(1)

        if kwargs['kernel_options'] is None:
            kwargs['kernel_options'] = ""
        pristine_kernel_options = kwargs['kernel_options']

        # get all tasks requested
        requestedTasks = self.getTasks(*args, **kwargs)

        # Create Job
        job = BeakerJob(*args, **kwargs)

        # Add Host Requirements
        for arch in arches:
            ks_args["ARCH"] = arch
            # Create Base Recipe
            recipeTemplate = BeakerRecipe()
            # get kickstart and add it to recipes
            kickstart = generateKickstart(ksTemplate, ks_args)
            kernel_options = generateKernelOptions(ksTemplate, ks_args)

            kwargs['kernel_options'] = pristine_kernel_options + " " + kernel_options
            kwargs['kernel_options'] = kwargs['kernel_options'].strip()

            recipeTemplate.addKickstart(kickstart)

            # Add Distro Requirements
            recipeTemplate.addBaseRequires(*args, **kwargs)

            arch_node = self.doc.createElement('distro_arch')
            arch_node.setAttribute('op', '=')
            arch_node.setAttribute('value', arch)
            recipeSet = BeakerRecipeSet(**kwargs)
            if self.multi_host:
                for i in range(self.n_servers):
                    recipeSet.addRecipe(self.processTemplate(recipeTemplate,
                                                             requestedTasks,
                                                             taskParams=taskParams,
                                                             distroRequires=arch_node,
                                                             role='SERVERS',
                                                             arch=arch,
                                                             **kwargs))
                for i in range(self.n_clients):
                    recipeSet.addRecipe(self.processTemplate(recipeTemplate,
                                                             requestedTasks,
                                                             taskParams=taskParams,
                                                             distroRequires=arch_node,
                                                             role='CLIENTS',
                                                             arch=arch,
                                                             **kwargs))
                job.addRecipeSet(recipeSet)
            else:
                recipe = self.processTemplate(recipeTemplate,
                                              requestedTasks,
                                              taskParams=taskParams,
                                              distroRequires=arch_node,
                                              arch=arch,
                                              **kwargs)
                recipeSet.addRecipe(recipe)
                job.addRecipeSet(recipeSet)

        # jobxml
        jobxml = job.toxml(**kwargs)

        if debug:
            print(jobxml)

        if not dryrun:
            if not hasattr(self, 'hub'):
                self.set_hub(**kwargs)
            try:
                job = self.hub.jobs.upload(jobxml)
            except Exception as ex:
                sys.stderr.write(ex)
                sys.exit(1)
            else:
                print("Submitted: %s" % job)
