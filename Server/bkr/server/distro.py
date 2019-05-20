
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from turbogears.database import session
from turbogears import expose, flash, redirect, paginate, url
from sqlalchemy.exc import InvalidRequestError

import cherrypy

from bkr.server.xmlrpccontroller import RPCRoot
from bkr.server.widgets import DistroTags, SearchBar
from bkr.server.widgets import TaskSearchForm
from bkr.server.widgets import myPaginateDataGrid
from bkr.server.helpers import make_link
from bkr.server.controller_utilities import restrict_http_method
from bkr.server import search_utility, identity
from bkr.common.bexceptions import BX
from bkr.server.bexceptions import DatabaseLookupError

from bkr.server.model import (OSMajor, OSVersion, Distro, DistroTree,
                             DistroTag, DistroActivity)

__all__ = ['Distros']

class Distros(RPCRoot):
    # For XMLRPC methods in this class.
    exposed = True

    tag_form = DistroTags(name='tags')

    @expose(template="bkr.server.templates.distro")
    def view(self, id=None, *args, **kw):
        try:
            distro = Distro.by_id(id)
        except InvalidRequestError:
            flash(_(u"Invalid distro id %s" % id))
            redirect(".")
        is_admin = identity.current.user and identity.current.user.is_admin() or False
        task_form = TaskSearchForm(hidden=dict(distro=True, osmajor_id=True))
        return dict(title       = 'Distro',
                    value       = distro,
                    value_task  = dict(distro_id = distro.id),
                    form        = self.tag_form,
                    form_task   = task_form,
                    action      = './save_tag',
                    action_task = '/tasks/do_search',
                    options   = dict(tags = distro.tags,
                                    readonly = not is_admin))

    @expose()
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

    @expose()
    def get_osmajor(self, distro):
        """ pass in a distro name and get back the osmajor is belongs to.
        """
        try:
            osmajor = '%s' % Distro.by_name(distro).osversion.osmajor
        except DatabaseLookupError:
            raise BX(_('Invalid Distro: %s' % distro))
        return osmajor

    get_family = get_osmajor

    @expose()
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
            raise BX(_('No distros match given filter: %r') % filter)
        return [arch.arch for arch in distro.osversion.arches]

    @expose()
    @identity.require(identity.has_permission('tag_distro'))
    def save_tag(self, id=None, tag=None, *args, **kw):
        try:
            distro = Distro.by_id(id)
        except InvalidRequestError:
            flash(_(u"Invalid distro id %s" % id))
            redirect(".")
        if tag['text']:
            distro.tags.append(tag['text'])
            distro.activity.append(DistroActivity(
                    user=identity.current.user, service=u'WEBUI',
                    action=u'Added', field_name=u'Tag',
                    old_value=None, new_value=tag['text']))
        flash(_(u"Added Tag %s" % tag['text']))
        redirect("./view?id=%s" % id)

    @cherrypy.expose
    @identity.require(identity.has_permission('distro_expire'))
    def expire(self, name, service=u'XMLRPC'):
        distro = Distro.by_name(name)
        distro.expire(service)

    @expose()
    @identity.require(identity.has_permission('tag_distro'))
    @restrict_http_method('post')
    def tag_remove(self, id=None, tag=None, *args, **kw):
        try:
            distro = Distro.by_id(id)
        except InvalidRequestError:
            flash(_(u"Invalid distro id %s" % id))
            redirect(".")
        if tag:
            for dtag in distro.tags:
                if dtag == tag:
                    distro.tags.remove(dtag)
                    distro.activity.append(DistroActivity(
                            user=identity.current.user, service=u'WEBUI',
                            action=u'Removed', field_name=u'Tag',
                            old_value=tag, new_value=None))
                    flash(_(u"Removed Tag %s" % tag))
        redirect("./view?id=%s" % id)

    def _distros(self,distro,**kw):
        return_dict = {}
        if 'simplesearch' in kw:
            simplesearch = kw['simplesearch']
            kw['distrosearch'] = [{'table' : 'Name',
                                   'operation' : 'contains',
                                   'value' : kw['simplesearch']}]
        else:
            simplesearch = None

        return_dict.update({'simplesearch':simplesearch})
        if kw.get("distrosearch"):
            searchvalue = kw['distrosearch']
            distros_found = self._distro_search(distro,**kw)
            return_dict.update({'distros_found':distros_found})
            return_dict.update({'searchvalue':searchvalue})
        return return_dict

    def _distro_search(self,distro,**kw):
        distro_search = search_utility.Distro.search(distro)
        for search in kw['distrosearch']:
            col = search['table']
            distro_search.append_results(search['value'],col,search['operation'],**kw)
        return distro_search.return_results()

    @expose(template="bkr.server.templates.grid")
    @paginate('list',default_order='-date_created', limit=50)
    def index(self,*args,**kw):
        distro_q = session.query(Distro).outerjoin(Distro.osversion, OSVersion.osmajor)\
                .filter(Distro.trees.any(DistroTree.lab_controller_assocs.any()))
        return self.distros(distros=distro_q, *args, **kw)

    @expose(template="bkr.server.templates.grid")
    @paginate('list',default_order='-date_created', limit=50)
    def name(self,*args,**kw):
        distro_q = session.query(Distro).join(Distro.osversion, OSVersion.osmajor)\
                .filter(Distro.trees.any(DistroTree.lab_controller_assocs.any()))\
                .filter(Distro.name.like(kw['name']))
        return self.distros(distros=distro_q, action='./name')

    def distros(self, distros,action='.',*args, **kw):
        distros_return = self._distros(distros,**kw) 
        searchvalue = None
        hidden_fields = None
        search_options = {}
        if distros_return:
            if 'distros_found' in distros_return:
                distros = distros_return['distros_found']
            if 'searchvalue' in distros_return:
                searchvalue = distros_return['searchvalue']
            if 'simplesearch' in distros_return:
                search_options['simplesearch'] = distros_return['simplesearch']

        distros_grid =  myPaginateDataGrid(fields=[
                                  myPaginateDataGrid.Column(name='id', getter=lambda x: make_link(url = '/distros/view?id=%s' % x.id, text = x.id), title='ID', options=dict(sortable=True)),
                                  myPaginateDataGrid.Column(name='name',
                                    getter=lambda x: make_link(url='/distros/view?id=%s' % x.id, text=x.name),
                                    title='Name', options=dict(sortable=True)),
                                  myPaginateDataGrid.Column(name='osversion.osmajor.osmajor', getter=lambda x: x.osversion.osmajor, title='OS Major Version', options=dict(sortable=True)),
                                  myPaginateDataGrid.Column(name='osversion.osminor', getter=lambda x: x.osversion.osminor, title='OS Minor Version', options=dict(sortable=True)),
                                  myPaginateDataGrid.Column(name='date_created',
                                    getter=lambda x: x.date_created,
                                    title='Date Created',
                                    options=dict(sortable=True, datetime=True)),
                              ])

        if 'tag' in kw: 
            hidden_fields = [('tag',kw['tag'])]

        search_bar = SearchBar(name='distrosearch',
                           label=_(u'Distro Search'),    
                           table=search_utility.Distro.search.create_complete_search_table(), 
                           search_controller=url("/get_search_options_distros"), 
                           extra_hiddens=hidden_fields,
                           date_picker=['created']
                           )

        return dict(title="Distros", 
                    grid=distros_grid,
                    search_bar=search_bar,
                    action=action,
                    options=search_options,
                    searchvalue=searchvalue,
                    list=distros)

    #XMLRPC method for listing distros
    @cherrypy.expose
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
                 'distro_version': unicode(distro.osversion),
                 'distro_tags': [unicode(tag) for tag in distro.tags],
                } for distro in distros]

    @cherrypy.expose
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
        distros = Distro.query.filter(Distro.name.like(unicode(name)))
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
                        old_value=unicode(distro.osversion),
                        new_value=unicode(osversion)))
                distro.osversion = osversion
        return edited


    @cherrypy.expose
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

    @cherrypy.expose
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

    default = index

# for sphinx
distros = Distros
