# -*- coding: utf-8 -*-

import os
import xml.dom.minidom
import sys
import copy
import re
from kobo.client import ClientCommand


class BeakerCommand(ClientCommand):
    enabled = False

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
            default=False,
            action="store_true",
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
            "--dump",
            default=False,
            action="store_true",
            help="Turn on ndnc/kdump. (which one depends on the family)",
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
            "--kernel_options",
            default=None,
            help="Boot arguments to supply (optional)"
        )
        self.parser.add_option(
            "--product",
            default=None,
            help="This should be a unique identifierf or a product"
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
        tasks    = kwargs.get("task", [])
        self.n_clients = kwargs.get("clients", None)
        self.n_servers = kwargs.get("servers", None)

        if self.n_clients or self.n_servers:
            self.multi_host = True

        filter = dict()
        if types:
            filter['types'] = types
        if packages:
            filter['packages'] = packages
        
        if not hasattr(self,'hub'):
            self.set_hub(username, password)
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
                         whiteboard=None,
                         install=None,
                         dump=None,
                         **kwargs):
        """ add tasks and additional requires to our template """
        # Copy basic requirements
        recipe = copy.deepcopy(recipeTemplate)
        if whiteboard:
            recipe.whiteboard = whiteboard
        if distroRequires:
            recipe.addDistroRequires(copy.deepcopy(distroRequires))
        if hostRequires:
            recipe.addHostRequires(copy.deepcopy(hostRequires))
        if '/distribution/install' not in requestedTasks:
            recipe.addTask('/distribution/install')
        if install:
            paramnode = self.doc.createElement('param')
            paramnode.setAttribute('name' , 'PKGARGNAME')
            paramnode.setAttribute('value' , ' '.join(install))
            recipe.addTask('/distribution/pkginstall', paramNodes=[paramnode])
        if dump:
            # Add both, One is for RHEL5 and newer, the Scheduler will filter out the wrong one.
            recipe.addTask('/kernel/networking/ndnc')
            recipe.addTask('/kernel/networking/kdump')
        for task in requestedTasks:
            recipe.addTask(task, role=role, taskParams=taskParams)
        return recipe


class BeakerBase(object):
    doc = xml.dom.minidom.Document()

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

    def addRecipeSet(self, recipeSet):
        """ properly add a recipeSet to this job """
        if isinstance(recipeSet, BeakerRecipeSet):
            self.node.appendChild(recipeSet.node)
        elif isinstance(recipeSet, xml.dom.minidom.Element):
            recipeSet.appendChild(recipeSet)
        else:
            #FIXME raise error here.
            sys.stderr.write("invalid object\n")

    def addRecipe(self, recipe):
        """ properly add a recipe to this job """
        recipeSet = self.doc.createElement('recipeSet')
        if isinstance(recipe, BeakerRecipe):
            recipeSet.appendChild(recipe.node)
        elif isinstance(recipe, xml.dom.minidom.Element):
            recipeSet.appendChild(recipe)
        else:
            #FIXME raise error here.
            sys.stderr.write("invalid object\n")
        self.node.appendChild(recipeSet)

class BeakerRecipeSet(BeakerBase):
    def __init__(self, *args, **kwargs):
        self.node = self.doc.createElement('recipeSet')
        self.node.setAttribute('priority', kwargs.get('priority', ''))
        if kwargs.get('retention_tag'):
            self.node.setAttribute('retention_tag', kwargs.get('retention_tag'))
        if kwargs.get('product'):
            self.node.setAttribute('product', kwargs.get('product'))

    def addRecipe(self, recipe):
        """ properly add a recipe to this recipeSet """
        if isinstance(recipe, BeakerRecipe):
            self.node.appendChild(recipe.node)
        elif isinstance(recipe, xml.dom.minidom.Element):
            self.node.appendChild(recipe)
        else:
            #FIXME raise error here.
            sys.stderr.write("invalid object\n")

class BeakerRecipeBase(BeakerBase):
    def __init__(self, *args, **kwargs):
        self.node.setAttribute('whiteboard','')
        self.andDistroRequires = self.doc.createElement('and')
        self.andHostRequires = self.doc.createElement('and')
        distroRequires = self.doc.createElement('distroRequires')
        hostRequires = self.doc.createElement('hostRequires')
        self.repos = self.doc.createElement('repos')
        distroRequires.appendChild(self.andDistroRequires)
        hostRequires.appendChild(self.andHostRequires)
        self.node.appendChild(distroRequires)
        self.node.appendChild(hostRequires)
        self.node.appendChild(self.repos)

    def addBaseRequires(self, *args, **kwargs):
        """ Add base requires """
        distro = kwargs.get("distro", None)
        family = kwargs.get("family", None)
        variant = kwargs.get("variant", None)
        method = kwargs.get("method", None)
        kernel_options = kwargs.get("kernel_options", '')
        tags = kwargs.get("tag", [])
        systype = kwargs.get("systype", None)
        machine = kwargs.get("machine", None)
        keyvalues = kwargs.get("keyvalue", [])
        repos = kwargs.get("repo", [])
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
            self.ks_meta = "method=%s" % method
        if kernel_options:
            self.kernel_options = kernel_options
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

    def addRepo(self, node):
        self.repos.appendChild(node)

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
                    self.andHostRequires.appendChild(node)

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
                    self.andDistroRequires.appendChild(node)

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

    def addKickstart(self, kickstart):
        recipeKickstart = self.doc.createElement('kickstart')
        recipeKickstart.appendChild(self.doc.createCDATASection(kickstart))
        self.node.appendChild(recipeKickstart)

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


class BeakerRecipe(BeakerRecipeBase):
    def __init__(self, *args, **kwargs):
        self.node = self.doc.createElement('recipe')
        super(BeakerRecipe,self).__init__(*args, **kwargs)

    def addGuestRecipe(self, guestrecipe):
        """ properly add a guest recipe to this recipe """
        if isinstance(guestrecipe, BeakerGuestRecipe):
            self.node.appendChild(guestrecipe.node)
        elif isinstance(guestrecipe, xml.dom.minidom.Element) and \
             guestrecipe.tagName == 'guestrecipe':
            self.node.appendChild(guestrecipe)
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

