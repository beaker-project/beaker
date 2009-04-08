#!/usr/bin/python

# Medusa - 
#
# Copyright (C) 2008 bpeck@redhat.com
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

import xmltramp
import os
import sys
import pkg_resources
pkg_resources.require("SQLAlchemy>=0.3.10")
from medusa.model import *
from medusa.commands import ConfigurationError
from turbogears.database import session
from os.path import dirname, exists, join
from os import getcwd
import turbogears

class ElementWrapper(object):
    # Operator translation table
    op_table = { '=' : '__eq__',
                 '==' : '__eq__',
                 '!=' : '__ne__',
                 '>'  : '__gt__',
                 '>=' : '__ge__',
                 '<'  : '__lt__',
                 '<=' : '__le__'}

    # Alias counter for each sub table
    alias = { 'key_value'  : 0,
              'distro_tag' : 0 }

    @classmethod
    def get_subclass(cls, element):
        name = element._name

        if name in subclassDict:
            return subclassDict[name]
        return UnknownElement
    
    def __init__(self, wrappedEl):
        self.wrappedEl = wrappedEl

    def __repr__(self):
        return '%s("%s")' % (self.__class__, repr(self.wrappedEl))

    def __iter__(self):
        for child in self.wrappedEl:
            if isinstance(child, xmltramp.Element):
                yield ElementWrapper.get_subclass(child)(child)
            else:
                yield child

    def __getitem__(self, n):
        child = self.wrappedEl[n]
        if isinstance(child, xmltramp.Element):
            return ElementWrapper.get_subclass(child)(child)
        else:
            return child

    def recurse(self, visitor):
        visitor.visit(self)
        for child in self:
            child.recurse(visitor)

    def get_text(self):
        # Simple API for extracting textual content below this node, stripping
        # out any markup
        #print 'get_text: %s' % self
        result = ''
        for child in self:
            if isinstance(child, ElementWrapper):
                # Recurse:
                result += child.get_text()
            else:
                #print child
                result += child

        return result

    def get_xml_attr(self, attr, typeCast, defaultValue):
        if attr in self.wrappedEl._attrs:
            return typeCast(self.wrappedEl(attr))
        else:
            return defaultValue

class UnknownElement(ElementWrapper):
    pass

class XmlHost(ElementWrapper):
    pass

class XmlDistro(ElementWrapper):
    pass

class XmlDistroArch(ElementWrapper):
    """
    Filer Distro based on Arch
    """
    def filter(self):
        op = self.op_table[self.get_xml_attr('op', unicode, '==')]
        value = self.get_xml_attr('value', unicode, None)
        query = None
        if op and value:
            query = and_(distro_table.c.arch_id == arch_table.c.id,
                         getattr(arch_table.c.arch, op)(value))
        return ([], query)
            
class XmlDistroFamily(ElementWrapper):
    """
    Filter Distro based on Family
    """
    def filter(self):
        op = self.op_table[self.get_xml_attr('op', unicode, '==')]
        value = self.get_xml_attr('value', unicode, None)
        query = None
        if op and value:
            query = and_(distro_table.c.osversion_id == osversion_table.c.id,
                         osversion_table.c.osmajor_id == osmajor_table.c.id,
                         getattr(osmajor_table.c.osmajor, op)(value))
        return ([], query)

class XmlDistroTag(ElementWrapper):
    """
    Filter Distro based on Tag
    """
    def filter(self):
        op = self.op_table[self.get_xml_attr('op', unicode, '==')]
        value = self.get_xml_attr('value', unicode, None)
        query = None
        if op and value:
            query = and_(
                      distro_table.c.id == distro_tag_map.c.distro_id,
                      distro_tag_table.c.id == distro_tag_map.c.distro_tag_id,
                      getattr(distro_tag_table.c.tag, op)(value)
                    )
        return ([], query)

class XmlDistroVariant(ElementWrapper):
    """
    Filter Distro based on Tag
    """
    def filter(self):
        op = self.op_table[self.get_xml_attr('op', unicode, '==')]
        value = self.get_xml_attr('value', unicode, None)
        query = None
        if op and value:
            query = getattr(distro_table.c.variant, op)(value)
        return ([], query)

class XmlDistroName(ElementWrapper):
    """
    Filter Distro based on Tag
    """
    def filter(self):
        op = self.op_table[self.get_xml_attr('op', unicode, '==')]
        value = self.get_xml_attr('value', unicode, None)
        query = None
        if op and value:
            query = getattr(distro_table.c.name, op)(value)
        return ([], query)

class XmlDistroVirt(ElementWrapper):
    """
    Filter Distro based on Virt
    """
    def filter(self):
        op = self.op_table[self.get_xml_attr('op', unicode, '==')]
        value = self.get_xml_attr('value', bool, False)
        query = None
        if op:
            query = getattr(distro_table.c.virt, op)(value)
        return ([], query)

class XmlSystem(ElementWrapper):
    """
    Filter 
    """
    def filter(self):
        key = self.get_xml_attr('key', unicode, None)
        op = self.op_table[self.get_xml_attr('op', unicode, '==')]
        value = self.get_xml_attr('value', unicode, None)
        joins = []
        query = None
        if key and op and value:
            # Filter using the operator we looked up
            query = getattr(getattr(system_table.c,key), op)(value)
        return (joins, query)

class XmlKeyValue(ElementWrapper):
    """
    Filter based on key_value
    """
    def filter(self):
        key = self.get_xml_attr('key', unicode, None)
        op = self.op_table[self.get_xml_attr('op', unicode, '==')]
        value = self.get_xml_attr('value', unicode, None)
        joins = []
        query = None
        try:
            _key = Key.by_name(key)
        except InvalidRequestError:
            return (joins, False)
        if key and op and value:
            # Alias since we may join on ourselves
            if _key.numeric:
                table = key_value_int_table
            else:
                table = key_value_string_table
            alias = table.alias('key%i' % self.alias['key_value'])
            self.alias['key_value'] += 1

            # Setup the joins
            joins = [alias.c.system_id==system_table.c.id]

            # Filter using the operator we looked up
            query = and_(alias.c.key_id==_key.id,
                         getattr(alias.c.key_value, op)(value))
        return (joins, query)

class XmlAnd(ElementWrapper):
    """
    Combine sub queries into and_ statements
    """
    def filter(self):
        queries = []
        joins = []
        for child in self:
            (join, query) = child.filter()
            queries.append(query)
            joins.extend(join)
        return (joins, and_(*queries))

class XmlOr(ElementWrapper):
    """
    Combine sub queries into or_ statements
    """
    def filter(self):
        queries = []
        joins = []
        for child in self:
            (join, query) = child.filter()
            queries.append(query)
            joins.extend(join)
        return (joins, or_(*queries))

class XmlAutoProv(ElementWrapper):
    """
    Verify that a system has the ability to power cycle and is connected to a 
    lab controller
    """
    def filter(self):
        value = self.get_xml_attr('value', unicode, False)
        joins = []
        query = None
        if value:
            joins = [power_table.c.system_id == system_table.c.id]
            query = system_table.c.lab_controller_id != None
        return (joins, query)

class XmlHostLabController(ElementWrapper):
    """
    Pick a system from this lab controller
    """
    def filter(self):
        value = self.get_xml_attr('value', unicode, None)
        joins = []
        query = None
        if value:
            joins = [system_table.c.lab_controller_id == lab_controller_table.c.id]
            query = lab_controller_table.c.fqdn == value
        return (joins, query)

class XmlDistroLabController(ElementWrapper):
    """
    Pick a system from this lab controller
    """
    def filter(self):
        value = self.get_xml_attr('value', unicode, None)
        joins = []
        query = None
        if value:
            joins = [distro_table.c.id == lab_controller_distro_map.c.distro_id,
                     lab_controller_table.c.id == lab_controller_distro_map.c.lab_controller_id]
            query = lab_controller_table.c.fqdn == value
        return (joins, query)

class XmlSystemType(ElementWrapper):
    """
    Pick a system with the correct system type.
    """
    def filter(self):
        value = self.get_xml_attr('value', unicode, None)
        joins = []
        query = None
        if value:
            joins = [system_table.c.type_id == system_type_table.c.id]
            query = system_type_table.c.type == value
        return (joins, query)

class XmlHostName(ElementWrapper):
    """
    Pick a system wth the correct hostname.
    """
    def filter(self):
        op = self.op_table[self.get_xml_attr('op', unicode, '==')]
        value = self.get_xml_attr('value', unicode, None)
        joins = []
        query = None
        if value:
            query = getattr(system_table.c.fqdn, op)(value)
        return (joins, query)

class XmlMemory(ElementWrapper):
    """
    Pick a system wth the correct amount of memory.
    """
    def filter(self):
        op = self.op_table[self.get_xml_attr('op', unicode, '==')]
        value = self.get_xml_attr('value', int, None)
        joins = []
        query = None
        if value:
            query = getattr(system_table.c.memory, op)(value)
        return (joins, query)

class XmlCpuCount(ElementWrapper):
    """
    Pick a system with the correct amount of processors.
    """
    def filter(self):
        op = self.op_table[self.get_xml_attr('op', unicode, '==')]
        value = self.get_xml_attr('value', int, None)
        joins = []
        query = None
        if value:
            joins = [system_table.c.id == cpu_table.c.system_id]
            query = getattr(cpu_table.c.processors, op)(value)
        return (joins, query)

subclassDict = {
    'host'                : XmlHost,
    'distro'              : XmlDistro,
    'key_value'           : XmlKeyValue,
    'auto_prov'           : XmlAutoProv,
    'and'                 : XmlAnd,
    'or'                  : XmlOr,
    'distro_arch'         : XmlDistroArch,
    'distro_family'       : XmlDistroFamily,
    'distro_variant'      : XmlDistroVariant,
    'distro_name'         : XmlDistroName,
    'distro_tag'          : XmlDistroTag,
    'distro_virt'         : XmlDistroVirt,
    'hostlabcontroller'   : XmlHostLabController,
    'distrolabcontroller' : XmlDistroLabController,
    'system_type'         : XmlSystemType,
    'system'              : XmlSystem,
    'memory'              : XmlMemory,
    'cpu_count'           : XmlCpuCount,
    'hostname'            : XmlHostName,
    }

if __name__=='__main__':
    setupdir = dirname(dirname(__file__))
    curdir = getcwd()
    if exists(join(setupdir, "setup.py")):
        configfile = join(setupdir, "dev.cfg")
    elif exists(join(curdir, "prod.cfg")):
        configfile = join(curdir, "prod.cfg")
    else:
        try:
            configfile = pkg_resources.resource_filename(
              pkg_resources.Requirement.parse("medusa"),
                "config/default.cfg")
        except pkg_resources.DistributionNotFound:
            raise ConfigurationError("Could not find default configuration.")

    turbogears.update_config(configfile=configfile,
        modulename="medusa.config")

    file = sys.argv[1]
    FH = open(file,"r")
    xml = FH.read()
    FH.close()

    myRequires = xmltramp.parse(xml)
    distros    = ElementWrapper(myRequires.distro)

    queries = []
    joins   = []
    for child in distros:
        if callable(getattr(child, 'filter')):
            (join, query) = child.filter()
            queries.append(query)
            joins.extend(join)
    distro = Distro.query()
    if joins:
        distro = distro.filter(and_(*joins))
    if queries:
        distro = distro.filter(and_(*queries))
    distro = distro.first()

    user = User.query()[0]
    system = distro.systems(user)


    queries = []
    joins   = []
    systems    = ElementWrapper(myRequires.host)
    for child in systems:
        if callable(getattr(child, 'filter')):
            (join, query) = child.filter()
            queries.append(query)
            joins.extend(join)
    if joins:
        system = system.filter(and_(*joins))
    if queries:
        system = system.filter(and_(*queries))
    print system.all()
