
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import six

from bkr.server.database import session
from bkr.server.model import (OSMajor, OSVersion, Distro, DistroTree,
                              DistroTag, DistroActivity)
from bkr.common.bexceptions import BX
from bkr.server.bexceptions import DatabaseLookupError
from bkr.server import identity
from bkr.server.rpc import expose, register


@register('distros')
class Distros(object):
    # For XMLRPC methods in this class.
    exposed = True

    @expose
    def get_osmajors(self, tags=None):
        """
        Returns a list of all distro families. If *tags* is given, limits to
        distros with at least one of the given tags.
        """
        osmajors = session.query(OSMajor.osmajor)
        if tags:
            osmajors = osmajors\
                .join(OSMajor.osversions, OSVersion.distros, Distro.trees)\
                .filter(DistroTree.lab_controller_assocs.any())\
                .filter(Distro._tags.any(DistroTag.tag.in_(tags)))
        return [osmajor for osmajor, in osmajors.distinct()]

    @expose
    def get_osmajor(self, distro):
        """ pass in a distro name and get back the osmajor is belongs to.
        """
        try:
            osmajor = '%s' % Distro.by_name(distro).osversion.osmajor
        except DatabaseLookupError:
            raise BX('Invalid Distro: %s' % distro)
        return osmajor

    get_family = get_osmajor

    @expose
    def get_arch(self, filter):
        """
        Pass in a dict() with either `distro` or `osmajor` to get possible arches.
        Further supported filters are `variant` and `tags`.
        """
        distros = Distro.query
        if 'distro' in filter:
            distros = distros.filter(Distro.name == filter['distro'])
        if 'osmajor' in filter:
            distros = distros.join(Distro.osversion).join(OSVersion.osmajor)\
                .filter(OSMajor.osmajor == filter['osmajor'])
        if filter.get('variant'):
            distros = distros.join(Distro.trees)\
                .filter(DistroTree.variant == filter['variant'])
        for tag in filter.get('tags', []):
            distros = distros.filter(Distro._tags.any(DistroTag.tag == tag))
        # approximates the behaviour of <distroRequires/>
        distro = distros.order_by(Distro.date_created.desc()).first()
        if distro is None:
            raise BX('No distros match given filter: %r' % filter)
        return [arch.arch for arch in distro.osversion.arches]

    @expose
    @identity.require(identity.has_permission('distro_expire'))
    def expire(self, name, service=u'XMLRPC'):
        distro = Distro.by_name(name)
        distro.expire(service)

    #XMLRPC method for listing distros
    @expose
    def filter(self, filter):
        """
        .. seealso:: :meth:`distrotrees.filter`

        Returns a list of details for distros filtered by the given criteria.

        The *filter* argument must be an XML-RPC structure (dict) specifying
        filter criteria. The following keys are recognised:

            'name'
                Distro name. May include % SQL wildcards, for example
                ``'%20101121.nightly'``.
            'family'
                Distro family name, for example ``'RedHatEnterpriseLinuxServer5'``.
                Matches are exact.
            'distroid'
                Distro id.
                Matches are exact.
            'tags'
                List of distro tags, for example ``['STABLE', 'RELEASED']``. All given
                tags must be present on the distro for it to match.
            'limit'
                Integer limit to number of distros returned.

        The return value is an array with one element per distro (up to the
        maximum number of distros given by 'limit'). Each element is an XML-RPC
        structure (dict) describing a distro.

        .. versionchanged:: 0.9
           Some return columns were removed, because they no longer apply to
           distros in Beaker. Use the new :meth:`distrotrees.filter` method
           to fetch details of distro trees.
        """
        distros = session.query(Distro)
        name = filter.get('name', None)
        family = filter.get('family', None)
        distroid = filter.get('distroid', None)
        tags = filter.get('tags', None) or []
        limit = filter.get('limit', None)
        for tag in tags:
            distros = distros.filter(Distro._tags.any(DistroTag.tag == tag))
        if name:
            distros = distros.filter(Distro.name.like('%s' % name))
        if distroid:
            distros = distros.filter(Distro.id == int(distroid))
        if family:
            distros = distros.join(Distro.osversion, OSVersion.osmajor)
            distros = distros.filter(OSMajor.osmajor == '%s' % family)
        # we only want distros that are active in at least one lab controller
        distros = distros.filter(Distro.trees.any(DistroTree.lab_controller_assocs.any()))
        distros = distros.order_by(Distro.date_created.desc())
        if limit:
            distros = distros[:limit]
        return [{'distro_id': distro.id,
                 'distro_name': distro.name,
                 'distro_version': six.text_type(distro.osversion),
                 'distro_tags': [six.text_type(tag) for tag in distro.tags],
                } for distro in distros]

    @expose
    @identity.require(identity.not_anonymous())
    def edit_version(self, name, version):
        """
        Updates the version for all distros with the given name.

        :param name: name of distros to be updated, for example
            'RHEL5.6-Server-20101110.0'
        :type name: string
        :param version: new version to be applied, for example
            'RedHatEnterpriseLinuxServer5.6' or 'Fedora14'
        :type version: string
        """
        distros = Distro.query.filter(Distro.name.like(six.text_type(name)))
        edited = []

        os_major = version.split('.')[0]

        # Try and split OSMinor
        try:
            os_minor = version.split('.')[1]
        except IndexError:
            os_minor = '0'

        # Try and find OSMajor
        osmajor = OSMajor.lazy_create(osmajor=os_major)

        # Try and find OSVersion
        osversion = OSVersion.lazy_create(osmajor=osmajor, osminor=os_minor)

        # Check each Distro
        for distro in distros:
            if osversion != distro.osversion:
                edited.append('%s' % distro.name)
                distro.activity.append(DistroActivity(user=identity.current.user,
                        service=u'XMLRPC', field_name=u'osversion', action=u'Changed',
                        old_value=six.text_type(distro.osversion),
                        new_value=six.text_type(osversion)))
                distro.osversion = osversion
        return edited


    @expose
    @identity.require(identity.has_permission('tag_distro'))
    def tag(self, name, tag):
        """
        Applies the given tag to all matching distros.

        :param name: distro name to filter by (may include SQL wildcards)
        :type name: string or nil
        :param tag: tag to be applied
        :type tag: string
        :returns: list of distro names which have been modified

        .. versionchanged:: 0.9
           Removed *arch* parameter. Tags apply to distros and not distro trees.
        """
        added = []
        distros = Distro.query.filter(Distro.name.like('%s' % name))
        for distro in distros:
            if tag not in distro.tags:
                added.append('%s' % distro.name)
                distro.activity.append(DistroActivity(
                        user=identity.current.user, service=u'XMLRPC',
                        action=u'Added', field_name=u'Tag',
                        old_value=None, new_value=tag))
                distro.tags.append(tag)
        return added

    @expose
    @identity.require(identity.has_permission('tag_distro'))
    def untag(self, name, tag):
        """
        Like :meth:`distros.tag` but the opposite.
        """
        removed = []
        distros = Distro.query.filter(Distro.name.like('%s' % name))
        for distro in distros:
            if tag in distro.tags:
                removed.append('%s' % distro.name)
                distro.activity.append(DistroActivity(
                        user=identity.current.user, service=u'XMLRPC',
                        action=u'Removed', field_name=u'Tag',
                        old_value=tag, new_value=None))
                distro.tags.remove(tag)
        return removed
