
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import urlparse
import cherrypy
import os
from kid import Element
from sqlalchemy.sql import exists
from sqlalchemy.orm import contains_eager
from sqlalchemy.orm.exc import NoResultFound
from turbogears import expose, flash, redirect, paginate
from bkr.server.model import session, DistroTree, Distro, OSVersion, OSMajor, \
        LabController, LabControllerDistroTree, DistroTreeActivity, \
        Arch, DistroTag
from bkr.server.widgets import TaskSearchForm, myPaginateDataGrid, SearchBar, \
        DistroTreeInstallOptionsWidget, DeleteLinkWidgetForm
from bkr.server.helpers import make_link
from bkr.server.controller_utilities import Utility, restrict_http_method
from bkr.server.xmlrpccontroller import RPCRoot
from bkr.server import search_utility, needpropertyxml, identity

__all__ = ['DistroTrees']

class DistroTrees(RPCRoot):
    # For XMLRPC methods in this class.
    exposed = True
    delete_link = DeleteLinkWidgetForm()

    @expose(template='bkr.server.templates.grid')
    @paginate('list', default_order='-date_created', limit=50)
    def index(self, **kwargs):
        query = DistroTree.query.join(DistroTree.distro, Distro.osversion, OSVersion.osmajor)\
                .filter(DistroTree.lab_controller_assocs.any())
        options = {}
        if 'simplesearch' in kwargs:
            kwargs['search'] = [{'table': 'Name',
                    'operation': 'contains',
                    'value': kwargs['simplesearch']}]
            options['simplesearch'] = kwargs['simplesearch']
        if 'search' in kwargs:
            search = search_utility.DistroTree.search(query)
            for row in kwargs['search']:
                search.append_results(row['value'], row['table'], row['operation'])
            query = search.return_results()

        grid = myPaginateDataGrid(fields=[
            myPaginateDataGrid.Column(name='id', title=u'ID',
                    getter=lambda x: make_link(url=str(x.id), text=str(x.id)),
                    options=dict(sortable=True)),
            myPaginateDataGrid.Column(name='distro.name', title=u'Distro',
                    getter=lambda x: x.distro.link,
                    options=dict(sortable=True)),
            myPaginateDataGrid.Column(name='variant', title=u'Variant',
                    options=dict(sortable=True)),
            myPaginateDataGrid.Column(name='arch.arch', title=u'Arch',
                    options=dict(sortable=True)),
            myPaginateDataGrid.Column(name='distro.osversion.osmajor.osmajor',
                    title=u'OS Major Version',
                    options=dict(sortable=True)),
            myPaginateDataGrid.Column(name='distro.osversion.osminor',
                    title=u'OS Minor Version',
                    options=dict(sortable=True)),
            myPaginateDataGrid.Column(name='date_created', title=u'Date Created',
                    options=dict(sortable=True, datetime=True)),
            Utility.direct_column(title=u'Provision', getter=self._provision_system_link),
        ])

        search_bar = SearchBar(name='search',
                label=_(u'Distro Tree Search'),
                table=search_utility.DistroTree.search.create_complete_search_table(),
                search_controller=None,
                date_picker=['created'],
                )

        return dict(title=u'Distro Trees',
                    action='.',
                    grid=grid,
                    search_bar=search_bar,
                    searchvalue=kwargs.get('search'),
                    options=options,
                    list=query)

    def _provision_system_link(self, distro_tree):
        return make_link('/reserveworkflow/?distro_tree_id=%s'
                % distro_tree.id, 'Provision', elem_class='btn')

    @expose(template='bkr.server.templates.distrotree')
    def default(self, id, *args, **kwargs):
        try:
            distro_tree = DistroTree.by_id(int(id))
        except (ValueError, NoResultFound):
            raise cherrypy.NotFound(id)
        form_task = TaskSearchForm(action='/tasks/do_search',
                hidden=dict(arch_id=True, distro=True, osmajor_id=True),
                options=dict())
        lab_controllers = LabController.query.filter_by(removed=None)\
                .order_by(LabController.fqdn).all()
        lab_controller_assocs = dict((lab_controller,
                sorted((lca for lca in distro_tree.lab_controller_assocs
                        if lca.lab_controller == lab_controller),
                       key=lambda lca: lca.url))
                for lab_controller in lab_controllers)
        is_admin = identity.current.user and identity.current.user.is_admin() or False
        return dict(title='Distro Tree',
                    value=distro_tree,
                    install_options_widget=DistroTreeInstallOptionsWidget(),
                    form_task=form_task,
                    delete_link=self.delete_link,
                    lab_controllers=lab_controllers,
                    lab_controller_assocs=lab_controller_assocs,
                    readonly=not is_admin)

    @expose(content_type='text/plain')
    def yum_config(self, distro_tree_id, *args, **kwargs):
        # Ignore positional args, so that we can make nice URLs like
        # /distrotrees/yum_config/12345/RHEL-6.2-Server-i386.repo
        try:
            distro_tree = DistroTree.by_id(int(distro_tree_id))
        except (ValueError, NoResultFound):
            raise cherrypy.NotFound(distro_tree_id)
        if not kwargs.get('lab'):
            lc = distro_tree.lab_controller_assocs[0].lab_controller
        else:
            try:
                lc = LabController.by_name(kwargs['lab'])
            except NoResultFound:
                raise cherrypy.HTTPError(status=400,
                        message='No such lab controller %r' % kwargs['lab'])
        base = distro_tree.url_in_lab(lc, scheme='http')
        if not base:
            raise cherrypy.HTTPError(status=404,
                    message='%s is not present in lab %s' % (distro_tree, lc))
        if not distro_tree.repos:
            return '# No repos for %s' % distro_tree
        sections = []
        for repo in distro_tree.repos:
            sections.append('''[%s]
name=%s
baseurl=%s
enabled=1
gpgcheck=0
''' % (repo.repo_id, repo.repo_id, urlparse.urljoin(base, repo.path)))
        return '\n'.join(sections)

    @expose()
    @identity.require(identity.in_group('admin'))
    def lab_controller_add(self, distro_tree_id, lab_controller_id, url):
        try:
            distro_tree = DistroTree.by_id(distro_tree_id)
        except NoResultFound:
            flash(_(u'Invalid distro tree id %s') % distro_tree_id)
            redirect('.')
        try:
            lab_controller = LabController.by_id(lab_controller_id)
        except ValueError:
            flash(_(u'Invalid lab controller id %s') % lab_controller_id)
            redirect(str(distro_tree.id))

        # make sure the url ends with /
        url = os.path.join(url.strip(),'')
        try:
            self.add_distro_urls(distro_tree, lab_controller, [url])
        except ValueError as e:
            flash(_(u'%s') % e)
            redirect(str(distro_tree.id))

        flash(_(u'Changed/Added %s %s') % (lab_controller, url))
        redirect(str(distro_tree.id))

    @expose()
    @identity.require(identity.in_group('admin'))
    @restrict_http_method('post')
    def lab_controller_remove(self, id):
        try:
            lca = LabControllerDistroTree.by_id(id)
        except NoResultFound:
            flash(_(u'Invalid lab_controller_assoc id %s') % id)
            redirect('.')

        session.delete(lca)
        lca.distro_tree.activity.append(DistroTreeActivity(
                user=identity.current.user, service=u'WEBUI',
                action=u'Removed', field_name=u'lab_controller_assocs',
                old_value=u'%s %s' % (lca.lab_controller, lca.url),
                new_value=None))
        flash(_(u'Deleted %s %s') % (lca.lab_controller, lca.url))
        redirect(str(lca.distro_tree.id))

    @expose()
    @identity.require(identity.in_group('admin'))
    def install_options(self, distro_tree_id, **kwargs):
        try:
            distro_tree = DistroTree.by_id(distro_tree_id)
        except NoResultFound:
            flash(_(u'Invalid distro tree id %s') % distro_tree_id)
            redirect('.')
        if 'ks_meta' in kwargs:
            distro_tree.activity.append(DistroTreeActivity(
                    user=identity.current.user, service=u'WEBUI',
                    action=u'Changed', field_name=u'InstallOption:ks_meta',
                    old_value=distro_tree.ks_meta,
                    new_value=kwargs['ks_meta']))
            distro_tree.ks_meta = kwargs['ks_meta']
        if 'kernel_options' in kwargs:
            distro_tree.activity.append(DistroTreeActivity(
                    user=identity.current.user, service=u'WEBUI',
                    action=u'Changed', field_name=u'InstallOption:kernel_options',
                    old_value=distro_tree.kernel_options,
                    new_value=kwargs['kernel_options']))
            distro_tree.kernel_options = kwargs['kernel_options']
        if 'kernel_options_post' in kwargs:
            distro_tree.activity.append(DistroTreeActivity(
                    user=identity.current.user, service=u'WEBUI',
                    action=u'Changed', field_name=u'InstallOption:kernel_options_post',
                    old_value=distro_tree.kernel_options_post,
                    new_value=kwargs['kernel_options_post']))
            distro_tree.kernel_options_post = kwargs['kernel_options_post']
        flash(_(u'Updated install options'))
        redirect(str(distro_tree.id))

    @staticmethod
    def add_distro_urls(distro_tree, lab_controller, urls):
        """
        Adds supplied URLs to specific distro tree under specific lab controller.
        Old URL will be replaced if new URL uses the same scheme
        """
        new_urls_by_scheme = dict(
            (urlparse.urlparse(url, scheme=None).scheme, url) for url in urls)
        if None in new_urls_by_scheme:
            raise ValueError('URL %r is not absolute' % new_urls_by_scheme[None])
        for lca in distro_tree.lab_controller_assocs:
            if lca.lab_controller == lab_controller:
                scheme = urlparse.urlparse(lca.url).scheme
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
    @cherrypy.expose
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
                 'distro_osversion': unicode(dt.distro.osversion),
                 'distro_osmajor' : unicode(dt.distro.osversion.osmajor),
                 'distro_tags': [unicode(tag) for tag in dt.distro.tags],
                 'arch': unicode(dt.arch),
                 'variant': dt.variant,
                 'images' : [(unicode(image.image_type), image.path) for image in dt.images],
                 'kernel_options': dt.kernel_options or u'',
                 'kernel_options_post': dt.kernel_options_post or u'',
                 'ks_meta': dt.ks_meta or u'',
                 'available': [(lca.lab_controller.fqdn, lca.url) for lca in dt.lab_controller_assocs],
                } for dt in query]

# for sphinx
distrotrees = DistroTrees
