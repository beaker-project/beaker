# -*- coding: utf-8 -*-

import xml.dom.minidom
import re, errno, sys, os
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

        self.parser.add_option(
            "--prettyxml",
            action="callback", 
            callback=prettyxml,
            default=False,
            help="print the xml in pretty format",
        )
        self.parser.add_option(
            "--debug",
            default=False,
            action="store_true",
            help="print the jobxml that it would submit",
        )
        self.parser.add_option(
            "--dryrun",
            default=False,
            action="store_true",
            help="Don't submit job to scheduler",
        )
        self.parser.add_option(
            "--arch",
            action="append",
            dest="arches",
            default=[],
            help="Include this Arch in job",
        )
        self.parser.add_option(
            "--distro",
            help="Use this Distro for job",
        )
        self.parser.add_option(
            "--family",
            help="Pick latest distro of this family for job",
        )
        self.parser.add_option(
            "--variant",
            help="Pick distro with this variant for job",
        )
        self.parser.add_option(
            "--machine",
            help="Require this machine for job",
        )
        self.parser.add_option(
            "--package",
            action="append",
            default=[],
            help="Include tests for Package in job",
        )
        self.parser.add_option(
            "--tag",
            action="append",
            default=[],
            help="Pick latest distro matching this tag for job",
        )
        self.parser.add_option(
            "--retention_tag",
            default="Scratch",
            help="Specify data retention policy for this job, defaults to Scratch",
        )
        self.parser.add_option(
            "--repo",
            action="append",
            default=[],
            help="Include this repo in job",
        )
        self.parser.add_option(
            "--task",
            action="append",
            default=[],
            help="Include this task in job",
        )
        self.parser.add_option(
            "--taskparam",
            action="append",
            default=[],
            help="Set task params 'name=value'",
        )
        self.parser.add_option(
            "--type",
            action="append",
            default=None,
            help="Include tasks of this type in job",
        )
        self.parser.add_option(
            "--systype",
            default=None,
            help="Specify the System Type (Machine, Laptop, etc..)",
        )
        self.parser.add_option(
            "--hostrequire",
            action="append",
            default=[],
            help="Specify a system that matches this require Example: hostlabcontroller=lab.example.com ",
        )
        self.parser.add_option(
            "--keyvalue",
            action="append",
            default=[],
            help="Specify a system that matches this key/value Example: NETWORK=e1000 ",
        )
        self.parser.add_option(
            "--whiteboard",
            default="",
            help="Set the whiteboard for this job",
        )
        self.parser.add_option(
            "--wait",
            default=False,
            action="store_true",
            help="wait on job completion",
        )
        self.parser.add_option(
            "--nowait",
            default=False,
            action="store_false",
            dest="wait",
            help="Do not wait on job completion [Default]",
        )
        self.parser.add_option(
            "--clients",
            default=None,
            type=int,
            help="Specify how many client hosts to be involved in multihost test",
        )
        self.parser.add_option(
            "--servers",
            default=None,
            type=int,
            help="Specify how many server hosts to be involved in multihost test",
        )
        self.parser.add_option(
            "--install",
            default=[],
            action="append",
            help="Specify Package to install, this will add /distribution/pkginstall.",
        )
        self.parser.add_option(
            "--cc",
            default=[],
            action="append",
            help="Specify additional email addresses to notify",
        )
        self.parser.add_option(
            "--kdump",
            default=False,
            action="store_true",
            help="Turn on kdump.",
        )
        self.parser.add_option(
            "--ndump",
            default=False,
            action="store_true",
            help="Turn on ndnc.",
        )
        self.parser.add_option(
            "--method",
            default="nfs",
            help="Installation source method (nfs/http) (optional)"
        )
        self.parser.add_option(
            "--priority",
            default="Normal",
            help="Set the priority to this (Low,Medium,Normal,High,Urgent) (optional)"
        )
        self.parser.add_option(
            "--ks-meta",
            default=None,
            help="kickstart meta arguments to supply (optional)"
        )
        self.parser.add_option(
            "--kernel_options",
            default=None,
            help="Boot arguments to supply (optional)"
        )
        self.parser.add_option(
            "--kernel_options_post",
            default=None,
            help="Boot arguments to supply post install (optional)"
        )
        self.parser.add_option(
            "--product",
            default=None,
            help="This should be a unique identifierf or a product"
        )
        self.parser.add_option(
            "--random",
            default=False,
            action="store_true",
            help="Pick systems randomly (default is owned, in group, other)"
        )
        self.parser.add_option(
            "--quiet",
            default=False,
            action="store_true",
            help="Be quiet, don't print warnings",
        )
        self.parser.add_option(
            "--suppress-install-task",
            dest="suppress_install_task",
            action="store_true",
            default=False,
            help="/distribution/install won't be added to recipe"
        )
        self.parser.add_option(
            "--ignore-panic",
            default=False,
            action="store_true",
            help="Tell the watchdog to not abort jobs that output panics on the serial console.",
        )

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
        tags = kwargs.get("tag", [])
        if not hasattr(self,'hub'):
            self.set_hub(username, password)
        return self.hub.distros.get_osmajors(tags)

    def getSystemOsMajorArches(self, *args, **kwargs):
        """ Get all OsMajors/arches that apply to this system, optionally filter by tag """
        username = kwargs.get("username", None)
        password = kwargs.get("password", None)
        fqdn = kwargs.get("machine", '')
        tags = kwargs.get("tag", [])
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
        tags = kwargs.get("tag", [])
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
        if family:
            distroFamily = self.doc.createElement('distro_family')
            distroFamily.setAttribute('op', '=')
            distroFamily.setAttribute('value', '%s' % family)
            self.addDistroRequires(distroFamily)
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
        for tag in tags:
            distroTag = self.doc.createElement('distro_tag')
            distroTag.setAttribute('op', '=')
            distroTag.setAttribute('value', '%s' % tag)
            self.addDistroRequires(distroTag)
        # If no tag is asked for default to distros tagged as STABLE
        # But only if we didn't ask for a specific distro
        if not tags and not distro:
            distroTag = self.doc.createElement('distro_tag')
            distroTag.setAttribute('op', '=')
            distroTag.setAttribute('value', 'STABLE')
            self.addDistroRequires(distroTag)
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

