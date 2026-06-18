
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from bkr.server.database import session
from turbogears import expose, flash, redirect, paginate
from bkr.server.util import url
from sqlalchemy.exc import InvalidRequestError

from bkr.server.xmlrpccontroller import RPCRoot
from bkr.server.widgets import DistroTags, SearchBar
from bkr.server.widgets import TaskSearchForm
from bkr.server.widgets import myPaginateDataGrid
from bkr.server.helpers import make_link
from bkr.server.controller_utilities import restrict_http_method
from bkr.server import search_utility, identity

from bkr.server.model import (OSVersion, Distro, DistroTree,
                              DistroActivity)

from bkr.server.rpc.distros import Distros as DistrosRPC


__all__ = ['Distros']

class Distros(RPCRoot, DistrosRPC):
    # For XMLRPC methods in this class.
    exposed = True

    tag_form = DistroTags(name='tags')

    @expose(template="bkr.server.templates.distro")
    def view(self, id=None, *args, **kw):
        try:
            distro = Distro.by_id(id)
        except InvalidRequestError:
            flash(u"Invalid distro id %s" % id)
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
    @identity.require(identity.has_permission('tag_distro'))
    def save_tag(self, id=None, tag=None, *args, **kw):
        try:
            distro = Distro.by_id(id)
        except InvalidRequestError:
            flash(u"Invalid distro id %s" % id)
            redirect(".")
        if tag['text']:
            distro.tags.append(tag['text'])
            distro.activity.append(DistroActivity(
                    user=identity.current.user, service=u'WEBUI',
                    action=u'Added', field_name=u'Tag',
                    old_value=None, new_value=tag['text']))
        flash(u"Added Tag %s" % tag['text'])
        redirect("./view?id=%s" % id)

    @expose()
    @identity.require(identity.has_permission('tag_distro'))
    @restrict_http_method('post')
    def tag_remove(self, id=None, tag=None, *args, **kw):
        try:
            distro = Distro.by_id(id)
        except InvalidRequestError:
            flash(u"Invalid distro id %s" % id)
            redirect(".")
        if tag:
            for dtag in distro.tags:
                if dtag == tag:
                    distro.tags.remove(dtag)
                    distro.activity.append(DistroActivity(
                            user=identity.current.user, service=u'WEBUI',
                            action=u'Removed', field_name=u'Tag',
                            old_value=tag, new_value=None))
                    flash(u"Removed Tag %s" % tag)
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
                           label=u'Distro Search',    
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

    default = index

# for sphinx
distros = Distros
