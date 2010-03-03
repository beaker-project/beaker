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
            require = self.doc.createElement('distro_%s' % key.lower())
            require.setAttribute('op', '%s' % op)
            require.setAttribute('value', '%s' % value)
        return require

    def handle_addrepo(self, addrepo):
        """ strip off \ from $ since new system doesn't need escaping """
        self.counter += 1
        repo = self.doc.createElement('repo')
        repo.setAttribute('name','myrepo_%s' % self.counter)
        repo.setAttribute('url','%s' % addrepo.replace('\\$','$'))
        return repo
    
    def handle_hostRequires(self, requires):
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
    
    def handle_recipes(self, recipes):
        for recipe in recipes:
            del_nodes = []
            and_distro = self.doc.createElement('and')
            and_host = self.doc.createElement('and')
            repos = self.doc.createElement('repos')
            for child in recipe.childNodes:
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
                   child.tagName == 'addrepo':
                       del_nodes.append(child)
                       repo = self.handle_addrepo(self.getText(child.childNodes))
                       repos.appendChild(repo)
    
            distro = self.doc.createElement('distroRequires')
            distro.appendChild(and_distro)
            host = self.doc.createElement('hostRequires')
            host.appendChild(and_host)
        
            for child in del_nodes:
                recipe.removeChild(child)
            recipe.appendChild(repos)
            recipe.appendChild(distro)
            recipe.appendChild(host)
    
