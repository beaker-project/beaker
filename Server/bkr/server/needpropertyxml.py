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

import operator
from sqlalchemy import or_, and_, not_, exists
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.orm import aliased
import datetime
from lxml import etree

from bkr.server.model import (Arch, Distro, DistroTree, DistroTag,
                              OSMajor, OSVersion, Group, System, User,
                              Key, Key_Value_Int, Key_Value_String,
                              LabController, distro_tree_lab_controller_map,
                              lab_controller_table, LabControllerDistroTree,
                              Hypervisor, Cpu, CpuFlag, Numa, Device,
                              DeviceClass, Disk, Power, PowerType)

# This follows the SI conventions used in disks and networks --
# *not* applicable to computer memory!
def bytes_multiplier(units):
    return {
        'bytes': 1,
        'B':     1,
        'kB':    1000,
        'KB':    1000,
        'KiB':   1024,
        'MB':    1000*1000,
        'MiB':   1024*1024,
        'GB':    1000*1000*1000,
        'GiB':   1024*1024*1024,
        'TB':    1000*1000*1000*1000,
        'TiB':   1024*1024*1024*1024,
    }.get(units)

# convert a date to a datetime range
def get_dtrange(dt):
    start_dt = datetime.datetime.combine(
        dt, datetime.time(0,0,0))
    end_dt = datetime.datetime.combine(
        dt, datetime.time(23,59,59))

    return start_dt, end_dt

# Common special query processing specific to
# System.date_added and System.date_lastcheckin
def date_filter(col, op, value):
    try:
        dt = datetime.datetime.strptime(value,'%Y-%m-%d').date()
    except ValueError:
        raise ValueError('Invalid date format: %s. '
                                 'Use YYYY-MM-DD.' % value)
    if op == '__eq__':
        start_dt, end_dt = get_dtrange(dt)
        clause = and_(getattr(col, '__ge__')(start_dt),
                                 (getattr(col, '__le__')(end_dt)))
    elif op == '__ne__':
        start_dt, end_dt = get_dtrange(dt)
        clause = not_(and_(getattr(col, '__ge__')(start_dt),
                                      (getattr(col, '__le__')(end_dt))))
    elif op == '__gt__':
        clause = getattr(col, '__gt__')(datetime.datetime.combine
                                       (dt,datetime.time(23, 59, 59)))
    else:
        clause = getattr(col, op)(datetime.datetime.combine
                                 (dt,datetime.time(0, 0, 0)))

    return clause

class NotVirtualisable(ValueError): pass

class ElementWrapper(object):
    # Operator translation table
    op_table = { '=' : '__eq__',
                 '==' : '__eq__',
                 'like': 'like',
                 '!=' : '__ne__',
                 '>'  : '__gt__',
                 '>=' : '__ge__',
                 '<'  : '__lt__',
                 '<=' : '__le__'}

    subclassDict = []

    def get_subclass(self, element):
        name = element.tag

        if name in self.subclassDict:
            return self.subclassDict[name]
        # As a kindness to the user we treat unrecognised elements like <and/>,
        # so that valid elements inside the unrecognised one are not ignored.
        return XmlAnd

    def __init__(self, wrappedEl, subclassDict=None):
        self.wrappedEl = wrappedEl
        if self.subclassDict == None:
            self.subclassDict = subclassDict

    def __repr__(self):
        return '%s("%s")' % (self.__class__, repr(self.wrappedEl))

    def __iter__(self):
        for child in self.wrappedEl:
            if isinstance(child, etree._Element):
                yield self.get_subclass(child)(child, self.subclassDict)
            else:
                yield child

    def __getitem__(self, n):
        child = self.wrappedEl[n]
        if isinstance(child, etree._Element):
            return self.get_subclass(child)(child, self.subclassDict)
        else:
            return child

    def get_xml_attr(self, attr, typeCast, defaultValue):
        attributes = self.wrappedEl.attrib
        if attr in attributes:
            return typeCast(attributes[attr])
        else:
            return defaultValue

    # These are the default behaviours for each element.
    # Note that unrecognised elements become XmlAnd!

    def filter(self, joins):
        return (joins, None)

    def filter_lab(self):
        return None

    def vm_params(self):
        raise NotVirtualisable()


class XmlAnd(ElementWrapper):
    subclassDict = None

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

    def filter_lab(self, query):
        clauses = []
        for child in self:
            clause = child.filter_lab()
            if clause is not None:
                clauses.append(clause)
        if not clauses:
            return None
        return and_(*clauses)

    def vm_params(self):
        d = {}
        for child in self:
            d.update(child.vm_params())
        return d


class XmlOr(ElementWrapper):
    """
    Combine sub queries into or_ statements
    """
    subclassDict = None

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

    def filter_lab(self, query):
        clauses = []
        for child in self:
            clause = child.filter_lab()
            if clause is not None:
                clauses.append(clause)
        if not clauses:
            return None
        return or_(*clauses)

    def vm_params(self):
        raise NotVirtualisable() # too hard!


class XmlNot(ElementWrapper):
    """
    Combines sub-filters with not_(and_()).
    """
    subclassDict = None

    def filter(self, joins):
        queries = []
        for child in self:
            if callable(getattr(child, 'filter', None)):
                (joins, query) = child.filter(joins)
                if query is not None:
                    queries.append(query)
        if not queries:
            return (joins, None)
        return (joins, not_(and_(*queries)))

    def filter_lab(self, query):
        clauses = []
        for child in self:
            clause = child.filter_lab()
            if clause is not None:
                clauses.append(clause)
        if not clauses:
            return None
        return not_(and_(*clauses))

    def vm_params(self):
        raise NotVirtualisable() # too hard!


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
    pass


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
        return (joins.join(System.lab_controller), self.filter_lab())

    def filter_lab(self):
        op = self.op_table[self.get_xml_attr('op', unicode, '==')]
        value = self.get_xml_attr('value', unicode, None)
        if not value:
            return None
        return getattr(LabController.fqdn, op)(value)

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

    def vm_params(self):
        # XXX 'KVM' is hardcoded here just because that is what RHEV/oVirt
        # uses, but we should have a better solution
        op = self.op_table[self.get_xml_attr('op', unicode, '==')]
        value = self.get_xml_attr('value', unicode, None) or None
        if getattr(operator, op)('KVM', value):
            return {}
        else:
            raise NotVirtualisable()

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

    def vm_params(self):
        value = self.get_xml_attr('value', unicode, None)
        if value == 'Machine':
            return {}
        else:
            raise NotVirtualisable()

class XmlSystemStatus(ElementWrapper):
    """
    Pick a system with the correct system status.
    """
    def filter(self, joins):
        value = self.get_xml_attr('value', unicode, None)
        query = None
        if value:
            query = System.status == value
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

class XmlLastInventoried(ElementWrapper):
    """
    Pick a system wth the correct last inventoried date/status
    """
    op_table = { '=' : '__eq__',
                 '==' : '__eq__',
                 '!=' : '__ne__',
                 '>'  : '__gt__',
                 '>=' : '__ge__',
                 '<'  : '__lt__',
                 '<=' : '__le__'}

    def filter(self, joins):
        col = System.date_lastcheckin
        op = self.op_table[self.get_xml_attr('op', unicode, '==')]
        value = self.get_xml_attr('value', unicode, None)

        if value:
            clause = date_filter(col, op, value)
        else:
            clause = getattr(col, op)(None)

        return (joins, clause)

class XmlSystemLender(ElementWrapper):
    """
    Pick a system wth the correct lender.
    """
    def filter(self, joins):
        op = self.op_table[self.get_xml_attr('op', unicode, '==')]
        value = self.get_xml_attr('value', unicode, None)
        query = None
        if value:
            query = getattr(System.lender, op)(value)
        return (joins, query)

class XmlSystemVendor(ElementWrapper):
    """
    Pick a system wth the correct vendor.
    """
    def filter(self, joins):
        op = self.op_table[self.get_xml_attr('op', unicode, '==')]
        value = self.get_xml_attr('value', unicode, None)
        query = None
        if value:
            query = getattr(System.vendor, op)(value)
        return (joins, query)

class XmlSystemLocation(ElementWrapper):
    """
    Pick a system wth the correct location.
    """
    def filter(self, joins):
        op = self.op_table[self.get_xml_attr('op', unicode, '==')]
        value = self.get_xml_attr('value', unicode, None)
        query = None
        if value:
            query = getattr(System.location, op)(value)
        return (joins, query)

class XmlSystemSerial(ElementWrapper):
    """
    Pick a system wth the correct Serial Number.
    """
    def filter(self, joins):
        op = self.op_table[self.get_xml_attr('op', unicode, '==')]
        value = self.get_xml_attr('value', unicode, None)
        query = None
        if value:
            query = getattr(System.serial, op)(value)
        return (joins, query)

class XmlSystemModel(ElementWrapper):
    """
    Pick a system wth the correct model.
    """
    def filter(self, joins):
        op = self.op_table[self.get_xml_attr('op', unicode, '==')]
        value = self.get_xml_attr('value', unicode, None)
        query = None
        if value:
            query = getattr(System.model, op)(value)
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

    def vm_params(self):
        # XXX add some logic here
        raise NotVirtualisable()

class XmlSystemOwner(ElementWrapper):
    """
    Pick a system with the correct owner.
    """
    def filter(self, joins):
        op = self.op_table[self.get_xml_attr('op', unicode, '==')]
        value = self.get_xml_attr('value', unicode, None)
        query = None
        if value:
            owner_alias = aliased(User)
            joins = joins.join((owner_alias, System.owner))
            query = getattr(owner_alias.user_name, op)(value)
        return (joins, query)

class XmlSystemUser(ElementWrapper):
    """
    Pick a system with the correct user.
    """
    def filter(self, joins):
        op = self.op_table[self.get_xml_attr('op', unicode, '==')]
        value = self.get_xml_attr('value', unicode, None)
        query = None
        if value:
            user_alias = aliased(User)
            joins = joins.join((user_alias, System.user))
            query = getattr(user_alias.user_name, op)(value)
        return (joins, query)

class XmlSystemLoaned(ElementWrapper):
    """
    Pick a system that has been loaned to this user.
    """
    def filter(self, joins):
        op = self.op_table[self.get_xml_attr('op', unicode, '==')]
        value = self.get_xml_attr('value', unicode, None)
        query = None
        if value:
            loaned_alias = aliased(User)
            joins = joins.join((loaned_alias, System.loaned))
            query = getattr(loaned_alias.user_name, op)(value)
        return (joins, query)

class XmlSystemAdded(ElementWrapper):
    """
    Pick a system based on when it was added
    """
    op_table = { '=' : '__eq__',
                 '==' : '__eq__',
                 '!=' : '__ne__',
                 '>'  : '__gt__',
                 '>=' : '__ge__',
                 '<'  : '__lt__',
                 '<=' : '__le__'}

    def filter(self, joins):
        col = System.date_added
        op = self.op_table[self.get_xml_attr('op', unicode, '==')]
        value = self.get_xml_attr('value', unicode, None)
        clause = None

        if value:
            clause = date_filter(col, op, value)

        return (joins, clause)

class XmlSystemPowertype(ElementWrapper):
    """
    Pick a system that has been loaned to this user.
    """
    def filter(self, joins):
        op = self.op_table[self.get_xml_attr('op', unicode, '==')]
        value = self.get_xml_attr('value', unicode, None)
        query = None
        if value:
            joins = joins.join(System.power, Power.power_type)
            query = getattr(PowerType.name, op)(value)
        return (joins, query)

class XmlCpuProcessors(ElementWrapper):
    """
    Pick a system with the correct amount of cpu processors.
    """
    def filter(self, joins):
        op = self.op_table[self.get_xml_attr('op', unicode, '==')]
        value = self.get_xml_attr('value', int, None)
        query = None
        if value:
            joins = joins.join(System.cpu)
            query = getattr(Cpu.processors, op)(value)
        return (joins, query)


class XmlCpuCores(ElementWrapper):
    """
    Pick a system with the correct amount of cpu cores.
    """
    def filter(self, joins):
        op = self.op_table[self.get_xml_attr('op', unicode, '==')]
        value = self.get_xml_attr('value', int, None)
        query = None
        if value:
            joins = joins.join(System.cpu)
            query = getattr(Cpu.cores, op)(value)
        return (joins, query)


class XmlCpuFamily(ElementWrapper):
    """
    Pick a system with the correct cpu family.
    """
    def filter(self, joins):
        op = self.op_table[self.get_xml_attr('op', unicode, '==')]
        value = self.get_xml_attr('value', int, None)
        query = None
        if value:
            joins = joins.join(System.cpu)
            query = getattr(Cpu.family, op)(value)
        return (joins, query)


class XmlCpuModel(ElementWrapper):
    """
    Pick a system with the correct cpu model.
    """
    def filter(self, joins):
        op = self.op_table[self.get_xml_attr('op', unicode, '==')]
        value = self.get_xml_attr('value', int, None)
        query = None
        if value:
            joins = joins.join(System.cpu)
            query = getattr(Cpu.model, op)(value)
        return (joins, query)


class XmlCpuModelName(ElementWrapper):
    """
    Pick a system with the correct cpu model_name.
    """
    def filter(self, joins):
        op = self.op_table[self.get_xml_attr('op', unicode, '==')]
        value = self.get_xml_attr('value', unicode, None)
        query = None
        if value:
            joins = joins.join(System.cpu)
            query = getattr(Cpu.model_name, op)(value)
        return (joins, query)


class XmlCpuSockets(ElementWrapper):
    """
    Pick a system with the correct number of cpu sockets.
    """
    def filter(self, joins):
        op = self.op_table[self.get_xml_attr('op', unicode, '==')]
        value = self.get_xml_attr('value', int, None)
        query = None
        if value:
            joins = joins.join(System.cpu)
            query = getattr(Cpu.sockets, op)(value)
        return (joins, query)


class XmlCpuSpeed(ElementWrapper):
    """
    Pick a system with the correct cpu speed.
    """
    def filter(self, joins):
        op = self.op_table[self.get_xml_attr('op', unicode, '==')]
        value = self.get_xml_attr('value', float, None)
        query = None
        if value:
            joins = joins.join(System.cpu)
            query = getattr(Cpu.speed, op)(value)
        return (joins, query)


class XmlCpuStepping(ElementWrapper):
    """
    Pick a system with the correct cpu stepping.
    """
    def filter(self, joins):
        op = self.op_table[self.get_xml_attr('op', unicode, '==')]
        value = self.get_xml_attr('value', int, None)
        query = None
        if value:
            joins = joins.join(System.cpu)
            query = getattr(Cpu.stepping, op)(value)
        return (joins, query)


class XmlCpuVendor(ElementWrapper):
    """
    Pick a system with the correct cpu vendor.
    """
    def filter(self, joins):
        op = self.op_table[self.get_xml_attr('op', unicode, '==')]
        value = self.get_xml_attr('value', unicode, None)
        query = None
        if value:
            joins = joins.join(System.cpu)
            query = getattr(Cpu.vendor, op)(value)
        return (joins, query)


class XmlCpuHyper(ElementWrapper):
    """
    Pick a system with cpu's that have hyperthreading enabled.
    """
    def filter(self, joins):
        op = '__eq__'
        uvalue = self.get_xml_attr('value', unicode, False).lower()
        value = uvalue in ('true', '1') and True or False
        query = None
        if value:
            joins = joins.join(System.cpu)
            query = getattr(Cpu.hyper, op)(value)
        return (joins, query)


class XmlCpuFlag(ElementWrapper):
    """
    Filter systems based on System.cpu.flags
    """

    op_table = { '=' : '__eq__',
                 '==' : '__eq__',
                 'like' : 'like',
                 '!=' : '__ne__'}

    def filter(self, joins):
        op = self.op_table[self.get_xml_attr('op', unicode, '==')]
        equal = op == '__ne__' and '__eq__' or op
        value = self.get_xml_attr('value', unicode, None)
        query = None
        if value:
            joins = joins.join(System.cpu)
            query = getattr(CpuFlag.flag, equal)(value)
            if op == '__ne__':
                query = not_(Cpu.flags.any(query))
            else:
                query = Cpu.flags.any(query)
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

    def vm_params(self):
        # XXX add some better logic here
        op = self.op_table[self.get_xml_attr('op', unicode, '==')]
        value = self.get_xml_attr('value', unicode, None)
        if getattr(operator, op)('x86_64', value):
            return {}
        else:
            raise NotVirtualisable()

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
                 'like' : 'like',
                 '!=' : '__ne__'}

    def filter(self, joins):
        op = self.op_table[self.get_xml_attr('op', unicode, '==')]
        equal = op == '__ne__' and '__equal__' or op
        query = None
        filter_clauses = []
        for attr in ['bus', 'driver', 'vendor_id', 'device_id',
                     'subsys_vendor_id', 'subsys_device_id', 'description']:
            value = self.get_xml_attr(attr, unicode, None)
            if value:
                filter_clauses.append(getattr(getattr(Device, attr),equal)(value))
        if self.get_xml_attr('type', unicode, None):
            filter_clauses.append(Device.device_class.has(
                    DeviceClass.device_class ==
                    self.get_xml_attr('type', unicode, None)))
        if filter_clauses:
            if op == '__ne__':
                query = not_(System.devices.any(and_(*filter_clauses)))
            else:
                query = System.devices.any(and_(*filter_clauses))
        return (joins, query)


# N.B. these XmlDisk* filters do not work outside of a <disk/> element!

class XmlDiskModel(ElementWrapper):
    op_table = { '=' : '__eq__',
                 '==' : '__eq__',
                 'like' : 'like',
                 '!=' : '__ne__'}
    def filter_disk(self):
        op = self.op_table[self.get_xml_attr('op', unicode, '==')]
        value = self.get_xml_attr('value', unicode, None)
        if value:
            return getattr(Disk.model, op)(value)
        return None

class XmlDiskSize(ElementWrapper):
    def filter_disk(self):
        op = self.op_table[self.get_xml_attr('op', unicode, '==')]
        value = self.get_xml_attr('value', int, None)
        units = self.get_xml_attr('units', unicode, 'bytes')
        if value:
            return getattr(Disk.size, op)(value * bytes_multiplier(units))
        return None

class XmlDiskSectorSize(ElementWrapper):
    def filter_disk(self):
        op = self.op_table[self.get_xml_attr('op', unicode, '==')]
        value = self.get_xml_attr('value', int, None)
        units = self.get_xml_attr('units', unicode, 'bytes')
        if value:
            return getattr(Disk.phys_sector_size, op)(
                    value * bytes_multiplier(units))
        return None

class XmlDiskPhysSectorSize(ElementWrapper):
    def filter_disk(self):
        op = self.op_table[self.get_xml_attr('op', unicode, '==')]
        value = self.get_xml_attr('value', int, None)
        units = self.get_xml_attr('units', unicode, 'bytes')
        if value:
            return getattr(Disk.phys_sector_size, op)(
                    value * bytes_multiplier(units))
        return None

class XmlDisk(ElementWrapper):
    subclassDict = {
        'model': XmlDiskModel,
        'size': XmlDiskSize,
        'sector_size': XmlDiskSectorSize,
        'phys_sector_size': XmlDiskPhysSectorSize,
    }

    def filter(self, joins):
        clauses = []
        for child in self:
            if callable(getattr(child, 'filter_disk', None)):
                clause = child.filter_disk()
                if clause is not None:
                    clauses.append(clause)
        if not clauses:
            return (joins, System.disks.any())
        return (joins, System.disks.any(and_(*clauses)))


class XmlCpu(XmlAnd):
    subclassDict = {
                    'and': XmlAnd,
                    'or': XmlOr,
                    'not': XmlNot,
                    'processors': XmlCpuProcessors,
                    'cores': XmlCpuCores,
                    'family': XmlCpuFamily,
                    'hyper': XmlCpuHyper,
                    'model': XmlCpuModel,
                    'model_name': XmlCpuModelName,
                    'sockets': XmlCpuSockets,
                    'speed': XmlCpuSpeed,
                    'stepping': XmlCpuStepping,
                    'vendor': XmlCpuVendor,
                    'flag': XmlCpuFlag,
                   }

class XmlSystem(XmlAnd):
    subclassDict = {
                    'and': XmlAnd,
                    'or': XmlOr,
                    'not': XmlNot,
                    'name': XmlHostName,
                    'type': XmlSystemType,
                    'status': XmlSystemStatus,
                    'lender': XmlSystemLender,
                    'vendor': XmlSystemVendor,
                    'model': XmlSystemModel,
                    'owner': XmlSystemOwner,
                    'user': XmlSystemUser,
                    'loaned': XmlSystemLoaned,
                    'location': XmlSystemLocation,
                    'powertype': XmlSystemPowertype, #Should this be here?
                    'serial': XmlSystemSerial,
                    'memory': XmlMemory,
                    'arch': XmlArch,
                    'numanodes': XmlNumaNodeCount,
                    'hypervisor': XmlHypervisor,
                    'added': XmlSystemAdded,
                    'last_inventoried':XmlLastInventoried
                   }


class XmlHost(XmlAnd):
    subclassDict = {
                    'and': XmlAnd,
                    'or': XmlOr,
                    'not': XmlNot,
                    'labcontroller': XmlHostLabController,
                    'system': XmlSystem,
                    'cpu': XmlCpu,
                    'device': XmlDevice,
                    'disk': XmlDisk,
                    'group': XmlGroup,
                    'key_value': XmlKeyValue,
                    'auto_prov': XmlAutoProv,
                    'hostlabcontroller': XmlHostLabController, #deprecated
                    'system_type': XmlSystemType, #deprecated
                    'memory': XmlMemory, #deprecated
                    'cpu_count': XmlCpuProcessors, #deprecated
                    'hostname': XmlHostName, #deprecated
                    'arch': XmlArch, #deprecated
                    'numa_node_count': XmlNumaNodeCount, #deprecated
                    'hypervisor': XmlHypervisor, #deprecated
                   }

class XmlDistro(XmlAnd):
    subclassDict = {
                    'and': XmlAnd,
                    'or': XmlOr,
                    'not': XmlNot,
                    'arch': XmlDistroArch,
                    'family': XmlDistroFamily,
                    'variant': XmlDistroVariant,
                    'name': XmlDistroName,
                    'tag': XmlDistroTag,
                    'virt': XmlDistroVirt,
                    'labcontroller': XmlDistroLabController,
                    'distro_arch': XmlDistroArch, #deprecated
                    'distro_family': XmlDistroFamily, #deprecated
                    'distro_variant': XmlDistroVariant, #deprecated
                    'distro_name': XmlDistroName, #deprecated
                    'distro_tag': XmlDistroTag, #deprecated
                    'distro_virt': XmlDistroVirt, #deprecated
                    'distrolabcontroller': XmlDistroLabController, #deprecated
                   }


def apply_system_filter(filter, query):
    if isinstance(filter, basestring):
        filter = XmlHost(etree.fromstring(filter))
    clauses = []
    for child in filter:
        if callable(getattr(child, 'filter', None)):
            (query, clause) = child.filter(query)
            if clause is not None:
                clauses.append(clause)
    if clauses:
        query = query.filter(and_(*clauses))

    return query

def apply_lab_controller_filter(filter, query):
    if isinstance(filter, basestring):
        filter = XmlHost(etree.fromstring(filter))
    clauses = []
    for child in filter:
        clause = child.filter_lab()
        if clause is not None:
            clauses.append(clause)
    if clauses:
        query = query.filter(and_(*clauses))
    return query

def vm_params(filter):
    if isinstance(filter, basestring):
        filter = XmlHost(etree.fromstring(filter))
    params = {}
    for child in filter:
        params.update(child.vm_params())
    return params

def apply_distro_filter(filter, query):
    if isinstance(filter, basestring):
        filter = XmlDistro(etree.fromstring(filter))
    clauses = []
    for child in filter:
        if callable(getattr(child, 'filter', None)):
            (query, clause) = child.filter(query)
            if clause is not None:
                clauses.append(clause)
    if clauses:
        query = query.filter(and_(*clauses))
    return query
