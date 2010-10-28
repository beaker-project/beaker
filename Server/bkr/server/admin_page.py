from turbogears import url
from turbogears.database import session
from turbogears.widgets import AutoCompleteField, TableForm
from bkr.server.xmlrpccontroller import RPCRoot
from bkr.server.bexceptions import BeakerException
from bkr.server.widgets import AlphaNavBar

class AdminPage(RPCRoot):
    exposed = False

    def __init__(self,**kw):
        if 'search_name' in kw:
            self.search_name = kw['search_name']
        else:
            self.search_name = 'default'

        if 'search_url' in kw:
            self.search_url = kw['search_url']
        else:
            raise BeakerException('%s does not specify a search_url' % self.__class__.__name__)

        if 'search_param' in kw:
            self.search_param = kw['search_param']
        else:
            self.search_param = "input"

        if 'result_name' in kw:
            self.result_name = kw['result_name']
        else:
            self.result_name = 'matches'

        if 'widget_action' in kw:
            self.widget_action = kw['widget_action']
        else:
            self.widget_action = '.'
 
        self.search_auto = AutoCompleteField(name=self.search_name,
                                                search_controller = url(self.search_url),
                                                search_param = self.search_param,
                                                result_name = self.result_name)
        self.search_widget_form = TableForm('Search', fields=[self.search_auto], action=self.widget_action, submit_text=_(u'Search'),) 
        if getattr(self,'join',None) is None:
            self.join = []
        self.add = True

    def _build_nav_bar(self, query_data, name):
        return AlphaNavBar(query_data,name)

    def process_search(self,*args,**kw): 
        q = session.query(self.search_mapper)
        for j in self.join: 
            q = q.join(j) 
        s_name = self.search_name 
        if s_name in kw:
            if 'text' in kw[s_name]:
                
                if 'starts_with' in kw[s_name]['text']:
                    q = q.filter(self.search_col.like('%s%%' % kw[s_name]['text']['starts_with']))
                else: 
                    q = q.filter(self.search_col == kw[s_name]['text'])
                
        return q 
