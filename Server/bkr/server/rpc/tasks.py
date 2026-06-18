
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import os
import logging

from sqlalchemy import or_
from sqlalchemy.exc import InvalidRequestError
from bkr.server.database import session
from bkr.server import identity
from bkr.common.bexceptions import BX
from bkr.server.model import (Distro, Task, OSMajor, TaskPackage, TaskType,
                              Arch)
from bkr.server.util import ensure_str
from bkr.server.rpc import expose, register

import six


log = logging.getLogger(__name__)


@register('tasks')
class Tasks(object):
    # For XMLRPC methods in this class.
    exposed = True

    @expose
    def filter(self, filter):
        """
        Returns a list of tasks filtered by the given criteria.

        The *filter* argument must be an XML-RPC structure (dict), with any of the following keys:

            'distro_name'
                Distro name. Include only tasks which are compatible
                with this distro.
            'osmajor'
                OSVersion OSMajor, like RedHatEnterpriseLinux6.  Include only
                tasks which are compatible with this OSMajor.
            'names'
                Task name. Include only tasks that are named. Useful when
                combined with 'osmajor' or 'distro_name'.
            'packages'
                List of package names. Include only tasks which have a Run-For
                entry matching any of these packages.
            'types'
                List of task types. Include only tasks which have one or more
                of these types.
            'valid'
                bool 0 or 1. Include only tasks which are valid or not.
            'destructive'
                bool 0 or 1. Set to 0 for only non-destructive tasks. Set to
                1 for only destructive tasks.

        The return value is an array of dicts, which are name and arches.
        name is the name of the matching tasks.
        arches is an array of arches which this task does not apply for.
        Call :meth:`tasks.to_dict` to fetch metadata for a particular task.

        .. versionchanged:: 0.9
           Changed 'install_name' to 'distro_name' in the *filter* argument.
        """
        tasks = Task.query

        if filter.get('distro_name'):
            distro = Distro.by_name(filter['distro_name'])
            tasks = tasks.filter(Task.compatible_with_distro(distro))
        elif 'osmajor' in filter and filter['osmajor']:
            try:
                osmajor = OSMajor.by_name(filter['osmajor'])
            except InvalidRequestError:
                raise BX('Invalid OSMajor: %s' % filter['osmajor'])
            tasks = tasks.filter(Task.compatible_with_osmajor(osmajor))

        # Filter by valid task if requested
        if 'valid' in filter:
            tasks = tasks.filter(Task.valid==bool(filter['valid']))

        # Filter by destructive if requested
        if 'destructive' in filter:
            tasks = tasks.filter(Task.destructive==bool(filter['destructive']))

        # Filter by name if specified
        # /distribution/install, /distribution/reservesys
        if 'names' in filter and filter['names']:
            # if not a list, make it into a list.
            if isinstance(filter['names'], str):
                filter['names'] = [filter['names']]
            or_names = []
            for tname in filter['names']:
                or_names.append(Task.name==tname)
            tasks = tasks.filter(or_(*or_names))

        # Filter by packages if specified
        # apache, kernel, mysql, etc..
        if 'packages' in filter and filter['packages']:
            # if not a list, make it into a list.
            if isinstance(filter['packages'], str):
                filter['packages'] = [filter['packages']]
            tasks = tasks.filter(Task.runfor.any(or_(
                    *[TaskPackage.package == package for package in filter['packages']])))

        # Filter by type if specified
        # Tier1, Regression, KernelTier1, etc..
        if 'types' in filter and filter['types']:
            # if not a list, make it into a list.
            if isinstance(filter['types'], str):
                filter['types'] = [filter['types']]
            tasks = tasks.join('types')
            or_types = []
            for type in filter['types']:
                try:
                    tasktype = TaskType.by_name(type)
                except InvalidRequestError as err:
                    raise BX('Invalid Task Type: %s' % type)
                or_types.append(TaskType.id==tasktype.id)
            tasks = tasks.filter(or_(*or_types))

        result = []
        for task in tasks:
            if task.exclusive_arches:
                excluded_arches = [arch.arch for arch in Arch.query
                                   if arch not in task.exclusive_arches]
            else:
                excluded_arches = [arch.arch for arch in task.excluded_arches]
            # Note that the 'arches' key in the return value is actually the
            # list of *excluded* arches, in spite of its name.
            result.append({'name': task.name, 'arches': excluded_arches})
        return result

    @expose
    @identity.require(identity.not_anonymous())
    def upload(self, task_rpm_name, task_rpm_data):
        """
        Uploads a new task RPM.

        :param task_rpm_name: filename of the task RPM, for example
            ``'beaker-distribution-install-1.10-11.noarch.rpm'``
        :type task_rpm_name: string
        :param task_rpm_data: contents of the task RPM
        :type task_rpm_data: XML-RPC binary
        """
        rpm_path = Task.get_rpm_path(task_rpm_name)
        # we do it here, since we do not want to proceed
        # any further
        if len(task_rpm_name) > 255:
            raise BX("Task RPM name should be <= 255 characters")
        if os.path.exists("%s" % rpm_path):
            raise BX(u'Cannot import duplicate task %s' % task_rpm_name)

        def write_data(f):
            f.write(task_rpm_data.data)
        Task.update_task(task_rpm_name, write_data)
        return "Success"

    @identity.require(identity.in_group('admin'))
    @expose
    def disable_from_ui(self, t_id, *args, **kw):
        to_return = dict( t_id = t_id )
        try:
            self._disable(t_id)
            to_return['success'] = True
        except Exception as e:
            log.exception('Unable to disable task:%s' % t_id)
            to_return['success'] = False
            to_return['err_msg'] = six.text_type(e)
            session.rollback()
        return to_return

    def _disable(self, t_id, *args, **kw):
        """
        disable task
         task.valid=False
         remove task rpms from filesystem
        """
        task = Task.by_id(t_id)
        return task.disable()

    @expose
    def to_xml(self, name, pretty, valid=True):
        """
        Returns task details as xml
        """
        return ensure_str(Task.by_name(name, valid).to_xml(pretty))

    @expose
    def to_dict(self, name, valid=None):
        """
        Returns an XML-RPC structure (dict) with details about the given task.
        """
        return Task.by_name(name, valid).to_dict()
