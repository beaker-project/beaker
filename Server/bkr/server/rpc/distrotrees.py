
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from sqlalchemy.sql import exists
from sqlalchemy.orm import contains_eager

import six
from six.moves import urllib

from bkr.server.model import DistroTree, Distro, OSVersion, OSMajor, \
        LabController, LabControllerDistroTree, DistroTreeActivity, \
        Arch, DistroTag
from bkr.server import needpropertyxml, identity
from bkr.server.rpc import expose, register


@register('distrotrees')
class DistroTrees(object):
    # For XMLRPC methods in this class.
    exposed = True

    @staticmethod
    def add_distro_urls(distro_tree, lab_controller, urls):
        """
        Adds supplied URLs to specific distro tree under specific lab controller.
        Old URL will be replaced if new URL uses the same scheme
        """
        unrecognized_scheme = ''
        new_urls_by_scheme = dict(
            (urllib.parse.urlparse(url, scheme=unrecognized_scheme).scheme, url) for url in urls)

        if unrecognized_scheme in new_urls_by_scheme:
            raise ValueError('URL %s is not absolute' % new_urls_by_scheme[unrecognized_scheme])

        for lca in distro_tree.lab_controller_assocs:
            if lca.lab_controller == lab_controller:
                scheme = urllib.parse.urlparse(lca.url).scheme
                new_url = new_urls_by_scheme.pop(scheme, None)
                # replace old url if it's the same scheme
                if new_url is not None and lca.url != new_url:
                    distro_tree.activity.append(DistroTreeActivity(
                        user=identity.current.user, service=u'XMLRPC',
                        action=u'Changed', field_name=u'lab_controller_assocs',
                        old_value=u'%s %s' % (lca.lab_controller, lca.url),
                        new_value=u'%s %s' % (lca.lab_controller, new_url)))
                    lca.url = new_url
        for url in new_urls_by_scheme.values():
            distro_tree.lab_controller_assocs.append(LabControllerDistroTree(
                lab_controller=lab_controller, url=url))
            distro_tree.activity.append(DistroTreeActivity(
                user=identity.current.user, service=u'XMLRPC',
                action=u'Added', field_name=u'lab_controller_assocs',
                old_value=None, new_value=u'%s %s' % (lab_controller, url)))

    # XMLRPC method for listing distro trees
    @expose
    def filter(self, filter):
        """
        Returns a list of details for distro trees filtered by the given criteria.

        The *filter* argument must be an XML-RPC structure (dict) specifying
        filter criteria. The following keys are recognised:

            'name'
                Distro name. May include % SQL wildcards, for example
                ``'%20101121.nightly'``.
            'family'
                Distro family name, for example ``'RedHatEnterpriseLinuxServer5'``.
                Matches are exact.
            'tags'
                List of distro tags, for example ``['STABLE', 'RELEASED']``. All given
                tags must be present on the distro for it to match.
            'arch'
                Architecture name, for example ``'x86_64'``.
            'treepath'
                Tree path (on any lab controller). May include % SQL wildcards, for
                example ``'nfs://nfs.example.com:%'``.
            'labcontroller'
                FQDN of lab controller. Limit to distro trees which are
                available on this lab controller. May include % SQL wildcards.
            'distro_id'
                Distro id.
                Matches are exact.
            'distro_tree_id'
                Distro Tree id.
                Matches are exact.
            'xml'
                XML filter criteria in the same format allowed inside
                ``<distroRequires/>`` in a job, for example
                ``<or><distro_tag value="RELEASED"/><distro_tag value="STABLE"/></or>``.
            'limit'
                Integer limit to number of distro trees returned.

        The return value is an array with one element per distro (up to the
        maximum number of distros given by 'limit'). Each element is an XML-RPC
        structure (dict) describing a distro tree.

        .. versionadded:: 0.9
        """
        query = DistroTree.query\
                .join(DistroTree.distro, Distro.osversion, OSVersion.osmajor)\
                .join(DistroTree.arch)\
                .options(contains_eager(DistroTree.distro),
                    contains_eager(DistroTree.arch))
        name = filter.get('name', None)
        family = filter.get('family', None)
        tags = filter.get('tags', None) or []
        arch = filter.get('arch', None)
        distro_id = filter.get('distro_id', None)
        distro_tree_id = filter.get('distro_tree_id', None)
        treepath = filter.get('treepath', None)
        labcontroller = filter.get('labcontroller', None)
        xml = filter.get('xml', None)
        limit = filter.get('limit', None)
        for tag in tags:
            query = query.filter(Distro._tags.any(DistroTag.tag == tag))
        if name:
            query = query.filter(Distro.name.like('%s' % name))
        if family:
            query = query.filter(OSMajor.osmajor == '%s' % family)
        if arch:
            if isinstance(arch, list):
                query = query.filter(Arch.arch.in_(arch))
            else:
                query = query.filter(Arch.arch == '%s' % arch)
        if distro_id:
            query = query.filter(Distro.id == int(distro_id))
        if distro_tree_id:
            query = query.filter(DistroTree.id == int(distro_tree_id))
        if treepath:
            query = query.filter(DistroTree.lab_controller_assocs.any(
                    LabControllerDistroTree.url.like('%s' % treepath)))
        elif labcontroller:
            query = query.filter(exists([1],
                    from_obj=[LabControllerDistroTree.__table__.join(LabController.__table__)])
                    .where(LabControllerDistroTree.distro_tree_id == DistroTree.id)
                    .where(LabController.fqdn.like(labcontroller)))
        else:
            # we only want distro trees that are active in at least one lab controller
            query = query.filter(DistroTree.lab_controller_assocs.any())
        if xml:
            query = needpropertyxml.apply_distro_filter('<and>%s</and>' % xml, query)
        query = query.order_by(DistroTree.date_created.desc())
        if limit:
            query = query[:limit]
        return [{'distro_tree_id': dt.id,
                 'distro_id': dt.distro.id,
                 'distro_name': dt.distro.name,
                 'distro_osversion': six.text_type(dt.distro.osversion),
                 'distro_osmajor' : six.text_type(dt.distro.osversion.osmajor),
                 'distro_tags': [six.text_type(tag) for tag in dt.distro.tags],
                 'arch': six.text_type(dt.arch),
                 'variant': dt.variant,
                 'images' : [(six.text_type(image.image_type), image.path) for image in dt.images],
                 'kernel_options': dt.kernel_options or u'',
                 'kernel_options_post': dt.kernel_options_post or u'',
                 'ks_meta': dt.ks_meta or u'',
                 'available': [(lca.lab_controller.fqdn, lca.url) for lca in dt.lab_controller_assocs],
                } for dt in query]
