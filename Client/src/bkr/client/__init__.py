# -*- coding: utf-8 -*-

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import glob
import json
import optparse
import os
import re
import sys
import xml.dom.minidom
from optparse import OptionGroup

import pkg_resources
from six.moves.urllib_parse import urljoin

from bkr.client.command import Command
from bkr.common.pyconfig import PyConfigParser

user_config_file = os.environ.get("BEAKER_CLIENT_CONF", None)
if not user_config_file:
    user_conf = os.path.expanduser('~/.beaker_client/config')
    old_conf = os.path.expanduser('~/.beaker')
    if os.path.exists(user_conf):
        user_config_file = user_conf
    elif os.path.exists(old_conf):
        user_config_file = old_conf
        sys.stderr.write(
            "%s is deprecated for config, please use %s instead\n" % (old_conf, user_conf))
    else:
        pass

system_config_file = None
if os.path.exists('/etc/beaker/client.conf'):
    system_config_file = '/etc/beaker/client.conf'

conf = PyConfigParser()
if system_config_file:
    conf.load_from_file(system_config_file)
if user_config_file:
    conf.load_from_file(user_config_file)

_host_filter_presets = None


def host_filter_presets():
    global _host_filter_presets
    if _host_filter_presets is not None:
        return _host_filter_presets

    _host_filter_presets = {}
    config_files = (
            sorted(glob.glob(pkg_resources.resource_filename('bkr.client', 'host-filters/*.conf')))
            + sorted(glob.glob('/etc/beaker/host-filters/*.conf')))
    user_config_file = os.path.expanduser('~/.beaker_client/host-filter')
    if os.path.exists(user_config_file):
        config_files.append(user_config_file)
    for f in config_files:
        with open(f) as fobj:
            for line in fobj:
                matched = re.match('^(\w+)\s+(\S+.*)$', line)
                if matched:
                    preset, xml = matched.groups()
                    _host_filter_presets[preset] = xml
    if not _host_filter_presets:
        sys.stderr.write("No presets found for the --host-filter option")
        raise SystemExit(1)
    return _host_filter_presets


class BeakerCommand(Command):
    enabled = False
    requires_login = True

    def set_hub(self, username=None, password=None, **kwargs):
        if kwargs.get('hub'):
            self.conf['HUB_URL'] = kwargs['hub']
        if kwargs.get('insecure'):
            self.conf['SSL_VERIFY'] = False
        proxy_user = kwargs.get('proxy_user')
        self.container.set_hub(username, password, auto_login=self.requires_login,
                               proxy_user=proxy_user)

    def requests_session(self):
        try:
            import requests
        except ImportError:
            # requests is not available for Python < 2.6 (for example on RHEL5),
            # so client commands which use it will raise this exception.
            raise RuntimeError('The requests package is not available on your system')
        # share cookiejar with hub, to re-use authentication token
        cookies = self.hub._transport.cookiejar
        # use custom CA cert/bundle, if given
        ca_cert = self.conf.get('CA_CERT', None)
        ssl_verify = self.conf.get('SSL_VERIFY', True)
        # HUB_URL will have no trailing slash in the config
        base_url = self.conf['HUB_URL'] + '/'

        class BeakerClientRequestsSession(requests.Session):
            """
            Custom requests.Session class with a few conveniences for bkr client code.
            """

            def __init__(self):
                super(BeakerClientRequestsSession,
                      self).__init__()  # pylint: disable=bad-super-call
                self.cookies = cookies
                if not ssl_verify:
                    self.verify = False
                elif ca_cert:
                    self.verify = ca_cert

            def request(self, method, url, **kwargs):
                # callers can pass in a relative URL and we will figure it out for them
                url = urljoin(base_url, url)
                # turn 'json' parameter into a suitably formatted request
                if 'json' in kwargs:
                    kwargs['data'] = json.dumps(kwargs.pop('json'))
                    kwargs.setdefault('headers', {}).update({'Content-Type': 'application/json'})
                return super(BeakerClientRequestsSession, self).request(
                    method, url, **kwargs)  # pylint: disable=bad-super-call

        return BeakerClientRequestsSession()

    t_id_types = dict(T='RecipeTask',
                      TR='RecipeTaskResult',
                      R='Recipe',
                      RS='RecipeSet',
                      J='Job')

    def check_taskspec_args(self, args, permitted_types=None):
        # The server is the one that actually parses these, but we can check
        # a few things on the client side first to catch errors early and give
        # the user better error messages.
        for task in args:
            if ':' not in task:
                self.parser.error('Invalid taskspec %r: '
                                  'see "Specifying tasks" in bkr(1)' % task)
            type, id = task.split(':', 1)
            if type not in self.t_id_types:
                self.parser.error('Unrecognised type %s in taskspec %r: '
                                  'see "Specifying tasks" in bkr(1)' % (type, task))
            if permitted_types is not None and type not in permitted_types:
                self.parser.error('Taskspec type must be one of [%s]'
                                  % ', '.join(permitted_types))


def prettyxml(option, opt_str, value, parser):
    # prettyxml implies debug as well.
    parser.values.prettyxml = True
    parser.values.debug = True


def generate_kickstart(template_file):
    abs_path = os.path.abspath(template_file)

    return open(abs_path, 'r').read()


generateKickstart = generate_kickstart


def generate_kernel_options(template_file):
    abs_path = os.path.abspath(template_file)

    lines = []
    # look for ## kernel_options: line
    kernel_options_line_prefix = '## kernel_options:'
    for line in open(abs_path, 'r').read().split("\n"):
        if line.startswith(kernel_options_line_prefix):
            line = line.split(kernel_options_line_prefix)[-1]
            lines.append(line.strip())
            break

    return " ".join(lines)


generateKernelOptions = generate_kernel_options


class BeakerWorkflow(BeakerCommand):
    doc = xml.dom.minidom.Document()

    def __init__(self, *args, **kwargs):
        """ Initialize Workflow """
        super(BeakerWorkflow, self).__init__(*args, **kwargs)
        self.multi_host = False

    def options(self):
        """ Default options that all Workflows use """

        # General options related to the operation of bkr
        self.parser.add_option(
            "--dry-run", "--dryrun",
            default=False, action="store_true", dest="dryrun",
            help="Don't submit job to scheduler",
        )
        self.parser.add_option(
            "--debug",
            default=False,
            action="store_true",
            help="Print generated job XML",
        )
        self.parser.add_option(
            "--pretty-xml", "--prettyxml",
            action="callback",
            callback=prettyxml,
            default=False,
            help="Pretty-print generated job XML with indentation",
        )
        self.parser.add_option(
            "--wait",
            default=False,
            action="store_true",
            help="Wait on job completion",
        )
        self.parser.add_option(
            "--no-wait", "--nowait",
            default=False,
            action="store_false",
            dest="wait",
            help="Do not wait on job completion [default]",
        )
        self.parser.add_option(
            "--quiet",
            default=False,
            action="store_true",
            help="Be quiet, don't print warnings",
        )

        distro_options = OptionGroup(self.parser,
                                     'Options for selecting distro tree(s)')
        distro_options.add_option(
            "--family",
            help="Use latest distro of this family for job",
        )
        distro_options.add_option(
            "--tag",
            action="append",
            default=[],
            help="Use latest distro tagged with TAG",
        )
        distro_options.add_option(
            "--distro",
            help="Use named distro for job",
        )
        distro_options.add_option(
            "--variant",
            help="Use only VARIANT in job",
        )
        distro_options.add_option(
            "--arch",
            action="append",
            dest="arches",
            default=[],
            help="Use only ARCH in job",
        )
        self.parser.add_option_group(distro_options)

        system_options = OptionGroup(self.parser,
                                     'Options for selecting system(s)')
        system_options.add_option(
            "--machine", metavar="FQDN",
            help="Require this machine for job",
        )
        system_options.add_option(
            "--ignore-system-status",
            action="store_true",
            default=False,
            help="Always use the system given by --machine, regardless of its status"
        )
        system_options.add_option(
            "--systype", metavar="TYPE",
            default=None,
            help="Require system of TYPE for job (Machine, Laptop, ..) [default: Machine]",
        )
        system_options.add_option(
            "--hostrequire", metavar='"TAG OPERATOR VALUE"',
            action="append",
            default=[],
            help="Additional <hostRequires/> for job (example: labcontroller=lab.example.com)",
        )
        system_options.add_option(
            "--keyvalue", metavar='"KEY OPERATOR VALUE"',
            action="append",
            default=[],
            help="Require system with matching legacy key-value (example: NETWORK=e1000)",
        )
        system_options.add_option(
            "--random",
            default=False,
            action="store_true",
            help="Pick systems randomly (default is owned, in group, other)"
        )
        system_options.add_option(
            "--host-filter",
            metavar="NAME",
            default=None,
            help="Apply pre-defined host filter"
        )
        self.parser.add_option_group(system_options)

        task_options = OptionGroup(self.parser, 'Options for selecting tasks')
        task_options.add_option(
            "--task",
            action="append",
            default=[],
            help="Include named task in job",
        )
        task_options.add_option(
            "--taskfile", metavar="FILENAME",
            default=None,
            help="Include all tasks from this file in job"
        )
        task_options.add_option(
            "--package",
            action="append",
            default=[],
            help="Include all tasks for PACKAGE in job",
        )
        task_options.add_option(
            "--task-type", metavar="TYPE",
            action="append", dest="type",
            default=[],
            help="Include all tasks of TYPE in job",
        )
        task_options.add_option(
            "--install", metavar="PACKAGE",
            default=[],
            action="append",
            help="Install PACKAGE using /distribution/pkginstall",
        )
        task_options.add_option(
            "--kdump",
            default=False,
            action="store_true",
            help="Enable kdump using /kernel/networking/kdump",
        )
        task_options.add_option(
            "--ndump",
            default=False,
            action="store_true",
            help="Enable ndnc using /kernel/networking/ndnc",
        )
        task_options.add_option(
            "--suppress-install-task",
            dest="suppress_install_task",
            action="store_true",
            default=False,
            help="Omit /distribution/check-install which is included by default",
        )
        # for compat only
        task_options.add_option("--type", action="append",
                                help=optparse.SUPPRESS_HELP)
        self.parser.add_option_group(task_options)

        job_options = OptionGroup(self.parser, 'Options for job configuration')
        job_options.add_option(
            '--job-owner', metavar='USERNAME',
            help='Submit job on behalf of USERNAME '
                 '(submitting user must be a submission delegate for job owner)',
        )
        job_options.add_option(
            "--job-group", metavar='GROUPNAME',
            help="Associate a group to this job"
        )
        job_options.add_option(
            "--whiteboard",
            default="",
            help="Set the whiteboard for this job",
        )
        job_options.add_option(
            "--taskparam", metavar="NAME=VALUE",
            action="append",
            default=[],
            help="Set parameter NAME=VALUE for every task in job",
        )
        job_options.add_option(
            "--ignore-panic",
            default=False,
            action="store_true",
            help="Do not abort job if panic message appears on serial console",
        )
        job_options.add_option(
            "--reserve", action="store_true",
            help="Reserve system at the end of the recipe",
        )
        job_options.add_option(
            "--reserve-duration", metavar="SECONDS",
            help="Release system automatically SECONDS after being reserved [default: 24 hours]",
        )
        job_options.add_option(
            "--cc",
            default=[],
            action="append",
            help="Notify additional e-mail address on job completion",
        )
        job_options.add_option(
            "--priority",
            default="Normal",
            help="Request PRIORITY for job (Low, Medium, Normal, High, Urgent) [default: %default]"
        )
        job_options.add_option(
            "--retention-tag", metavar="TAG",
            default="Scratch",
            help="Specify data retention policy for this job [default: %default]",
        )
        job_options.add_option(
            "--product",
            default=None,
            help="Associate job with PRODUCT for data retention purposes"
        )
        # for compat only
        job_options.add_option("--retention_tag", help=optparse.SUPPRESS_HELP)
        self.parser.add_option_group(job_options)

        installation_options = OptionGroup(self.parser, 'Options for installation')
        installation_options.add_option(
            "--method",
            default=None,
            help="Installation source method (nfs, http, ftp)",
        )
        installation_options.add_option(
            "--kernel-options", metavar="OPTIONS",
            default=None,
            help="Pass OPTIONS to kernel during installation",
        )
        installation_options.add_option(
            "--kernel-options-post", metavar="OPTIONS",
            default=None,
            help="Pass OPTIONS to kernel after installation",
        )
        installation_options.add_option(
            "--kickstart", metavar="FILENAME",
            default=None,
            help="Use this kickstart template for installation. Rendered on the server!",
        )
        installation_options.add_option(
            "--ks-append", metavar="COMMANDS",
            default=[], action="append",
            help="Specify additional kickstart commands to add to the base kickstart file",
        )
        installation_options.add_option(
            "--ks-meta", metavar="OPTIONS",
            default=None,
            help="Pass kickstart metadata OPTIONS when generating kickstart",
        )
        installation_options.add_option(
            "--repo", metavar="URL",
            action="append",
            default=[],
            help=("Configure repo at <URL> in the kickstart. The repo "
                  "will be available during initial package installation "
                  "and subsequent recipe execution."),
        )
        installation_options.add_option(
            "--repo-post", metavar="URL",
            default=[], action="append",
            help=("Configure repo at <URL> as part of kickstart %post "
                  "execution. The repo will NOT be available during "
                  "initial package installation."),
        )
        # for compat only
        installation_options.add_option("--kernel_options",
                                        help=optparse.SUPPRESS_HELP)
        installation_options.add_option("--kernel_options_post",
                                        help=optparse.SUPPRESS_HELP)
        self.parser.add_option_group(installation_options)

        multihost_options = OptionGroup(self.parser, 'Options for multi-host testing')
        multihost_options.add_option(
            "--clients", metavar="NUMBER",
            default=0,
            type=int,
            help="Include NUMBER client hosts in multi-host test [default: %default]",
        )
        multihost_options.add_option(
            "--servers", metavar="NUMBER",
            default=0,
            type=int,
            help="Include NUMBER server hosts in multi-host test [default: %default]",
        )
        self.parser.add_option_group(multihost_options)

    def get_arches(self, *args, **kwargs):
        """
        Get all arches that apply to either this distro, or the distro which
        will be selected by the given family and tag.
        Variant can be used as a further filter.
        """

        distro = kwargs.get("distro")
        family = kwargs.get("family")
        tags = kwargs.get("tag")
        variant = kwargs.get("variant")

        if not hasattr(self, 'hub'):
            self.set_hub(**kwargs)

        if distro:
            return self.hub.distros.get_arch(dict(distro=distro, variant=variant))
        else:
            return self.hub.distros.get_arch(dict(osmajor=family, tags=tags, variant=variant))

    getArches = get_arches

    def get_os_majors(self, *args, **kwargs):
        """
        Get all OsMajors, optionally filter by tag
        """

        tags = kwargs.get("tag", [])
        if not hasattr(self, 'hub'):
            self.set_hub(**kwargs)
        return self.hub.distros.get_osmajors(tags)

    getOsMajors = get_os_majors

    def get_system_os_major_arches(self, *args, **kwargs):
        """
        Get all OsMajors/arches that apply to this system, optionally filter by tag
        """

        fqdn = kwargs.get("machine", '')
        tags = kwargs.get("tag", [])
        if not hasattr(self, 'hub'):
            self.set_hub(**kwargs)
        return self.hub.systems.get_osmajor_arches(fqdn, tags)

    getSystemOsMajorArches = get_system_os_major_arches

    def get_family(self, *args, **kwargs):
        """
        Get the family / OS major for a particular distro
        """
        distro = kwargs.get("distro", None)
        family = kwargs.get("family", None)

        if family:
            return family

        if not hasattr(self, 'hub'):
            self.set_hub(**kwargs)
        return self.hub.distros.get_osmajor(distro)

    getFamily = get_family

    def get_task_names_from_file(self, kwargs):
        """
        Get list of task(s) from a file
        """

        task_names = []
        tasklist = kwargs.get('taskfile')
        if tasklist:
            if not os.path.exists(tasklist):
                self.parser.error("Task file not found: %s\n" % tasklist)
            with open(tasklist) as fobj:
                for line in fobj:
                    # If the line does not start with /, assume it is not a
                    # valid test and don't submit it to the scheduler.
                    if line.startswith('/'):
                        task_names.append(line.rstrip())
        return task_names

    getTaskNamesFromFile = get_task_names_from_file

    def get_tasks(self, *args, **kwargs):
        """
        Get all requested tasks
        """

        types = kwargs.get("type", None)
        packages = kwargs.get("package", None)
        self.n_clients = kwargs.get("clients", 0)
        self.n_servers = kwargs.get("servers", 0)
        quiet = kwargs.get("quiet", False)

        if not hasattr(self, 'hub'):
            self.set_hub(**kwargs)

        # We only want valid tasks
        filter = dict(valid=1)

        # Pre Filter based on osmajor
        filter['osmajor'] = self.getFamily(*args, **kwargs)

        tasks = []
        valid_tasks = dict()
        task_names = list(kwargs['task'])
        task_names.extend(self.getTaskNamesFromFile(kwargs))
        if task_names:
            for task in self.hub.tasks.filter(dict(names=task_names,
                                                   osmajor=filter['osmajor'])):
                valid_tasks[task['name']] = task
            for name in task_names:
                task = valid_tasks.get(name, None)
                if task:
                    tasks.append(task)
                elif not quiet:
                    sys.stderr.write('WARNING: task %s not applicable for distro, ignoring\n' % name)

        if self.n_clients or self.n_servers:
            self.multi_host = True

        if types:
            filter['types'] = types
        if packages:
            filter['packages'] = packages

        if types or packages:
            ntasks = self.hub.tasks.filter(filter)

            multihost_tasks = self.hub.tasks.filter(dict(types=['Multihost']))

            if self.multi_host:
                for t in ntasks[:]:
                    if t not in multihost_tasks:
                        # FIXME add debug print here
                        ntasks.remove(t)
            else:
                for t in ntasks[:]:
                    if t in multihost_tasks:
                        # FIXME add debug print here
                        ntasks.remove(t)
            tasks.extend(ntasks)
        return tasks

    getTasks = get_tasks

    def get_install_task_name(self, *args, **kwargs):
        """
        Returns the name of the task which is injected at the start of the recipe.
        Its job is to check for any problems in the installation.
        We have one implementation:
            /distribution/check-install is used by default
        """
        return '/distribution/check-install'

    getInstallTaskName = get_install_task_name

    def process_template(self, recipeTemplate,
                        requestedTasks,
                        taskParams=None,
                        distroRequires=None,
                        hostRequires=None,
                        role='STANDALONE',
                        arch=None,
                        whiteboard=None,
                        install=None,
                        reserve=None,
                        reserve_duration=None,
                        **kwargs):
        """
        Add tasks and additional requires to our template
        """

        if taskParams is None:
            taskParams = []

        actualTasks = []

        for task in requestedTasks:
            if arch not in task['arches']:
                actualTasks.append(task['name'])

        # Don't create empty recipes
        if actualTasks or reserve or kwargs.get('allow_empty_recipe', False):

            # Copy basic requirements
            recipe = recipeTemplate.clone()
            if whiteboard:
                recipe.whiteboard = whiteboard
            if distroRequires:
                recipe.addDistroRequires(distroRequires)
            if hostRequires:
                recipe.addHostRequires(hostRequires)
            add_install_task = not kwargs.get("suppress_install_task", False)
            if add_install_task:
                install_task_name = self.getInstallTaskName(**kwargs)
                # Don't add it if it's already explicitly requested
                if dict(name=install_task_name, arches=[]) not in requestedTasks:
                    recipe.addTask(install_task_name)
            if install:
                paramnode = self.doc.createElement('param')
                paramnode.setAttribute('name', 'PKGARGNAME')
                paramnode.setAttribute('value', ' '.join(install))
                recipe.addTask('/distribution/pkginstall', paramNodes=[paramnode])
            if kwargs.get("ndump"):
                recipe.addTask('/kernel/networking/ndnc')
            if kwargs.get("kdump"):
                recipe.addTask('/kernel/networking/kdump')
            for task in actualTasks:
                recipe.addTask(task, role=role, taskParams=taskParams)
            if reserve:
                recipe.addReservesys(duration=reserve_duration)

            # process kickstart template if given
            ksTemplate = kwargs.get("kickstart", None)
            if ksTemplate:
                kickstart = generateKickstart(ksTemplate)
                # additional kernel options from template
                kernel_options = recipe.kernel_options + " " + generateKernelOptions(ksTemplate)

                recipe.kernel_options = kernel_options.strip()
                recipe.addKickstart(kickstart)
        else:
            recipe = None
        return recipe

    processTemplate = process_template


class BeakerJobTemplateError(ValueError):
    """
    Raised to indicate that something invalid or impossible has been requested
    while a BeakerJob template was being used to generate a job definition.
    """
    pass


class BeakerBase(object):
    doc = xml.dom.minidom.Document()

    def clone(self):
        cloned = self.__class__()
        cloned.node = self.node.cloneNode(True)
        return cloned

    def toxml(self, prettyxml=False, **kwargs):
        """ return xml of job """
        if prettyxml:
            myxml = self.node.toprettyxml()
        else:
            myxml = self.node.toxml()
        return myxml


class BeakerJob(BeakerBase):
    def __init__(self, *args, **kwargs):
        self.node = self.doc.createElement('job')
        whiteboard = self.doc.createElement('whiteboard')
        whiteboard.appendChild(self.doc.createTextNode(kwargs.get('whiteboard', '')))
        if kwargs.get('cc'):
            notify = self.doc.createElement('notify')
            for cc in kwargs.get('cc'):
                ccnode = self.doc.createElement('cc')
                ccnode.appendChild(self.doc.createTextNode(cc))
                notify.appendChild(ccnode)
            self.node.appendChild(notify)
        self.node.appendChild(whiteboard)
        if kwargs.get('retention_tag'):
            self.node.setAttribute('retention_tag', kwargs.get('retention_tag'))
        if kwargs.get('product'):
            self.node.setAttribute('product', kwargs.get('product'))
        if kwargs.get('job_group'):
            self.node.setAttribute('group', kwargs.get('job_group'))
        if kwargs.get('job_owner'):
            self.node.setAttribute('user', kwargs.get('job_owner'))

    def add_recipe_set(self, recipeSet=None):
        """
        Properly add a recipeSet to this job
        """
        if recipeSet:
            if isinstance(recipeSet, BeakerRecipeSet):
                node = recipeSet.node
            elif isinstance(recipeSet, xml.dom.minidom.Element):
                node = recipeSet
            else:
                raise TypeError('recipeSet must be BeakerRecipeSet or xml.dom.minidom.Element')
            if len(node.getElementsByTagName('recipe')) > 0:
                self.node.appendChild(node.cloneNode(True))

    addRecipeSet = add_recipe_set

    def add_recipe(self, recipe=None):
        """
        Properly add a recipe to this job
        """
        if recipe:
            if isinstance(recipe, BeakerRecipe):
                node = recipe.node
            elif isinstance(recipe, xml.dom.minidom.Element):
                node = recipe
            else:
                raise TypeError('recipe must be BeakerRecipe or xml.dom.minidom.Element')
            if len(node.getElementsByTagName('task')) > 0:
                recipeSet = self.doc.createElement('recipeSet')
                recipeSet.appendChild(node.cloneNode(True))
                self.node.appendChild(recipeSet)

    addRecipe = add_recipe


class BeakerRecipeSet(BeakerBase):
    def __init__(self, *args, **kwargs):
        self.node = self.doc.createElement('recipeSet')
        self.node.setAttribute('priority', kwargs.get('priority', ''))

    def add_recipe(self, recipe=None):
        """
        Properly add a recipe to this recipeSet
        """
        if recipe:
            if isinstance(recipe, BeakerRecipe):
                node = recipe.node
            elif isinstance(recipe, xml.dom.minidom.Element):
                node = recipe
            else:
                raise TypeError('recipe must be BeakerRecipe or xml.dom.minidom.Element')
            if len(node.getElementsByTagName('task')) > 0:
                self.node.appendChild(node.cloneNode(True))

    addRecipe = add_recipe


class BeakerRecipeBase(BeakerBase):
    def __init__(self, *args, **kwargs):
        self.node.setAttribute('whiteboard', '')
        andDistroRequires = self.doc.createElement('and')

        partitions = self.doc.createElement('partitions')
        distroRequires = self.doc.createElement('distroRequires')
        hostRequires = self.doc.createElement('hostRequires')
        repos = self.doc.createElement('repos')
        distroRequires.appendChild(andDistroRequires)
        self.node.appendChild(distroRequires)
        self.node.appendChild(hostRequires)
        self.node.appendChild(repos)
        self.node.appendChild(partitions)

    def _addBaseHostRequires(self, **kwargs):
        """
        Add hostRequires
        """

        machine = kwargs.get("machine", None)
        force = kwargs.get('ignore_system_status', False)
        systype = kwargs.get("systype", None)
        keyvalues = kwargs.get("keyvalue", [])
        requires = kwargs.get("hostrequire", [])
        random = kwargs.get("random", False)
        host_filter = kwargs.get('host_filter', None)
        if machine and force:
            # if machine is specified, emit a warning message that any
            # other host selection criteria is ignored
            for opt in ['hostrequire', 'keyvalue', 'random', 'systype',
                        'host_filter']:
                if kwargs.get(opt, None):
                    sys.stderr.write('Warning: Ignoring --%s'
                                     ' because --machine was specified\n' % opt.replace('_', '-'))
            hostRequires = self.node.getElementsByTagName('hostRequires')[0]
            hostRequires.setAttribute("force", "%s" % kwargs.get('machine'))
        else:
            if machine:
                hostMachine = self.doc.createElement('hostname')
                hostMachine.setAttribute('op', '=')
                hostMachine.setAttribute('value', '%s' % machine)
                self.addHostRequires(hostMachine)
            if systype:
                systemType = self.doc.createElement('system_type')
                systemType.setAttribute('op', '=')
                systemType.setAttribute('value', '%s' % systype)
                self.addHostRequires(systemType)
            p2 = re.compile(r'\s*([\!=<>]+|&gt;|&lt;|(?<=\s)like(?=\s))\s*')
            for keyvalue in keyvalues:
                splitkeyvalue = p2.split(keyvalue, 3)
                if len(splitkeyvalue) != 3:
                    raise BeakerJobTemplateError(
                        '--keyvalue option must be in the form "KEY OPERATOR VALUE"')
                key, op, value = splitkeyvalue
                mykeyvalue = self.doc.createElement('key_value')
                mykeyvalue.setAttribute('key', '%s' % key)
                mykeyvalue.setAttribute('op', '%s' % op)
                mykeyvalue.setAttribute('value', '%s' % value)
                self.addHostRequires(mykeyvalue)
            for require in requires:
                if require.lstrip().startswith('<'):
                    myrequire = xml.dom.minidom.parseString(require).documentElement
                else:
                    splitrequire = p2.split(require, 3)
                    if len(splitrequire) != 3:
                        raise BeakerJobTemplateError(
                            '--hostrequire option must be in the form "TAG OPERATOR VALUE"')
                    key, op, value = splitrequire
                    myrequire = self.doc.createElement('%s' % key)
                    myrequire.setAttribute('op', '%s' % op)
                    myrequire.setAttribute('value', '%s' % value)
                self.addHostRequires(myrequire)
            if random:
                self.addAutopick(random)
            if host_filter:
                _host_filter_presets = host_filter_presets()
                host_filter_expanded = _host_filter_presets.get(host_filter, None)
                if host_filter_expanded:
                    self.addHostRequires(xml.dom.minidom.parseString
                                         (host_filter_expanded).documentElement)
                else:
                    sys.stderr.write('Pre-defined host-filter does not exist: %s\n' % host_filter)
                    sys.exit(1)

    def add_base_requires(self, *args, **kwargs):
        """
        Add base requires
        """

        self._addBaseHostRequires(**kwargs)
        distro = kwargs.get("distro", None)
        family = kwargs.get("family", None)
        variant = kwargs.get("variant", None)
        method = kwargs.get("method", None)
        ks_metas = []
        ks_meta = kwargs.get("ks_meta", "")
        kernel_options = kwargs.get("kernel_options", '')
        kernel_options_post = kwargs.get("kernel_options_post", '')
        ks_appends = kwargs.get("ks_append", [])
        tags = kwargs.get("tag", [])
        repos = kwargs.get("repo", [])
        postrepos = kwargs.get("repo_post", [])
        ignore_panic = kwargs.get("ignore_panic", False)
        if distro:
            distroName = self.doc.createElement('distro_name')
            if '%' not in distro:
                distroName.setAttribute('op', '=')
            else:
                distroName.setAttribute('op', 'like')
            distroName.setAttribute('value', '%s' % distro)
            self.addDistroRequires(distroName)
        else:
            if family:
                distroFamily = self.doc.createElement('distro_family')
                distroFamily.setAttribute('op', '=')
                distroFamily.setAttribute('value', '%s' % family)
                self.addDistroRequires(distroFamily)
            for tag in tags:
                distroTag = self.doc.createElement('distro_tag')
                distroTag.setAttribute('op', '=')
                distroTag.setAttribute('value', '%s' % tag)
                self.addDistroRequires(distroTag)
        if variant:
            distroVariant = self.doc.createElement('distro_variant')
            distroVariant.setAttribute('op', '=')
            distroVariant.setAttribute('value', '%s' % variant)
            self.addDistroRequires(distroVariant)
        if method:
            ks_metas.append("method=%s" % method)
        if ks_meta:
            ks_metas.append(ks_meta)
        self.ks_meta = ' '.join(ks_metas)
        if kernel_options:
            self.kernel_options = kernel_options
        if kernel_options_post:
            self.kernel_options_post = kernel_options_post
        for ks_command in ks_appends:
            ks_append = self.doc.createElement('ks_append')
            ks_append.appendChild(self.doc.createCDATASection(ks_command))
            self.ks_appends.appendChild(ks_append.cloneNode(True))
        for i, repo in enumerate(repos):
            myrepo = self.doc.createElement('repo')
            myrepo.setAttribute('name', 'myrepo_%s' % i)
            myrepo.setAttribute('url', '%s' % repo)
            self.addRepo(myrepo)
        if postrepos:
            self.addPostRepo(postrepos)
        if ignore_panic:
            self.add_ignore_panic()

    addBaseRequires = add_base_requires

    def add_repo(self, node):
        self.repos.appendChild(node.cloneNode(True))

    addRepo = add_repo

    def add_post_repo(self, repourl_lst):
        """
        Function to add repos only in %post section of kickstart

        add_repo() function does add the repos to be available during the
        installation time whereas this function appends the yum repo config
        files in the %post section of the kickstart so that they are ONLY
        available after the installation.
        """
        post_repo_config = ""
        for i, repoloc in enumerate(repourl_lst):
            post_repo_config += '''
cat << EOF >/etc/yum.repos.d/beaker-postrepo%(i)s.repo
[beaker-postrepo%(i)s]
name=beaker-postrepo%(i)s
baseurl=%(repoloc)s
enabled=1
gpgcheck=0
skip_if_unavailable=1
EOF
''' % dict(i=i, repoloc=repoloc)

        post_repo_config = "\n%post" + post_repo_config + "%end\n"
        ks_append = self.doc.createElement('ks_append')
        ks_append.appendChild(self.doc.createCDATASection(post_repo_config))
        self.ks_appends.appendChild(ks_append.cloneNode(True))

    addPostRepo = add_post_repo

    def add_host_requires(self, nodes):
        """
        Accepts either xml, dom.Element or a list of dom.Elements
        """
        if isinstance(nodes, str):
            parse = xml.dom.minidom.parseString(nodes.strip())
            nodes = []
            for node in parse.getElementsByTagName("hostRequires"):
                nodes.extend(node.childNodes)
        elif isinstance(nodes, xml.dom.minidom.Element):
            nodes = [nodes]
        if isinstance(nodes, list):
            for node in nodes:
                if isinstance(node, xml.dom.minidom.Element):
                    self.and_host_requires.appendChild(node.cloneNode(True))

    addHostRequires = add_host_requires

    def add_distro_requires(self, nodes):
        """
        Accepts either xml, dom.Element or a list of dom.Elements
        """
        if isinstance(nodes, str):
            parse = xml.dom.minidom.parseString(nodes.strip())
            nodes = []
            for node in parse.getElementsByTagName("distroRequires"):
                nodes.extend(node.childNodes)
        elif isinstance(nodes, xml.dom.minidom.Element):
            nodes = [nodes]
        if isinstance(nodes, list):
            for node in nodes:
                if isinstance(node, xml.dom.minidom.Element):
                    self.and_distro_requires.appendChild(node.cloneNode(True))

    addDistroRequires = add_distro_requires

    def add_task(self, task, role='STANDALONE', paramNodes=None, taskParams=None):

        if taskParams is None:
            taskParams = []
        if paramNodes is None:
            paramNodes = []

        recipeTask = self.doc.createElement('task')
        recipeTask.setAttribute('name', '%s' % task)
        recipeTask.setAttribute('role', '%s' % role)
        params = self.doc.createElement('params')
        for param in paramNodes:
            params.appendChild(param)
        for taskParam in taskParams:
            param = self.doc.createElement('param')
            param.setAttribute('name', taskParam.split('=', 1)[0])
            param.setAttribute('value', taskParam.split('=', 1)[1])
            params.appendChild(param)
        recipeTask.appendChild(params)
        self.node.appendChild(recipeTask)

    addTask = add_task

    def add_reservesys(self, duration=None):
        reservesys = self.doc.createElement('reservesys')
        if duration:
            reservesys.setAttribute('duration', duration)
        self.node.appendChild(reservesys)

    addReservesys = add_reservesys

    def add_partition(self, name=None, type=None, fs=None, size=None):
        """
        Add a partition node
        """
        if name:
            partition = self.doc.createElement('partition')
            partition.setAttribute('name', str(name))
        else:
            raise BeakerJobTemplateError(u'You must specify name when adding a partition')
        if size:
            partition.setAttribute('size', str(size))
        else:
            raise BeakerJobTemplateError(u'You must specify size when adding a partition')
        if type:
            partition.setAttribute('type', str(type))
        if fs:
            partition.setAttribute('fs', str(fs))
        self.partitions.appendChild(partition)

    addPartition = add_partition

    def add_kickstart(self, kickstart):
        recipeKickstart = self.doc.createElement('kickstart')
        recipeKickstart.appendChild(self.doc.createCDATASection(kickstart))
        self.node.appendChild(recipeKickstart)

    addKickstart = add_kickstart

    def add_autopick(self, random):
        recipeAutopick = self.doc.createElement('autopick')
        random = u'{}'.format(random).lower()
        recipeAutopick.setAttribute('random', random)
        self.node.appendChild(recipeAutopick)

    addAutopick = add_autopick

    def add_ignore_panic(self):
        recipeIgnorePanic = self.doc.createElement('watchdog')
        recipeIgnorePanic.setAttribute('panic', 'ignore')
        self.node.appendChild(recipeIgnorePanic)

    def set_ks_meta(self, value):
        self.node.setAttribute('ks_meta', value)

    def get_ks_meta(self):
        return self.node.getAttribute('ks_meta')

    ks_meta = property(get_ks_meta, set_ks_meta)

    def set_kernel_options(self, value):
        self.node.setAttribute('kernel_options', value)

    def get_kernel_options(self):
        return self.node.getAttribute('kernel_options')

    kernel_options = property(get_kernel_options, set_kernel_options)

    def set_kernel_options_post(self, value):
        self.node.setAttribute('kernel_options_post', value)

    def get_kernel_options_post(self):
        return self.node.getAttribute('kernel_options_post')

    kernel_options_post = property(get_kernel_options_post, set_kernel_options_post)

    def set_whiteboard(self, value):
        self.node.setAttribute('whiteboard', value)

    def get_whiteboard(self):
        return self.node.getAttribute('whiteboard')

    whiteboard = property(get_whiteboard, set_whiteboard)

    def get_and_distro_requires(self):
        return self.node.getElementsByTagName('distroRequires')[0].getElementsByTagName('and')[0]

    and_distro_requires = andDistroRequires = property(get_and_distro_requires)

    def get_and_host_requires(self):
        hostRequires = self.node.getElementsByTagName('hostRequires')[0]
        if not hostRequires.getElementsByTagName('and'):
            andHostRequires = self.doc.createElement('and')
            hostRequires.appendChild(andHostRequires)
        return hostRequires.getElementsByTagName('and')[0]

    and_host_requires = andHostRequires = property(get_and_host_requires)

    def get_repos(self):
        return self.node.getElementsByTagName('repos')[0]

    repos = property(get_repos)

    def get_partitions(self):
        return self.node.getElementsByTagName('partitions')[0]

    partitions = property(get_partitions)

    @property
    def ks_appends(self):
        existing = self.node.getElementsByTagName('ks_appends')
        if existing:
            return existing[0]
        ks_appends = self.doc.createElement('ks_appends')
        self.node.appendChild(ks_appends)
        return ks_appends


class BeakerRecipe(BeakerRecipeBase):
    def __init__(self, *args, **kwargs):
        self.node = self.doc.createElement('recipe')
        super(BeakerRecipe, self).__init__(*args, **kwargs)

    def add_guest_recipe(self, guestrecipe):
        """ properly add a guest recipe to this recipe """
        if isinstance(guestrecipe, BeakerGuestRecipe):
            self.node.appendChild(guestrecipe.node.cloneNode(True))
        elif (isinstance(guestrecipe, xml.dom.minidom.Element)
              and guestrecipe.tagName == 'guestrecipe'):
            self.node.appendChild(guestrecipe.cloneNode(True))
        else:
            raise BeakerJobTemplateError(u'Invalid guest recipe')

    addGuestRecipe = add_guest_recipe


class BeakerGuestRecipe(BeakerRecipeBase):
    def __init__(self, *args, **kwargs):
        self.node = self.doc.createElement('guestrecipe')
        super(BeakerGuestRecipe, self).__init__(*args, **kwargs)

    def set_guestargs(self, value):
        self.node.setAttribute('guestargs', value)

    def get_guestargs(self):
        return self.node.getAttribute('guestargs')

    guestargs = property(get_guestargs, set_guestargs)

    def set_guestname(self, value):
        self.node.setAttribute('guestname', value)

    def get_guestname(self):
        return self.node.getAttribute('guestname')

    guestname = property(get_guestname, set_guestname)
