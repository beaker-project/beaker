#!/usr/bin/python

import sys
import re
import xml.dom.minidom

__all__ = (
    "Convert",
    "rhts2beaker",
)

def rhts2beaker(jobfile):
    convert = Convert(xml.dom.minidom.parseString(jobfile))
    return convert.toxml()

class Convert(object):

    doc = xml.dom.minidom.Document()
    rhts2beaker = staticmethod(rhts2beaker)

    def __init__(self, jobxml):
        self.counter = 0
        self.jobxml = jobxml

    def toxml(self):
        self.handle_tasks(self.jobxml)
        self.handle_recipes(self.jobxml.getElementsByTagName("recipe"))
        self.handle_recipes(self.jobxml.getElementsByTagName("guestrecipe"))
        return self.jobxml.toxml()

    def getText(self, nodelist):
        rc = ""
        for node in nodelist:
            if node.nodeType == node.TEXT_NODE:
                rc = rc + node.data
        return rc

    def handle_distroRequires(self, requires):
        require = None
        requires_search = re.compile(r'([^\s]+)\s+([^\s]+)\s+([^\s]+)')
        if requires_search.match(requires):
            (dummy, key, op, value, dummy) = requires_search.split(requires)
            if key in ['ARCH', 'FAMILY', 'NAME', 'VARIANT', 'METHOD']:
                require = self.doc.createElement('distro_%s' % key.lower())
                require.setAttribute('value', '%s' % value)
            else:
                require = self.doc.createElement('distro_tag')
                require.setAttribute('value', '%s' % key)
            require.setAttribute('op', '%s' % op)
        return require

    def handle_addrepo(self, addrepo):
        """ process repos """
        self.counter += 1
        repo = self.doc.createElement('repo')
        repo.setAttribute('name','myrepo_%s' % self.counter)
        repo.setAttribute('url','%s' % addrepo)
        return repo
    
    def handle_hostRequires(self, requires):
        require = None
        requires_search = re.compile(r'([^\s]+)\s+([^\s]+)\s+([^\s]+)')
        if requires_search.match(requires):
            (dummy, key, op, value, dummy) = requires_search.split(requires)
            if key == 'ARCH':
                require = self.doc.createElement('arch')
            elif key == 'LABCONTROLLER':
                require = self.doc.createElement('hostlabcontroller')
            elif key == 'HOSTNAME':
                require = self.doc.createElement('hostname')
            elif key == 'MEMORY':
                require = self.doc.createElement('memory')
            elif key == 'PROCESSORS':
                require = self.doc.createElement('cpu_count')
            elif key == 'FAMILY':
                # FAMILY doesn't make sense to beaker
                require = None
            else:
                require = self.doc.createElement('key_value')
                require.setAttribute('key', '%s' % key)
            if require:
                require.setAttribute('op', '%s' % op)
                require.setAttribute('value', '%s' % value)
        return require
    
    def handle_tasks(self, nodes):
        for child in nodes.childNodes:
            if child.nodeType == child.ELEMENT_NODE:
                if child.tagName == 'test':
                    child.tagName = 'task'
                else:
                    self.handle_tasks(child)
    
    def handle_partition(self, partition):
        fs = None
        type = 'part'
        name = 'testarea'
        size = '5'
        for child in partition.childNodes:
            if child.nodeName == 'type':
                type = self.getText(child.childNodes)
            if child.nodeName == 'name':
                name = self.getText(child.childNodes)
            if child.nodeName == 'size':
                size = self.getText(child.childNodes)
            if child.nodeName == 'fs':
                fs = self.getText(child.childNodes)
        part_str = '%s:%s:%s' % (name,type,size)
        if fs:
            part_str = '%s:%s' % (part_str, fs)
        return part_str

    def handle_recipes(self, recipes):
        for recipe in recipes:
            del_nodes = []
            partitions = []
            and_distro = self.doc.createElement('and')
            and_host = self.doc.createElement('and')
            repos = self.doc.createElement('repos')
            kernel_options = ''
            if 'kernel_options' in recipe._attrs:
                kernel_options = '%s ' % recipe.getAttribute('kernel_options')
            if 'bootargs' in recipe._attrs:
                kernel_options = '%s%s' % (kernel_options, recipe.getAttribute('bootargs'))
                recipe.setAttribute('kernel_options',kernel_options)
                recipe.removeAttribute('bootargs')
            for child in recipe.childNodes:
                if child.nodeType == child.ELEMENT_NODE and \
                   child.tagName == 'bootargs':
                       del_nodes.append(child)
                       kernel_options = '%s%s' % (kernel_options, self.getText(child.childNodes))
                       recipe.setAttribute('kernel_options' , kernel_options)
                if child.nodeType == child.ELEMENT_NODE and \
                   child.tagName == 'distroRequires':
                       del_nodes.append(child)
                       require = self.handle_distroRequires(self.getText(child.childNodes))
                       if require:
                           and_distro.appendChild(require)
    
                if child.nodeType == child.ELEMENT_NODE and \
                   child.tagName == 'hostRequires':
                       del_nodes.append(child)
                       require = self.handle_hostRequires(self.getText(child.childNodes))
                       if require:
                           and_host.appendChild(require)
    
                if child.nodeType == child.ELEMENT_NODE and \
                   child.tagName == 'partition':
                       del_nodes.append(child)
                       partitions.append(self.handle_partition(child))
                   
                if child.nodeType == child.ELEMENT_NODE and \
                   child.tagName == 'addrepo':
                       del_nodes.append(child)
                       repo = self.handle_addrepo(self.getText(child.childNodes))
                       repos.appendChild(repo)
    
            distro = self.doc.createElement('distroRequires')
            distro.appendChild(and_distro)
            host = self.doc.createElement('hostRequires')
            host.appendChild(and_host)
            if partitions:
                ks_meta = ''
                if recipe.hasAttribute('ks_meta'):
                    ks_meta = '%s ' % recipe.getAttribute('ks_meta')
                recipe.setAttribute('ks_meta','%spartitions=%s' % (ks_meta, ';'.join(partitions)))
        
            for child in del_nodes:
                recipe.removeChild(child)
            recipe.appendChild(repos)
            recipe.appendChild(distro)
            recipe.appendChild(host)
    
