# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import copy
import json
import logging
import os
import pprint
import socket
import sys
import time
import uuid
from optparse import OptionGroup, OptionParser

import dnf
from six.moves import configparser, urllib, xmlrpc_client

from bkr.common.bexceptions import BX
from bkr.log import log_to_stream


def url_exists(url):
    try:
        urllib.request.urlopen(url)
    except urllib.error.URLError:
        return False
    except IOError as e:
        # errno 21 is you tried to retrieve a directory.  Thats ok. We just
        # want to ensure the path is valid so far.
        if e.errno == 21:
            pass
        else:
            raise
    return True


def is_rhel8_alpha(parser):
    result = False
    try:
        result = (
            parser.get("compose", "label") == "Alpha-1.2"
            and parser.get("product", "short") == "RHEL"
            and parser.get("product", "version") == "8.0"
            and
            # If the partner has made adjustments to the composeinfo
            # files so that the compose looks like a unified compose,
            # don't execute the extra code we would normally do for RHEL8
            # Alpha on partner servers. Instead assume that the code
            # which can import RHEL7 will do. This is the best guess at
            # the moment, since there is nothing really explicit which
            # distinguishes the ordinary partner sync from a non-adjusted
            # composeinfo.
            not parser.has_option("variant-BaseOS", "variants")
        )
    except configparser.Error:
        pass
    return result


class IncompleteTree(BX):
    """
    IncompleteTree is raised when there is a discrepancy between
    what is specified in a .composeinfo/.treeinfo, and what is actually
    found on disk.
    """

    pass


class _DummyProxy:

    """A class that enables RPCs to be accessed as attributes ala xmlrpc_client.ServerProxy
    Inspired/ripped from xmlrpc_client.ServerProxy
    """

    def __init__(self, name):
        self.__name = name

    def __getattr__(self, name):
        return _DummyProxy("%s.%s" % (self.__name, name))

    def __call__(self, *args):
        logging.debug("Dummy call to: %s, args: %s" % (self.__name, args))
        return True


class SchedulerProxy(object):
    """Scheduler Proxy"""

    def __init__(self, options):
        self.add_distro_cmd = options.add_distro_cmd
        # addDistroCmd = '/var/lib/beaker/addDistro.sh'
        if options.dry_run:

            class _Dummy(object):
                def __getattr__(self, name):
                    return _DummyProxy(name)

            self.proxy = _Dummy()
        else:
            self.proxy = xmlrpc_client.ServerProxy(
                options.lab_controller, allow_none=True
            )

    def add_distro(self, profile):
        return self.proxy.add_distro_tree(profile)

    def run_distro_test_job(
        self, name=None, tags=[], osversion=None, arches=[], variants=[]
    ):
        if self.is_add_distro_cmd:
            cmd = self._make_add_distro_cmd(
                name=name,
                tags=tags,
                osversion=osversion,
                arches=arches,
                variants=variants,
            )
            logging.debug(cmd)
            os.system(cmd)
        else:
            raise BX("%s is missing" % self.add_distro_cmd)

    def _make_add_distro_cmd(
        self, name=None, tags=[], osversion=None, arches=[], variants=[]
    ):
        # addDistro.sh "rel-eng" RHEL6.0-20090626.2 RedHatEnterpriseLinux6.0 x86_64,i386 "Server,Workstation,Client"
        cmd = '%s "%s" "%s" "%s" "%s" "%s"' % (
            self.add_distro_cmd,
            ",".join(tags),
            name,
            osversion,
            ",".join(arches),
            ",".join(variants),
        )
        return cmd

    @property
    def is_add_distro_cmd(self):
        # Kick off jobs automatically
        if os.path.exists(self.add_distro_cmd):
            return True
        return False


class Parser(object):
    """
    base class to use for processing .composeinfo and .treeinfo
    """

    url = None
    parser = None
    last_modified = 0.0
    infofile = None  # overriden in subclasses
    discinfo = None

    def parse(self, url):
        self.url = url
        try:
            f = urllib.request.urlopen("%s/%s" % (self.url, self.infofile))
            self.parser = configparser.ConfigParser()
            self.parser.readfp(f)
            f.close()
        except urllib.error.URLError:
            return False
        except configparser.MissingSectionHeaderError as e:
            raise BX("%s/%s is not parsable: %s" % (self.url, self.infofile, e))

        if self.discinfo:
            try:
                f = urllib.request.urlopen("%s/%s" % (self.url, self.discinfo))
                self.last_modified = f.read().split("\n")[0]
                f.close()
            except urllib.error.URLError:
                pass
        return True

    def get(self, section, key, default=None):
        if self.parser:
            try:
                default = self.parser.get(section, key)
            except (configparser.NoSectionError, configparser.NoOptionError):
                if default is None:
                    raise
        return default

    def sections(self):
        return self.parser.sections()

    def has_option(self, section, option):
        return self.parser.has_option(section, option)

    def has_section_startswith(self, s):
        for section in self.parser.sections():
            if section.startswith(s):
                return True
        return False

    def __repr__(self):
        return "%s/%s" % (self.url, self.infofile)


class Cparser(Parser):
    infofile = ".composeinfo"
    discinfo = None


class Tparser(Parser):
    infofile = ".treeinfo"
    discinfo = ".discinfo"


class TparserRhel5(Tparser):
    def get(self, section, key, default=None):
        value = super(TparserRhel5, self).get(section, key, default=default)
        # .treeinfo for RHEL5 incorrectly reports ppc when it should report ppc64
        if section == "general" and key == "arch" and value == "ppc":
            value = "ppc64"
        return value


class Importer(object):
    def __init__(self, parser):
        self.parser = parser

    def check_input(self, opts):
        pass

    def check_arches(self, arches, multiple=True, single=True):
        if not arches:
            return
        if len(arches) > 1 and not multiple:
            raise BX(
                "Multiple values for arch are incompatible with %s "
                "importer" % self.__class__.__name__
            )
        if not single:
            raise BX(
                "Specific value for arch is incompatible with %s "
                "importer" % self.__class__.__name__
            )

    def check_variants(self, variants, multiple=True, single=True):
        if not variants:
            return
        if len(variants) > 1 and not multiple:
            raise BX(
                "Multiple values for variant are incompatible with %s "
                "importer" % self.__class__.__name__
            )
        if not single:
            raise BX(
                "Specific value for variant is incompatible with %s "
                "importer" % self.__class__.__name__
            )


class ComposeInfoMixin(object):
    @classmethod
    def is_importer_for(cls, url, options=None):
        parser = Cparser()
        if not parser.parse(url):
            return False
        for r in cls.required:
            if parser.get(r["section"], r["key"], "") == "":
                return False
        for e in cls.excluded:
            if parser.get(e["section"], e["key"], "") != "":
                return False
        return parser

    def run_jobs(self):
        """
        Run a job with the newly imported distro_trees
        """
        arches = []
        variants = []
        for distro_tree in self.distro_trees:
            arches.append(distro_tree["arch"])
            variants.append(distro_tree["variant"])
            name = distro_tree["name"]
            tags = distro_tree.get("tags", [])
            osversion = "%s.%s" % (distro_tree["osmajor"], distro_tree["osminor"])
        self.scheduler.run_distro_test_job(
            name=name,
            tags=tags,
            osversion=osversion,
            arches=list(set(arches)),
            variants=list(set(variants)),
        )


class ComposeInfoLegacy(ComposeInfoMixin, Importer):
    """
    [tree]
    arches = i386,x86_64,ia64,ppc64,s390,s390x
    name = RHEL4-U8
    """

    required = [
        dict(section="tree", key="name"),
    ]
    excluded = [
        dict(section="product", key="variants"),
    ]
    arches = ["i386", "x86_64", "ia64", "ppc", "ppc64", "s390", "s390x"]
    os_dirs = ["os", "tree"]

    def get_arches(self):
        """Return a list of arches"""
        specific_arches = self.options.arch
        if specific_arches:
            return filter(
                lambda x: url_exists(os.path.join(self.parser.url, x)) and x,
                [arch for arch in specific_arches],
            )
        else:
            return filter(
                lambda x: url_exists(os.path.join(self.parser.url, x)) and x,
                [arch for arch in self.arches],
            )

    def get_os_dir(self, arch):
        """Return path to os directory"""
        base_path = os.path.join(self.parser.url, arch)
        try:
            os_dir = filter(
                lambda x: url_exists(os.path.join(base_path, x)) and x, self.os_dirs
            )[0]
        except IndexError as e:
            raise BX("%s no os_dir found: %s" % (base_path, e))
        return os.path.join(arch, os_dir)

    def check_input(self, options):
        self.check_variants(options.variant, single=False)

    def process(self, urls, options):
        exit_status = 0

        self.options = options
        self.scheduler = SchedulerProxy(self.options)
        self.distro_trees = []
        for arch in self.get_arches():
            try:
                os_dir = self.get_os_dir(arch)
                full_os_dir = os.path.join(self.parser.url, os_dir)
                options = copy.deepcopy(self.options)
                if not options.name:
                    options.name = self.parser.get("tree", "name")
                urls_arch = [os.path.join(url, os_dir) for url in urls]
                # find our repos, but relative from os_dir
                # repos = self.find_repos(full_os_dir, arch)
                build = Build(full_os_dir)
                build.process(urls_arch, options)
                self.distro_trees.append(build.tree)
            except BX as err:
                if not options.ignore_missing:
                    exit_status = 1
                    logging.warning(err)

        return exit_status


class ComposeInfo(ComposeInfoMixin, Importer):
    """
    [product]
    family = RHEL
    name = Red Hat Enterprise Linux
    variants = Client,ComputeNode,Server,Workstation
    version = 7.0

    [variant-Client]
    arches = x86_64
    id = Client
    name = Client
    type = variant
    uid = Client
    variants = Client-optional

    [variant-Client-optional]
    arches = x86_64
    id = optional
    name = optional
    parent = Client
    type = optional
    uid = Client-optional
    variants =

    [variant-Client-optional.x86_64]
    arch = x86_64
    debuginfo = Client-optional/x86_64/debuginfo
    os_dir = Client-optional/x86_64/os
    packages = Client-optional/x86_64/os/Packages
    parent = Client.x86_64
    repository = Client-optional/x86_64/os
    sources = Client-optional/source/SRPMS

    [variant-Client.x86_64]
    arch = x86_64
    debuginfo = Client/x86_64/debuginfo
    isos = Client/x86_64/iso
    os_dir = Client/x86_64/os
    packages = Client/x86_64/os/Packages
    repository = Client/x86_64/os
    source_isos = Client/source/iso
    sources = Client/source/SRPMS

    [variant-ComputeNode]
    arches = x86_64
    id = ComputeNode
    name = Compute Node
    type = variant
    uid = ComputeNode
    variants = ComputeNode-optional

    [variant-ComputeNode-optional]
    arches = x86_64
    id = optional
    name = optional
    parent = ComputeNode
    type = optional
    uid = ComputeNode-optional
    variants =

    [variant-ComputeNode-optional.x86_64]
    arch = x86_64
    debuginfo = ComputeNode-optional/x86_64/debuginfo
    os_dir = ComputeNode-optional/x86_64/os
    packages = ComputeNode-optional/x86_64/os/Packages
    parent = ComputeNode.x86_64
    repository = ComputeNode-optional/x86_64/os
    sources = ComputeNode-optional/source/SRPMS

    [variant-ComputeNode.x86_64]
    arch = x86_64
    debuginfo = ComputeNode/x86_64/debuginfo
    isos = ComputeNode/x86_64/iso
    os_dir = ComputeNode/x86_64/os
    packages = ComputeNode/x86_64/os/Packages
    repository = ComputeNode/x86_64/os
    source_isos = ComputeNode/source/iso
    sources = ComputeNode/source/SRPMS

    [variant-Server]
    arches = ppc64,s390x,x86_64
    id = Server
    name = Server
    type = variant
    uid = Server
    variants = Server-HighAvailability,Server-LoadBalancer,Server-ResilientStorage,Server-ScalableFileSystem,Server-optional

    [variant-Server-HighAvailability]
    arches = x86_64
    id = HighAvailability
    name = High Availability
    parent = Server
    type = addon
    uid = Server-HighAvailability
    variants =

    [variant-Server-HighAvailability.x86_64]
    arch = x86_64
    debuginfo = Server/x86_64/debuginfo
    os_dir = Server/x86_64/os
    packages = Server/x86_64/os/addons/HighAvailability
    parent = Server.x86_64
    repository = Server/x86_64/os/addons/HighAvailability
    sources = Server/source/SRPMS

    [variant-Server-LoadBalancer]
    arches = x86_64
    id = LoadBalancer
    name = Load Balancer
    parent = Server
    type = addon
    uid = Server-LoadBalancer
    variants =

    [variant-Server-LoadBalancer.x86_64]
    arch = x86_64
    debuginfo = Server/x86_64/debuginfo
    os_dir = Server/x86_64/os
    packages = Server/x86_64/os/addons/LoadBalancer
    parent = Server.x86_64
    repository = Server/x86_64/os/addons/LoadBalancer
    sources = Server/source/SRPMS

    [variant-Server-ResilientStorage]
    arches = x86_64
    id = ResilientStorage
    name = Resilient Storage
    parent = Server
    type = addon
    uid = Server-ResilientStorage
    variants =

    [variant-Server-ResilientStorage.x86_64]
    arch = x86_64
    debuginfo = Server/x86_64/debuginfo
    os_dir = Server/x86_64/os
    packages = Server/x86_64/os/addons/ResilientStorage
    parent = Server.x86_64
    repository = Server/x86_64/os/addons/ResilientStorage
    sources = Server/source/SRPMS

    [variant-Server-ScalableFileSystem]
    arches = x86_64
    id = ScalableFileSystem
    name = Scalable Filesystem Support
    parent = Server
    type = addon
    uid = Server-ScalableFileSystem
    variants =

    [variant-Server-ScalableFileSystem.x86_64]
    arch = x86_64
    debuginfo = Server/x86_64/debuginfo
    os_dir = Server/x86_64/os
    packages = Server/x86_64/os/addons/ScalableFileSystem
    parent = Server.x86_64
    repository = Server/x86_64/os/addons/ScalableFileSystem
    sources = Server/source/SRPMS

    [variant-Server-optional]
    arches = ppc64,s390x,x86_64
    id = optional
    name = optional
    parent = Server
    type = optional
    uid = Server-optional
    variants =

    [variant-Server-optional.ppc64]
    arch = ppc64
    debuginfo = Server-optional/ppc64/debuginfo
    os_dir = Server-optional/ppc64/os
    packages = Server-optional/ppc64/os/Packages
    parent = Server.ppc64
    repository = Server-optional/ppc64/os
    sources = Server-optional/source/SRPMS

    [variant-Server-optional.s390x]
    arch = s390x
    debuginfo = Server-optional/s390x/debuginfo
    os_dir = Server-optional/s390x/os
    packages = Server-optional/s390x/os/Packages
    parent = Server.s390x
    repository = Server-optional/s390x/os
    sources = Server-optional/source/SRPMS

    [variant-Server-optional.x86_64]
    arch = x86_64
    debuginfo = Server-optional/x86_64/debuginfo
    os_dir = Server-optional/x86_64/os
    packages = Server-optional/x86_64/os/Packages
    parent = Server.x86_64
    repository = Server-optional/x86_64/os
    sources = Server-optional/source/SRPMS

    [variant-Server.ppc64]
    arch = ppc64
    debuginfo = Server/ppc64/debuginfo
    isos = Server/ppc64/iso
    os_dir = Server/ppc64/os
    packages = Server/ppc64/os/Packages
    repository = Server/ppc64/os
    source_isos = Server/source/iso
    sources = Server/source/SRPMS

    [variant-Server.s390x]
    arch = s390x
    debuginfo = Server/s390x/debuginfo
    isos = Server/s390x/iso
    os_dir = Server/s390x/os
    packages = Server/s390x/os/Packages
    repository = Server/s390x/os
    source_isos = Server/source/iso
    sources = Server/source/SRPMS

    [variant-Server.x86_64]
    arch = x86_64
    debuginfo = Server/x86_64/debuginfo
    isos = Server/x86_64/iso
    os_dir = Server/x86_64/os
    packages = Server/x86_64/os/Packages
    repository = Server/x86_64/os
    source_isos = Server/source/iso
    sources = Server/source/SRPMS

    [variant-Workstation]
    arches = x86_64
    id = Workstation
    name = Workstation
    type = variant
    uid = Workstation
    variants = Workstation-ScalableFileSystem,Workstation-optional

    [variant-Workstation-ScalableFileSystem]
    arches = x86_64
    id = ScalableFileSystem
    name = Scalable Filesystem Support
    parent = Workstation
    type = addon
    uid = Workstation-ScalableFileSystem
    variants =

    [variant-Workstation-ScalableFileSystem.x86_64]
    arch = x86_64
    debuginfo = Workstation/x86_64/debuginfo
    os_dir = Workstation/x86_64/os
    packages = Workstation/x86_64/os/addons/ScalableFileSystem
    parent = Workstation.x86_64
    repository = Workstation/x86_64/os/addons/ScalableFileSystem
    sources = Workstation/source/SRPMS

    [variant-Workstation-optional]
    arches = x86_64
    id = optional
    name = optional
    parent = Workstation
    type = optional
    uid = Workstation-optional
    variants =

    [variant-Workstation-optional.x86_64]
    arch = x86_64
    debuginfo = Workstation-optional/x86_64/debuginfo
    os_dir = Workstation-optional/x86_64/os
    packages = Workstation-optional/x86_64/os/Packages
    parent = Workstation.x86_64
    repository = Workstation-optional/x86_64/os
    sources = Workstation-optional/source/SRPMS

    [variant-Workstation.x86_64]
    arch = x86_64
    debuginfo = Workstation/x86_64/debuginfo
    isos = Workstation/x86_64/iso
    os_dir = Workstation/x86_64/os
    packages = Workstation/x86_64/os/Packages
    repository = Workstation/x86_64/os
    source_isos = Workstation/source/iso
    sources = Workstation/source/SRPMS

    """

    required = [
        dict(section="product", key="variants"),
    ]
    excluded = []

    def get_arches(self, variant):
        """Return a list of arches for variant"""

        all_arches = self.parser.get("variant-%s" % variant, "arches").split(",")
        # Fedora 25+ .composeinfo includes src but it's not a real arch that can be installed
        if "src" in all_arches:
            all_arches.remove("src")
        specific_arches = set(self.options.arch)
        if specific_arches:
            applicable_arches = specific_arches.intersection(set(all_arches))
            return list(applicable_arches)
        else:
            return all_arches

    def get_variants(self):
        """Return a list of variants"""
        specific_variants = self.options.variant
        if specific_variants:
            return specific_variants
        return self.parser.get("product", "variants").split(",")

    def find_repos(self, repo_base, rpath, variant, arch):
        """Find all variant repos"""
        repos = []
        variants = self.parser.get("variant-%s" % variant, "variants", "")
        if variants:
            for sub_variant in variants.split(","):
                repos.extend(self.find_repos(repo_base, rpath, sub_variant, arch))

        # Skip addon variants from .composeinfo, we pick these up from
        # .treeinfo
        repotype = self.parser.get("variant-%s" % variant, "type", "")
        if repotype == "addon":
            return repos

        repopath = self.parser.get("variant-%s.%s" % (variant, arch), "repository", "")
        if repopath:
            if url_exists(os.path.join(repo_base, rpath, repopath, "repodata")):
                repos.append(
                    dict(
                        repoid=variant,
                        type=repotype,
                        path=os.path.join(rpath, repopath),
                    )
                )
            else:
                logging.warning(
                    "%s repo found in .composeinfo but does not exist", variant
                )

        debugrepopath = self.parser.get(
            "variant-%s.%s" % (variant, arch), "debuginfo", ""
        )
        if debugrepopath:
            if url_exists(os.path.join(repo_base, rpath, debugrepopath, "repodata")):
                repos.append(
                    dict(
                        repoid="%s-debuginfo" % variant,
                        type="debug",
                        path=os.path.join(rpath, debugrepopath),
                    )
                )
            else:
                logging.warning(
                    "%s-debuginfo repo found in .composeinfo but does not exist",
                    variant,
                )
        if is_rhel8_alpha(self.parser):
            appstream_repos = self._guess_appstream_repos(rpath, arch, repo_base)
            if not debugrepopath:
                appstream_repos.pop()

            for repo in appstream_repos:
                url = os.path.join(repo_base, repo[2], "repodata")
                if url_exists(url):
                    repos.append(dict(repoid=repo[0], type=repo[1], path=repo[2]))
                else:
                    raise ValueError(
                        "Expected {0} compose at {1} but it doesn't exist".format(
                            repo[0], url
                        )
                    )

        return repos

    def _guess_appstream_repos(self, rpath, arch, repo_base):
        """Iterate over possible layouts to guess which one fits and return a list of repositories."""
        repo_layout = {
            "8.0-AppStream-Alpha": [
                (
                    "AppStream",
                    "variant",
                    os.path.join(
                        rpath, "..", "8.0-AppStream-Alpha", "AppStream", arch, "os"
                    ),
                ),
                (
                    "AppStream-debuginfo",
                    "debug",
                    os.path.join(
                        rpath,
                        "..",
                        "8.0-AppStream-Alpha",
                        "AppStream",
                        arch,
                        "debug",
                        "tree",
                    ),
                ),
            ],
            "AppStream-8.0-20180531.0": [
                (
                    "AppStream",
                    "variant",
                    os.path.join(
                        rpath,
                        "..",
                        "..",
                        "AppStream-8.0-20180531.0",
                        "compose",
                        "AppStream",
                        arch,
                        "os",
                    ),
                ),
                (
                    "AppStream-debuginfo",
                    "debug",
                    os.path.join(
                        rpath,
                        "..",
                        "..",
                        "AppStream-8.0-20180531.0",
                        "compose",
                        "AppStream",
                        arch,
                        "debug",
                        "tree",
                    ),
                ),
            ],
        }

        appstream_repos = []
        for dirname, repos in repo_layout.items():
            url = os.path.join(repo_base, repos[0][2], "repodata")
            logging.debug("Trying to import %s", repos[0][2])
            if not url_exists(url):
                continue
            else:
                appstream_repos = repos

        if not appstream_repos:
            raise ValueError(
                "Could not determine repository layout to import AppStream repo"
            )
        return appstream_repos

    def process(self, urls, options):
        exit_status = 0

        self.options = options
        self.scheduler = SchedulerProxy(self.options)
        self.distro_trees = []
        for variant in self.get_variants():
            for arch in self.get_arches(variant):
                os_dir = self.parser.get("variant-%s.%s" % (variant, arch), "os_dir")
                options = copy.deepcopy(self.options)
                if not options.name:
                    options.name = self.parser.get("product", "name")

                # our current path relative to the os_dir "../.."
                rpath = os.path.join(*[".." for i in range(0, len(os_dir.split("/")))])

                # find our repos, but relative from os_dir
                repos = self.find_repos(
                    os.path.join(self.parser.url, os_dir), rpath, variant, arch
                )

                urls_variant_arch = [os.path.join(url, os_dir) for url in urls]
                try:
                    options.variant = [variant]
                    options.arch = [arch]
                    build = Build(os.path.join(self.parser.url, os_dir))
                    labels = self.parser.get("compose", "label", "")
                    tags = [
                        label.strip() for label in (labels and labels.split() or [])
                    ]
                    try:
                        isos_path = self.parser.get(
                            "variant-%s.%s" % (variant, arch), "isos"
                        )
                        isos_path = os.path.join(rpath, isos_path)
                    except configparser.NoOptionError:
                        isos_path = None
                    build.process(
                        urls_variant_arch,
                        options,
                        repos=repos,
                        tags=tags,
                        isos_path=isos_path,
                    )
                    self.distro_trees.append(build.tree)
                except BX as err:
                    if not options.ignore_missing:
                        exit_status = 1
                        logging.warning(err)
        return exit_status


class TreeInfoMixin(object):
    """
    Base class for TreeInfo methods
    """

    required = [
        dict(section="general", key="family"),
        dict(section="general", key="version"),
        dict(section="general", key="arch"),
    ]
    excluded = []

    # This is a best guess for the relative iso path
    # for RHEL5/6/7 and Fedora trees
    isos_path = "../iso/"

    def check_input(self, options):
        self.check_variants(options.variant, single=False)
        self.check_arches(options.arch, single=False)

    def get_os_dir(self):
        """Return path to os directory
        This is just a sanity check, the parser's URL should be the os dir.
        """
        try:
            os_dir = filter(lambda x: url_exists(x) and x, [self.parser.url])[0]
        except IndexError as e:
            raise BX("%s no os_dir found: %s" % (self.parser.url, e))
        return os_dir

    def _installable_isos_url(self, nfs_url, isos_path_from_compose=None):
        """Returns the URL of an installable iso.

        The scheme of the returned URL is 'nfs+iso',
        which only has meaning to Beaker.
        """

        isos_path = isos_path_from_compose
        if not isos_path_from_compose:
            # Let's just guess! These are based on
            # well known locations for each family
            isos_path = self.isos_path
        http_url_components = list(urllib.parse.urlparse(self.parser.url))
        http_url_path = http_url_components[2]
        normalized_isos_path = os.path.normpath(os.path.join(http_url_path, isos_path))
        if not normalized_isos_path.endswith("/"):
            normalized_isos_path += "/"
        http_url_components[2] = normalized_isos_path
        http_isos_url = urllib.parse.urlunparse(http_url_components)
        reachable_iso_dir = url_exists(http_isos_url)
        if isos_path_from_compose and not reachable_iso_dir:
            # If .composeinfo says the isos path is there but it isn't, we
            # should let it be known.
            raise IncompleteTree(
                "Could not find iso url %s as specified "
                "in composeinfo" % http_isos_url
            )
        elif not isos_path_from_compose and not reachable_iso_dir:
            # We can't find the isos path, but we were only ever guessing.
            return None
        elif reachable_iso_dir:
            # We've found the isos path via http, convert it back to
            # nfs+iso URL.
            nfs_url_components = list(urllib.parse.urlparse(nfs_url))
            nfs_url_path = nfs_url_components[2]
            normalized_isos_path = os.path.normpath(
                os.path.join(nfs_url_path, isos_path)
            )
            if not normalized_isos_path.endswith("/"):
                normalized_isos_path += "/"
            nfs_isos_url_components = list(nfs_url_components)
            nfs_isos_url_components[2] = normalized_isos_path
            nfs_isos_url_components[0] = "nfs+iso"
            return urllib.parse.urlunparse(nfs_isos_url_components)

    def process(self, urls, options, repos=None, tags=None, isos_path=None):
        """
        distro_data = dict(
                name='RHEL-6-U1',
                arches=['i386', 'x86_64'], arch='x86_64',
                osmajor='RedHatEnterpriseLinux6', osminor='1',
                variant='Workstation', tree_build_time=1305067998.6483951,
                urls=['nfs://example.invalid:/RHEL-6-Workstation/U1/x86_64/os/',
                      'file:///net/example.invalid/RHEL-6-Workstation/U1/x86_64/os/',
                      'http://example.invalid/RHEL-6-Workstation/U1/x86_64/os/'],
                repos=[
                    dict(repoid='Workstation', type='os', path=''),
                    dict(repoid='ScalableFileSystem', type='addon', path='ScalableFileSystem/'),
                    dict(repoid='optional', type='addon', path='../../optional/x86_64/os/'),
                    dict(repoid='debuginfo', type='debug', path='../debug/'),
                ],
                images=[
                    dict(type='kernel', path='images/pxeboot/vmlinuz'),
                    dict(type='initrd', path='images/pxeboot/initrd.img'),
                ])

        """
        if not repos:
            repos = []
        self.options = options
        self.scheduler = SchedulerProxy(options)
        self.tree = dict()
        # Make sure all url's end with /
        urls = [os.path.join(url, "") for url in urls]
        self.tree["urls"] = urls
        family = self.options.family or self.parser.get("general", "family").replace(
            " ", ""
        )
        version = self.options.version or self.parser.get("general", "version").replace(
            "-", "."
        )
        self.tree["name"] = self.options.name or self.parser.get(
            "general", "name", "%s-%s" % (family, version)
        )

        try:
            self.tree["variant"] = self.options.variant[0]
        except IndexError:
            self.tree["variant"] = self.parser.get("general", "variant", "")
        self.tree["arch"] = self.parser.get("general", "arch")
        self.tree["tree_build_time"] = self.options.buildtime or self.parser.get(
            "general", "timestamp", self.parser.last_modified
        )
        common_tags = tags or []  # passed in from .composeinfo
        labels = self.parser.get("general", "label", "")
        self.tree["tags"] = list(
            set(self.options.tags)
            | set(common_tags)
            | set(map(lambda label: label.strip(), labels and labels.split(",") or []))
        )
        self.tree["osmajor"] = "%s%s" % (family, version.split(".")[0])
        if version.find(".") != -1:
            self.tree["osminor"] = version.split(".")[1]
        else:
            self.tree["osminor"] = "0"

        arches = self.parser.get("general", "arches", "")
        self.tree["arches"] = map(
            lambda arch: arch.strip(), arches and arches.split(",") or []
        )
        full_os_dir = self.get_os_dir()
        # These would have been passed from the Compose*.process()
        common_repos = repos
        if not common_repos:
            common_repos = self.find_common_repos(full_os_dir, self.tree["arch"])
        self.tree["repos"] = self.find_repos() + common_repos

        # Add install images
        self.tree["images"] = self.get_images()

        if not self.options.preserve_install_options:
            self.tree["kernel_options"] = self.options.kopts
            self.tree["kernel_options_post"] = self.options.kopts_post
            self.tree["ks_meta"] = self.options.ks_meta
        nfs_url = _get_url_by_scheme(urls, "nfs")
        if nfs_url:
            try:
                nfs_isos_url = self._installable_isos_url(nfs_url, isos_path)
            except IncompleteTree as e:
                logging.warning(str(e))
            else:
                if nfs_isos_url:
                    self.tree["urls"].append(nfs_isos_url)

        self.extend_tree()
        if options.json:
            print(json.dumps(self.tree))
        logging.debug("\n%s" % pprint.pformat(self.tree))
        try:
            self.add_to_beaker()
            logging.info(
                "%s %s %s added to beaker."
                % (self.tree["name"], self.tree["variant"], self.tree["arch"])
            )
        except (xmlrpc_client.Fault, socket.error) as e:
            raise BX(
                "failed to add %s %s %s to beaker: %s"
                % (self.tree["name"], self.tree["variant"], self.tree["arch"], e)
            )

    def extend_tree(self):
        pass

    def find_common_repos(self, repo_base, arch):
        """
        RHEL6 repos
        ../../optional/<ARCH>/os/repodata
        ../../optional/<ARCH>/debug/repodata
        ../debug/repodata
        """
        repo_paths = [
            ("debuginfo", "debug", "../debug"),
            ("optional-debuginfo", "debug", "../../optional/%s/debug" % arch),
            ("optional", "optional", "../../optional/%s/os" % arch),
        ]
        repos = []
        for repo in repo_paths:
            if url_exists(os.path.join(repo_base, repo[2], "repodata")):
                repos.append(
                    dict(
                        repoid=repo[0],
                        type=repo[1],
                        path=repo[2],
                    )
                )
        return repos

    def get_images(self):
        images = []
        images.append(dict(type="kernel", path=self.get_kernel_path()))
        images.append(dict(type="initrd", path=self.get_initrd_path()))
        return images

    def add_to_beaker(self):
        self.scheduler.add_distro(self.tree)

    def run_jobs(self):
        arches = [self.tree["arch"]]
        variants = [self.tree["variant"]]
        name = self.tree["name"]
        tags = self.tree.get("tags", [])
        osversion = "%s.%s" % (self.tree["osmajor"], self.tree["osminor"])
        self.scheduler.run_distro_test_job(
            name=name, tags=tags, osversion=osversion, arches=arches, variants=variants
        )


class TreeInfoLegacy(TreeInfoMixin, Importer):
    """
    This version of .treeinfo importer has a workaround for missing
    images-$arch sections.
    """

    kernels = [
        "images/pxeboot/vmlinuz",
        "images/kernel.img",
        "ppc/ppc64/vmlinuz",
        "ppc/chrp/vmlinuz",
        # We don't support iSeries right now 'ppc/iSeries/vmlinux',
    ]
    initrds = [
        "images/pxeboot/initrd.img",
        "images/initrd.img",
        "ppc/ppc64/ramdisk.image.gz",
        "ppc/chrp/ramdisk.image.gz",
        # We don't support iSeries right now 'ppc/iSeries/ramdisk.image.gz',
    ]

    isos_path = "../ftp-isos/"

    @classmethod
    def is_importer_for(cls, url, options=None):
        parser = Tparser()
        if not parser.parse(url):
            return False
        for r in cls.required:
            if parser.get(r["section"], r["key"], "") == "":
                return False
        for e in cls.excluded:
            if parser.get(e["section"], e["key"], "") != "":
                return False
        if not (
            parser.get("general", "family").startswith("Red Hat Enterprise Linux")
            or parser.get("general", "family").startswith("CentOS")
        ):
            return False
        if int(parser.get("general", "version").split(".")[0]) > 4:
            return False
        return parser

    def get_kernel_path(self):
        try:
            return filter(
                lambda x: url_exists(os.path.join(self.parser.url, x)) and x,
                [kernel for kernel in self.kernels],
            )[0]
        except IndexError as e:
            raise BX("%s no kernel found: %s" % (self.parser.url, e))

    def get_initrd_path(self):
        try:
            return filter(
                lambda x: url_exists(os.path.join(self.parser.url, x)) and x,
                [initrd for initrd in self.initrds],
            )[0]
        except IndexError as e:
            raise BX("%s no kernel found: %s" % (self.parser.url, e))

    def find_repos(self, *args, **kw):
        """
        using info from .treeinfo and known locations

        RHEL4 repos
        ../repo-<VARIANT>-<ARCH>/repodata
        ../repo-debug-<VARIANT>-<ARCH>/repodata
        ../repo-srpm-<VARIANT>-<ARCH>/repodata
        arch = ppc64 = ppc

        RHEL3 repos
        ../repo-<VARIANT>-<ARCH>/repodata
        ../repo-debug-<VARIANT>-<ARCH>/repodata
        ../repo-srpm-<VARIANT>-<ARCH>/repodata
        arch = ppc64 = ppc
        """
        repos = []
        # ppc64 arch uses ppc for the repos
        arch = self.tree["arch"].replace("ppc64", "ppc")

        repo_paths = [
            ("%s-debuginfo" % self.tree["variant"], "debug", "../debug"),
            (
                "%s-debuginfo" % self.tree["variant"],
                "debug",
                "../repo-debug-%s-%s" % (self.tree["variant"], arch),
            ),
            (
                "%s-optional-debuginfo" % self.tree["variant"],
                "debug",
                "../optional/%s/debug" % arch,
            ),
            (
                "%s" % self.tree["variant"],
                "variant",
                "../repo-%s-%s" % (self.tree["variant"], arch),
            ),
            ("%s" % self.tree["variant"], "variant", "."),
            (
                "%s-optional" % self.tree["variant"],
                "optional",
                "../../optional/%s/os" % arch,
            ),
            ("VT", "addon", "VT"),
            ("Server", "addon", "Server"),
            ("Cluster", "addon", "Cluster"),
            ("ClusterStorage", "addon", "ClusterStorage"),
            ("Client", "addon", "Client"),
            ("Workstation", "addon", "Workstation"),
        ]
        for repo in repo_paths:
            if url_exists(os.path.join(self.parser.url, repo[2], "repodata")):
                repos.append(
                    dict(
                        repoid=repo[0],
                        type=repo[1],
                        path=repo[2],
                    )
                )
        return repos


class TreeInfoRhel5(TreeInfoMixin, Importer):
    # Used in RHEL5 and all CentOS releases from 5 onwards.
    # Has image locations but no repo info so we guess that.
    """
    [general]
    family = Red Hat Enterprise Linux Server
    timestamp = 1209596791.91
    totaldiscs = 1
    version = 5.2
    discnum = 1
    label = RELEASED
    packagedir = Server
    arch = ppc

    [images-ppc64]
    kernel = ppc/ppc64/vmlinuz
    initrd = ppc/ppc64/ramdisk.image.gz
    zimage = images/netboot/ppc64.img

    [stage2]
    instimage = images/minstg2.img
    mainimage = images/stage2.img

    """

    @classmethod
    def is_importer_for(cls, url, options=None):
        parser = TparserRhel5()
        if not parser.parse(url):
            return False
        for r in cls.required:
            if parser.get(r["section"], r["key"], "") == "":
                return False
        for e in cls.excluded:
            if parser.get(e["section"], e["key"], "") != "":
                return False
        if (
            not parser.has_section_startswith("images-")
            or parser.has_option("general", "repository")
            or parser.has_section_startswith("variant-")
            or parser.has_section_startswith("addon-")
        ):
            return False
        # Fedora has a special case below, see TreeInfoFedora
        if "Fedora" in parser.get("general", "family"):
            return False
        return parser

    def get_kernel_path(self):
        return self.parser.get("images-%s" % self.tree["arch"], "kernel")

    def get_initrd_path(self):
        return self.parser.get("images-%s" % self.tree["arch"], "initrd")

    def find_repos(self):
        """
        using info from known locations

        RHEL5 repos
        ../debug/repodata
        ./Server
        ./Cluster
        ./ClusterStorage
        ./VT
        ./Client
        ./Workstation

        CentOS repos
        .
        """
        # ppc64 arch uses ppc for the repos
        arch = self.tree["arch"].replace("ppc64", "ppc")

        repo_paths = [
            ("VT", "addon", "VT"),
            ("Server", "addon", "Server"),
            ("Cluster", "addon", "Cluster"),
            ("ClusterStorage", "addon", "ClusterStorage"),
            ("Client", "addon", "Client"),
            ("Workstation", "addon", "Workstation"),
            ("distro", "distro", "."),
        ]
        repos = []
        for repo in repo_paths:
            if url_exists(os.path.join(self.parser.url, repo[2], "repodata")):
                repos.append(
                    dict(
                        repoid=repo[0],
                        type=repo[1],
                        path=repo[2],
                    )
                )
        return repos


class TreeInfoFedora(TreeInfoMixin, Importer):
    # This is basically the same as TreeInfoRHEL5 except that it hardcodes
    # 'Fedora' in the repoids.
    """ """

    @classmethod
    def is_importer_for(cls, url, options=None):
        parser = Tparser()
        if not parser.parse(url):
            return False
        for r in cls.required:
            if parser.get(r["section"], r["key"], "") == "":
                return False
        for e in cls.excluded:
            if parser.get(e["section"], e["key"], "") != "":
                return False
        if not parser.get("general", "family").startswith("Fedora"):
            return False
        # Arm uses a different importer because of all the kernel types.
        if parser.get("general", "arch") in ["arm", "armhfp"]:
            return False
        return parser

    def get_kernel_path(self):
        return self.parser.get("images-%s" % self.tree["arch"], "kernel")

    def get_initrd_path(self):
        return self.parser.get("images-%s" % self.tree["arch"], "initrd")

    def find_common_repos(self, repo_base, arch):
        """
        Fedora repos
        ../debug/repodata
        """
        repo_paths = [
            ("Fedora-debuginfo", "debug", "../debug"),
        ]
        repos = []
        for repo in repo_paths:
            if url_exists(os.path.join(repo_base, repo[2], "repodata")):
                repos.append(
                    dict(
                        repoid=repo[0],
                        type=repo[1],
                        path=repo[2],
                    )
                )
        return repos

    def find_repos(self):
        """
        using info from known locations

        """
        repos = []
        repo_paths = [
            ("Fedora", "variant", "."),
            (
                "Fedora-Everything",
                "fedora",
                "../../../Everything/%s/os" % self.tree["arch"],
            ),
        ]

        for repo in repo_paths:
            if url_exists(os.path.join(self.parser.url, repo[2], "repodata")):
                repos.append(
                    dict(
                        repoid=repo[0],
                        type=repo[1],
                        path=repo[2],
                    )
                )

        return repos


class TreeInfoFedoraArm(TreeInfoFedora, Importer):
    """ """

    @classmethod
    def is_importer_for(cls, url, options=None):
        parser = Tparser()
        if not parser.parse(url):
            return False
        for r in cls.required:
            if parser.get(r["section"], r["key"], "") == "":
                return False
        for e in cls.excluded:
            if parser.get(e["section"], e["key"], "") != "":
                return False
        if not parser.get("general", "family").startswith("Fedora"):
            return False
        # Arm uses a different importer because of all the kernel types.
        if parser.get("general", "arch") not in ["arm", "armhfp"]:
            return False
        return parser

    def get_kernel_path(self, kernel_type=None):
        if kernel_type:
            kernel_type = "%s-" % kernel_type
        else:
            kernel_type = ""
        return self.parser.get(
            "images-%s%s" % (kernel_type, self.tree["arch"]), "kernel"
        )

    def get_initrd_path(self, kernel_type=None):
        if kernel_type:
            kernel_type = "%s-" % kernel_type
        else:
            kernel_type = ""
        return self.parser.get(
            "images-%s%s" % (kernel_type, self.tree["arch"]), "initrd"
        )

    def get_uimage_path(self, kernel_type=None):
        if kernel_type:
            kernel_type = "%s-" % kernel_type
        else:
            kernel_type = ""
        return self.parser.get(
            "images-%s%s" % (kernel_type, self.tree["arch"]), "uimage", ""
        )

    def get_uinitrd_path(self, kernel_type=None):
        if kernel_type:
            kernel_type = "%s-" % kernel_type
        else:
            kernel_type = ""
        return self.parser.get(
            "images-%s%s" % (kernel_type, self.tree["arch"]), "uinitrd", ""
        )

    def get_images(self):
        images = []
        images.append(dict(type="kernel", path=self.get_kernel_path()))
        images.append(dict(type="initrd", path=self.get_initrd_path()))
        uimage = self.get_uimage_path()
        if uimage:
            images.append(dict(type="uimage", path=uimage))
        uinitrd = self.get_uinitrd_path()
        if uinitrd:
            images.append(dict(type="uinitrd", path=uinitrd))
        kernel_type_string = self.parser.get(self.tree["arch"], "platforms", "")
        kernel_types = map(
            lambda item: item.strip(),
            kernel_type_string and kernel_type_string.split(",") or [],
        )
        for kernel_type in kernel_types:
            images.append(
                dict(
                    type="kernel",
                    kernel_type=kernel_type,
                    path=self.get_kernel_path(kernel_type=kernel_type),
                )
            )
            images.append(
                dict(
                    type="uimage",
                    kernel_type=kernel_type,
                    path=self.get_uimage_path(kernel_type=kernel_type),
                )
            )
            images.append(
                dict(
                    type="initrd",
                    kernel_type=kernel_type,
                    path=self.get_initrd_path(kernel_type=kernel_type),
                )
            )
            images.append(
                dict(
                    type="uinitrd",
                    kernel_type=kernel_type,
                    path=self.get_uinitrd_path(kernel_type=kernel_type),
                )
            )
        return images


class TreeInfoRhel6(TreeInfoMixin, Importer):
    # Used in RHS2 and RHEL6.
    # variant-* section has a repository key, and an addons key pointing at
    # addon-* sections.
    """
    [addon-ScalableFileSystem]
    identity = ScalableFileSystem/ScalableFileSystem.cert
    name = Scalable Filesystem Support
    repository = ScalableFileSystem

    [addon-ResilientStorage]
    identity = ResilientStorage/ResilientStorage.cert
    name = Resilient Storage
    repository = ResilientStorage

    [images-x86_64]
    kernel = images/pxeboot/vmlinuz
    initrd = images/pxeboot/initrd.img
    boot.iso = images/boot.iso

    [general]
    family = Red Hat Enterprise Linux
    timestamp = 1328166952.001091
    variant = Server
    totaldiscs = 1
    version = 6.3
    discnum = 1
    packagedir = Packages
    variants = Server
    arch = x86_64

    [images-xen]
    initrd = images/pxeboot/initrd.img
    kernel = images/pxeboot/vmlinuz

    [variant-Server]
    addons = ResilientStorage,HighAvailability,ScalableFileSystem,LoadBalancer
    identity = Server/Server.cert
    repository = Server/repodata

    [addon-HighAvailability]
    identity = HighAvailability/HighAvailability.cert
    name = High Availability
    repository = HighAvailability

    [checksums]
    images/pxeboot/initrd.img = sha256:4ffa63cd7780ec0715bd1c50b9eda177ecf28c58094ca519cfb6bb6aca5c225a
    images/efiboot.img = sha256:d9ba2cc6fd3286ed7081ce0846e9df7093f5d524461580854b7ac42259c574b1
    images/boot.iso = sha256:5e10d6d4e6e22a62cae1475da1599a8dac91ff7c3783fda7684cf780e067604b
    images/pxeboot/vmlinuz = sha256:7180f7f46682555cb1e86a9f1fbbfcc193ee0a52501de9a9002c34528c3ef9ab
    images/install.img = sha256:85aaf9f90efa4f43475e4828168a3f7755ecc62f6643d92d23361957160dbc69
    images/efidisk.img = sha256:e9bf66f54f85527e595c4f3b5afe03cdcd0bf279b861c7a20898ce980e2ce4ff

    [stage2]
    mainimage = images/install.img

    [addon-LoadBalancer]
    identity = LoadBalancer/LoadBalancer.cert
    name = Load Balancer
    repository = LoadBalancer
    """

    @classmethod
    def is_importer_for(cls, url, options=None):
        parser = Tparser()
        if not parser.parse(url):
            return False
        for r in cls.required:
            if parser.get(r["section"], r["key"], "") == "":
                return False
        for e in cls.excluded:
            if parser.get(e["section"], e["key"], "") != "":
                return False
        if parser.get("images-%s" % parser.get("general", "arch"), "kernel", "") == "":
            return False
        if parser.get("images-%s" % parser.get("general", "arch"), "initrd", "") == "":
            return False
        if not (
            parser.has_section_startswith("images-")
            and parser.has_section_startswith("variant-")
        ):
            return False
        for section in parser.sections():
            if section.startswith("variant-") and not parser.has_option(
                section, "addons"
            ):
                return False
        return parser

    def get_kernel_path(self):
        return self.parser.get("images-%s" % self.tree["arch"], "kernel")

    def get_initrd_path(self):
        return self.parser.get("images-%s" % self.tree["arch"], "initrd")

    def find_repos(self):
        """
        using info from .treeinfo
        """

        repos = []
        try:
            repopath = self.parser.get(
                "variant-%s" % self.tree["variant"], "repository"
            )
            # remove the /repodata from the entry, this should not be there
            repopath = repopath.replace("/repodata", "")
            repos.append(
                dict(
                    repoid=str(self.tree["variant"]),
                    type="variant",
                    path=repopath,
                )
            )
        except (configparser.NoSectionError, configparser.NoOptionError) as e:
            logging.debug(
                ".treeinfo has no repository for variant %s, %s" % (self.parser.url, e)
            )
        try:
            addons = self.parser.get("variant-%s" % self.tree["variant"], "addons")
            addons = addons and addons.split(",") or []
            for addon in addons:
                repopath = self.parser.get("addon-%s" % addon, "repository", "")
                if repopath:
                    repos.append(
                        dict(
                            repoid=addon,
                            type="addon",
                            path=repopath,
                        )
                    )
        except (configparser.NoSectionError, configparser.NoOptionError) as e:
            logging.debug(
                ".treeinfo has no addon repos for %s, %s" % (self.parser.url, e)
            )
        return repos


class TreeInfoRHVH4(TreeInfoMixin, Importer):
    @classmethod
    def is_importer_for(cls, url, options=None):
        parser = Tparser()
        if not parser.parse(url):
            return False
        if parser.get("general", "family") != "RHVH":
            return False
        return parser

    def extend_tree(self):
        kopts = self.tree.get("kernel_options") or ""
        self.tree["kernel_options"] = kopts + " inst.stage2=%s" % self.parser.url
        img_rpm = self._find_image_update_rpm()
        ks_meta = self.tree.get("ks_meta") or ""

        # RHVH assumes that installation is happening based on 'inst.ks' on kernel cmdline
        ks_keyword = "ks_keyword=inst.ks"
        autopart_type = "autopart_type=thinp liveimg={}".format(img_rpm)
        self.tree["ks_meta"] = "{} {} {}".format(ks_meta, autopart_type, ks_keyword)

    def _find_image_update_rpm(self):
        base = dnf.Base()
        base.repos.add_new_repo(uuid.uuid4().hex, base.conf, baseurl=[self.parser.url])
        base.fill_sack(load_system_repo=False)
        pkgs = (
            base.sack.query()
            .filter(name="redhat-virtualization-host-image-update")
            .run()
        )
        if not pkgs:
            raise IncompleteTree("Could not find a valid RHVH rpm")
        return pkgs[0].relativepath

    def find_repos(self):
        return []

    def get_kernel_path(self):
        return self.parser.get("images-%s" % self.tree["arch"], "kernel")

    def get_initrd_path(self):
        return self.parser.get("images-%s" % self.tree["arch"], "initrd")


class TreeInfoRhel7(TreeInfoMixin, Importer):
    # Used in RHEL7 GA.
    # Main variant-* section has a repository and a variants key pointing at
    # addons (represented as additional variants).

    @classmethod
    def is_importer_for(cls, url, options=None):
        parser = Tparser()
        if not parser.parse(url):
            return False
        for r in cls.required:
            if parser.get(r["section"], r["key"], "") == "":
                return False
        for e in cls.excluded:
            if parser.get(e["section"], e["key"], "") != "":
                return False
        if parser.has_option("general", "addons") or not parser.has_section_startswith(
            "variant-"
        ):
            return False
        return parser

    def find_repos(self):
        repos = []
        try:
            addons = self.parser.get("variant-%s" % self.tree["variant"], "variants")
            addons = addons.split(",")
            for addon in addons:
                addon_section = "variant-%s" % addon
                addon_type = self.parser.get(addon_section, "type", "")
                # The type should be self-evident, but let's double check
                if addon_type == "addon":
                    repopath = self.parser.get(addon_section, "repository", "")
                    if repopath:
                        repos.append(
                            dict(
                                repoid=self.parser.get(addon_section, "id"),
                                type="addon",
                                path=repopath,
                            )
                        )
        except (configparser.NoSectionError, configparser.NoOptionError) as e:
            logging.debug("no addon repos for %s, %s" % (self.parser.url, e))
        return repos

    def get_kernel_path(self):
        return self.parser.get("images-%s" % self.tree["arch"], "kernel")

    def get_initrd_path(self):
        return self.parser.get("images-%s" % self.tree["arch"], "initrd")


class TreeInfoRhel(TreeInfoMixin, Importer):
    # Only used in RHEL7 prior to GA?!?
    # No variant-* sections, general has repository key, and addons key
    # pointing at addon-* sections.
    """
    [addon-HighAvailability]
    id = HighAvailability
    name = High Availability
    repository = addons/HighAvailability
    uid = Server-HighAvailability

    [addon-LoadBalancer]
    id = LoadBalancer
    name = Load Balancer
    repository = addons/LoadBalancer
    uid = Server-LoadBalancer

    [addon-ResilientStorage]
    id = ResilientStorage
    name = Resilient Storage
    repository = addons/ResilientStorage
    uid = Server-ResilientStorage

    [addon-ScalableFileSystem]
    id = ScalableFileSystem
    name = Scalable Filesystem Support
    repository = addons/ScalableFileSystem
    uid = Server-ScalableFileSystem

    [general]
    addons = HighAvailability,LoadBalancer,ResilientStorage,ScalableFileSystem
    arch = x86_64
    family = Red Hat Enterprise Linux
    version = 7.0
    variant = Server
    timestamp =
    name = RHEL-7.0-20120201.0
    repository =

    [images-x86_64]
    boot.iso = images/boot.iso
    initrd = images/pxeboot/initrd.img
    kernel = images/pxeboot/vmlinuz

    [images-xen]
    initrd = images/pxeboot/initrd.img
    kernel = images/pxeboot/vmlinuz

    """

    @classmethod
    def is_importer_for(cls, url, options=None):
        parser = Tparser()
        if not parser.parse(url):
            return False
        for r in cls.required:
            if parser.get(r["section"], r["key"], "") == "":
                return False
        for e in cls.excluded:
            if parser.get(e["section"], e["key"], "") != "":
                return False
        if parser.get("images-%s" % parser.get("general", "arch"), "kernel", "") == "":
            return False
        if parser.get("images-%s" % parser.get("general", "arch"), "initrd", "") == "":
            return False
        if not parser.has_option(
            "general", "repository"
        ) or parser.has_section_startswith("variant-"):
            return False
        # Arm uses a different importer because of all the kernel types.
        if parser.get("general", "arch") in ["arm", "armhfp"]:
            return False
        return parser

    def find_repos(self):
        """
        using info from .treeinfo find addon repos
        """
        repos = []
        repos.append(
            dict(
                repoid="distro",
                type="distro",
                path=self.parser.get("general", "repository"),
            )
        )
        try:
            addons = self.parser.get("general", "addons")
            addons = addons and addons.split(",") or []
            for addon in addons:
                repopath = self.parser.get("addon-%s" % addon, "repository", "")
                if repopath:
                    repos.append(
                        dict(
                            repoid=addon,
                            type="addon",
                            path=repopath,
                        )
                    )
        except (configparser.NoSectionError, configparser.NoOptionError) as e:
            logging.debug("no addon repos for %s, %s" % (self.parser.url, e))
        return repos

    def get_kernel_path(self):
        return self.parser.get("images-%s" % self.tree["arch"], "kernel")

    def get_initrd_path(self):
        return self.parser.get("images-%s" % self.tree["arch"], "initrd")


class TreeInfoRhelArm(TreeInfoRhel, Importer):
    """
    [addon-HighAvailability]
    id = HighAvailability
    name = High Availability
    repository = addons/HighAvailability
    uid = Server-HighAvailability

    [addon-LoadBalancer]
    id = LoadBalancer
    name = Load Balancer
    repository = addons/LoadBalancer
    uid = Server-LoadBalancer

    [addon-ResilientStorage]
    id = ResilientStorage
    name = Resilient Storage
    repository = addons/ResilientStorage
    uid = Server-ResilientStorage

    [addon-ScalableFileSystem]
    id = ScalableFileSystem
    name = Scalable Filesystem Support
    repository = addons/ScalableFileSystem
    uid = Server-ScalableFileSystem

    [general]
    addons = HighAvailability,LoadBalancer,ResilientStorage,ScalableFileSystem
    arch = x86_64
    family = Red Hat Enterprise Linux
    version = 7.0
    variant = Server
    timestamp =
    name = RHEL-7.0-20120201.0
    repository =

    [images-x86_64]
    boot.iso = images/boot.iso
    initrd = images/pxeboot/initrd.img
    kernel = images/pxeboot/vmlinuz

    [images-xen]
    initrd = images/pxeboot/initrd.img
    kernel = images/pxeboot/vmlinuz

    """

    @classmethod
    def is_importer_for(cls, url, options=None):
        parser = Tparser()
        if not parser.parse(url):
            return False
        for r in cls.required:
            if parser.get(r["section"], r["key"], "") == "":
                return False
        for e in cls.excluded:
            if parser.get(e["section"], e["key"], "") != "":
                return False
        if parser.get("images-%s" % parser.get("general", "arch"), "kernel", "") == "":
            return False
        if parser.get("images-%s" % parser.get("general", "arch"), "initrd", "") == "":
            return False
        if not parser.has_option(
            "general", "repository"
        ) or parser.has_section_startswith("variant-"):
            return False
        # Arm uses a different importer because of all the kernel types.
        if parser.get("general", "arch") not in ["arm", "armhfp"]:
            return False
        return parser

    def get_kernel_path(self, kernel_type=None):
        if kernel_type:
            kernel_type = "%s-" % kernel_type
        else:
            kernel_type = ""
        return self.parser.get(
            "images-%s%s" % (kernel_type, self.tree["arch"]), "kernel"
        )

    def get_initrd_path(self, kernel_type=None):
        if kernel_type:
            kernel_type = "%s-" % kernel_type
        else:
            kernel_type = ""
        return self.parser.get(
            "images-%s%s" % (kernel_type, self.tree["arch"]), "initrd"
        )

    def get_uimage_path(self, kernel_type=None):
        if kernel_type:
            kernel_type = "%s-" % kernel_type
        else:
            kernel_type = ""
        return self.parser.get(
            "images-%s%s" % (kernel_type, self.tree["arch"]), "uimage", ""
        )

    def get_uinitrd_path(self, kernel_type=None):
        if kernel_type:
            kernel_type = "%s-" % kernel_type
        else:
            kernel_type = ""
        return self.parser.get(
            "images-%s%s" % (kernel_type, self.tree["arch"]), "uinitrd", ""
        )

    def get_images(self):
        images = []
        images.append(dict(type="kernel", path=self.get_kernel_path()))
        images.append(dict(type="initrd", path=self.get_initrd_path()))
        uimage = self.get_uimage_path()
        if uimage:
            images.append(dict(type="uimage", path=uimage))
        uinitrd = self.get_uinitrd_path()
        if uinitrd:
            images.append(dict(type="uinitrd", path=uinitrd))
        kernel_type_string = self.parser.get(self.tree["arch"], "platforms", "")
        kernel_types = map(
            lambda item: item.strip(),
            kernel_type_string and kernel_type_string.split(",") or [],
        )
        for kernel_type in kernel_types:
            images.append(
                dict(
                    type="kernel",
                    kernel_type=kernel_type,
                    path=self.get_kernel_path(kernel_type=kernel_type),
                )
            )
            images.append(
                dict(
                    type="uimage",
                    kernel_type=kernel_type,
                    path=self.get_uimage_path(kernel_type=kernel_type),
                )
            )
            images.append(
                dict(
                    type="initrd",
                    kernel_type=kernel_type,
                    path=self.get_initrd_path(kernel_type=kernel_type),
                )
            )
            images.append(
                dict(
                    type="uinitrd",
                    kernel_type=kernel_type,
                    path=self.get_uinitrd_path(kernel_type=kernel_type),
                )
            )
        return images


class NakedTree(Importer):
    @classmethod
    def is_importer_for(cls, url, options=None):
        if not options:
            return False
        if not options.kernel:
            return False
        if not options.initrd:
            return False
        if not options.name:
            return False
        if not options.family:
            return False
        if not options.version:
            return False
        if not options.arch:
            return False
        return True

    def check_input(self, options):
        self.check_variants(options.variant, multiple=False)
        self.check_arches(options.arch, multiple=False)

    def process(self, urls, options, repos=[]):
        self.scheduler = SchedulerProxy(options)
        self.tree = dict()

        urls = [os.path.join(url, "") for url in urls]
        self.tree["urls"] = urls
        if not options.preserve_install_options:
            self.tree["kernel_options"] = options.kopts
            self.tree["kernel_options_post"] = options.kopts_post
            self.tree["ks_meta"] = options.ks_meta
        family = options.family
        version = options.version
        self.tree["name"] = options.name
        try:
            self.tree["variant"] = options.variant[0]
        except IndexError:
            self.tree["variant"] = ""
        try:
            self.tree["arch"] = options.arch[0]
        except IndexError:
            self.tree["arch"] = ""
        self.tree["tree_build_time"] = options.buildtime or time.time()
        self.tree["tags"] = options.tags
        self.tree["osmajor"] = "%s%s" % (family, version.split(".")[0])
        if version.find(".") != -1:
            self.tree["osminor"] = version.split(".")[1]
        else:
            self.tree["osminor"] = "0"

        self.tree["arches"] = options.arch
        self.tree["repos"] = repos

        # Add install images
        self.tree["images"] = []
        self.tree["images"].append(dict(type="kernel", path=options.kernel))
        self.tree["images"].append(dict(type="initrd", path=options.initrd))

        if options.json:
            print(json.dumps(self.tree))
        logging.debug("\n%s" % pprint.pformat(self.tree))
        try:
            self.add_to_beaker()
            logging.info("%s added to beaker." % self.tree["name"])
        except (xmlrpc_client.Fault, socket.error) as e:
            raise BX("failed to add %s to beaker: %s" % (self.tree["name"], e))

    def add_to_beaker(self):
        self.scheduler.add_distro(self.tree)


def Build(url, options=None):
    # Try all other importers before trying NakedTree
    for cls in Importer.__subclasses__() + [NakedTree]:
        parser = cls.is_importer_for(url, options)
        if parser:
            logging.debug("\tImporter %s Matches", cls.__name__)
            logging.info("Attempting to import: %s", url)
            return cls(parser)
        else:
            logging.debug("\tImporter %s does not match", cls.__name__)
    raise BX("No valid importer found for %s" % url)


_primary_methods = [
    "http",
    "https",
    "ftp",
]


def _get_primary_url(urls):
    """Return primary method used to import distro

    Primary method is what we use to import the distro, we look for
            .composeinfo or .treeinfo at that location.  Because of this
             nfs can't be the primary install method.
    """
    for url in urls:
        method = url.split(":", 1)[0]
        if method in _primary_methods:
            primary = url
            return primary
    return None


def _get_url_by_scheme(urls, scheme):
    """Return the first url that matches the given scheme"""
    for url in urls:
        method = url.split(":", 1)[0]
        if method == scheme:
            return url
    return None


def main():
    usage = "usage: %prog [options] distro_url [distro_url] [distro_url]"
    description = """Imports distro(s) from the given distro_url.  Valid distro_urls are nfs://, http:// and ftp://.  A primary distro_url of either http:// or ftp:// must be specified. In order for an import to succeed a .treeinfo or a .composeinfo must be present at the distro_url or you can do what is called a "naked" import if you specify the following arguments: --family, --version, --name, --arch, --kernel, --initrd. Only one tree can be imported at a time when doing a naked import."""

    parser = OptionParser(usage=usage, description=description)
    parser.add_option(
        "-j",
        "--json",
        default=False,
        action="store_true",
        help="Prints the tree to be imported, in JSON format",
    )
    parser.add_option(
        "-c",
        "--add-distro-cmd",
        default="/var/lib/beaker/addDistro.sh",
        help="Command to run to add a new distro",
    )
    parser.add_option(
        "-n",
        "--name",
        default=None,
        help="Alternate name to use, otherwise we read it from .treeinfo",
    )
    parser.add_option(
        "-t",
        "--tag",
        default=[],
        action="append",
        dest="tags",
        help="Additional tags to add",
    )
    parser.add_option(
        "-r",
        "--run-jobs",
        action="store_true",
        default=False,
        help="Run automated Jobs",
    )
    parser.add_option(
        "-v", "--debug", action="store_true", default=False, help="show debug messages"
    )
    parser.add_option(
        "--dry-run",
        action="store_true",
        help="Do not actually add any distros to beaker",
    )
    parser.add_option(
        "-q", "--quiet", action="store_true", default=False, help="less messages"
    )
    parser.add_option("--family", default=None, help="Specify family")
    parser.add_option(
        "--variant",
        action="append",
        default=[],
        help="Specify variant. Multiple values are valid when importing a compose >=RHEL7",
    )
    parser.add_option("--version", default=None, help="Specify version")
    parser.add_option(
        "--kopts", default=None, help="add kernel options to use for install"
    )
    parser.add_option(
        "--kopts-post", default=None, help="add kernel options to use for after install"
    )
    parser.add_option(
        "--ks-meta", default=None, help="add variables to use in kickstart templates"
    )
    parser.add_option(
        "--preserve-install-options",
        action="store_true",
        default=False,
        help=(
            "Do not overwrite the 'Install Options' (Kickstart "
            "Metadata, Kernel Options, & Kernel Options Post) already "
            "stored for the distro. This option can not be used with "
            "any of --kopts, --kopts-post, or --ks-meta"
        ),
    )
    parser.add_option(
        "--buildtime", default=None, type=float, help="Specify build time"
    )
    parser.add_option(
        "--arch",
        action="append",
        default=[],
        help="Specify arch. Multiple values are valid when importing a compose",
    )
    parser.add_option(
        "--ignore-missing-tree-compose",
        dest="ignore_missing",
        action="store_true",
        default=False,
        help="If a specific tree within a compose is missing, do not print any errors",
    )
    group = OptionGroup(
        parser,
        "Naked Tree Options",
        "These options only apply when importing without a .treeinfo or .composeinfo",
    )
    group.add_option(
        "--kernel", default=None, help="Specify path to kernel (relative to distro_url)"
    )
    group.add_option(
        "--initrd", default=None, help="Specify path to initrd (relative to distro_url)"
    )
    group.add_option(
        "--lab-controller",
        default="http://localhost:8000",
        help="Specify which lab controller to import to. Defaults to http://localhost:8000",
    )
    parser.add_option_group(group)

    (opts, urls) = parser.parse_args()

    logging.getLogger().setLevel(logging.DEBUG)
    if opts.debug:
        log_level = logging.DEBUG
    elif opts.quiet:
        log_level = logging.CRITICAL
    else:
        log_level = logging.INFO
    log_to_stream(sys.stderr, level=log_level)

    if opts.preserve_install_options:
        if any([opts.kopts, opts.kopts_post, opts.ks_meta]):
            logging.critical(
                "--preserve-install-options can not be used with any of: "
                "--kopt, --kopts-post, or --ks-meta"
            )
            sys.exit(4)

    if not urls:
        logging.critical("No location(s) specified!")
        sys.exit(1)

    primary_url = _get_primary_url(urls)
    if primary_url is None:
        logging.critical(
            "missing a valid primary installer! %s, are valid install methods"
            % " and ".join(_primary_methods)
        )
        sys.exit(2)
    if opts.dry_run:
        logging.info("Dry Run only, no data will be sent to beaker")
    exit_status = []
    try:
        build = Build(primary_url, options=opts)
        try:
            build.check_input(opts)
            exit_status.append(build.process(urls, opts))
        except (configparser.NoSectionError, configparser.NoOptionError) as e:
            logging.critical(str(e))
            sys.exit(3)
    except (xmlrpc_client.Fault, BX) as err:
        logging.critical(err)
        sys.exit(127)
    if opts.run_jobs:
        logging.info("running jobs.")
        build.run_jobs()

    # if the list of exit_status-es contain any non-zero
    # value it means that at least one tree failed to import
    # correctly, and hence set the exit status of the script
    # accordingly
    return bool(any(exit_status))


if __name__ == "__main__":
    sys.exit(main())
