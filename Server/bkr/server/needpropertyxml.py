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
from bkr.server.model import *
from turbogears.database import session
import turbogears
from sqlalchemy import or_, and_
from sqlalchemy.orm.exc import NoResultFound

class ElementWrapper(object):
    # Operator translation table
    op_table = { '=' : '__eq__',
                 '==' : '__eq__',
                 '!=' : '__ne__',
                 '>'  : '__gt__',
                 '>=' : '__ge__',
                 '<'  : '__lt__',
                 '<=' : '__le__'}

    @classmethod
    def get_subclass(cls, element):
        name = element._name

        if name in subclassDict:
            return subclassDict[name]
        return UnknownElement
    
    def __init__(self, wrappedEl, alias=None):
        self.wrappedEl = wrappedEl
        if alias:
            self.alias = alias
        else:
            ## Alias counter for each sub table
            self.alias = { 'key_value'  : 0,
                           'arch'       : {},
                           'distro_tag' : 0,
                           'system_group' : 0,
                         }


    def __repr__(self):
        return '%s("%s")' % (self.__class__, repr(self.wrappedEl))

    def __iter__(self):
        for child in self.wrappedEl:
            if isinstance(child, xmltramp.Element):
                yield ElementWrapper.get_subclass(child)(child,self.alias)
            else:
                yield child

    def __getitem__(self, n):
        child = self.wrappedEl[n]
        if isinstance(child, xmltramp.Element):
            return ElementWrapper.get_subclass(child)(child,self.alias)
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
    Filter distro tree based on Aarch
    """
    def filter(self, joins):
        op = self.op_table[self.get_xml_attr('op', unicode, '==')]
        value = self.get_xml_attr('value', unicode, None)
        query = None
        if op and value:
            joins = joins.join(DistroTree.arch)
            query = getattr(Arch.arch, op)(value)
        return (joins, query)

class XmlDistroFamily(ElementWrapper):
    """
    Filter distro tree based on Family
    """
    def filter(self, joins):
        op = self.op_table[self.get_xml_attr('op', unicode, '==')]
        value = self.get_xml_attr('value', unicode, None)
        query = None
        if op and value:
            joins = joins.join(DistroTree.distro, Distro.osversion, OSVersion.osmajor)
            query = getattr(OSMajor.osmajor, op)(value)
        return (joins, query)

class XmlDistroTag(ElementWrapper):
    """
    Filter distro tree based on Tag
    """

    op_table = { '=' : '__eq__',
                 '==' : '__eq__',
                 '!=' : '__ne__'}

    def filter(self, joins):
        op = self.op_table[self.get_xml_attr('op', unicode, '==')]
        value = self.get_xml_attr('value', unicode, None)
        query = None
        if value:
            joins = joins.join(DistroTree.distro)
            if op == '__ne__':
                query = not_(Distro._tags.any(DistroTag.tag == value))
            else:
                query = Distro._tags.any(getattr(DistroTag.tag, op)(value))
        return (joins, query)

class XmlDistroVariant(ElementWrapper):
    """
    Filter distro tree based on variant
    """
    def filter(self, joins):
        op = self.op_table[self.get_xml_attr('op', unicode, '==')]
        value = self.get_xml_attr('value', unicode, None)
        query = None
        if op and value:
            query = getattr(DistroTree.variant, op)(value)
        return (joins, query)

class XmlDistroName(ElementWrapper):
    """
    Filter distro tree based on distro name
    """
    def filter(self, joins):
        op = self.op_table[self.get_xml_attr('op', unicode, '==')]
        value = self.get_xml_attr('value', unicode, None)
        query = None
        if op and value:
            joins = joins.join(DistroTree.distro)
            query = getattr(Distro.name, op)(value)
        return (joins, query)

class XmlDistroVirt(ElementWrapper):
    """
    This is a noop, since we don't have virt distros anymore.
    """
    def filter(self, joins):
        return (joins, None)

class XmlSystem(ElementWrapper):
    """
    Filter 
    """
    def filter(self, joins):
        key = self.get_xml_attr('key', unicode, None)
        op = self.op_table[self.get_xml_attr('op', unicode, '==')]
        value = self.get_xml_attr('value', unicode, None)
        query = None
        if key and op and value:
            # Filter using the operator we looked up
            query = getattr(getattr(System, key), op)(value)
        return (joins, query)


class XmlGroup(ElementWrapper):
    """
    Filter based on group
    """

    op_table = { '=' : '__eq__',
                 '==' : '__eq__',
                 '!=' : '__ne__'}

    def filter(self, joins):
        op = self.op_table[self.get_xml_attr('op', unicode, '==')]
        value = self.get_xml_attr('value', unicode, None)
        if value:
            # - '==' - search for system which is member of given group
            # - '!=' - search for system which is not member of given group
            try:
                group = Group.by_name(value)
            except NoResultFound:
                return (joins, None)
            if op == '__eq__':
                query = System.groups.contains(group)
            else:
                query = not_(System.groups.contains(group))
        else:
            # - '!=' - search for system which is member of any group
            # - '==' - search for system which is not member of any group
            if op == '__eq__':
                query = System.group_assocs == None
            else:
                query = System.group_assocs != None
        return (joins, query)


class XmlKeyValue(ElementWrapper):
    """
    Filter based on key_value
    """
    def filter(self, joins):
        key = self.get_xml_attr('key', unicode, None)
        op = self.op_table[self.get_xml_attr('op', unicode, '==')]
        value = self.get_xml_attr('value', unicode, None)
        try:
            _key = Key.by_name(key)
        except NoResultFound:
            return (joins, None)
        if op not in ('__eq__', '__ne__') and not value:
            # makes no sense, discard
            return (joins, None)
        if _key.numeric:
            key_value_cls = Key_Value_Int
            collection = System.key_values_int
        else:
            key_value_cls = Key_Value_String
            collection = System.key_values_string
        # <key_value key="THING" op="==" /> -- must have key with any value
        # <key_value key="THING" op="==" value="VALUE" /> -- must have key with given value
        # <key_value key="THING" op="!=" /> -- must not have key
        # <key_value key="THING" op="!=" value="VALUE" /> -- must not have key with given value
        if op == '__ne__' and value is None:
            query = not_(collection.any(key_value_cls.key == _key))
        elif op == '__ne__':
            query = not_(collection.any(and_(
                    key_value_cls.key == _key,
                    key_value_cls.key_value == value)))
        elif op == '__eq__' and value is None:
            query = collection.any(key_value_cls.key == _key)
        elif op == '__eq__':
            query = collection.any(and_(
                    key_value_cls.key == _key,
                    key_value_cls.key_value == value))
        else:
            query = collection.any(and_(
                    key_value_cls.key == _key,
                    getattr(key_value_cls.key_value, op)(value)))
        return (joins, query)

class XmlAnd(ElementWrapper):
    """
    Combine sub queries into and_ statements
    """
    def filter(self, joins):
        queries = []
        for child in self:
            if callable(getattr(child, 'filter', None)):
                (joins, query) = child.filter(joins)
                if query is not None:
                    queries.append(query)
        if not queries:
            return (joins, None)
        return (joins, and_(*queries))

class XmlOr(ElementWrapper):
    """
    Combine sub queries into or_ statements
    """
    def filter(self, joins):
        queries = []
        for child in self:
            if callable(getattr(child, 'filter', None)):
                (joins, query) = child.filter(joins)
                if query is not None:
                    queries.append(query)
        if not queries:
            return (joins, None)
        return (joins, or_(*queries))

class XmlAutoProv(ElementWrapper):
    """
    Verify that a system has the ability to power cycle and is connected to a 
    lab controller
    """
    def filter(self, joins):
        value = self.get_xml_attr('value', unicode, False)
        query = None
        if value:
            joins = joins.join(System.power)
            query = System.lab_controller != None
        return (joins, query)

class XmlHostLabController(ElementWrapper):
    """
    Pick a system from this lab controller
    """
    op_table = { '=' : '__eq__',
                 '==' : '__eq__',
                 '!=' : '__ne__'}
    def filter(self, joins):
        op = self.op_table[self.get_xml_attr('op', unicode, '==')]
        value = self.get_xml_attr('value', unicode, None)
        if not value:
            return (joins, None)
        joins = joins.join(System.lab_controller)
        query = getattr(LabController.fqdn, op)(value)
        return (joins, query)

class XmlDistroLabController(ElementWrapper):
    """
    Pick a distro tree available on this lab controller
    """
    op_table = { '=' : '__eq__',
                 '==' : '__eq__',
                 '!=' : '__ne__'}
    def filter(self, joins):
        op = self.op_table[self.get_xml_attr('op', unicode, '==')]
        value = self.get_xml_attr('value', unicode, None)
        if not value:
            return (joins, None)
        if op == '__eq__':
            query = exists([1],
                    from_obj=[distro_tree_lab_controller_map.join(lab_controller_table)])\
                    .where(LabControllerDistroTree.distro_tree_id == DistroTree.id)\
                    .where(LabController.fqdn == value)
        else:
            query = not_(exists([1],
                    from_obj=[distro_tree_lab_controller_map.join(lab_controller_table)])\
                    .where(LabControllerDistroTree.distro_tree_id == DistroTree.id)\
                    .where(LabController.fqdn == value))
        return (joins, query)

class XmlHypervisor(ElementWrapper):
    """ 
    Pick a system based on the hypervisor.
    """
    def filter(self, joins):
        op = self.op_table[self.get_xml_attr('op', unicode, '==')]
        value = self.get_xml_attr('value', unicode, None) or None
        query = None
        if op:
            joins = joins.outerjoin(System.hypervisor)
            query = getattr(Hypervisor.hypervisor, op)(value)
        return (joins, query)

class XmlSystemType(ElementWrapper):
    """
    Pick a system with the correct system type.
    """
    def filter(self, joins):
        value = self.get_xml_attr('value', unicode, None)
        query = None
        if value:
            query = System.type == value
        return (joins, query)

class XmlHostName(ElementWrapper):
    """
    Pick a system wth the correct hostname.
    """
    def filter(self, joins):
        op = self.op_table[self.get_xml_attr('op', unicode, '==')]
        value = self.get_xml_attr('value', unicode, None)
        query = None
        if value:
            query = getattr(System.fqdn, op)(value)
        return (joins, query)

class XmlMemory(ElementWrapper):
    """
    Pick a system wth the correct amount of memory.
    """
    def filter(self, joins):
        op = self.op_table[self.get_xml_attr('op', unicode, '==')]
        value = self.get_xml_attr('value', int, None)
        query = None
        if value:
            query = getattr(System.memory, op)(value)
        return (joins, query)

class XmlCpuCount(ElementWrapper):
    """
    Pick a system with the correct amount of processors.
    """
    def filter(self, joins):
        op = self.op_table[self.get_xml_attr('op', unicode, '==')]
        value = self.get_xml_attr('value', int, None)
        query = None
        if value:
            joins = joins.join(System.cpu)
            query = getattr(Cpu.processors, op)(value)
        return (joins, query)

class XmlArch(ElementWrapper):
    """
    Pick a system with the correct arch
    """

    op_table = { '=' : '__eq__',
                 '==' : '__eq__',
                 '!=' : '__ne__'}

    def filter(self, joins):
        op = self.op_table[self.get_xml_attr('op', unicode, '==')]
        value = self.get_xml_attr('value', unicode, None)
        query = None
        if value:
            # As per XmlGroup above,
            # - '==' - search for system which has given arch
            # - '!=' - search for system which does not have given arch
            try:
                arch = Arch.by_name(value)
            except NoResultFound:
                return (joins, None)
            if op == '__eq__':
                query = System.arch.contains(arch)
            else:
                query = not_(System.arch.contains(arch))
        return (joins, query)

class XmlNumaNodeCount(ElementWrapper):
    """
    Pick a system with the correct number of NUMA nodes.
    """
    def filter(self, joins):
        op = self.op_table[self.get_xml_attr('op', unicode, '==')]
        value = self.get_xml_attr('value', int, None)
        query = None
        if value:
            joins = joins.join(System.numa)
            query = getattr(Numa.nodes, op)(value)
        return (joins, query)

class XmlDevice(ElementWrapper):
    """
    Pick a system with a matching device.
    """

    op_table = { '=' : '__eq__',
                 '==' : '__eq__',
                 '!=' : '__ne__'}

    def filter(self, joins):
        op = self.op_table[self.get_xml_attr('op', unicode, '==')]
        query = None
        filter_clauses = []
        for attr in ['bus', 'driver', 'vendor_id', 'device_id',
                     'subsys_vendor_id', 'subsys_device_id']:
            value = self.get_xml_attr(attr, unicode, None)
            if value:
                filter_clauses.append(getattr(Device, attr) == value)
        if self.get_xml_attr('type', unicode, None):
            filter_clauses.append(Device.device_class.has(
                    DeviceClass.device_class ==
                    self.get_xml_attr('type', unicode, None)))
        if filter_clauses:
            if op == '__eq__':
                query = System.devices.any(and_(*filter_clauses))
            else:
                query = not_(System.devices.any(and_(*filter_clauses)))
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
    'arch'                : XmlArch,
    'numa_node_count'     : XmlNumaNodeCount,
    'group'               : XmlGroup,
    'hypervisor'          : XmlHypervisor,
    'device'              : XmlDevice,
    }

def apply_filter(filter, query):
    if isinstance(filter, basestring):
        filter = ElementWrapper(xmltramp.parse(filter))
    clauses = []
    for child in filter:
        if callable(getattr(child, 'filter', None)):
            (query, clause) = child.filter(query)
            if clause is not None:
                clauses.append(clause)
    if clauses:
        query = query.filter(and_(*clauses))
    return query
