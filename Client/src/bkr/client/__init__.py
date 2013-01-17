# -*- coding: utf-8 -*-

import xml.dom.minidom
import re, errno, sys, os
import optparse
from optparse import OptionGroup
from kobo.client import ClientCommand
import kobo.conf

config_file = os.environ.get("BEAKER_CLIENT_CONF", None)
if not config_file:
    user_conf = os.path.expanduser('~/.beaker_client/config')
    old_conf = os.path.expanduser('~/.beaker')
    if os.path.exists(user_conf):
        config_file = user_conf
    elif os.path.exists(old_conf):
        config_file = old_conf
        sys.stderr.write("%s is deprecated for config, please use %s instead\n" % (old_conf, user_conf))
    elif os.path.exists('/etc/beaker/client.conf'):
        config_file = "/etc/beaker/client.conf"
        sys.stderr.write("%s not found, using %s\n" % (user_conf, config_file))
    else:
        pass

conf = kobo.conf.PyConfigParser()
if config_file:
    conf.load_from_file(config_file)

class BeakerCommand(ClientCommand):
    enabled = False

    t_id_types = dict(T = 'RecipeTask',
                      TR = 'RecipeTaskResult',
                      R = 'Recipe',
                      RS = 'RecipeSet',
                      J = 'Job')

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

class BeakerWorkflow(BeakerCommand):
    doc = xml.dom.minidom.Document()

    def __init__(self, *args, **kwargs):
        """ Initialize Workflow """
        super(BeakerWorkflow, self).__init__(*args, **kwargs)
        self.multi_host = False
        self.n_clients = 1
        self.n_servers = 1

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
            help="Use latest distro tagged with TAG [default: STABLE]",
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
        self.parser.add_option_group(system_options)

        task_options = OptionGroup(self.parser, 'Options for selecting tasks')
        task_options.add_option(
            "--task",
            action="append",
            default=[],
            help="Include named task in job",
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
            help="Omit /distribution/install which is included by default",
        )
        # for compat only
        task_options.add_option("--type", action="append",
                help=optparse.SUPPRESS_HELP)
        self.parser.add_option_group(task_options)

        job_options = OptionGroup(self.parser, 'Options for job configuration')
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
            "--repo", metavar="URL",
            action="append",
            default=[],
            help="Include this repo in job",
        )
        job_options.add_option(
            "--ignore-panic",
            default=False,
            action="store_true",
            help="Do not abort job if panic message appears on serial console",
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
            default="nfs",
            help="Installation source method (nfs, http, ftp) [default: %default]",
        )
        installation_options.add_option(
            "--ks-meta", metavar="OPTIONS",
            default=None,
            help="Pass kickstart metadata OPTIONS when generating kickstart",
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
        # for compat only
        installation_options.add_option("--kernel_options",
                help=optparse.SUPPRESS_HELP)
        installation_options.add_option("--kernel_options_post",
                help=optparse.SUPPRESS_HELP)
        self.parser.add_option_group(installation_options)

        multihost_options = OptionGroup(self.parser, 'Options for multi-host testing')
        multihost_options.add_option(
            "--clients", metavar="NUMBER",
            default=None,
            type=int,
            help="Include NUMBER client hosts in multi-host test",
        )
        multihost_options.add_option(
            "--servers", metavar="NUMBER",
            default=None,
            type=int,
            help="Include NUMBER server hosts in multi-host test",
        )
        self.parser.add_option_group(multihost_options)

    def getArches(self, *args, **kwargs):
        """ Get all arches that apply to either this distro or family/osmajor """

        username = kwargs.get("username", None)
        password = kwargs.get("password", None)
        distro   = kwargs.get("distro", None)
        family   = kwargs.get("family", None)

        if not hasattr(self,'hub'):
            self.set_hub(username, password)

        if family:
            return self.hub.distros.get_arch(dict(osmajor=family))
        if distro:
            return self.hub.distros.get_arch(dict(distro=distro))

    def getOsMajors(self, *args, **kwargs):
        """ Get all OsMajors, optionally filter by tag """ 
        username = kwargs.get("username", None)
        password = kwargs.get("password", None)
        tags = kwargs.get("tag", []) or ['STABLE']
        if not hasattr(self,'hub'):
            self.set_hub(username, password)
        return self.hub.distros.get_osmajors(tags)

    def getSystemOsMajorArches(self, *args, **kwargs):
        """ Get all OsMajors/arches that apply to this system, optionally filter by tag """
        username = kwargs.get("username", None)
        password = kwargs.get("password", None)
        fqdn = kwargs.get("machine", '')
        tags = kwargs.get("tag", []) or ['STABLE']
        if not hasattr(self,'hub'):
            self.set_hub(username, password)
        return self.hub.systems.get_osmajor_arches(fqdn, tags)

    def getFamily(self, *args, **kwargs):
        """ Get the family/osmajor for a particular distro """
        username = kwargs.get("username", None)
        password = kwargs.get("password", None)
        distro   = kwargs.get("distro", None)
        family   = kwargs.get("family", None)

        if family:
            return family

        if not hasattr(self,'hub'):
            self.set_hub(username, password)
        return self.hub.distros.get_osmajor(distro)
    
    def getTasks(self, *args, **kwargs):
        """ get all requested tasks """

        username = kwargs.get("username", None)
        password = kwargs.get("password", None)
        types    = kwargs.get("type", None)
        packages = kwargs.get("package", None)
        self.n_clients = kwargs.get("clients", None)
        self.n_servers = kwargs.get("servers", None)
        quiet = kwargs.get("quiet", False)

        if not hasattr(self,'hub'):
            self.set_hub(username, password)

        # We only want valid tasks
        filter = dict(valid=1)

        # Pre Filter based on osmajor
        filter['osmajor'] = self.getFamily(*args, **kwargs)

        tasks = []
        valid_tasks = dict()
        if kwargs.get("task", None):
            for task in self.hub.tasks.filter(dict(names=kwargs.get('task'),
                                               osmajor=filter['osmajor'])):
                valid_tasks[task['name']] = task
            for name in kwargs['task']:
                task = valid_tasks.get(name, None)
                if task:
                    tasks.append(task)
                elif not quiet:
                    print >>sys.stderr, 'WARNING: task %s not applicable ' \
                            'for distro, ignoring' % name

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
                        #FIXME add debug print here
                        ntasks.remove(t)
            else:
                for t in ntasks[:]:
                    if t in multihost_tasks:
                        #FIXME add debug print here
                        ntasks.remove(t)
            tasks.extend(ntasks)
        return tasks

    def processTemplate(self, recipeTemplate,
                         requestedTasks,
                         taskParams=[],
                         distroRequires=None,
                         hostRequires=None,
                         role='STANDALONE',
                         arch=None,
                         whiteboard=None,
                         install=None,
                         **kwargs):
        """ add tasks and additional requires to our template """
        actualTasks = []
        for task in requestedTasks:
            if arch not in task['arches']:
                actualTasks.append(task['name'])
        # Don't create empty recipes
        if actualTasks:
            # Copy basic requirements
            recipe = recipeTemplate.clone()
            if whiteboard:
                recipe.whiteboard = whiteboard
            if distroRequires:
                recipe.addDistroRequires(distroRequires)
            if hostRequires:
                recipe.addHostRequires(hostRequires)
            add_install_task = not kwargs.get("suppress_install_task", False)
            if add_install_task and \
               dict(name='/distribution/install', arches=[]) not \
               in requestedTasks:
                recipe.addTask('/distribution/install')
            if install:
                paramnode = self.doc.createElement('param')
                paramnode.setAttribute('name' , 'PKGARGNAME')
                paramnode.setAttribute('value' , ' '.join(install))
                recipe.addTask('/distribution/pkginstall', paramNodes=[paramnode])
            if kwargs.get("ndump"):
                recipe.addTask('/kernel/networking/ndnc')
            if kwargs.get("kdump"):
                recipe.addTask('/kernel/networking/kdump')
            for task in actualTasks:
                recipe.addTask(task, role=role, taskParams=taskParams)
        else:
            recipe = None
        return recipe


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
        whiteboard.appendChild(self.doc.createTextNode(kwargs.get('whiteboard','')))
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

    def addRecipeSet(self, recipeSet=None):
        """ properly add a recipeSet to this job """
        if recipeSet:
            if isinstance(recipeSet, BeakerRecipeSet):
                node = recipeSet.node
            elif isinstance(recipeSet, xml.dom.minidom.Element):
                node = recipeSet
            else:
                raise
            if len(node.getElementsByTagName('recipe')) > 0:
                self.node.appendChild(node.cloneNode(True))

    def addRecipe(self, recipe=None):
        """ properly add a recipe to this job """
        if recipe:
            if isinstance(recipe, BeakerRecipe):
                node = recipe.node
            elif isinstance(recipe, xml.dom.minidom.Element):
                node = recipe
            else:
                raise
            if len(node.getElementsByTagName('task')) > 0:
                recipeSet = self.doc.createElement('recipeSet')
                recipeSet.appendChild(node.cloneNode(True))
                self.node.appendChild(recipeSet)

class BeakerRecipeSet(BeakerBase):
    def __init__(self, *args, **kwargs):
        self.node = self.doc.createElement('recipeSet')
        self.node.setAttribute('priority', kwargs.get('priority', ''))

    def addRecipe(self, recipe=None):
        """ properly add a recipe to this recipeSet """
        if recipe:
            if isinstance(recipe, BeakerRecipe):
                node = recipe.node
            elif isinstance(recipe, xml.dom.minidom.Element):
                node = recipe
            else:
                raise
            if len(node.getElementsByTagName('task')) > 0:
                self.node.appendChild(node.cloneNode(True))

class BeakerRecipeBase(BeakerBase):
    def __init__(self, *args, **kwargs):
        self.node.setAttribute('whiteboard','')
        andDistroRequires = self.doc.createElement('and')
        andHostRequires = self.doc.createElement('and')
        partitions = self.doc.createElement('partitions')
        distroRequires = self.doc.createElement('distroRequires')
        hostRequires = self.doc.createElement('hostRequires')
        repos = self.doc.createElement('repos')
        distroRequires.appendChild(andDistroRequires)
        hostRequires.appendChild(andHostRequires)
        self.node.appendChild(distroRequires)
        self.node.appendChild(hostRequires)
        self.node.appendChild(repos)
        self.node.appendChild(partitions)

    def addBaseRequires(self, *args, **kwargs):
        """ Add base requires """
        distro = kwargs.get("distro", None)
        family = kwargs.get("family", None)
        variant = kwargs.get("variant", None)
        method = kwargs.get("method", None)
        ks_metas = []
        ks_meta = kwargs.get("ks_meta", "")
        kernel_options = kwargs.get("kernel_options", '')
        kernel_options_post = kwargs.get("kernel_options_post", '')
        tags = kwargs.get("tag", []) or ['STABLE']
        systype = kwargs.get("systype", None)
        machine = kwargs.get("machine", None)
        keyvalues = kwargs.get("keyvalue", [])
        requires = kwargs.get("hostrequire", [])
        repos = kwargs.get("repo", [])
        random = kwargs.get("random", False)
        ignore_panic = kwargs.get("ignore_panic", False)
        if distro:
            distroName = self.doc.createElement('distro_name')
            distroName.setAttribute('op', '=')
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
            distroMethod = self.doc.createElement('distro_method')
            distroMethod.setAttribute('op', '=')
            distroMethod.setAttribute('value', 'nfs')
            self.addDistroRequires(distroMethod)
            ks_metas.append("method=%s" % method)
        if ks_meta:
            ks_metas.append(ks_meta)
        self.ks_meta = ' '.join(ks_metas)
        if kernel_options:
            self.kernel_options = kernel_options
        if kernel_options_post:
            self.kernel_options_post = kernel_options_post
        for i, repo in enumerate(repos):
            myrepo = self.doc.createElement('repo')
            myrepo.setAttribute('name', 'myrepo_%s' % i)
            myrepo.setAttribute('url', '%s' % repo)
            self.addRepo(myrepo)
        if systype:
            systemType = self.doc.createElement('system_type')
            systemType.setAttribute('op', '=')
            systemType.setAttribute('value', '%s' % systype)
            self.addHostRequires(systemType)
        if machine:
            hostMachine = self.doc.createElement('hostname')
            hostMachine.setAttribute('op', '=')
            hostMachine.setAttribute('value', '%s' % machine)
            self.addHostRequires(hostMachine)
        p2 = re.compile(r'([\!=<>]+|&gt;|&lt;)')
        for keyvalue in keyvalues:
            key, op, value = p2.split(keyvalue,3)
            mykeyvalue = self.doc.createElement('key_value')
            mykeyvalue.setAttribute('key', '%s' % key)
            mykeyvalue.setAttribute('op', '%s' % op)
            mykeyvalue.setAttribute('value', '%s' % value)
            self.addHostRequires(mykeyvalue)
        for require in requires:
            key, op, value = p2.split(require,3)
            myrequire = self.doc.createElement('%s' % key)
            myrequire.setAttribute('op', '%s' % op)
            myrequire.setAttribute('value', '%s' % value)
            self.addHostRequires(myrequire)
        
        if random:
            self.addAutopick(random)
        if ignore_panic:
            self.add_ignore_panic()

    def addRepo(self, node):
        self.repos.appendChild(node.cloneNode(True))

    def addHostRequires(self, nodes):
        """ Accepts either xml, dom.Element or a list of dom.Elements """
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
                    self.andHostRequires.appendChild(node.cloneNode(True))

    def addDistroRequires(self, nodes):
        """ Accepts either xml, dom.Element or a list of dom.Elements """
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
                    self.andDistroRequires.appendChild(node.cloneNode(True))

    def addTask(self, task, role='STANDALONE', paramNodes=[], taskParams=[]):
        recipeTask = self.doc.createElement('task')
        recipeTask.setAttribute('name', '%s' % task)
        recipeTask.setAttribute('role', '%s' % role)
        params = self.doc.createElement('params')
        for param in paramNodes:
            params.appendChild(param)
        for taskParam in taskParams:
            param = self.doc.createElement('param')
            param.setAttribute('name' , taskParam.split('=',1)[0])
            param.setAttribute('value' , taskParam.split('=',1)[1])
            params.appendChild(param)
        recipeTask.appendChild(params)
        self.node.appendChild(recipeTask)

    def addPartition(self,name=None, type=None, fs=None, size=None):
        """ add a partition node
        """
        if name:
            partition = self.doc.createElement('partition')
            partition.setAttribute('name', str(name))
        else:
            raise ValueError(u'You must specify name when adding a partition')
        if size:
            partition.setAttribute('size', str(size))
        else:
            raise ValueError(u'You must specify size when adding a partition')
        if type:
            partition.setAttribute('type', str(type))
        if fs:
            partition.setAttribute('fs', str(fs))
        self.partitions.appendChild(partition)

    def addKickstart(self, kickstart):
        recipeKickstart = self.doc.createElement('kickstart')
        recipeKickstart.appendChild(self.doc.createCDATASection(kickstart))
        self.node.appendChild(recipeKickstart)

    def addAutopick(self, random):
        recipeAutopick = self.doc.createElement('autopick')
        recipeAutopick.setAttribute('random', unicode(random).lower())
        self.node.appendChild(recipeAutopick)

    def add_ignore_panic(self):
        recipeIgnorePanic = self.doc.createElement('watchdog')
        recipeIgnorePanic.setAttribute('panic', 'ignore')
        self.node.appendChild(recipeIgnorePanic)

    def set_ks_meta(self, value):
        return self.node.setAttribute('ks_meta', value)

    def get_ks_meta(self):
        return self.node.getAttribute('ks_meta')

    ks_meta = property(get_ks_meta, set_ks_meta)

    def set_kernel_options(self, value):
        return self.node.setAttribute('kernel_options', value)

    def get_kernel_options(self):
        return self.node.getAttribute('kernel_options')

    kernel_options = property(get_kernel_options, set_kernel_options)

    def set_kernel_options_post(self, value):
        return self.node.setAttribute('kernel_options_post', value)

    def get_kernel_options_post(self):
        return self.node.getAttribute('kernel_options_post')

    kernel_options_post = property(get_kernel_options_post, set_kernel_options_post)

    def set_whiteboard(self, value):
        return self.node.setAttribute('whiteboard', value)

    def get_whiteboard(self):
        return self.node.getAttribute('whiteboard')

    whiteboard = property(get_whiteboard, set_whiteboard)

    def get_andDistroRequires(self):
        return self.node\
                .getElementsByTagName('distroRequires')[0]\
                .getElementsByTagName('and')[0]
    andDistroRequires = property(get_andDistroRequires)

    def get_andHostRequires(self):
        return self.node\
                .getElementsByTagName('hostRequires')[0]\
                .getElementsByTagName('and')[0]
    andHostRequires = property(get_andHostRequires)

    def get_repos(self):
        return self.node.getElementsByTagName('repos')[0]
    repos = property(get_repos)

    def get_partitions(self):
        return self.node.getElementsByTagName('partitions')[0]
    partitions = property(get_partitions)


class BeakerRecipe(BeakerRecipeBase):
    def __init__(self, *args, **kwargs):
        self.node = self.doc.createElement('recipe')
        super(BeakerRecipe,self).__init__(*args, **kwargs)

    def addGuestRecipe(self, guestrecipe):
        """ properly add a guest recipe to this recipe """
        if isinstance(guestrecipe, BeakerGuestRecipe):
            self.node.appendChild(guestrecipe.node.cloneNode(True))
        elif isinstance(guestrecipe, xml.dom.minidom.Element) and \
             guestrecipe.tagName == 'guestrecipe':
            self.node.appendChild(guestrecipe.cloneNode(True))
        else:
            #FIXME raise error here.
            sys.stderr.write("invalid object\n")

class BeakerGuestRecipe(BeakerRecipeBase):
    def __init__(self, *args, **kwargs):
        self.node = self.doc.createElement('guestrecipe')
        super(BeakerGuestRecipe,self).__init__(*args, **kwargs)

    def set_guestargs(self, value):
        return self.node.setAttribute('guestargs', value)

    def get_guestargs(self):
        return self.node.getAttribute('guestargs')

    guestargs = property(get_guestargs, set_guestargs)

    def set_guestname(self, value):
        return self.node.setAttribute('guestname', value)

    def get_guestname(self):
        return self.node.getAttribute('guestname')

    guestname = property(get_guestname, set_guestname)

