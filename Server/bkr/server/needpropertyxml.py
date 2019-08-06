
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import operator

import datetime
from lxml import etree
from sqlalchemy import or_, and_, not_, exists, func
from sqlalchemy.orm import aliased
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.sql import false

from bkr.server.model import (Arch, Distro, DistroTree, DistroTag,
                              OSMajor, OSVersion, SystemPool, System, User,
                              Key, Key_Value_Int, Key_Value_String,
                              LabController, LabControllerDistroTree,
                              Hypervisor, Cpu, CpuFlag, Numa, Device,
                              DeviceClass, Disk, Power, PowerType)


# This follows the SI conventions used in disks and networks --
# *not* applicable to computer memory!
def bytes_multiplier(units):
    return {
        'bytes': 1,
        'B': 1,
        'kB': 1000,
        'KB': 1000,
        'KiB': 1024,
        'MB': 1000 * 1000,
        'MiB': 1024 * 1024,
        'GB': 1000 * 1000 * 1000,
        'GiB': 1024 * 1024 * 1024,
        'TB': 1000 * 1000 * 1000 * 1000,
        'TiB': 1024 * 1024 * 1024 * 1024,
    }.get(units)


# convert a date to a datetime range
def get_dtrange(dt):
    start_dt = datetime.datetime.combine(
        dt, datetime.time(0, 0, 0))
    end_dt = datetime.datetime.combine(
        dt, datetime.time(23, 59, 59))

    return start_dt, end_dt


# Common special query processing specific to
# System.date_added and System.date_lastcheckin
def date_filter(col, op, value):
    try:
        dt = datetime.datetime.strptime(value, '%Y-%m-%d').date()
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
                                        (dt, datetime.time(23, 59, 59)))
    else:
        clause = getattr(col, op)(datetime.datetime.combine
                                  (dt, datetime.time(0, 0, 0)))

    return clause


class ElementWrapper(object):
    # Operator translation table
    op_table = {'=': '__eq__',
                '==': '__eq__',
                'like': 'like',
                '!=': '__ne__',
                '>': '__gt__',
                '>=': '__ge__',
                '<': '__lt__',
                '<=': '__le__'}

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

    def apply_filter(self, query):
        query, clause = self.filter(query)
        if clause is not None:
            query = query.filter(clause)
        return query

    def filter(self, joins):
        return (joins, None)

    def filter_disk(self):
        return None

    def filter_openstack_flavors(self, flavors, lab_controller):
        return []

    def virtualisable(self):
        """
        In addition to the flavor filtering, we have this simple boolean check as
        an extra optimisation. This should return False if the host requirements
        could *never* be satisfied by a dynamic virt guest. That way we can bail
        out early and avoid going to OpenStack at all for this recipe.
        """
        return False


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

    def filter_disk(self):
        queries = []
        for child in self:
            if callable(getattr(child, 'filter_disk', None)):
                query = child.filter_disk()
                if query is not None:
                    queries.append(query)
        return and_(*queries)

    def filter_openstack_flavors(self, flavors, lab_controller):
        result = set(flavors)
        for child in self:
            child_result = child.filter_openstack_flavors(flavors, lab_controller)
            result.intersection_update(child_result)
        return list(result)

    def virtualisable(self):
        for child in self:
            if not child.virtualisable():
                return False
        return True


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

    def filter_disk(self):
        queries = []
        for child in self:
            if callable(getattr(child, 'filter_disk', None)):
                query = child.filter_disk()
                if query is not None:
                    queries.append(query)
        return or_(*queries)

    def filter_openstack_flavors(self, flavors, lab_controller):
        result = set()
        for child in self:
            child_result = child.filter_openstack_flavors(flavors, lab_controller)
            result.update(child_result)
        return list(result)

    def virtualisable(self):
        for child in self:
            if child.virtualisable():
                return True
        return False


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

    def filter_disk(self):
        queries = []
        for child in self:
            if callable(getattr(child, 'filter_disk', None)):
                query = child.filter_disk()
                if query is not None:
                    queries.append(query)
        return not_(and_(*queries))

    def filter_openstack_flavors(self, flavors, lab_controller):
        # Acceptable flavours are any flavour which was *not* matched by the
        # child filters.
        result = set(flavors)
        for child in self:
            child_result = child.filter_openstack_flavors(flavors, lab_controller)
            result.difference_update(child_result)
        return list(result)

    def virtualisable(self):
        # Even if the child filters cannot be satisfied by OpenStack,
        # the negation of them probably can be.
        return True


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

    op_table = {'=': '__eq__',
                '==': '__eq__',
                '!=': '__ne__'}

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


class XmlPool(ElementWrapper):
    """
    Filter based on pool
    """

    op_table = {'=': '__eq__',
                '==': '__eq__',
                '!=': '__ne__'}

    def filter(self, joins):
        op = self.op_table[self.get_xml_attr('op', unicode, '==')]
        value = self.get_xml_attr('value', unicode, None)
        if value:
            # - '==' - search for system which is member of given pool
            # - '!=' - search for system which is not member of given pool
            try:
                pool = SystemPool.by_name(value)
            except NoResultFound:
                return (joins, None)
            if op == '__eq__':
                query = System.pools.any(SystemPool.id == pool.id)
            else:
                query = not_(System.pools.any(SystemPool.id == pool.id))
        else:
            # - '!=' - search for system which is member of any pool
            # - '==' - search for system which is not member of any pool
            if op == '__eq__':
                query = System.pools == None
            else:
                query = System.pools != None
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
    op_table = {'=': '__eq__',
                '==': '__eq__',
                '!=': '__ne__'}

    def filter(self, joins):
        op = self.op_table[self.get_xml_attr('op', unicode, '==')]
        value = self.get_xml_attr('value', unicode, None)
        query = None
        if value:
            joins = joins.join(System.lab_controller)
            query = getattr(LabController.fqdn, op)(value)
        return (joins, query)

    def filter_openstack_flavors(self, flavors, lab_controller):
        op = self.op_table[self.get_xml_attr('op', unicode, '==')]
        value = self.get_xml_attr('value', unicode, None)
        if not value:
            return []
        matched = getattr(lab_controller.fqdn, op)(value)
        if matched:
            return flavors
        else:
            return []

    def virtualisable(self):
        return True


class XmlDistroLabController(ElementWrapper):
    """
    Pick a distro tree available on this lab controller
    """
    op_table = {'=': '__eq__',
                '==': '__eq__',
                '!=': '__ne__'}

    def filter(self, joins):
        op = self.op_table[self.get_xml_attr('op', unicode, '==')]
        value = self.get_xml_attr('value', unicode, None)
        if not value:
            return (joins, None)
        if op == '__eq__':
            query = exists([1],
                           from_obj=
                           [LabControllerDistroTree.__table__.join(LabController.__table__)]) \
                .where(LabControllerDistroTree.distro_tree_id == DistroTree.id) \
                .where(LabController.fqdn == value)
        else:
            query = not_(exists([1],
                                from_obj=[LabControllerDistroTree.__table__.join
                                          (LabController.__table__)]) \
                         .where(LabControllerDistroTree.distro_tree_id == DistroTree.id) \
                         .where(LabController.fqdn == value))
        return (joins, query)


class XmlHypervisor(ElementWrapper):
    """
    Pick a system based on the hypervisor.
    """

    def filter(self, joins):
        op = self.op_table[self.get_xml_attr('op', unicode, '==')]
        value = self.get_xml_attr('value', unicode, '')
        joins = joins.outerjoin(System.hypervisor)
        query = getattr(func.coalesce(Hypervisor.hypervisor, ''), op)(value)
        return (joins, query)

    def filter_openstack_flavors(self, flavors, lab_controller):
        if self._matches_kvm():
            return flavors
        else:
            return []

    def virtualisable(self):
        return self._matches_kvm()

    def _matches_kvm(self):
        # XXX 'KVM' is hardcoded here assuming that is what OpenStack is using,
        # but we should have a better solution
        op = self.op_table[self.get_xml_attr('op', unicode, '==')]
        value = self.get_xml_attr('value', unicode, '')
        return getattr(operator, op)('KVM', value)


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

    def filter_openstack_flavors(self, flavors, lab_controller):
        if self._matches_machine():
            return flavors
        else:
            return []

    def virtualisable(self):
        return self._matches_machine()

    def _matches_machine(self):
        value = self.get_xml_attr('value', unicode, None)
        return value == 'Machine'


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
    op_table = {'=': '__eq__',
                '==': '__eq__',
                '!=': '__ne__',
                '>': '__gt__',
                '>=': '__ge__',
                '<': '__lt__',
                '<=': '__le__'}

    def filter(self, joins):
        col = System.date_lastcheckin
        op = self.op_table[self.get_xml_attr('op', unicode, '==')]
        value = self.get_xml_attr('value', unicode, None)

        if value:
            clause = date_filter(col, op, value)
        else:
            clause = getattr(col, op)(None)

        return (joins, clause)


class XmlSystemCompatibleWithDistro(ElementWrapper):
    """
    Matches systems which are compatible with the given OS version.
    """

    def filter(self, joins):
        arch_name = self.get_xml_attr('arch', unicode, None)
        try:
            arch = Arch.by_name(arch_name)
        except ValueError:
            return (joins, false())
        osmajor = self.get_xml_attr('osmajor', unicode, None)
        if not osmajor:
            return (joins, false())
        osminor = self.get_xml_attr('osminor', unicode, None) or None
        clause = System.compatible_with_distro_tree(arch, osmajor, osminor)
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

    def filter_openstack_flavors(self, flavors, lab_controller):
        op = self.op_table[self.get_xml_attr('op', unicode, '==')]
        value = self.get_xml_attr('value', int, None)
        if value:
            flavors = [flavor for flavor in flavors
                       if getattr(operator, op)(flavor.ram, value)]
        return flavors

    def virtualisable(self):
        return True


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
    op_table = {'=': '__eq__',
                '==': '__eq__',
                '!=': '__ne__',
                '>': '__gt__',
                '>=': '__ge__',
                '<': '__lt__',
                '<=': '__le__'}

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

    def filter_openstack_flavors(self, flavors, lab_controller):
        # We treat an OpenStack flavor with N vcpus as having N single-core
        # processors. Not sure how realistic that is but we have to pick
        # something...
        op = self.op_table[self.get_xml_attr('op', unicode, '==')]
        value = self.get_xml_attr('value', int, None)
        if value:
            flavors = [flavor for flavor in flavors
                       if getattr(operator, op)(flavor.vcpus, value)]
        return flavors

    def virtualisable(self):
        return True


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

    def filter_openstack_flavors(self, flavors, lab_controller):
        op = self.op_table[self.get_xml_attr('op', unicode, '==')]
        value = self.get_xml_attr('value', int, None)
        if value:
            flavors = [flavor for flavor in flavors
                       if getattr(operator, op)(flavor.vcpus, value)]
        return flavors

    def virtualisable(self):
        return True


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

    op_table = {'=': '__eq__',
                '==': '__eq__',
                'like': 'like',
                '!=': '__ne__'}

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

    op_table = {'=': '__eq__',
                '==': '__eq__',
                '!=': '__ne__'}

    def filter(self, joins):
        op = self.op_table[self.get_xml_attr('op', unicode, '==')]
        value = self.get_xml_attr('value', unicode, None)
        query = None
        if value:
            # As per XmlPool above,
            # - '==' - search for system which has given arch
            # - '!=' - search for system which does not have given arch
            try:
                arch = Arch.by_name(value)
            except ValueError:
                return (joins, None)
            if op == '__eq__':
                query = System.arch.any(Arch.id == arch.id)
            else:
                query = not_(System.arch.any(Arch.id == arch.id))
        return (joins, query)

    def filter_openstack_flavors(self, flavors, lab_controllers):
        if self._matches_x86():
            return flavors
        else:
            return []

    def virtualisable(self):
        return self._matches_x86()

    def _matches_x86(self):
        op = self.op_table[self.get_xml_attr('op', unicode, '==')]
        value = self.get_xml_attr('value', unicode, None)
        return (getattr(operator, op)('x86_64', value) or
                getattr(operator, op)('i386', value))


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

    op_table = {'=': '__eq__',
                '==': '__eq__',
                'like': 'like',
                '!=': '__ne__'}

    def filter(self, joins):
        op = self.op_table[self.get_xml_attr('op', unicode, '==')]
        equal = op == '__ne__' and '__eq__' or op
        query = None
        filter_clauses = []
        for attr in ['bus', 'driver', 'vendor_id', 'device_id',
                     'subsys_vendor_id', 'subsys_device_id', 'description']:
            value = self.get_xml_attr(attr, unicode, None)
            if value:
                filter_clauses.append(getattr(getattr(Device, attr), equal)(value))
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
    op_table = {'=': '__eq__',
                '==': '__eq__',
                'like': 'like',
                '!=': '__ne__'}

    def filter_disk(self):
        op = self.op_table[self.get_xml_attr('op', unicode, '==')]
        value = self.get_xml_attr('value', unicode, None)
        if value:
            return getattr(Disk.model, op)(value)
        return None


class XmlDiskSize(ElementWrapper):

    def _bytes_value(self):
        value = self.get_xml_attr('value', int, None)
        units = self.get_xml_attr('units', unicode, 'bytes')
        if value:
            return value * bytes_multiplier(units)

    def filter_disk(self):
        op = self.op_table[self.get_xml_attr('op', unicode, '==')]
        value = self._bytes_value()
        if value:
            return getattr(Disk.size, op)(value)
        return None

    def filter_openstack_flavors(self, flavors, lab_controller):
        op = self.op_table[self.get_xml_attr('op', unicode, '==')]
        value = self._bytes_value()
        if value:
            flavors = [flavor for flavor in flavors
                       if getattr(operator, op)(flavor.disk, value)]
        return flavors

    def virtualisable(self):
        return True


class XmlDiskSectorSize(ElementWrapper):
    def filter_disk(self):
        op = self.op_table[self.get_xml_attr('op', unicode, '==')]
        value = self.get_xml_attr('value', int, None)
        units = self.get_xml_attr('units', unicode, 'bytes')
        if value:
            return getattr(Disk.sector_size, op)(
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


class XmlDisk(XmlAnd):
    subclassDict = {
        'and': XmlAnd,
        'or': XmlOr,
        'not': XmlNot,
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


class XmlDiskSpace(ElementWrapper):
    """
    Filter systems by total disk space
    """

    def _bytes_value(self):
        value = self.get_xml_attr('value', int, None)
        units = self.get_xml_attr('units', unicode, 'bytes')
        if value:
            return value * bytes_multiplier(units)

    def filter(self, joins):
        op = self.op_table[self.get_xml_attr('op', unicode, '==')]
        value = self._bytes_value()
        query = None
        if value:
            query = getattr(System.diskspace, op)(value)
        return (joins, query)


class XmlDiskCount(ElementWrapper):
    """
    Filter systems by total number of disks
    """

    def filter(self, joins):
        op = self.op_table[self.get_xml_attr('op', unicode, '==')]
        value = self.get_xml_attr('value', int, None)
        query = None
        if value:
            query = getattr(System.diskcount, op)(value)
        return (joins, query)


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
        'powertype': XmlSystemPowertype,  # Should this be here?
        'serial': XmlSystemSerial,
        'memory': XmlMemory,
        'arch': XmlArch,
        'numanodes': XmlNumaNodeCount,
        'hypervisor': XmlHypervisor,
        'added': XmlSystemAdded,
        'last_inventoried': XmlLastInventoried,
        'compatible_with_distro': XmlSystemCompatibleWithDistro,
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
        'diskspace': XmlDiskSpace,
        'diskcount': XmlDiskCount,
        'pool': XmlPool,
        # for backward compatibility
        'group': XmlPool,
        'key_value': XmlKeyValue,
        'auto_prov': XmlAutoProv,
        'hostlabcontroller': XmlHostLabController,  # deprecated
        'system_type': XmlSystemType,  # deprecated
        'memory': XmlMemory,  # deprecated
        'cpu_count': XmlCpuProcessors,  # deprecated
        'hostname': XmlHostName,  # deprecated
        'arch': XmlArch,  # deprecated
        'numa_node_count': XmlNumaNodeCount,  # deprecated
        'hypervisor': XmlHypervisor,  # deprecated
    }

    @classmethod
    def from_string(cls, xml_string):
        try:
            return cls(etree.fromstring(xml_string))
        except etree.XMLSyntaxError as e:
            raise ValueError('Invalid XML syntax for host filter: %s' % e)

    @property
    def force(self):
        """
        <hostRequires force="$FQDN"/> means to skip all normal host filtering
        and always use the named system.
        """
        return self.get_xml_attr('force', unicode, None)

    def virtualisable(self):
        if self.force:
            return False
        return super(XmlHost, self).virtualisable()

    # Physical Beaker systems are expected to have at least one disk of a sane
    # size, so recipes will often not bother including a requirement on disk
    # size. But OpenStack flavors can have no disk at all or really small disk,
    # so we filter those out here.
    def filter_openstack_flavors(self, flavors, lab_controller):
        result = super(XmlHost, self).filter_openstack_flavors(flavors, lab_controller)
        # 10G is sufficient for most of current distributions supported by Beaker
        return [flavor for flavor in result if flavor.disk >= 10]


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
        'distro_arch': XmlDistroArch,  # deprecated
        'distro_family': XmlDistroFamily,  # deprecated
        'distro_variant': XmlDistroVariant,  # deprecated
        'distro_name': XmlDistroName,  # deprecated
        'distro_tag': XmlDistroTag,  # deprecated
        'distro_virt': XmlDistroVirt,  # deprecated
        'distrolabcontroller': XmlDistroLabController,  # deprecated
    }


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
