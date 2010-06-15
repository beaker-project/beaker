from turbogears import expose, paginate
from bkr.server.osversion import OSVersions
from bkr.server.widgets import myPaginateDataGrid


class DistroFamily(OSVersions):


    @expose(template="bkr.server.templates.admin_grid")
    @paginate('list',limit=50, default_order='osmajor', allow_limit_override=True)
    def index(self,*args,**kw):        
        kw['grid'] = myPaginateDataGrid(fields=[
                                  myPaginateDataGrid.Column(name='osmajor', getter=lambda x: x, title='OS Version', options=dict(sortable=True)),
                                  myPaginateDataGrid.Column(name='arches', getter=lambda x: " ".join([arch.arch for arch in x.arches]), title='Arches', options=dict(sortable=True)), 
                              ])
        return super(DistroFamily,self).index(*args,**kw)

