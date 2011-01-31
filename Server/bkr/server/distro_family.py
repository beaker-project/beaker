from turbogears import expose, paginate
from bkr.server.osversion import OSVersions
from bkr.server.widgets import myPaginateDataGrid


class DistroFamily(OSVersions):
 
    @expose(template="bkr.server.templates.grid") 
    @paginate('list',limit=50, default_order='osmajor.osmajor')
    def index(self,*args,**kw): 
        template_data = self.osversions(*args, **kw)
        template_data['search_bar'] = None
        template_data['grid'] = myPaginateDataGrid(fields=[
                                  myPaginateDataGrid.Column(name='osmajor.osmajor', getter=lambda x: x.osmajor, title='OS Major', options=dict(sortable=True)),
                                  myPaginateDataGrid.Column(name='osminor', getter=lambda x: x.osminor, title='OS Minor', options=dict(sortable=True)),
                                  myPaginateDataGrid.Column(name='arches', getter=lambda x: " ".join([arch.arch for arch in x.arches]), title='Arches', options=dict(sortable=True)), 
                              ])
        return template_data
