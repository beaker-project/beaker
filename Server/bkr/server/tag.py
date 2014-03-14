
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from turbogears.database import session
from turbogears import expose, widgets, paginate
from bkr.server.xmlrpccontroller import RPCRoot
from bkr.server.helpers import make_link

from bkr.server.model import DistroTag

# Validation Schemas

class Tags(RPCRoot):
    # For XMLRPC methods in this class.
    exposed = True

    @expose(format='json')
    def by_tag(self, tag, *args, **kw):
        tag = tag.lower()
        search = DistroTag.list_by_tag(tag)
        tags = [match.tag for match in search]
        return dict(tags=tags)

    @expose(template="bkr.server.templates.grid")
    @paginate('list',default_order='tag',limit=50)
    def index(self):
        tags = session.query(DistroTag)
        tags_grid = widgets.PaginateDataGrid(fields=[
                                  widgets.PaginateDataGrid.Column(name='tag', getter=lambda x: make_link(url  = '../distros/tagsearch/?tag=%s' % x.tag,
                                  text = x.tag), title='Tag', options=dict(sortable=True)),
                              ])
        return dict(title="Tags", grid = tags_grid,
                                         search_bar = None,
                                         list = tags)

    default = index
